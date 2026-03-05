# Argus FS: Kernel-Space Filesystem Integrity Scanner

Argus FS is a specialized security tool designed to detect filesystem inconsistencies by comparing low-level kernel directory iterations with standard userspace API results. This "cross-view" approach is highly effective at identifying hidden files, "phantom" entries, or metadata tampering typically associated with rootkits.

## Components

### 1. `file_itr.c` (Kernel Module)
The heart of the project is a Linux kernel module that provides a raw view of the filesystem.
- **Functionality**: Creates a interface at `/proc/argus_fs`.
- **Mechanism**: 
  - **Write**: Accepts a directory path from userspace.
  - **Read**: Uses the internal kernel function `iterate_dir` to walk the target directory and collect metadata (Inodes, UID/GID, size, and mode) directly from the VFS layer.
- **Safety**: Implements mutex locking to ensure thread-safe path updates and utilizes the `seq_file` interface for efficient data streaming.

### 2. `helper.py` (Analysis Tool)
A Python-based companion script that orchestrates the comparison.
- **Userspace View**: Scans the directory using standard system calls (`os.scandir`).
- **Kernel View**: Communicates with the Argus FS module to get the "ground truth" from the kernel.
- **Comparison Engine**: Flags three types of anomalies:
  - **[HIDDEN]**: Files visible to the kernel but hidden from userspace.
  - **[PHANTOM]**: Files appearing in userspace but not existing in the kernel's iteration.
  - **[MISMATCH]**: Discrepancies in file metadata (e.g., mismatched UIDs or sizes).

---

## Getting Started

### Prerequisites
- Linux Kernel Headers (for building the module)
- Python 3.x
- Root/Sudo privileges (required for kernel module operations)

### Installation & Build

1. **Compile the Kernel Module**:
   ```bash
   make
   ```

2. **Load the Module**:
   ```bash
   sudo insmod file_itr.ko
   ```

3. **Verify Initialization**:
   Check dmesg to confirm the module is loaded:
   ```bash
   dmesg | tail -n 1
   # Expected: [timestamp] Argus FS module loaded
   ```

### Usage

Run the helper script with sudo (to allow it to write to the `/proc` interface):

```bash
sudo python3 helper.py
```

1. Enter the full path of the directory you wish to scan when prompted.
2. The tool will display a report of any detected inconsistencies.

---

## Clean Up

To remove the kernel module and clean the build artifacts:

```bash
sudo rmmod file_itr
make clean
```

## Security Disclaimer
This tool is intended for educational and security auditing purposes. Interacting with kernel space requires caution; always test in a non-production environment first.
