# Kprobe Example: Monitoring `mkdir` Syscall

This kernel module demonstrates how to use **kprobes** to trace the
`mkdir` system call on x86_64 Linux.
---
## Working

-   Attaches a probe to the `__x64_sys_mkdir` symbol (the system call
    entry point for `mkdir`).
-   Extracts the syscall arguments:
    -   **filename** (user-space pointer to the directory path)
    -   **mode** (permission bits for the new directory)
-   Safely copies the filename from user space into the kernel buffer.
-   Prints details whenever a process calls `mkdir`:


```
    [mkdir-probe] pid=1234 comm=myprocess path=/tmp/newdir mode=0755

```
---
## Code Breakdown

-   **handler_pre()**: Runs before the probed function executes.

    -   Reads syscall arguments from registers (`regs->di` = first arg,
        `regs->si` = second arg).\
    -   Copies filename from user space using `strncpy_from_user`.\
    -   Handles errors gracefully (`<FAULT>` if invalid, `<NULL>` if
        pointer is null).\
    -   Logs PID, process name, path, and mode.

-   **kp struct**: Defines the probe, attaching to `__x64_sys_mkdir`.

-   **probe_entry() / probe_exit()**: Registers and unregisters the
    probe.

---
## Notes on Registers

On x86_64 Linux syscall ABI:\
- 1st arg → `rdi` (`regs->di` in kernel) - 2nd arg → `rsi`
(`regs->si`) - This is why we fetch `filename` from `regs->di` and
`mode` from `regs->si`.
---
## Warning 

This example attaches to the symbol `__x64_sys_mkdir`.\
On some modern kernels, this symbol may:\
- Be renamed (e.g., `__x64_sys_mkdirat` instead).\
- Or not be exported / available.

Additionally, the filename pointer comes from **user space**. If it
points to invalid memory, the kernel may return `<FAULT>`.\
Always be careful when copying data from user space in kernel modules.


---
