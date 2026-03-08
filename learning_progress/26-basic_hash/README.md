# Hash Basic: Linux Kernel SHA256 Demonstration Module

## Overview

`hash_basic` is a minimalist Linux kernel module designed to demonstrate the utilization of the Linux Kernel Crypto API (specifically the Synchronous Hash API - `shash`). The module computes the SHA256 message digest of a hardcoded string ("HELLO") upon initialization and outputs the hexadecimal result to the kernel ring buffer.

This project serves as a foundational example for developers looking to integrate cryptographic primitives into kernel-space applications, illustrating the lifecycle of a hash transformation and the necessary memory management patterns required within the kernel environment.

## Technical Architecture

### 1. Kernel Crypto API Integration
The module leverages the `crypto/hash.h` interface to perform synchronous hashing. Unlike asynchronous hashing (which may involve DMA or hardware acceleration that returns later), `shash` operations are performed immediately in the calling context.

### 2. Implementation Flow
The cryptographic process follows a strictly defined lifecycle within the `hash_basic_entry` function:

1.  **Transformation Allocation**: `crypto_alloc_shash("sha256", 0, 0)` is called to find and load the SHA256 algorithm implementation.
2.  **Descriptor Setup**: A `shash_desc` structure is allocated. This structure is critical as it holds the state of the hashing operation. The allocation size must include both the base descriptor and the specific context size required by the chosen algorithm (`crypto_shash_descsize`).
3.  **Hash Lifecycle**:
    *   **Init**: `crypto_shash_init` sets up the initial state.
    *   **Update**: `crypto_shash_update` processes the input data ("HELLO").
    *   **Final**: `crypto_shash_final` completes the computation and extracts the 32-byte digest.
4.  **Reporting**: The result is iterated through and printed using `pr_info` and `pr_cont`.
5.  **Resource Deallocation**: Both the descriptor and the transformation object are freed to prevent memory leaks in kernel space.

### 3. Error Handling
The module implements robust kernel-space error checking using the `IS_ERR()` and `PTR_ERR()` macros. It utilizes a `goto` pattern for clean exit paths, ensuring that if an intermediate step fails, previously allocated resources are correctly released.

## Prerequisites

To build and run this module, your environment must meet the following requirements:
*   **Linux Kernel Headers**: Matching your currently running kernel version.
*   **Build Essentials**: `gcc`, `make`, and standard C development tools.
*   **Root Privileges**: Required for loading and unloading kernel modules (`insmod`/`rmmod`).

## Building the Module

The included `Makefile` uses the standard kbuild system. To compile the module, execute:

```bash
make
```

This will produce several files, the most important being `hash_basic.ko` (the Kernel Object).

## Usage

### Loading the Module
Load the module into the running kernel using `insmod`:

```bash
sudo insmod hash_basic.ko
```

### Viewing the Output
Since the module performs its computation during initialization, you can view the results immediately in the kernel logs:

```bash
dmesg | tail -n 5
```

You should see output similar to:
```text
[   ...] sha256 of HELLO: 185f8db32271fe25f561a6fc938b2e264306ec304eda518007d1764826381969
```

### Unloading the Module
To remove the module from the kernel:

```bash
sudo rmmod hash_basic
```

Check `dmesg` again to see the exit message:
```bash
dmesg | tail -n 1
# Output: Unloading this bad boi
```

## Safety and Best Practices
*   **Kernel Space Caution**: This code runs with full system privileges. Errors can lead to kernel panics or system instability.
*   **Memory Management**: Always ensure `kmalloc` results are checked and that `crypto_free_shash` is called to avoid resource exhaustion.
*   **GPL Compliance**: The module is licensed under GPL to ensure compatibility with kernel symbols exported as `EXPORT_SYMBOL_GPL`.
