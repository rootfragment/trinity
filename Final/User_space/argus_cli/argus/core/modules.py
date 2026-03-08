from ..utils.constants import PROC_MODULES, PROC_MODS_FILE

def get_user_modules(proc_file=PROC_MODULES):
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
        
def get_kernel_modules(proc_file=PROC_MODS_FILE):
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
