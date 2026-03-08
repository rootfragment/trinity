import subprocess
from ..utils.constants import PROC_PS_FILE

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
        
def get_kernel_processes(proc_file=PROC_PS_FILE):
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
