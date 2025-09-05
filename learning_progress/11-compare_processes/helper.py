import subprocess

def get_ps_process():
    ps_output = subprocess.check_output(["ps", "-e", "-o", "pid=,comm="]).decode()
    ps_dict = {}
    for line in ps_output.strip().splitlines():
        pid, cmd = line.strip().split(maxsplit=1)
        ps_dict[pid] = cmd
    return ps_dict

def get_kernel_process():
    ker_dict = {}
    with open("/proc/p1", "r") as f:
        for line in f:
            parts = line.strip().split(maxsplit=1)
            if not parts:
                continue
            pid = parts[0]
            cmd = parts[1] if len(parts) > 1 else "?"
            ker_dict[pid] = cmd
    return ker_dict

def compare_process(ps_process, kern_process):
    missing_ps = set(kern_process.keys()) - set(ps_process.keys())
    missing_ker = set(ps_process.keys()) - set(kern_process.keys())

    print("---- COMPARISON RESULT ----")

    if missing_ps:
        print("\n[!] Hidden from ps:")
        for pid in sorted(missing_ps, key=int):
            print(f"  PID {pid:<6} {kern_process[pid]}")
    else:
        print("[+] No processes hidden from ps")

    if missing_ker:
        print("\n[!] Present in ps but missing in kernel:")
        for pid in sorted(missing_ker, key=int):
            print(f"  PID {pid:<6} {ps_process[pid]}")
    else:
        print("[+] No extra processes in ps")

if __name__ == "__main__":
    ps_process = get_ps_process()
    kern_process = get_kernel_process()
    compare_process(ps_process, kern_process)
