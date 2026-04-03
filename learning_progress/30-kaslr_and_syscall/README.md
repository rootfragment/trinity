# KASLR Offset & Syscall Inspector Toolkit

A Linux kernel module for runtime syscall table inspection and KASLR (Kernel Address Space Layout Randomization) offset derivation. Designed for kernel security research, exploit development analysis, and low-level system introspection on x86-64 Linux systems.

---



## Overview

Modern Linux kernels randomize kernel memory layout at boot via KASLR, making it non-trivial to derive the relationship between compile-time (static) symbol addresses and their actual runtime locations. This toolkit bridges that gap using a three-stage pipeline:

1. **`syscall_reporter`** — A loadable kernel module (LKM) that exposes the live syscall table via `/proc/syscall_live`, resolving each entry's symbol name at runtime.
2. **`syscall_optimizer.py`** — A userspace Python script that correlates live symbol names against the static addresses in `/boot/System.map-<kernel>`, producing a clean mapping of `static_address → symbol_name`.
3. **`kaslr_offset_proc`** — A second LKM that consumes pre-selected anchor symbols (injected at compile time via the Makefile) and cross-references their static vs. runtime addresses to derive and verify the KASLR slide, exposing the result via `/proc/kaslr_offset`.

```
┌─────────────────────────────────────────────────────────────────┐
│                         PIPELINE FLOW                           │
│                                                                 │
│  syscall_reporter  ──►  /proc/syscall_live                      │
│        │                      │                                 │
│        │               syscall_optimizer.py                     │
│        │                (correlates with System.map)            │
│        │                      │                                 │
│        │               syscall_optimised.txt                    │
│        │               (static_addr → symbol_name)              │
│        │                      │                                 │
│        └──────────────► Makefile reads anchors                  │
│                               │                                 │
│                         kaslr_offset_proc                       │
│                               │                                 │
│                         /proc/kaslr_offset  ◄── KASLR slide     │
└─────────────────────────────────────────────────────────────────┘
```

---

## Components

### 1. `syscall_reporter` (Kernel Module)

**File:** `syscall_reporter.c`

A lightweight kernel module that enumerates all `NR_syscalls` entries in the live `sys_call_table` and exposes them as human-readable symbol names through the procfs interface at `/proc/syscall_live`.

**Key mechanics:**

- Uses a `kprobe` on `kallsyms_lookup_name` to recover a pointer to that function (necessary since it is no longer exported in kernels ≥ 5.7).
- Iterates the syscall table, calling `sprint_symbol()` on each entry to resolve the kernel symbol name and offset.
- Registers a `proc_ops`-based read handler using `seq_file` for efficient, paginated output.

**Output format (`/proc/syscall_live`):**

```
  0 | __x64_sys_read+0x0/0x40
  1 | __x64_sys_write+0x0/0x40
  2 | __x64_sys_open+0x0/0x40
  ...
```

Each line contains the syscall number and the resolved symbol (with offset), separated by `|`.

---

### 2. `syscall_optimizer.py` (Userspace Script)

**File:** `syscall_optimizer.py`

A Python 3 script that acts as the bridge between the live syscall table and the static symbol map. It reads `/proc/syscall_live` produced by `syscall_reporter`, looks up each symbol's compile-time address in `/boot/System.map-<kernel>`, and writes a deduplicated `static_address symbol_name` mapping to `syscall_optimised.txt`.

**Key mechanics:**

- Automatically detects the running kernel version via `platform.release()` to locate the correct `System.map` file.
- Filters the `System.map` to only text/weak symbols (`t`, `w` type codes), avoiding data and debug entries.
- Strips the `+offset` suffix from `sprint_symbol` output before performing the lookup.
- Deduplicates by symbol name, ensuring each symbol appears exactly once in the output regardless of how many syscall table slots share the same handler.

**Output file (`syscall_optimised.txt`):**

```
ffffffff81234560 __x64_sys_getpid
ffffffff81234590 __x64_sys_getuid
...
```

This file is used directly by the Makefile to supply anchor addresses to `kaslr_offset_proc`.

**Error handling:**

| Condition | Behaviour |
|---|---|
| `System.map` not found | Prints path and exits |
| Permission denied on `System.map` | Advises `sudo` and exits |
| `syscall_reporter` module not loaded | Prints warning and exits |

---

### 3. `kaslr_offset_proc` (Kernel Module)

**File:** `29-kaslr_offset_proc.c`

The core module responsible for computing and verifying the KASLR offset. It receives up to three anchor syscall symbols (name + static address pairs) injected as compile-time `#define` macros, resolves each symbol's current runtime address using `kallsyms_lookup_name`, and computes the offset as:

```
kaslr_offset = runtime_address - static_address
```

It verifies consistency across all anchors: if all computed offsets agree, the result is written to `/proc/kaslr_offset`. Any mismatch is flagged as a potential integrity anomaly.

**Verification states exposed via `/proc/kaslr_offset`:**

| Output | Meaning |
|---|---|
| `0x<hex_value>` | KASLR slide verified consistently across all anchors |
| `Mismatch of offsets.` | Anchor offsets do not agree — possible rootkit/hook present |
| `Couldnt resolve anchor at runtime.` | `kallsyms_lookup_name` returned NULL for one or more anchors |
| `Unknown error occurred.` | Internal state error |

**Security note:** An inconsistent offset across anchors can indicate that one or more syscall table entries have been hooked or redirected — a common rootkit technique. This module provides a passive, read-only signal of such tampering.

---

### 4. `Makefile`

**File:** `Makefile`

Orchestrates the build of both kernel modules and automates the injection of anchor symbol data into `kaslr_offset_proc` at compile time.

**Default anchor syscalls:**

```makefile
SYSCALL1 := __x64_sys_getpid
SYSCALL2 := __x64_sys_getuid
SYSCALL3 := __x64_sys_getgid
```

These can be overridden on the command line (see [Usage](#usage)).

**At build time, the Makefile:**
1. Reads `/boot/System.map-$(uname -r)` (requires `sudo`) to extract the static virtual address of each anchor symbol.
2. Passes those addresses and names to the compiler as `-D` preprocessor flags, baking them directly into the `kaslr_offset_proc` binary.

**Targets:**

| Target | Action |
|---|---|
| `make all` | Build both kernel modules |
| `make clean` | Remove build artifacts |

---

## How It Works

### The `kallsyms_lookup_name` Problem

Since Linux kernel 5.7, `kallsyms_lookup_name` is no longer exported to modules. Both modules work around this by registering a temporary `kprobe` on `kallsyms_lookup_name` to capture its address, then immediately unregistering the probe. This is a well-known technique for recovering unexported symbol addresses.

### KASLR Offset Derivation

KASLR randomises the base address of the kernel image at each boot. All kernel symbols are shifted by the same constant offset. Given:

- **Static address** (`S`): the address from `System.map`, i.e., the address without KASLR.
- **Runtime address** (`R`): the address resolved via `kallsyms_lookup_name` at runtime.

Then: `KASLR offset = R - S`

By computing this for multiple independent symbols and checking that all results agree, the module achieves high confidence in the derived offset.

---

## Prerequisites

- Linux kernel with `CONFIG_KPROBES=y` and `CONFIG_KALLSYMS=y`
- Kernel headers installed for the running kernel:
  ```bash
  sudo apt install linux-headers-$(uname -r)   # Debian/Ubuntu
  sudo dnf install kernel-devel                 # Fedora/RHEL
  ```
- `gcc`, `make`
- Python 3 (standard library only)
- Read access to `/boot/System.map-$(uname -r)` (typically requires `sudo`)
- Ability to load kernel modules (`CAP_SYS_MODULE` / root)

---

## Building

### Step 1 — Build the kernel modules

```bash
sudo make all
```

This will read `/boot/System.map` to extract anchor addresses and compile both modules. Successful output ends with:

```
  LD [M]  /path/to/syscall_reporter.ko
  LD [M]  /path/to/29-kaslr_offset_proc.ko
```

To override the default anchor syscalls:

```bash
sudo make all SYSCALL1=__x64_sys_read SYSCALL2=__x64_sys_write SYSCALL3=__x64_sys_open
```

> **Note:** Anchor symbols must be present in `/boot/System.map-$(uname -r)` with type `T`. Use `grep ' T __x64_sys_' /boot/System.map-$(uname -r)` to find valid candidates.

### Step 2 — (Optional) Generate `syscall_optimised.txt` for custom anchors

If you want to select anchors from the live syscall table rather than using the defaults:

```bash
sudo insmod syscall_reporter.ko
sudo python3 syscall_optimizer.py
sudo rmmod syscall_reporter
```

Then pick entries from `syscall_optimised.txt` and rebuild with those as your `SYSCALL1/2/3` values.

### Step 3 — Clean build artifacts

```bash
make clean
```

---

## Usage

### Loading and reading `syscall_reporter`

```bash
# Load the module
sudo insmod syscall_reporter.ko

# Read the live syscall table
cat /proc/syscall_live

# Example output:
#   0 | __x64_sys_read+0x0/0x40
#   1 | __x64_sys_write+0x0/0x40
# ...

# Unload when done
sudo rmmod syscall_reporter
```

### Running `syscall_optimizer.py`

Requires `syscall_reporter` to be loaded and read access to `System.map`:

```bash
sudo python3 syscall_optimizer.py
# [*] Successfully identified 312 runtime syscalls.
# [*] Generated syscall_optimised.txt using STATIC addresses

cat syscall_optimised.txt
```

### Loading and reading `kaslr_offset_proc`

Requires the module to have been compiled with valid anchor addresses (Step 1 above):

```bash
# Load the module
sudo insmod 29-kaslr_offset_proc.ko

# Read the KASLR offset
cat /proc/kaslr_offset
# Example: 0x1a200000

# Unload when done
sudo rmmod 29-kaslr_offset_proc
```

Check kernel logs for diagnostic messages:

```bash
sudo dmesg | tail -20
```

---

## Security Considerations

- **Root required.** Loading kernel modules requires `CAP_SYS_MODULE`. All operations here run in ring 0 once modules are loaded. Only use on systems you own or are explicitly authorised to test.
- **Tamper detection.** The multi-anchor verification in `kaslr_offset_proc` provides a passive signal of syscall table hooks. A `Mismatch of offsets.` result warrants further investigation with a tool like `unhide` or a kernel integrity checker.
- **Read-only procfs entries.** Both `/proc/syscall_live` and `/proc/kaslr_offset` are created with mode `0444` — no write surface is exposed.
- **Kernel version compatibility.** The `kprobe`-based `kallsyms_lookup_name` workaround is tested on kernels ≥ 5.7. Behaviour on older kernels (where `kallsyms_lookup_name` was still exported) is untested but should degrade gracefully.

---

## Limitations

- **x86-64 only.** The anchor syscall names (`__x64_sys_*`) and `System.map` address format are specific to `x86_64`. Porting to other architectures requires updating symbol naming conventions.
- **Three anchors maximum.** The Makefile and `kaslr_offset_proc.c` support up to three anchor symbols. This is sufficient for high-confidence verification but could be extended by adding further `#ifdef SYSCALN_NAME` blocks.
- **System.map must match running kernel.** If the `System.map` does not correspond exactly to the loaded kernel image (e.g., after an update without reboot), static addresses will be incorrect and the KASLR calculation will fail or produce wrong results.
- **Secure Boot / lockdown.** On systems with kernel lockdown mode enabled, loading unsigned kernel modules may be blocked regardless of root privileges.

---
