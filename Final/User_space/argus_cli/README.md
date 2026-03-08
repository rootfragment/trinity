# Argus - Linux Kernel Intrusion Detection System

**Argus** is a sophisticated security tool designed for Linux systems to detect the presence of rootkits and other kernel-level malware. It operates by cross-validating the system's state between the kernel's internal view and the user-space's perception. Discrepancies between these two views are strong indicators of malicious activity.

This project consists of two primary components:

1.  **Argus LKM (Loadable Kernel Module)**: A kernel module (`argus_lkm.ko`) that acts as a trusted anchor within the kernel. It collects ground-truth information about the system's state and exposes it through a series of custom `/proc` entries.
2.  **Argus CLI (`argus_cli.py`)**: A Python-based user-space client that interacts with the LKM's `/proc` entries and compares that data against standard user-space utilities to identify hidden artifacts.

## System Architecture

The core design philosophy of Argus is to **"Trust the Kernel."** While user-space tools can be deceived by hooked system calls or manipulated `/proc` files, the Argus LKM, once loaded, has a privileged and direct view of the kernel's internal data structures.

The workflow is as follows:

1.  The **Argus LKM** is loaded into the kernel (`insmod argus_lkm.ko`).
2.  The LKM registers several read-only `/proc` files (e.g., `/proc/rk_ps`, `/proc/rk_mods`).
3.  When the **Argus CLI** initiates a scan, it reads from these `/proc` files to get the kernel's "true" view of the system.
4.  The CLI then executes standard user-space commands (e.g., `ps`, `lsmod`, `ss`) to get the user-space view.
5.  Finally, the CLI computes the **set difference** between these two views. Any items present in the kernel's view but absent from the user-space's view are flagged as suspicious.



---

## Key Features & Technical Implementation

### 1. Syscall Table Integrity Monitoring

This is one of Argus's most critical features. It actively monitors the kernel's system call table for unauthorized modifications (hooks).

*   **Mechanism**: The Argus LKM stores a pristine copy of the system call table's function pointers upon loading. Periodically, and on-demand via `/proc/rk_syscalls`, it compares the live system call table addresses against this stored baseline.
*   **Detection**: If a mismatch is found, it means a system call (e.g., `sys_getdents64`, `sys_kill`) has been redirected to a malicious function.
*   **Reporting**: Argus identifies exactly which syscall is hooked, the original kernel function address, and the address of the malicious hook. This is crucial for forensic analysis.
*   **Live Monitoring**: In interactive mode, a background thread continuously polls `/proc/rk_syscalls` every 3 seconds, providing instant alerts in the console if tampering occurs.

### 2. Process Hiding Detection

*   **Kernel View**: The Argus LKM iterates through the kernel's task list (linked list of `task_struct`s) and writes the PID and command name of every process to `/proc/rk_ps`.
*   **User-space View**: The CLI executes `ps -e -o pid=,comm=`.
*   **Analysis**: It identifies PIDs present in `/proc/rk_ps` but missing from the `ps` output. This is a classic technique used by rootkits to hide malicious processes.

### 3. Hidden Kernel Module (LKM) Detection

*   **Kernel View**: The LKM traverses the kernel's internal list of loaded modules and records their names in `/proc/rk_mods`. This is the ground truth.
*   **User-space View**: The CLI reads from `/proc/modules`, which is what `lsmod` uses. A common rootkit technique is to unlink a malicious module from the list that populates `/proc/modules`, effectively hiding it from `lsmod`.
*   **Analysis**: Argus compares the LKM's direct list with the `/proc/modules` list to find modules that are loaded but "invisible" to user-space.

### 4. Hidden Network Port Detection

*   **Kernel View**: The Argus LKM inspects the kernel's data structures for TCP and UDP listeners, recording the port, PID, and process name for each listening socket into `/proc/rk_sockets`.
*   **User-space View**: The CLI runs `ss -ltunp` to get the list of listening ports visible to the user.
*   **Analysis**: By comparing these datasets, Argus can uncover listening ports that are being deliberately hidden from tools like `ss` and `netstat`, which are often backdoors.

### 5. Filesystem Integrity Scanning

This scan detects hidden files, "phantom" files (files visible in user-space but not in the kernel), and metadata tampering.

*   **Mechanism**:
    1.  The user specifies a list of directories to scan in `dir_list.txt`.
    2.  For each directory, the CLI writes the path to `/proc/rk_fs`.
    3.  The LKM's handler for this `/proc` file then performs its *own* `readdir` operation on that directory from within the kernel, recording the metadata for each file (inode, size, mode, UID, GID).
    4.  The CLI reads this kernel-generated list and compares it against its own user-space `os.scandir()` results.
*   **Detected Anomalies**:
    *   **Hidden Files**: Present in the kernel's view but not user-space.
    *   **Phantom Files**: Present in user-space but not the kernel's view.
    *   **Metadata Mismatches**: Differences in file size, ownership, or permissions.

### 6. Threat Analysis Engine

After a full scan, Argus doesn't just present a list of findings; it attempts to classify the threat based on the combination of anomalies detected.

*   **Syscall Hooking Rootkit**: `syscall_tampering` is true.
*   **Process-Hiding Rootkit**: `hidden_procs` is true, but `hidden_mods` is false (suggests a user-land hook).
*   **Kernel-Level Rootkit (LKM)**: `hidden_mods` is true.
*   **Advanced Kernel-Level Rootkit**: `hidden_procs`, `hidden_mods`, `hidden_ports`, and `syscall_tampering` are all true, indicating a highly sophisticated and comprehensive threat.

---

## Daemon Mode for Autonomous Monitoring

For continuous, unattended monitoring, Argus can be run as a daemon process.

*   **Daemonization Process**:
    1.  The script performs a double-fork to detach from the controlling terminal.
    2.  It changes its working directory to `/`, resets its umask, and becomes a session leader (`os.setsid()`).
    3.  Standard input, output, and error are redirected to `/dev/null`.
    4.  A PID file is created at `/tmp/argus_daemon.pid` to prevent multiple instances and to allow for graceful termination.
*   **Operation**: In daemon mode, the `daemon_worker` function runs an infinite loop, performing a full scan at a user-defined interval. If any anomalies are found, it sends a UDP alert to all configured listeners.

---

## Prerequisites

1.  **Argus LKM**: The `argus_lkm.ko` module must be compiled and loaded into the kernel.
2.  **Root Privileges**: The CLI must be run as `root` (`sudo`).
3.  **Python 3**: And standard Linux utilities (`ps`, `ss`).

---

## Usage

### Interactive Mode

For manual scans and real-time monitoring.

1.  **Load the Kernel Module**:
    ```bash
    sudo insmod argus_lkm.ko
    ```
2.  **Run the CLI**:
    ```bash
    sudo ./argus_cli.py
    ```
3.  **Use the Menu**: Select scans from the interactive menu. The background syscall monitor starts automatically.

### Daemon Mode

For "set it and forget it" monitoring.

1.  **Start the Daemon**: Run a full scan every 10 minutes (600 seconds):
    ```bash
    sudo ./argus_cli.py --daemon 600
    ```
2.  **Stop the Daemon**:
    ```bash
    sudo ./argus_cli.py --stop
    ```

---

## Configuration

Configuration is managed via `config.json` and `dir_list.txt`.

### `config.json` - UDP Alerting

Configure one or more remote listeners to receive alerts.

```json
{
    "listener_list": [
        {
            "ip": "192.168.1.100",
            "port": 12345,
            "enabled": true
        },
        {
            "ip": "10.0.0.5",
            "port": 514,
            "enabled": false
        }
    ]
}
```

### `dir_list.txt` - Filesystem Scan Targets

Add the absolute paths of directories you want Argus to scan, one per line. Comments are allowed.

```
# System Binaries
/bin
/sbin
/usr/bin

# Web Server Root
/var/www/html
```
