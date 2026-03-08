import os
from ..utils.constants import PROC_FS_FILE, DIR_LIST_FILE

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
