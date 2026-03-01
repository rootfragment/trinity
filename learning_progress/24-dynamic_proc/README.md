# Stealth Proc: Linux Kernel Module

Stealth Proc is a Linux Kernel Module (LKM) designed to provide a configurable interface within the `/proc` filesystem. It demonstrates the creation of dynamic proc directory entries and file operations using the `proc_fs` and `seq_file` APIs.The objective of this excercise is to make a the `proc_file` generation in a randomized manner so that it is difficult for a rootkit to tamper it .
Eventhough the `/proc` entries are not hidden it serves it purpose of trying to make the output a bit more difficult to bypass as we introduce randomness in the naming convention of the detector.

## Functionality

The module performs the following operations:
1.  **Directory Creation:** Creates a custom directory under `/proc` based on a user-defined prefix.
2.  **File Creation:** Populates the custom directory with a read-only file that provides status information.
3.  **Cleanup:** Ensures all registered proc entries are removed upon module unloading to prevent kernel resource leaks.

## Architecture and Implementation

The module is implemented using standard Linux Kernel interfaces:

- **Module Parameters:** Utilizes `module_param` to allow the user to specify a `prefix` at load time. This prefix determines the naming of the directory and the nested file.
- **`proc_fs` API:** Uses `proc_mkdir` and `proc_create` for managing the lifecycle of filesystem entries within the `/proc` tree.
- **`seq_file` Interface:** Implements `proc_ops` using the `seq_file` interface. This provides a robust mechanism for handling large kernel data exports to user space by managing buffering and pagination automatically.
- **Memory Safety:** Includes validation checks for parameter length and ensures atomic cleanup during the `__exit` routine.

## Build Instructions

To compile the module, ensure the kernel development headers for your running kernel version are installed.

```bash
make
```

The build process will produce the kernel object file `24-dynamic_proc.ko`.

## Usage Instructions

### Loading the Module

The module can be loaded with an optional `prefix` parameter.

```bash
# Loading with a custom prefix
sudo insmod 24-dynamic_proc.ko prefix=workload_monitor

# Loading with the default prefix ("default")
sudo insmod 24-dynamic_proc.ko
```

### Verification

Once loaded, the directory and file can be inspected in `/proc`:

```bash
# List the contents of the created directory
ls /proc/workload_monitor

# Read the module status file
cat /proc/workload_monitor/workload_monitor_mods
```

### Unloading the Module

To remove the module and its associated proc entries:

```bash
sudo rmmod 24-dynamic_proc
```
