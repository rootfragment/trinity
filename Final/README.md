# Argus - Proof of Concept Linux Rootkit Detection Framework

<pre>
          ___      .______        _______  __    __       _______.
         /   \     |   _  \      /  _____||  |  |  |     /       |
        /  ^  \    |  |_)  |    |  |  __  |  |  |  |    |   (----`
       /  /_\  \   |      /     |  | |_ | |  |  |  |     \   \    
      /  _____  \  |  |\  \----.|  |__| | |  `--'  | .----)   |   
     /__/     \__\ | _| `._____| \______|  \______/  |_______/    
</pre>

---

## Overview

Argus is a Linux security tool designed to detect the presence of rootkits and other malicious software. It operates on a simple but powerful principle: **comparing the system's state as seen from within the kernel against the state observed by standard user-space utilities.** Discrepancies between these two views are strong indicators of stealth techniques used by malware to hide its tracks.

This tool is composed of two main parts:
1.  A **Linux Kernel Module (LKM)** that acts as a trusted observer, gathering raw data directly from kernel data structures and monitoring critical kernel integrity.
2.  A **Python user-space client** that orchestrates scans, performs comparisons, and reports findings.

## Features

- **Process Hiding Detection**: Uncovers processes that are running but are hidden from user-space tools like `ps`.
- **Module Hiding Detection**: Detects Loadable Kernel Modules (LKMs) that are active in the kernel but invisible to `lsmod`.
- **Hidden Port Detection**: Finds network listening ports that are open and active but are concealed from utilities like `ss` and `netstat`.
- **Syscall Integrity Monitoring**: Detects unauthorized modifications to the kernel's system call table by comparing live addresses against known-good values, identifying hooked syscalls and their new addresses.
- **Threat Analysis**: Provides a high-level summary of detected anomalies to help classify the potential threat (e.g., User-land Rootkit, Kernel-Level Rootkit, Syscall Hooking Rootkit).
- **Configurable UDP Alerting**: Sends alerts containing scan findings to one or more remote listeners over UDP, allowing for centralized monitoring.
- **Interactive and Daemon Modes**: The user-space client can be run interactively for manual scans or as a background daemon for continuous, automated monitoring.

## How It Works

Argus's detection strategy relies on establishing a trusted baseline from the kernel's perspective and comparing it against the potentially compromised user-space environment.

### Kernel Module (`argus_lkm.ko`)

The kernel module is the core of the detection engine. When loaded, it creates several read-only files in the `/proc` filesystem:

-   `/proc/rk_ps`: Exposes a list of all running processes by directly iterating through the kernel's task list (`for_each_process`).
-   `/proc/rk_mods`: Exposes a list of all loaded kernel modules by traversing the internal module list.
-   `/proc/rk_sockets`: Exposes a list of all listening TCP and UDP sockets by inspecting kernel network data structures.
-   `/proc/rk_syscalls`: Compares the live system call table against a trusted "golden" copy captured at module load time. Returns `0` if no changes are detected, or `-1` followed by a list of tampered syscalls and their new addresses.

This data, coming directly from the kernel, is considered a "ground truth" view of the system's state.

### User-Space Client (`argus_cli.py`)

The Python client provides a command-line interface to interact with the kernel module and perform scans. For each scan type, it:

1.  **Reads the "ground truth"** from the corresponding `/proc` file created by the Argus kernel module.
2.  **Gathers the user-space view** by executing standard Linux commands (`ps`, `cat /proc/modules`, `ss`).
3.  **Compares the two lists** and reports any items present in the kernel's list but missing from the user-space list.
4.  **For syscalls**, it directly reads `/proc/rk_syscalls` to determine if the system call table has been tampered with.
5.  **Sends alerts** and provides a final analysis based on the findings.
6.  **Background Syscall Monitoring**: In interactive mode, a background thread continuously monitors syscall integrity, providing immediate alerts if tampering is detected.

## Getting Started

### Prerequisites

- A Linux system with kernel headers installed (required to build the module). The package name is typically `linux-headers-$(uname -r)`.
- `make` and `gcc`.
- Python 3.

### Compilation

Navigate to the `Kernel_space` directory and compile the kernel module:

```bash
cd Kernel_space
make
```

This will produce the kernel object file: `argus_lkm.ko`.

### Configuration

The user-space client can send UDP alerts to remote systems. To configure the listeners, edit the `config.json` file in the `User_space/argus_cli` directory. A default file is created automatically if one is not found.

```json
{
    "listener_list": [
        {
            "ip": "127.0.0.1",
            "port": 12345,
            "enabled": true
        },
        {
            "ip": "192.168.1.100",
            "port": 5555,
            "enabled": false
        }
    ]
}
```

## Usage

All commands require `sudo` or root privileges to load/unload kernel modules and to read the `/proc` entries.

1.  **Load the Kernel Module**:
    ```bash
    sudo insmod Kernel_space/argus_lkm.ko
    ```

2.  **Run the User-Space Client**:
    Navigate to the `User_space/argus_cli` directory.
    ```bash
    cd User_space/argus_cli
    sudo python3 argus_cli.py
    ```

3.  **Use the Menu (Interactive Mode)**:
    The client will present a menu with the following options:
    - `[1] Compare Processes`: Scan for hidden processes.
    - `[2] Compare Kernel Modules`: Scan for hidden LKMs.
    - `[3] Compare Network Ports`: Scan for hidden listening ports.
    - `[4] Perform Syscall Integrity Scan`: Check for syscall table tampering.
    - `[5] Perform Full Scan`: Run all checks sequentially.
    - `[6] Toggle UDP Alert`: Enable or disable sending findings via UDP for the current session.
    - `[99] Exit`: Terminate the client (does not unload the kernel module).

4.  **Daemon Mode**:
    To run a full scan every `N` seconds and send alerts on findings:
    ```bash
    sudo python3 argus_cli.py --daemon N
    ```
    To stop the daemon:
    ```bash
    sudo python3 argus_cli.py --stop
    ```

5.  **Unload the Kernel Module**:
    When you are finished, unload the module to clean up the `/proc` entries.
    ```bash
    sudo rmmod argus_lkm
    ```

## Project Structure

```
.
├── Kernel_space/
│   ├── core.c              # Main kernel module file (init, exit, proc creation)
│   ├── Makefile            # Makefile for compiling the kernel module
│   ├── modules.c / .h      # Logic for iterating kernel modules
│   ├── process.c / .h      # Logic for iterating processes
│   ├── socket.c / .h       # Logic for iterating network sockets
│   ├── syscall.c / .h      # Logic for syscall table integrity checking
│   └── README.md           # Kernel-space specific README
└── User_space/
    ├── argus_alert_receiver/
    │   ├── argus_alert_receiver.py # UDP server for receiving and logging alerts
    │   └── README.md               # Alert receiver specific README
    └── argus_cli/
        ├── argus_cli.py            # Main user-space client and scanning engine
        └── README.md               # CLI specific README
```

## Dependencies and Installation

### Dependencies
- **Kernel-space:** `make`, `gcc`, and Linux kernel headers for your running kernel version (e.g., `linux-headers-$(uname -r)`).
- **User-space:** Python 3.

### Installation Steps

1.  **Clone the repository:**
    ```bash
    git clone <your-repo-url>
    cd argus
    ```

2.  **Compile the kernel module:**
    ```bash
    cd Kernel_space
    make
    cd ..
    ```

3.  **Review the configuration:**
    Before running, review and edit the `config.json` file located in `User_space/argus_cli` to set up your desired UDP alert listeners.

4.  **Run the tool:**
    Follow the instructions in the [Usage](#usage) section.

## Threat Model and Limitations

### In-Scope Threats
- **Stealth Malware:** The primary target is malware that actively hides its presence by manipulating the data returned to standard user-space tools.
- **Process/Module/Port Hiding:** It is effective against rootkits that hook syscalls like `getdents64` or modify the results of `/proc` reads to hide files, processes, kernel modules, or network connections from tools like `ps`, `lsmod`, and `ss`.
- **Syscall Hooking:** Directly detects rootkits that modify the `sys_call_table` to hijack system calls.

### Out-of-Scope Threats
- **Non-Stealth Malware:** Argus is not a signature-based antivirus; it will not detect malware that doesn't actively hide itself.
- **Evasion-aware Rootkits:** A sophisticated rootkit could potentially detect Argus by its `/proc` entries and temporarily disable its own hiding mechanisms to evade a scan.
- **User-land Hooks:** Some rootkits compromise libraries (e.g., via `LD_PRELOAD`) instead of the kernel. Argus would not detect this.
- **Bootkits and Firmware-level Threats:** Argus operates only when the Linux kernel is running and cannot detect threats that compromise the bootloader or underlying firmware.

## Project Analysis

#### Advantages (Pros)

*   **Deep Visibility**: Operating from within the kernel provides a privileged viewpoint that is more trustworthy than user-space tools alone.
*   **Effective Detection Principle**: The core logic of comparing kernel and user-space views is a proven method for uncloaking many common rootkit hiding techniques.
*   **Comprehensive Scans**: Argus covers the three most common hiding places: processes, kernel modules, and network ports, plus critical syscall integrity.
*   **Syscall Tamper Detection**: Directly identifies modifications to the system call table, a hallmark of many kernel-level rootkits.
*   **User-Friendly**: The Python client offers a clear interface, actionable summaries, and helpful features like UDP alerting, interactive and daemon modes, making it easy to use and integrate into a lab environment.

#### Disadvantages (Cons)

*   **Predictable Footprint**: The use of well-known `/proc` file names (`rk_ps`, `rk_mods`, etc.) creates a predictable footprint that could be detected and targeted by advanced malware.
*   **Snapshot-in-Time**: While the daemon mode provides continuous monitoring, individual scans are snapshots. A sophisticated rootkit could potentially detect the scan and temporarily hide its activities, leading to a false negative.
*   **Requires Root Privileges**: Like all tools of this nature, it must be run as root. This carries inherent risk, and a compromised Argus tool could become a security threat itself.
  

### Explored Research: Runtime Integrity Verification

During the development of this project, a more advanced detection concept was explored: **runtime integrity verification of kernel modules**.

The idea was to have the Argus kernel module calculate a cryptographic hash (e.g., SHA-256) of the executable `.text` section of all other loaded kernel modules. This hash could then be compared against a known-good baseline to detect if a module's code had been tampered with in memory (a technique used by some advanced malware).

This feature was **successfully implemented on older Linux kernel versions** (pre-4.x). However, it was ultimately not included in the final framework because it is **no longer feasible on modern kernels**. Due to critical security enhancements like `CONFIG_STRICT_MODULE_RWX`, the memory pages holding executable kernel code are marked as read-only and non-executable data is strictly separated. These protections prevent one kernel module from easily reading the executable code of another, making the hashing attempt fail. While there are complex and unstable methods to bypass this for research, it goes against the security-first principles of modern kernel design, making it an impractical feature for a stable detection tool.

## Disclaimer

This project is for **educational purposes only**. It is a tool for learning about kernel programming, system internals, and rootkit detection techniques. It is not intended for production use as a standalone security solution.
