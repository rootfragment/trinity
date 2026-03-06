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
1.  A **Linux Kernel Module (LKM)** that acts as a trusted observer, gathering raw data directly from kernel data structures.
2.  A **Python user-space client** that orchestrates scans, performs comparisons, and reports findings.

## Features

- **Process Hiding Detection**: Uncovers processes that are running but are hidden from user-space tools like `ps`.
- **Module Hiding Detection**: Detects Loadable Kernel Modules (LKMs) that are active in the kernel but invisible to `lsmod`.
- **Hidden Port Detection**: Finds network listening ports that are open and active but are concealed from utilities like `ss` and `netstat`.
- **Syscall Integrity Checking**: Detects unauthorized modifications (hooking) to the system call table.
- **Continuous Syscall Monitoring**: When running in interactive mode, Argus maintains a background thread that monitors the syscall table every 3 seconds, providing real-time alerts upon tampering.
- **Background Daemon Mode**: Supports running as a persistent background process that performs periodic full-system scans and sends alerts to remote listeners.
- **Advanced Filesystem Forensics**: Enumerates directories from the kernel's perspective to uncover hidden files, "phantom" files (user-space only), and metadata mismatches (size, inode, permissions).
- **Threat Analysis**: Provides a high-level summary of detected anomalies to help classify the potential threat (e.g., User-land Rootkit, Kernel-Level Rootkit).
- **Configurable UDP Alerting**: Sends alerts containing scan findings to one or more remote listeners over UDP, allowing for centralized monitoring.

## How It Works

Argus's detection strategy relies on establishing a trusted baseline from the kernel's perspective and comparing it against the potentially compromised user-space environment.

### Kernel Module (`argus_lkm.ko`)

The kernel module is the core of the detection engine. When loaded, it creates several entries in the `/proc` filesystem:

-   `/proc/rk_ps`: Exposes a list of all running processes by directly iterating through the kernel's task list (`for_each_process`).
-   `/proc/rk_mods`: Exposes a list of all loaded kernel modules by traversing the internal module list.
-   `/proc/rk_sockets`: Exposes a list of all listening TCP and UDP sockets by inspecting kernel network data structures.
-   `/proc/rk_syscalls`: Performs an integrity check of the system call table by comparing it against a "golden" copy captured at boot/load time.
-   `/proc/rk_fs`: Allows for directory enumeration. By writing a path to this entry, the kernel iterates through the directory and returns a full list of entries and their metadata.

This data, coming directly from the kernel, is considered a "ground truth" view of the system's state.

### User-Space Client (`argus_cli.py`)

The Python client provides a command-line interface to interact with the kernel module and perform scans. For each scan type, it:

1.  **Reads the "ground truth"** from the corresponding `/proc` file created by the Argus kernel module.
2.  **Gathers the user-space view** by executing standard Linux commands (`ps`, `cat /proc/modules`, `ss`).
3.  **Compares the two lists** and reports any items present in the kernel's list but missing from the user-space list.
4.  **Sends alerts** and provides a final analysis based on the findings.

## Getting Started

### Prerequisites

- A Linux system with kernel headers installed (required to build the module). The package name is typically `linux-headers-$(uname -r)`.
- `make` and `gcc`.
- Python 3.

### Compilation

Navigate to the project directory and compile the kernel module:

```bash
make
```

This will produce the kernel object file: `argus_lkm.ko`.

### Configuration

The user-space client can send UDP alerts to remote systems. To configure the listeners, edit the `config.json` file. A default file is created automatically if one is not found.

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
    Argus can be run in **Interactive Mode** or **Daemon Mode**.
    
    **Interactive Mode:**
    ```bash
    sudo python3 User_space/argus_cli/argus_cli.py
    ```
    (Note: A background thread will automatically start monitoring syscall integrity every 3 seconds while in interactive mode.)

    **Daemon Mode (Background):**
    Run Argus in the background to perform full scans at a regular interval (e.g., every 60 seconds) and send alerts to your listeners:
    ```bash
    sudo python3 User_space/argus_cli/argus_cli.py -t 60
    ```
    
    **Stopping the Daemon:**
    ```bash
    sudo python3 User_space/argus_cli/argus_cli.py --stop
    ```

3.  **Set Up the Alert Receiver**:
    Argus includes a standalone UDP receiver to log alerts from one or more machines.
    
    **Run Interactive Receiver:**
    ```bash
    python3 User_space/argus_alert_receiver/argus_alert_receiver.py
    ```
    
    **Run Receiver as Daemon:**
    ```bash
    python3 User_space/argus_alert_receiver/argus_alert_receiver.py --daemon
    ```
    
    **Stopping the Receiver Daemon:**
    ```bash
    python3 User_space/argus_alert_receiver/argus_alert_receiver.py --stop
    ```

4.  **Use the Interactive Menu**:
    The client will present a menu with the following options:
    - `[1] Compare Processes`: Scan for hidden processes.
    - `[2] Compare Kernel Modules`: Scan for hidden LKMs.
    - `[3] Compare Network Ports`: Scan for hidden listening ports.
    - `[4] Perform Syscall Integrity Scan`: Detect modifications to the system call table.
    - `[5] Perform Full Scan`: Run all checks sequentially (Process, Module, Port, FS, Syscall).
    - `[6] Perform Filesystem Scan`: Explore directories for hidden files and metadata anomalies (based on `dir_list.txt`).
    - `[7] Toggle UDP Alert`: Enable or disable sending findings via UDP for the current session.
    - `[99] Exit`: Terminate the client (does not unload the kernel module).

5.  **Unload the Kernel Module**:
    When you are finished, unload the module to clean up the `/proc` entries.
    ```bash
    sudo rmmod argus_lkm
    ```

## Project Structure

```
.
├── Kernel_space/        # Source code for the LKM
│   ├── core.c           # Main kernel module file (init, exit, proc creation)
│   ├── process.c / .h   # Logic for iterating kernel processes
│   ├── modules.c / .h   # Logic for iterating modules
│   ├── socket.c / .h    # Logic for iterating network sockets
│   ├── syscall.c / .h   # Logic for syscall table integrity
│   └── fs.c / .h        # Logic for filesystem iteration
└── User_space/          # Source code for the Python client
    ├── argus_cli/       # CLI and detection logic
    └── argus_alert_receiver/ # UDP alert listener
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
    make
    ```

3.  **Review the configuration:**
    Before running, review and edit the `config.json` file to set up your desired UDP alert listeners.

4.  **Run the tool:**
    Follow the instructions in the [Usage](#usage) section.

## Threat Model and Limitations

### In-Scope Threats
- **Stealth Malware:** The primary target is malware that actively hides its presence by manipulating the data returned to standard user-space tools.
- **Process/Module/Port Hiding:** It is effective against rootkits that hook syscalls like `getdents64` or modify the results of `/proc` reads to hide files, processes, kernel modules, or network connections from tools like `ps`, `lsmod`, and `ss`.
- **Syscall Hooking:** Unauthorized system call table modifications used to intercept system calls to hide presence or alter system behavior.
- **Metadata Manipulation:** Rootkits that alter file size, permissions, or timestamps to hide malicious changes.
- **Persistent Stealth:** Detection of persistent hiding across reboots via daemon mode and background monitoring.

### Out-of-Scope Threats
- **Non-Stealth Malware:** Argus is not a signature-based antivirus; it will not detect malware that doesn't actively hide itself.
- **Argus-Specific Countermeasures:** A sophisticated rootkit could potentially detect Argus by its `/proc` entries, kill its process, block its UDP traffic, or temporarily disable its own hiding mechanisms to evade a scan.
- **User-land Library Injection:** Some rootkits compromise libraries (e.g., via `LD_PRELOAD`) instead of the kernel. Argus would not detect this.
- **Bootkits and Firmware-level Threats:** Argus operates only when the Linux kernel is running and cannot detect threats that compromise the bootloader or underlying firmware.
- **Direct Memory Access (DMA) Attacks:** Attacks that bypass the CPU and Kernel entirely to read/write memory.

## Project Analysis

#### Advantages (Pros)

*   **Deep Visibility**: Operating from within the kernel provides a privileged viewpoint that is more trustworthy than user-space tools alone.
*   **Effective Detection Principle**: The core logic of comparing kernel and user-space views is a proven method for uncloaking many common rootkit hiding techniques.
*   **Comprehensive Scans**: Argus covers the three most common hiding places: processes, kernel modules, and network ports.
*   **User-Friendly**: The Python client offers a clear interface, actionable summaries, and helpful features like UDP alerting, making it easy to use and integrate into a lab environment.

#### Disadvantages (Cons)

*   **Predictable Footprint**: The use of well-known `/proc` file names (`rk_ps`, `rk_mods`, etc.) creates a predictable footprint that could be detected and targeted by advanced malware.
*   **Snapshot-in-Time**: The scans are not continuous. A sophisticated rootkit could potentially detect the scan and temporarily hide its activities, leading to a false negative.
*   **Requires Root Privileges**: Like all tools of this nature, it must be run as root. This carries inherent risk, and a compromised Argus tool could become a security threat itself.
  

### Explored Research: Runtime Integrity Verification

During the development of this project, a more advanced detection concept was explored: **runtime integrity verification of kernel modules**.

The idea was to have the Argus kernel module calculate a cryptographic hash (e.g., SHA-256) of the executable `.text` section of all other loaded kernel modules. This hash could then be compared against a known-good baseline to detect if a module's code had been tampered with in memory (a technique used by some advanced malware).

This feature was **successfully implemented on older Linux kernel versions** (pre-4.x). However, it was ultimately not included in the final framework because it is **no longer feasible on modern kernels**. Due to critical security enhancements like `CONFIG_STRICT_MODULE_RWX`, the memory pages holding executable kernel code are marked as read-only and non-executable data is strictly separated. These protections prevent one kernel module from easily reading the executable code of another, making the hashing attempt fail. While there are complex and unstable methods to bypass this for research, it goes against the security-first principles of modern kernel design, making it an impractical feature for a stable detection tool.

## Disclaimer

This project is for **educational purposes only**. It is a tool for learning about kernel programming, system internals, and rootkit detection techniques. It is not intended for production use as a standalone security solution.
