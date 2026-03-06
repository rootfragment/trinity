#!/usr/bin/env python3
import subprocess
import re
import os
import sys
import socket
import json    
import time
import argparse
import signal
import threading


syscall_monitor_thread = None
syscall_tampering_detected = threading.Event()
syscall_currently_hooked = False

def display_banner():
    banner = r"""
          ___      .______        _______  __    __       _______.
         /   \     |   _  \      /  _____||  |  |  |     /       |
        /  ^  \    |  |_)  |    |  |  __  |  |  |  |    |   (----`
       /  /_\  \   |      /     |  | |_ | |  |  |  |     \   \    
      /  _____  \  |  |\  \----.|  |__| | |  `--'  | .----)   |   
     /__/     \__\ | _| `._____| \______|  \______/  |_______/    
                                                                  
                                          
    -- Linux Rootkit Detection Framework --
    """
    print(banner)
    
    
CONFIG_FILE = "config.json"
DEFAULT_CONFIG = {
    "listener_list":[
        {
        "ip" : "127.0.0.1",
        "port" : 12345,
        "enabled" : True,
        }
    ]
}
def create_config():
    is_sudo = os.getuid() == 0 and 'SUDO_UID' in os.environ
    try:
        if is_sudo:
            orginal_uid = int(os.environ['SUDO_UID'])
            orginal_gid = int(os.environ['SUDO_GID'])
            root_euid = os.geteuid()
            root_egid = os.getegid()
            
            try:
                os.setegid(orginal_gid)
                os.seteuid(orginal_uid)
                with open(CONFIG_FILE , "w") as f:
                    json.dump(DEFAULT_CONFIG, f, indent=4)
            except OSError as e:
                print(f"[!] Error : Could not create config file for the user {orginal_uid} : {e}")
            finally:
                os.seteuid(root_euid)
                os.setegid(root_egid)
        else:
            with open(CONFIG_FILE, "w") as f:   
                json.dump(DEFAULT_CONFIG, f, indent=4)
        print("[*] Created a sample config file since no configuration file was found. Edit the file and rerun the program")
    except OSError as e:
        print(f,"[x] Error : Could not create config file : {e}")
    except KeyError:
        print("[x] Error : SUDO_UID or SUDO_GID not found in environment. Cannot determine the user.")
    sys.exit(0)
        
    
def load_config():
    if not os.path.exists(CONFIG_FILE):
        create_config()
    with open(CONFIG_FILE,"r") as f:
        return json.load(f)
        
        

def send_udp_alert(findings, config):
    if not findings:
        return
    message = "\n".join(findings)
    sent_count = 0
    for listener in config.get("listener_list", []):
        if not listener.get("enabled", False):
            continue
        ip = listener["ip"]
        port = listener["port"]
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
                s.sendto(message.encode('utf-8'), (ip, port))
            sent_count += 1
        except Exception as e:
            print(f"[!] UDP send failed ({ip}:{port}): {e}")
    if sent_count > 0:
        print(f"[+] UDP alert sent to {sent_count} listener(s).")
        

PROC_SYSCALLS_FILE = "/proc/rk_syscalls"
PROC_FS_FILE = "/proc/rk_fs"
DIR_LIST_FILE = "dir_list.txt"

def create_dir_list():
    try:
        if not os.path.exists(DIR_LIST_FILE):
            with open(DIR_LIST_FILE, "w") as f:
                f.write("# Add directories to scan (one per line)\n/bin\n/usr/bin\n/sbin\n")
            
            # Try to set ownership if running as root
            sudo_uid = os.environ.get("SUDO_UID")
            sudo_gid = os.environ.get("SUDO_GID")
            if sudo_uid and sudo_gid:
                os.chown(DIR_LIST_FILE, int(sudo_uid), int(sudo_gid))
            
            print(f"[*] Created '{DIR_LIST_FILE}' template. Please edit it and rerun the scan.")
            return False
    except Exception as e:
        print(f"[x] Error creating '{DIR_LIST_FILE}': {e}")
    return True

def get_user_fs_view(directory):
    view = {}
    try:
        for entry in os.scandir(directory):
            try:
                s = entry.stat(follow_symlinks=True)
                path = os.path.normpath(entry.path)
                view[path] = {
                    "inode": s.st_ino,
                    "size": s.st_size,
                    "mode": s.st_mode,
                    "uid": s.st_uid,
                    "gid": s.st_gid
                }
            except Exception:
                continue
    except Exception as e:
        print(f"[x] Error gathering user-space view of '{directory}': {e}")
    return view

def get_kernel_fs_view(directory):
    view = {}
    try:
        # Write path to proc file
        with open(PROC_FS_FILE, 'w') as f:
            f.write(directory)
        
        # Read results
        with open(PROC_FS_FILE, 'r') as f:
            for line in f:
                line = line.strip()
                if not line or "|" not in line:
                    continue

                # Split path from metadata
                parts = line.rsplit("|", 5)
                if len(parts) < 6:
                    continue

                path = os.path.normpath(parts[0].strip())
                meta = {}
                for field in parts[1:]:
                    field = field.strip()
                    if "=" not in field:
                        continue
                    k, v = field.split("=")
                    if k == "mode":
                        meta[k] = int(v, 8)  # parse octal
                    else:
                        meta[k] = int(v)

                if all(k in meta for k in ["inode", "size", "mode", "uid", "gid"]):
                    view[path] = meta
    except Exception as e:
        print(f"[x] Error gathering kernel-space view of '{directory}': {e}")
    return view

def run_fs_scan():
    print("\n" + "="*25)
    print("  Running Filesystem Scan")
    print("="*25)
    
    if not os.path.exists(PROC_FS_FILE):
        print(f"[!] Kernel proc file '{PROC_FS_FILE}' not found. Is the kernel module loaded?")
        return []

    if not os.path.exists(DIR_LIST_FILE):
        create_dir_list()
        return []

    all_findings = []
    
    try:
        with open(DIR_LIST_FILE, "r") as f:
            directories = [line.strip() for line in f if line.strip() and not line.startswith("#")]
        
        if not directories:
            print(f"[!] '{DIR_LIST_FILE}' is empty. Add directories to scan.")
            return []

        for path in directories:
            if not os.path.isdir(path):
                print(f"[!] Skipping '{path}': Not a valid directory.")
                continue

            print(f"\n[*] Scanning directory: {path}")
            user_view = get_user_fs_view(path)
            kernel_view = get_kernel_fs_view(path)
            
            # Files seen by kernel but not by user
            hidden = set(kernel_view.keys()) - set(user_view.keys())
            if hidden:
                print(f"  [!] Files hidden from user-space in '{path}':")
                for f in sorted(hidden):
                    finding = f"Hidden File: {f}"
                    print(f"    -> {finding}")
                    all_findings.append(finding)
                    
            # Files seen by user but not by kernel (phantom)
            phantom = set(user_view.keys()) - set(kernel_view.keys())
            if phantom:
                print(f"  [!] Files missing from kernel view in '{path}':")
                for f in sorted(phantom):
                    finding = f"Phantom File: {f}"
                    print(f"    -> {finding}")
                    all_findings.append(finding)

            # Metadata mismatches
            mismatches = []
            for f in set(user_view.keys()) & set(kernel_view.keys()):
                if user_view[f] != kernel_view[f]:
                    mismatches.append(f)
                    
            if mismatches:
                print(f"  [!] Metadata mismatches in '{path}':")
                for f in sorted(mismatches):
                    finding = f"Metadata Mismatch: {f}"
                    print(f"    -> {finding}")
                    all_findings.append(finding)

            if not hidden and not phantom and not mismatches:
                print(f"  [+] No discrepancies found in '{path}'.")

    except Exception as e:
        print(f"[x] Error during filesystem scan: {e}")

    if all_findings:
        print(f"\n[!] Total filesystem anomalies detected: {len(all_findings)}")

    print("\n" + "="*25)
    print("  Filesystem Scan Complete")
    print("="*25)
    return all_findings

def handle_syscall_tampering(hooked_syscall_details: list[str], config, interactive: bool):
    findings_messages = []
    for detail in hooked_syscall_details:
        original, new = [s.strip() for s in detail.split('|')]
        findings_messages.append(f"Syscall integrity compromised: '{original}' hooked with '{new}'")
    
    
    send_udp_alert(findings_messages, config)

    if interactive:
        
        print("\033[1m\nCRITICAL BREACH: Syscall integrity failed! Syscall hooks detected for the given syscalls:\033[0m")
        for detail in hooked_syscall_details:
            original, new = [s.strip() for s in detail.split('|')]
            print(f"  -> Original: {original}, Hooked with: {new}")

        while True:
            choice = input("\nDo you want to continue to the menu? (y/n): ").lower().strip()
            if choice == 'y':
                print("Continuing to main menu...")
                break
            elif choice == 'n':
                print("Exiting.")
                sys.exit(0)
            else:
                print("Invalid choice. Please enter 'y' or 'n'.")

def check_syscall_integrity(config, interactive: bool, is_background_check: bool = False):
    global syscall_currently_hooked

    findings = []

    if not os.path.exists(PROC_SYSCALLS_FILE):
        if not is_background_check:
            print(f"[!] Kernel proc file '{PROC_SYSCALLS_FILE}' not found. Is the kernel module loaded?", file=sys.stderr)
        return findings

    try:
        with open(PROC_SYSCALLS_FILE, 'r') as f:
            lines = f.readlines()
    except Exception as e:
        if not is_background_check:
            print(f"[x] Error reading {PROC_SYSCALLS_FILE}: {e}", file=sys.stderr)
        return findings

    if not lines:
        return findings

    status = lines[0].strip()

    if is_background_check:

        if status == "-1":
            if not syscall_currently_hooked:
                syscall_currently_hooked = True
                syscall_tampering_detected.set()

        elif status == "0":
            syscall_currently_hooked = False

        return []

    if status == "-1":
        hooked_syscall_details = [line.strip() for line in lines[1:] if line.strip()]

        if hooked_syscall_details:
            handle_syscall_tampering(hooked_syscall_details, config, interactive)

            for detail in hooked_syscall_details:
                original, new = [s.strip() for s in detail.split('|')]
                findings.append(f"Syscall Integrity: Original '{original}' hooked with '{new}'")

    return findings

    
def get_ps_processes():
    try:
        ps_output = subprocess.check_output(["ps", "-e", "-o", "pid=,comm="]).decode()
        ps_dict = {}
        for line in ps_output.strip().splitlines():
            parts = line.strip().split(maxsplit=1)
            if len(parts) == 2:
                pid, cmd = parts
                ps_dict[pid.strip()] = cmd.strip()
        return ps_dict
    except FileNotFoundError:
        print("[!] 'ps' command not found. Is this a standard Linux environment?")
        return {}
    except Exception as e:
        print(f"[x] Error running 'ps': {e}")
        return {}
        
        
def get_kernel_processes(proc_file="/proc/rk_ps"):
    ker_dict = {}
    try:
        with open(proc_file, "r") as f:
            for line in f:
                parts = line.strip().split(maxsplit=1)
                if not parts:
                    continue
                pid = parts[0]
                cmd = parts[1] if len(parts) > 1 else "?"
                ker_dict[pid] = cmd
        return ker_dict
    except FileNotFoundError:
        print(f"[!] Kernel proc file '{proc_file}' not found. Is the kernel module loaded?")
        return None
    except Exception as e:
        print(f"[x] Error reading {proc_file}: {e}")
        return None
        
        
def run_process_scan():
    print("\n" + "="*20)
    print("  Running Process Scan")
    print("="*20)
    ps_process = get_ps_processes()
    kern_process = get_kernel_processes()
    if kern_process is None:
        return []
    missing_ps = set(kern_process.keys()) - set(ps_process.keys())
    findings = []
    if missing_ps:
        print("\n[!] Processes found by kernel but hidden from 'ps' (potential rootkit activity):")
        for pid in sorted(missing_ps, key=int):
            finding = f"Hidden Process: PID {pid:<6} {kern_process[pid]}"
            print(f"  -> {finding}")
            findings.append(finding)
    else:
        print("\n[+] No processes appear to be hidden from 'ps'.")
    print("\n" + "="*25)
    print("  Process Scan Complete")
    print("="*25)
    return findings
    
    
def get_user_modules(proc_file="/proc/modules"):
    user_view = set()
    try:
        with open(proc_file) as f:
            for line in f:
                if not line.strip():
                    continue
                mod_name = line.split()[0]
                user_view.add(mod_name)
        return user_view
    except FileNotFoundError:
        print(f"[!] Could not open '{proc_file}'.")
        return None
    except Exception as e:
        print(f"[x] Error reading {proc_file}: {e}")
        return None
        
        
def get_kernel_modules(proc_file="/proc/rk_mods"):
    kern_view = set()
    try:
        with open(proc_file) as f:
            for line in f:
                if not line.strip():
                    continue
                mod_name = line.split()[0]
                kern_view.add(mod_name)
        return kern_view
    except FileNotFoundError:
        print(f"[!] Kernel proc file '{proc_file}' not found. Is the kernel module loaded?")
        return None
    except Exception as e:
        print(f"[x] Error reading {proc_file}: {e}")
        return None
        
        
def run_module_scan():
    print("\n" + "="*25)
    print("  Running Module Scan")
    print("="*25)
    user_view = get_user_modules()
    kern_view = get_kernel_modules()
    if user_view is None or kern_view is None:
        return []
    hidden_mods = kern_view - user_view
    findings = []
    if hidden_mods:
        print("\n[!] Kernel modules hidden from 'lsmod' (strong indicator of LKM rootkit):")
        for mod in sorted(hidden_mods):
            finding = f"Hidden Module: {mod}"
            print(f"  -> {finding}")
            findings.append(finding)
    else:
        print("\n[+] No hidden kernel modules detected.")
    print("\n" + "="*25)
    print("  Module Scan Complete")
    print("="*25)
    return findings
    
    
def get_kernel_ports(proc_file="/proc/rk_sockets"):
    kernel_ports = set()
    port_map = {}
    try:
        with open(proc_file, "r") as f:
            data = f.read()
            entries = re.findall(r"pid=(\d+)\s+comm=([\w\-\.\/]+)\s+sport=(\d+)", data)
            for pid, comm, port in entries:
                port_num = int(port)
                kernel_ports.add(port_num)
                port_map[port_num] = (pid, comm)
    except FileNotFoundError:
        print(f"[!] Kernel proc file '{proc_file}' not found. Is the kernel module loaded?")
        return None, {}
    except Exception as e:
        print(f"[x] Error reading {proc_file}: {e}")
        return None, {}
    return kernel_ports, port_map
    
    
def get_userspace_ports():
    userspace_ports = set()
    try:
        result = subprocess.run(["ss", "-ltunp"], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        ports = re.findall(r":(\d+)\s", result.stdout)
        for p in ports:
            userspace_ports.add(int(p))
    except FileNotFoundError:
        print("[!] 'ss' command not found. Is this a standard Linux environment?")
        return set()
    except Exception as e:
        print(f"[x] Error fetching userspace ports with 'ss': {e}")
        return set()
    return userspace_ports
    
    
def run_port_scan():
    print("\n" + "="*25)
    print("  Running Port Scan")
    print("="*25)
    kernel_ports, port_map = get_kernel_ports()
    userspace_ports = get_userspace_ports()
    if kernel_ports is None:
        return []
    hidden_from_userspace = kernel_ports - userspace_ports
    findings = []
    if hidden_from_userspace:
        print("\n[!] Listening ports found by kernel but hidden from 'ss' (potential backdoor):")
        for port in sorted(hidden_from_userspace):
            pid, comm = port_map.get(port, ("?", "?"))
            finding = f"Hidden Port: {port} held by '{comm}' (PID {pid})"
            print(f"    -> {finding}")
            findings.append(finding)
    else:
        print("\n[+] No hidden listening ports detected.")
    print("\n" + "="*25)
    print("  Port Scan Complete")
    print("="*25)
    return findings
    
    
def analyze_findings(all_findings):
    print("\n" + "#"*25)
    print("  Full Scan Analysis")
    print("#"*25)
    if not all_findings:
        print("\n[***] System appears clean. No anomalies detected across all scans.")
        return
    
    has_hidden_procs = any("Hidden Process" in f for f in all_findings)
    has_hidden_mods = any("Hidden Module" in f for f in all_findings)
    has_hidden_ports = any("Hidden Port" in f for f in all_findings)
    has_syscall_tampering = any("Syscall Integrity" in f for f in all_findings)

    print("\n[!] Potential threats detected. Summary based on findings:")
    
    if has_syscall_tampering:
        print("""
    - Type: Syscall Hooking Rootkit
    - Details: The system call table has been modified, indicating a potential rootkit
      that is intercepting system calls to hide its presence or alter system behavior.
""")
    if has_hidden_procs and not has_hidden_mods:
        print("""
    - Type: Process-Hiding Rootkit
    - Details: The malware is actively hiding its processes from standard tools like 'ps'.
      This is common for user-land rootkits that modify /proc or intercept system calls.
""")
    if has_hidden_mods:
        print("""
    - Type: Kernel-Level Rootkit (LKM)
    - Details: A Loadable Kernel Module (LKM) is hiding itself from 'lsmod'. This is a
      strong indicator of a sophisticated rootkit operating with kernel privileges. It may
      also be responsible for hiding processes and ports.
""")
    if has_hidden_ports and not has_hidden_mods:
        print("""
    - Type: Hidden Backdoor / Service
    - Details: A service is listening on a port but is hiding from standard tools like 'ss'.
      This could be a standalone backdoor or part of a larger malware framework.
""")
    if has_hidden_procs and has_hidden_mods and has_hidden_ports and has_syscall_tampering:
        print("""
    - Type: Advanced Kernel-Level Rootkit (Comprehensive)
    - Details: The malware exhibits multiple stealth capabilities, including syscall hooking,
      hiding its kernel module, its processes, and its network listeners. This indicates a
      full-featured rootkit with deep system integration and evasion techniques.
""")
    elif has_hidden_procs or has_hidden_mods or has_hidden_ports or has_syscall_tampering:
        print("""
    - Type: Combination Rootkit / Malware
    - Details: Multiple indicators of compromise suggest a sophisticated threat, potentially
      combining different evasion and malicious functionalities.
""")
    print("#"*25)
    
    
def run_full_scan(config):
    all_findings = []
    all_findings.extend(run_process_scan())
    all_findings.extend(run_module_scan())
    all_findings.extend(run_port_scan())
    all_findings.extend(run_fs_scan())
    all_findings.extend(check_syscall_integrity(config, interactive=False)) 
    analyze_findings(all_findings)
    return all_findings
    
    
def display_menu(stat):
    print("\n" + "#"*60)
    print(" "*23 +"ARGUS Scan Menu")
    print("#"*60)
    print("\n"+"[1] Compare Processes (Kernel vs /bin/ps)")
    print("[2] Compare Kernel Modules (Kernel vs /proc/modules)")
    print("[3] Compare Network Ports (Kernel vs /bin/ss)")
    print("[4] Perform Syscall Integrity Scan") 
    print("[5] Perform Full Scan (All checks)") 
    print("[6] Perform Filesystem Scan")
    print(f"[7] Toggle udp alert (Currently : {'ON' if stat else 'OFF'})" ) 
    print("\n[99] Exit")
    print("-"*15)
    

PID_FILE = "/tmp/argus_daemon.pid"

def signal_handler(signum, frame):
    print("Daemon shutting down...")
    try:
        if os.path.exists(PID_FILE):
            os.remove(PID_FILE)
    except OSError as e:
        print(f"Error removing PID file: {e}", file=sys.stderr)
    sys.exit(0)


def daemon_worker(interval, config):
   
    signal.signal(signal.SIGTERM, signal_handler)
    signal.signal(signal.SIGINT, signal_handler)
    
    print(f"[*] Argus daemon started (PID: {os.getpid()}). Running scans every {interval} seconds.")
    while True:
        try:
            all_findings = []
            original_stdout = sys.stdout
            sys.stdout = open(os.devnull, 'w')
            
            all_findings.extend(run_process_scan())
            all_findings.extend(run_module_scan())
            all_findings.extend(run_port_scan())
            all_findings.extend(run_fs_scan())
            all_findings.extend(check_syscall_integrity(config, interactive=False)) 
            
            sys.stdout.close()
            sys.stdout = original_stdout
            
            if all_findings:
                print(f"[{time.ctime()}] Daemon detected {len(all_findings)} anomalies. Sending alert.")
                send_udp_alert(all_findings, config)

        except Exception as e:
            print(f"[!] Error in daemon loop: {e}", file=sys.stderr)
        
        time.sleep(interval)


def daemonize():
   
    if os.path.exists(PID_FILE):
        try:
            with open(PID_FILE, 'r') as f:
                old_pid = int(f.read().strip())
            os.kill(old_pid, 0)
            sys.stderr.write(f"Daemon is already running with PID {old_pid}. Aborting.\n")
            sys.exit(1)
        except (OSError, ValueError):
            os.remove(PID_FILE)

    try:
        pid = os.fork()
        if pid > 0:
            sys.exit(0)
    except OSError as e:
        sys.stderr.write(f"fork #1 failed: {e}\n")
        sys.exit(1)

    os.chdir("/")
    os.setsid()
    os.umask(0)

    try:
        pid = os.fork()
        if pid > 0:
            sys.exit(0)
    except OSError as e:
        sys.stderr.write(f"fork #2 failed: {e}\n")
        sys.exit(1)

    try:
        with open(PID_FILE, 'w') as f:
            f.write(str(os.getpid()))
    except OSError as e:
        sys.stderr.write(f"Unable to write PID file {PID_FILE}: {e}\n")
        sys.exit(1)


    sys.stdout.flush()
    sys.stderr.flush()
    si = open(os.devnull, 'r')
    so = open(os.devnull, 'a+')
    se = open(os.devnull, 'a+')
    os.dup2(si.fileno(), sys.stdin.fileno())
    os.dup2(so.fileno(), sys.stdout.fileno())
    os.dup2(se.fileno(), sys.stderr.fileno())


def stop_daemon():
    if not os.path.exists(PID_FILE):
        sys.stderr.write("Daemon is not running (PID file not found).\n")
        return

    try:
        with open(PID_FILE, 'r') as f:
            pid = int(f.read().strip())
    except (ValueError, IOError) as e:
        sys.stderr.write(f"Error reading PID file: {e}\n")
        os.remove(PID_FILE)
        return

    try:
        print(f"Stopping daemon with PID {pid}...")
        os.kill(pid, signal.SIGTERM)

        time.sleep(1)

        os.kill(pid, 0) 
        print("Daemon did not stop gracefully, sending SIGKILL.")
        os.kill(pid, signal.SIGKILL)

    except OSError:
        print("Daemon stopped successfully.")
    finally:
        if os.path.exists(PID_FILE):
            os.remove(PID_FILE)


def main():
    parser = argparse.ArgumentParser(description="Argus Linux Rootkit Detection Framework.")
    parser.add_argument("-t", "--daemon", type=int, metavar="SECONDS",
                        help="Run as a daemon, checking every N seconds.")
    parser.add_argument("--stop", action="store_true",
                        help="Stop the running daemon process.")
    
    args = parser.parse_args()

    if args.stop:
        stop_daemon()
        sys.exit(0)

    if os.geteuid() != 0:
        print("[!] This tool must be run as root to function correctly.")
        sys.exit(1)
    
    try:
        config = load_config()
    except Exception as e:
        print(f"[x] Critical error loading config.json: {e}")
        sys.exit(1)

    if args.daemon:
        if args.daemon <= 0:
            print("[!] Daemon interval must be a positive number of seconds.")
            sys.exit(1)
        print(f"[*] Starting Argus in daemon mode with a {args.daemon} second interval.")
        daemonize()
        daemon_worker(args.daemon, config)
    else:
        interactive_menu(config)


def interactive_menu(config):
    global syscall_monitor_thread
    stat = False
    display_banner()

    
    def syscall_monitor_loop():
        global syscall_currently_hooked

        while True:
            previous_state = syscall_currently_hooked

            check_syscall_integrity(
                config,
                interactive=False,
                is_background_check=True
            )

            if syscall_currently_hooked and not previous_state:
                print("\n\033[1m[CRITICAL] Syscall tampering detected!\033[0m")
                print("Run option [4] to view detailed hook information.")
                print("Argus > ", end="", flush=True)

            time.sleep(3)
            
    
    if syscall_monitor_thread is None or not syscall_monitor_thread.is_alive():
        syscall_monitor_thread = threading.Thread(target=syscall_monitor_loop, daemon=True)
        syscall_monitor_thread.start()
        print("[+] Syscall integrity monitoring started in background (every 3 seconds).")

    while True:
        if syscall_tampering_detected.is_set():
            print("\n\033[1m[CRITICAL] Syscall tampering detected by background monitor!\033[0m")
            print("Run option [4] to view detailed hook information.\n")
            syscall_tampering_detected.clear()

        display_menu(stat)
        try:
            choice = input("Argus > ")
            if choice == '1':
                findings = run_process_scan()
                if stat and findings:
                    send_udp_alert(findings, config)
            elif choice == '2':
                findings = run_module_scan()
                if stat and findings:
                    send_udp_alert(findings, config)
            elif choice == '3':
                findings = run_port_scan()
                if stat and findings:
                    send_udp_alert(findings, config)
            elif choice == '4': 
                print("\n" + "="*25)
                print("  Running Syscall Integrity Scan")
                print("="*25)
                
                findings = check_syscall_integrity(config, interactive=True) 
                if findings:
                    if stat:
                            send_udp_alert(findings, config)
                else :
                    print("Syscall table is intact since argus started.")
                print("="*25)
                print("  Syscall Scan Complete")
                print("="*25)
            elif choice == '5': 
                findings = run_full_scan(config)
                if stat and findings:
                    send_udp_alert(findings, config)
            elif choice == '6':
                findings = run_fs_scan()
                if stat and findings:
                    send_udp_alert(findings, config)
            elif choice == '7':
                stat = not stat
                print(f"[+] UDP alerts {'ENABLED' if stat else 'DISABLED'}")
            elif choice == '99':
                print("System observation terminated." + "\n" +"ARGUS sleeps")
                break
            else:
                print(f"Unknown command: {choice}")
        except KeyboardInterrupt:
            print("\nSystem observation terminated. ARGUS sleeps.")
            break
        except Exception as e:
            print(f"\nAn unexpected error occurred: {e}")
            
            
            
if __name__ == "__main__":
    main()
