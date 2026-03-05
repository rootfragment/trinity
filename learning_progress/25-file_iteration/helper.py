import os
import stat

PROC = "/proc/argus_fs"


# ----------------------------
# Userspace view (via syscalls)
# ----------------------------
def get_user_view(directory):
    view = {}

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

    return view
# ----------------------------
# Kernel view (via /proc)
# ----------------------------
def get_kernel_view(directory):
    # Send directory to kernel
    with open(PROC, "w") as f:
        f.write(directory)

    view = {}

    with open(PROC, "r") as f:
        for line in f:
            line = line.strip()

            if not line or "|" not in line:
                continue

            # USE RSPLIT to handle paths containing the delimiter |
            # We expect 5 metadata fields at the end.
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
                    meta[k] = int(v, 8)  # parse octal correctly
                else:
                    meta[k] = int(v)

            # Ensure all fields exist
            required = {"inode", "size", "mode", "uid", "gid"}
            if not required.issubset(meta.keys()):
                continue

            view[path] = {
                "inode": meta["inode"],
                "size": meta["size"],
                "mode": meta["mode"],
                "uid": meta["uid"],
                "gid": meta["gid"]
            }

    return view


# ----------------------------
# Comparison Engine
# ----------------------------
def compare(user_view, kernel_view):
    hidden = False
    phantom = False
    mismatch = False

    # Files seen by kernel but not by user
    for path in kernel_view:
        if path not in user_view:
            print("[HIDDEN]", path)
            hidden = True

    # Files seen by user but not by kernel
    for path in user_view:
        if path not in kernel_view:
            print("[PHANTOM]", path)
            phantom = True

    # Metadata mismatches
    for path in user_view:
        if path in kernel_view:
            if user_view[path] != kernel_view[path]:
                print("[MISMATCH]", path)
                print("  USER  :", user_view[path])
                print("  KERNEL:", kernel_view[path])
                print()
                mismatch = True

    if not hidden and not phantom and not mismatch:
        print("✔ No mismatches detected.")


# ----------------------------
# Main
# ----------------------------
if __name__ == "__main__":

    directory = input("Enter directory to scan: ").strip()

    if not os.path.isdir(directory):
        print("Invalid directory.")
        exit(1)

    user_view = get_user_view(directory)
    kernel_view = get_kernel_view(directory)
    compare(user_view, kernel_view)
    print("Kernel count:", len(kernel_view))
    print("User count:", len(user_view))
