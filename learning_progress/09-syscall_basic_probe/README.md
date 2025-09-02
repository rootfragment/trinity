# Kernel Module: Trace `mkdir` Syscall

This Linux kernel module demonstrates how to **trace the `mkdir` system
call** using the **kprobes** framework.\
It records which process invoked `mkdir` and prints the **PID** and
**command name** into the kernel log.

------------------------------------------------------------------------

## Core Idea

-   The Linux kernel provides **kprobes** to dynamically insert probes
    at almost any kernel function.

-   Here, we attach a probe to the syscall handler:

        __x64_sys_mkdir

-   Every time a process calls `mkdir()`, our pre-handler runs and logs
    process details.

------------------------------------------------------------------------

## Key Components

### 1. `handler_pre`

-   The **pre-handler** function that executes *before* the probed
    function.\

-   In this module:

    ``` c
    static int handler_pre(struct kprobe *kp, struct pt_regs *reg) {
        pr_info("[mkdir-trace] pid=%d comm=%s called mkdir\n",
                current->pid, current->comm);
        return 0;
    }
    ```

-   Logs:

    -   `pid` → process ID of the caller.\
    -   `comm` → short command name (max 16 chars).

------------------------------------------------------------------------

### 2. `struct kprobe kp`

-   Defines which function to probe and what handler to use:

    ``` c
    static struct kprobe kp = {
        .symbol_name = "__x64_sys_mkdir",
        .pre_handler = handler_pre,
    };
    ```

-   `symbol_name` → kernel symbol to hook (`__x64_sys_mkdir`).\

-   `pre_handler` → function to run on each call.

------------------------------------------------------------------------

### 3. `probe_init`

-   Called when the module is loaded:

    ``` c
    static int __init probe_init(void) {
        pr_info("MODULE LOADED\n");
        int ret = register_kprobe(&kp);
        if (ret < 0) {
            pr_info("Registering module failed error code %d\n", ret);
            return ret;
        }
        pr_info("Probe registered successfully\n");
        return 0;
    }
    ```

-   Registers the kprobe.\

-   Prints logs for success or failure.

------------------------------------------------------------------------

### 4. `probe_exit`

-   Called when the module is unloaded:

    ``` c
    static void __exit probe_exit(void) {
        unregister_kprobe(&kp);
        pr_info("Probe removed , Unloading module\n");
    }
    ```

-   Ensures cleanup so the kernel is restored to normal state.

------------------------------------------------------------------------

## Module Lifecycle

1.  **On Load**
    -   Prints `"MODULE LOADED"`.\
    -   Registers the probe on `__x64_sys_mkdir`.\
    -   Prints `"Probe registered successfully"`.
2.  **When `mkdir()` is Called**
    -   `handler_pre` runs.\
    -   Logs process PID and command name.
3.  **On Unload**
    -   Removes the probe.\
    -   Prints `"Probe removed , Unloading module"`.

------------------------------------------------------------------------

## Notes & Limitations

-   This module does **not capture the directory path** --- only PID and
    process name.
-   Requires **root privileges** to load/unload.\
-   Needs kernel headers installed (`linux-headers-$(uname -r)`).\
-   Will log every `mkdir()` call from every process --- noise may
    appear if many background processes create directories.

------------------------------------------------------------------------
