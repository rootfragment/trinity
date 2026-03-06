# Argus - Userspace Detection Client

This is the userspace command-line interface (CLI) for the Argus Linux Rootkit Detection Framework. This Python script interacts with the Argus kernel module to scan for and identify discrepancies between the kernel's view of the system and the userspace's view, which can be a strong indication of rootkit activity.

## Features

- **Interactive Menu:** Provides a simple, menu-driven interface to run different security scans.
- **Continuous Background Monitoring:** In interactive mode, a background thread monitors syscall integrity every 3 seconds, providing immediate visual alerts if tampering is detected.
- **Syscall Integrity Scanning:** Detects unauthorized modifications to the kernel's system call table by comparing live addresses against known-good values, identifying the exact syscalls hooked and the malicious function addresses.
- **Filesystem Integrity Scanning:** Identifies hidden or "phantom" files and metadata mismatches by comparing the userspace directory listing with the kernel's internal view (`/proc/rk_fs`).
- **Process Scan:** Compares the process list from the Argus kernel module (`/proc/rk_ps`) with the output of the standard `ps` command to detect hidden processes.
- **Module Scan:** Compares the kernel module list from `/proc/rk_mods` with the list from `/proc/modules` to detect hidden LKMs.
- **Port Scan:** Compares the list of listening network ports from `/proc/rk_sockets` with the output of the `ss` command to find hidden backdoors.
- **Full Scan:** Runs all scans sequentially for a comprehensive system check.
- **Threat Analysis:** Categorizes detected anomalies into specific threat types, such as Syscall Hooking Rootkits, Process-Hiding Malware, or Advanced Kernel-Level Rootkits.
- **Configurable UDP Alerts:** Supports multiple remote UDP listeners for centralized logging and real-time incident response.
- **Daemon Mode:** Provides autonomous, persistent monitoring with user-definable scan intervals and automatic remote alerting.

## How It Works

The client operates on a simple principle: **trust the kernel**. It reads the "ground truth" data from the `/proc/rk_*` files created by the Argus kernel module. It then gathers the equivalent data from standard userspace utilities (`ps`, `ss`, etc.). By finding the difference between these two sets, it can pinpoint resources that are being actively hidden from the userspace, a common technique used by rootkits.

For example, if a process PID appears in `/proc/rk_ps` but not in the output of `ps -e`, it is flagged as a "Hidden Process."

### Filesystem Scan

The Filesystem Scan uses a configurable list of directories (defined in `dir_list.txt`) to check for inconsistencies:
- **Hidden Files:** Files present in the kernel's view but missing from userspace (standard `ls` or `scandir`).
- **Phantom Files:** Files visible in userspace but not recognized by the kernel.
- **Metadata Mismatches:** Files where attributes like size, permissions (mode), owner (UID), or group (GID) differ between the kernel and userspace views.

The tool writes the target directory to `/proc/rk_fs` and reads back the kernel's metadata for every file in that path for comparison.

### Syscall Tamper Detection

This is a critical security feature that monitors the integrity of the Linux system call table. 
- **Verification:** The Argus kernel module compares the current addresses of system calls in memory with the original, verified addresses.
- **Reporting:** When a hook is detected, Argus identifies the specific system call (e.g., `sys_read`, `sys_getdents64`) and reports both the original kernel address and the address of the hook.
- **Interactive Alerts:** If tampering is detected during an interactive session, Argus provides a critical breach notification and requires user confirmation to proceed, ensuring the administrator is immediately aware of the compromise.

### Threat Classification

The "Full Scan" feature doesn't just list anomalies; it analyzes the combination of findings to classify the threat:

*   **Syscall Hooking Rootkit:** Detected when the system call table has been modified.
*   **Process-Hiding Rootkit:** Found when processes are hidden but no unauthorized kernel modules are detected (often user-land hooks).
*   **Kernel-Level Rootkit (LKM):** Identified when a kernel module is hiding itself from `lsmod`.
*   **Hidden Backdoor / Service:** Flagged when a network port is listening but hidden from `ss`.
*   **Advanced Kernel-Level Rootkit:** A comprehensive classification for threats that hide modules, processes, ports, and hook syscalls simultaneously.

## Prerequisites

1.  **Argus Kernel Module:** The `argus_lkm.ko` module must be loaded into the kernel. This script is entirely dependent on the `/proc/rk_*` files created by the module.
2.  **Root Privileges:** The script should be run as root (`sudo`) to ensure it has the necessary permissions to read proc files and run system commands accurately.
3.  **Standard Linux Utilities:** The script relies on `ps` and `ss` being installed and available in the system's PATH.

## Usage

1.  Ensure the Argus kernel module is loaded (`sudo insmod argus_lkm.ko`).
2.  Run the client with root privileges:
    ```bash
    sudo ./argus_cli.py
    ```
3.  Use the interactive menu to select a scan:
    - `[1]` Compare Processes (Kernel vs /bin/ps)
    - `[2]` Compare Kernel Modules (Kernel vs /proc/modules)
    - `[3]` Compare Network Ports (Kernel vs /bin/ss)
    - `[4]` Perform Syscall Integrity Scan
    - `[5]` Perform Full Scan (All checks)
    - `[6]` Perform Filesystem Scan
    - `[7]` Toggle UDP alerts ON/OFF for the current session.
    - `[99]` Exit

## Configuration

The script uses a `config.json` file for configuration. If this file is not found, a default one will be created automatically.

### Target Directories (`dir_list.txt`)

For the Filesystem Scan, Argus reads a list of directories from `dir_list.txt`. If the file doesn't exist, a template is created with common system paths (`/bin`, `/usr/bin`, `/sbin`). You can add any directory you wish to monitor, one per line.

### UDP Alerts

To receive alerts, edit the `config.json` file and add your listener details.

**Default `config.json`:**
```json
{
    "listener_list": [
        {
            "ip": "127.0.0.1",
            "port": 12345,
            "enabled": true
        }
    ]
}
```

- **`ip`**: The IP address of the machine listening for UDP packets.
- **`port`**: The port on the listening machine.
- **`enabled`**: Set to `true` to send alerts to this listener, `false` to disable.

You can add multiple listener objects to the `listener_list` array to send alerts to several destinations.

## What is Daemon Mode?

Daemon mode is designed for continuous, autonomous monitoring of your system. Instead of running scans manually, you can launch Argus as a background process (a "daemon") that will periodically perform a full system scan without any further user interaction.

When a potential threat is detected, the daemon will automatically send a UDP alert to all configured listeners.

This "set it and forget it" approach ensures your system is consistently monitored for suspicious activity.

## How It Works

When you start the tool with the `--daemon` flag, the script performs several actions to become a true daemon process:

1.  **Forking:** The script "forks" itself into a child process and a parent process. The parent process exits immediately, returning you to your command prompt.
2.  **Detaching:** The child process detaches from the terminal, ensuring it won't be terminated if you close your shell session.
3.  **PID File:** It creates a PID (Process ID) file at `/tmp/argus_daemon.pid`. This file stores the daemon's process ID and is used to prevent multiple daemons from running simultaneously and to stop the correct process.
4.  **Scanning Loop:** The daemon enters an infinite loop where it:
    *   Performs a full scan (processes, modules, ports, and **syscall integrity**).
    *   Pauses for the user-defined interval.
    *   Repeats the cycle.

### Starting the Daemon

To start Argus in daemon mode, use the `-t` or `--daemon` flag, followed by the scan interval in seconds.

**Example:** To run a full scan every 5 minutes (300 seconds):
```bash
sudo ./argus_cli.py --daemon 300
```
You will see a confirmation message, and the daemon will begin running in the background:
```
[*] Starting Argus in daemon mode with a 300 second interval.
```

### Stopping the Daemon

To stop a running daemon, use the `--stop` flag:
```bash
sudo ./argus_cli.py --stop
```
This command reads the PID from `/tmp/argus_daemon.pid` and sends a termination signal to the correct process.
