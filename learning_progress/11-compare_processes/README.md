# Process Comparison Tool (Userspace + Kernel Module)

## Overview

This project demonstrates a method to **detect hidden or suspicious
processes** in a Linux system by comparing process lists obtained from
**userspace (`ps`)** and **kernelspace (`/proc`)**.

Modern rootkits often attempt to hide processes from system utilities
such as `ps`, `top`, or `htop` by intercepting syscalls and filtering
output. However, they usually fail to remove the process entirely from
kernel-level structures like the `task_struct` list.

This project leverages that fact by: 1. Collecting process information
from **userspace (`ps`)**. 2. Collecting process information directly
from the **kernel process list** using a custom kernel module. 3.
Comparing both datasets to identify: - Processes that are hidden from
`ps` but exist in the kernel. - Processes that appear in `ps` but not in
the kernel (rare, but indicates corruption or inconsistencies).

------------------------------------------------------------------------

## How It Works

### 1. Kernel Module

-   A **Linux kernel module (LKM)** is created, which exposes process
    information via a **`/proc` entry**.
-   It iterates over the kernel's task list (`task_struct`) and writes:
    -   PID (Process ID)
    -   Command name (comm)
-   The result is made available under `/proc/p1`.

This ensures the data is gathered **directly from kernel structures**,
bypassing userspace libraries or utilities that can be hooked or
tampered with.

------------------------------------------------------------------------

### 2. Userspace Program

-   A Python script is used to gather:
    -   Process list from `ps` (`subprocess.check_output`).
    -   Process list from `/proc/p1` (output of the kernel module).
-   The script compares the two lists:
    -   **Missing from ps** → Hidden processes (likely malicious or
        cloaked).
    -   **Missing from kernel** → Phantom entries in ps (indicates
        corruption or tampering).

------------------------------------------------------------------------

### 3. Comparison Logic

-   Results are clearly displayed:
    -   `[!] Hidden from ps:` → Processes detected in the kernel but
        absent from `ps`.
    -   `[!] Present in ps but missing in kernel:` → Processes shown by
        `ps` but not found in kernel task structures.
-   If nothing unusual is found, messages confirm system integrity.

------------------------------------------------------------------------

## Why This is Practical

-   **Rootkit Detection:**\
    Rootkits often hide their controlling processes from userspace
    utilities. Since this approach reads directly from kernel space,
    such tricks can be uncovered.

-   **Forensics & Incident Response:**\
    Security analysts can quickly detect hidden processes, which might
    indicate malware or unauthorized activity.

-   **Educational Value:**\
    This project is a clear, hands-on demonstration of the difference
    between userspace views (`ps`) and kernel reality (`task_struct`
    list). It helps students and researchers understand process hiding
    techniques and kernel-level detection methods.

------------------------------------------------------------------------

## Usage

1.  **Build & Insert the Kernel Module**

    ``` bash
    make
    sudo insmod kernel_module.ko
    ```

    This creates a `/proc/p1` file with kernel process data.

2.  **Run the Python Userspace Script**

    ``` bash
    python3 compare_process.py
    ```

    The script fetches process lists from both `ps` and `/proc/p1`, then
    performs a comparison.

3.  **Interpret Results**

    -   If hidden processes exist, they will be displayed.
    -   If all matches, the tool confirms no inconsistencies.

4.  **Cleanup**

    ``` bash
    sudo rmmod kernel_module
    ```

    This removes the `/proc/p1` entry and unloads the kernel module.

------------------------------------------------------------------------

## Security Considerations

-   This project is **read-only**:\
    It does not modify kernel structures or interfere with running
    processes.

-   It should be run with root privileges since inserting kernel modules
    requires administrative access.

-   Like any kernel code, it must be used responsibly and **never on
    production systems without proper testing**.

------------------------------------------------------------------------
