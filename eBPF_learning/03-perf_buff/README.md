# eBPF Process Execution Monitor

This program uses eBPF (Extended Berkeley Packet Filter) to monitor process execution on a Linux system. It hooks into the `execve` syscall to capture and report information about every new program that is executed.

## Description

The script attaches an eBPF program to the `execve` syscall. Whenever a new program is launched, the eBPF program captures the process ID (PID), user ID (UID), and the command name. This information is then passed to the user-space Python script, which prints the details to the console.

This tool is a great example of how eBPF can be used for system monitoring and observability. It is a simple yet powerful demonstration of the capabilities of eBPF.

## How it works

The program consists of two parts:

1.  **eBPF program (in C):** This part is loaded into the kernel. It defines a data structure to hold the process information and a function that is attached to the `execve` syscall. When the syscall is triggered, this function collects the data and sends it to a perf buffer.

2.  **User-space program (in Python):** This script loads the eBPF program into the kernel, attaches the eBPF function to the `execve` syscall, and then listens for data from the perf buffer. When data is received, it is formatted and printed to the console.

## Requirements

To run this program, you will need:

*   A Linux system with a kernel version that supports eBPF (4.1 or later is recommended).
*   The `bcc` library, which is a Python framework for creating eBPF programs. You can find installation instructions for `bcc` [here](https://github.com/iovisor/bcc/blob/master/INSTALL.md).
*   Python 3.

## Usage

1.  Make sure you have the necessary requirements installed.
2.  Save the code as a Python file (e.g., `exp_3.py`).
3.  Run the script with root privileges:

    ```bash
    sudo python3 exp_3.py
    ```

4.  The program will start monitoring `execve` syscalls. Open another terminal and run some commands. You will see the process information printed in the terminal where the script is running.

## Example Output

When you run a command like `ls -l` in another terminal, you will see output similar to this:

```
cpu : 0 pid : 12345 uid : 1000 command : ls
```

This indicates that the `ls` command was executed with PID 12345 by a user with UID 1000.
