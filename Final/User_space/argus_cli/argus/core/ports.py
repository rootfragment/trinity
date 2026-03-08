import re
import subprocess
from ..utils.constants import PROC_SOCKETS_FILE

def get_kernel_ports(proc_file=PROC_SOCKETS_FILE):
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
