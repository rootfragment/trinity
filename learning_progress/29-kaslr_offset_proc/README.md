# kaslr-offset-probe

A Linux kernel module that computes and exposes the **KASLR (Kernel Address Space Layout Randomization) slide offset** at runtime by cross-referencing static symbol addresses from `System.map` against live addresses resolved via `kallsyms_lookup_name`. The verified offset is exposed to all users through `/proc/kaslr_offset`.

---

## Table of Contents

- [Overview](#overview)
- [How It Works](#how-it-works)
- [Security Model](#security-model)
- [Requirements](#requirements)
- [Building](#building)
- [Usage](#usage)
- [Output Reference](#output-reference)
- [Internals](#internals)
- [Caveats](#caveats)
- [License](#license)

---

## Overview

KASLR randomizes the base address of the kernel image on each boot to make exploitation harder. This module determines the exact slide by:

1. Reading the **compile-time (static) addresses** of known syscall symbols from `/boot/System.map-$(uname -r)` at build time via the Makefile.
2. Resolving those same symbols' **runtime addresses** using `kallsyms_lookup_name` (accessed via kprobes, since it is no longer exported in kernels ≥ 5.7).
3. Computing `offset = runtime_addr - static_addr` for each anchor and **verifying consistency** across all of them.
4. Exposing the result at `/proc/kaslr_offset`, readable by any user.

If the offsets across anchors disagree, the module flags a potential integrity violation (e.g. a rootkit hooking symbol resolution).

---

## How It Works

```
System.map (build time)          kallsyms_lookup_name (runtime)
        │                                    │
        ▼                                    ▼
 static_addr[0..2]               runtime_addr[0..2]
        │                                    │
        └──────────── offset = runtime - static ──────────────┐
                                                               ▼
                                                   all equal? → /proc/kaslr_offset
                                                   mismatch?  → error string
```

Three syscall symbols are used as anchors by default:

| Anchor | Symbol |
|--------|--------|
| 1 | `__x64_sys_getpid` |
| 2 | `__x64_sys_getuid` |
| 3 | `__x64_sys_getgid` |

Using multiple independent anchors means a single corrupted or hooked symbol cannot produce a false positive — all three must agree.

---

## Security Model

| Threat | Detection |
|--------|-----------|
| Single symbol hook (rootkit) | Offset mismatch across anchors → error reported |
| KASLR disabled (offset = 0x0) | Valid, reported correctly |
| Symbol not found at runtime | Explicit `-2` error state in proc output |

> **Note:** This module itself taints the kernel (`out-of-tree`, `unsigned`). It is intended as a diagnostic/research tool, not a production hardening mechanism.

---

## Requirements

- Linux kernel **5.7 or later** (uses kprobe-based `kallsyms_lookup_name` resolution)
- Kernel headers for the running kernel:
  ```bash
  sudo apt install linux-headers-$(uname -r)
  ```
- Root privileges to load/unload the module
- `/boot/System.map-$(uname -r)` present and readable (standard on Ubuntu/Debian/Kali)

---

## Building

```bash
git clone <repo-url>
cd kaslr-offset-probe
make
```

The Makefile automatically extracts static addresses for all three anchor symbols from `System.map` and passes them as compile-time `-D` defines:

```makefile
STATIC_ADDR1 := 0x$(shell sudo grep " T __x64_sys_getpid$$" /boot/System.map-$(shell uname -r) | awk '{print $$1}')
```

To clean build artifacts:

```bash
make clean
```

---

## Usage

**Load the module:**
```bash
sudo insmod 29-kaslr_offset_proc.ko
```

**Read the KASLR offset (no root required):**
```bash
cat /proc/kaslr_offset
```

**Check kernel log for detailed per-symbol breakdown:**
```bash
dmesg | grep "KASLR Finder"
```

**Unload the module:**
```bash
sudo rmmod 29_kaslr_offset_proc
```

**One-liner reload during development:**
```bash
sudo rmmod 29_kaslr_offset_proc 2>/dev/null; sudo insmod ./29-kaslr_offset_proc.ko
```

---

## Output Reference

### `/proc/kaslr_offset`

| Output | Meaning |
|--------|---------|
| `0x1a3400000` | KASLR slide offset — add this to any static address to get the runtime address |
| `0x0` | KASLR is disabled on this boot (`nokaslr` kernel param or VM default) |
| `Mismatch of offsets.` | Anchors disagree — possible symbol hook or memory corruption |
| `Couldnt resolve anchor at runtime.` | `kallsyms_lookup_name` returned 0 for one or more symbols |
| `Unknown error occurred.` | `kaslr_verified` in unexpected state |

### `dmesg` output (example — KASLR disabled)

```
KASLR Finder: Verifying across 3 symbols
KASLR Finder: [Symbol: __x64_sys_getpid] [Static: 0xffffffff810df080] [Runtime: 0xffffffff810df080] [Offset: 0x0]
KASLR Finder: [Symbol: __x64_sys_getuid] [Static: 0xffffffff810df230] [Runtime: 0xffffffff810df230] [Offset: 0x0]
KASLR Finder: [Symbol: __x64_sys_getgid] [Static: 0xffffffff810df410] [Runtime: 0xffffffff810df410] [Offset: 0x0]
KASLR Finder: Verified! KASLR Offset is consistently 0x0
KASLR Finder: /proc/kaslr_offset created
```

---

## Internals

### File Structure

```
kaslr-offset-probe/
├── 29-kaslr_offset_proc.c     # Module source
├── Makefile            # Builds module, extracts static addresses
└── README.md
```

### Key Implementation Details

**`kallsyms_lookup_name` resolution via kprobes**

Since kernel 5.7, `kallsyms_lookup_name` is no longer exported. The module registers a kprobe on it by symbol name, reads `kp.addr` (the resolved address), then immediately unregisters the probe — leaving no persistent hook:

```c
struct kprobe kp = { .symbol_name = "kallsyms_lookup_name" };
register_kprobe(&kp);
kallsyms_lookup_name_ptr = (void *)kp.addr;
unregister_kprobe(&kp);
```

**`/proc` entry via `seq_file`**

Uses the standard `single_open` + `seq_printf` pattern with `struct proc_ops`, which is the correct API for kernels ≥ 5.6 (replaces the old `struct file_operations` approach for proc files).

**Verification state machine**

`kaslr_verified` uses distinct integer sentinels rather than booleans so the proc output can communicate the specific failure reason without a separate error field:

| Value | Meaning |
|-------|---------|
| `0` | Not yet determined (default) |
| `1` | Verified successfully |
| `-1` | Offset mismatch across anchors |
| `-2` | One or more symbols unresolvable at runtime |

---

## Caveats

- **Taints the kernel.** Loading any out-of-tree or unsigned module sets the taint flag. This is expected and unavoidable without kernel module signing.
- **x86-64 only.** The anchor symbols (`__x64_sys_*`) are architecture-specific. ARM64 equivalents would use `__arm64_sys_*`.
- **System.map must match the running kernel.** If you've booted a kernel different from the one the headers/System.map belong to, static addresses will be wrong and the offset will be garbage.
- **KASLR offset of `0x0` is valid.** It means the kernel was booted with `nokaslr` or the hypervisor disabled randomization — it is not an error.
- **Do not use in production.** This is a research and diagnostic tool.

---

## License

GPL v2 — see `MODULE_LICENSE("GPL")` in source.
