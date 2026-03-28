# KASLR Offset Finder (Multi-Anchor Verification)

This project consists of a Linux kernel module designed to accurately determine and verify the **Kernel Address Space Layout Randomization (KASLR)** offset. Unlike basic tools that rely on a single memory address, this implementation uses a robust **multi-anchor verification** strategy to ensure the integrity of the calculated offset against potential interference, such as rootkit hooks.

## 1. Overview

Kernel Address Space Layout Randomization (KASLR) is a critical security feature that randomizes the base address of the kernel image upon every boot. This prevents attackers from using fixed addresses for return-oriented programming (ROP) or other memory-corruption exploits.

The **KASLR Offset Finder** calculates the discrepancy between a symbol's **static address** (from the system map) and its **runtime address** (actual location in memory).

### The Multi-Anchor Strategy
The core enhancement in this version is the use of **three independent syscall anchors**:
1.  `__x64_sys_getpid`
2.  `__x64_sys_getuid`
3.  `__x64_sys_getgid`

#### Why Use Three Syscalls?
-   **Rootkit Resilience**: Rootkits often "hook" specific syscalls to hide processes, files, or network connections. If a rootkit hooks `getpid`, the runtime address for that syscall will point to the rootkit's malicious code rather than the original kernel handler. This would result in a bogus KASLR offset calculation.
-   **Verification Consistency**: By calculating the offset for three different syscalls and comparing them, the module can mathematically confirm the result. If all three offsets match, the probability of the KASLR offset being correct—and the system being unhooked at those points—is significantly higher.
-   **Inconsistency Detection**: If one offset differs from the others, the module logs an error. This serves as a primitive but effective **Rootkit Detection** mechanism, signaling that one or more syscall handlers have been diverted.

#### Choice of Syscalls
The syscalls `getpid`, `getuid`, and `getgid` were chosen for several strategic reasons:
-   **Simplicity and Stability**: These are low yeild systemcalls, that is a rootkit cant do much with it even if it does hooks these systemcalls and hence are usually left alone.
-   **System Map Availability**: These symbols are consistently exported and easy to locate in `System.map`, ensuring the `Makefile` can reliably extract their static addresses across different distributions.

---

## 2. Working Mechanism Thoroughly Explained

### A. Static Address Acquisition (Compile-Time)
The `Makefile` performs automated reconnaissance on the host system:
```makefile
STATIC_ADDR1 := 0x$(shell sudo grep " T $(SYSCALL1)$$" /boot/System.map-$(shell uname -r) | awk '{print $$1}')
```
- It identifies the current kernel version and reads `/boot/System.map`.
- It extracts the "base" address (where the symbol resides when KASLR offset is 0).
- These addresses are injected into the C code as preprocessor macros (`STATIC_ADDR1`, `STATIC_ADDR2`, etc.).

### B. Runtime Symbol Resolution (Initialization)
Modern kernels do not export `kallsyms_lookup_name` to prevent easy exploitation by modules. This tool circumvents this limitation using a **Kprobe**:
- It registers a Kprobe on the `kallsyms_lookup_name` symbol.
- The Kprobe infrastructure provides the actual memory address of the function through `kp.addr`.
- The module then uses this resolved pointer to find the live memory addresses of our three syscall anchors.

### C. Offset Calculation and Verification
The module iterates through the anchors:
1.  **Discovery**: Fetches `runtime_addr` for each syscall via `kallsyms_lookup_name`.
2.  **Calculation**: `current_offset = runtime_addr - static_addr`.
3.  **Comparison**: The first calculated offset is used as the "Gold Standard." Subsequent offsets are compared against it.
4.  **Logging**: All results are printed to `dmesg`. If a mismatch occurs, a `pr_err` is triggered, warning of potential system inconsistency or rootkit activity.

---

## 3. How to Use

### Build
To compile the module and automatically fetch system-specific static addresses:
```bash
make
```

### Load
Insert the module into the kernel:
```bash
sudo insmod 28-kaslr_adv.ko
```

### Verify Results
Check the kernel logs for the verification report:
```bash
dmesg | grep "KASLR Finder"
```
**Expected Output (Clean System):**
```text
KASLR Finder: Verifying across 3 symbols
KASLR Finder: [Symbol: __x64_sys_getpid] [Static: 0xffffffff810a...] [Runtime: 0xffffffff9a0a...] [Offset: 0x19000000]
...
KASLR Finder: Verified! KASLR Offset is consistently 0x19000000
```

### Unload
Remove the module:
```bash
sudo rmmod 28-kaslr_adv
```

---

## Technical Significance

The program is an improvement to the earlier KASLR finder program, which uses only one syscall entry to find the offset. This is however fragile, because if the getpid() is hooked we will be working with a corrupted KASLR offset.
This will in turn convert to false negetives when i implement the out-of-band syscall integerity check using using `system.map` vs runtime address comparion.
