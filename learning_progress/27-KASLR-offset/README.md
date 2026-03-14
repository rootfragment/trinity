# KASLR Offset Finder

This project consists of a Linux kernel module designed to determine the **Kernel Address Space Layout Randomization (KASLR)** offset. It achieves this by identifying the discrepancy between a symbol's static address (as defined in the system map) and its actual location in memory at runtime.

## Project Components

- **`27-kaslr_offset.c`**: The source code for the kernel module.
- **`Makefile`**: The build script that handles environment-specific configurations and compilation.

---

## 1. Analysis of `27-kaslr_offset.c`

The kernel module is responsible for the runtime discovery and calculation of the KASLR offset.

### Key Functional Areas:

#### A. Runtime Symbol Resolution (`resolve_kallsyms`)
Modern kernels often do not export `kallsyms_lookup_name` to prevent easy exploitation. This module circumvents this by using a **Kprobe**.
- It registers a Kprobe on the `kallsyms_lookup_name` symbol.
- Once registered, the Kprobe structure (`kp.addr`) contains the actual memory address of the function.
- It then unregisters the Kprobe and stores the address in a function pointer for subsequent use.

#### B. Offset Calculation (`kaslr_finder_init`)
Upon initialization (`insmod`), the module performs the following:
1.  **Locates the Target**: It calls `kallsyms_lookup_name_ptr("__x64_sys_getpid")` to find where the `getpid` syscall handler is currently residing in memory.
2.  **Computes the Difference**: It subtracts the `STATIC_SYSCALL_ADDR` (provided during compilation) from the `runtime_addr`.
    - `kaslr_offset = runtime_addr - static_anchor_addr;`
3.  **Reporting**: It prints the results to the kernel log (`dmesg`), providing the symbol name, the static base, the runtime address, and the resulting KASLR offset.

#### C. Cleanup (`kaslr_finder_exit`)
The exit function simply logs that the module has been unloaded, ensuring a clean removal from the kernel space.

---

## 2. Analysis of the `Makefile`

The Makefile is sophisticated as it dynamically pulls information from the host system to configure the module.

### Workflow Breakdown:

- **Target Definition**: `obj-m += kaslr_offset_finder.o` specifies that the final module will be named `kaslr_offset_finder.ko`.
- **Static Address Extraction**:
  ```makefile
  STATIC_ADDR := 0x$(shell sudo grep " T $(SYSCALL_SYMBOL)$$" /boot/System.map-$(shell uname -r) | awk '{print $$1}')
  ```
  - It identifies the current kernel version using `uname -r`.
  - It searches `/boot/System.map` for the `__x64_sys_getpid` symbol.
  - The `awk` command extracts the hexadecimal address from the first column. This address represents where the symbol *would* be if KASLR were disabled.
- **Compiler Flags**:
  ```makefile
  EXTRA_CFLAGS_kaslr_offset_finder.o := -DSTATIC_SYSCALL_ADDR=$(STATIC_ADDR) ...
  ```
  - It uses `-D` to define preprocessor macros. This "injects" the static address discovered by the shell command directly into the C code at compile time.
- **Build Commands**:
  - `all`: Invokes the standard kernel build system pointing to the current directory (`M=$(PWD)`).
  - `clean`: Cleans the build artifacts.

---

## 3. How to Use

### Build
To compile the module, run:
```bash
make
```

### Load
Insert the module into the kernel:
```bash
sudo insmod kaslr_offset_finder.ko
```

### Verify
Check the kernel logs to see the calculated KASLR offset:
```bash
dmesg | tail -n 5
```

### Unload
Remove the module:
```bash
sudo rmmod kaslr_offset_finder
```

---

## Technical Significance

KASLR is a security feature that randomizes the base address of the kernel image on every boot to mitigate "Return-to-libc" and similar memory corruption attacks. This tool is a fundamental utility for security researchers and kernel developers to verify if KASLR is active and to understand how the kernel is being mapped into memory on a specific system.
KASLR requires entropy at runtime, most VMs disable it by default to make the boot process simpler and also due to low entropy.
It can be turned off by running `nokaslr` command or editing grub configuration.  
