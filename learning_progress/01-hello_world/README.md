# Hello World Kernel Module

## Overview
This module demonstrates the basic structure of a Linux kernel module.  
When loaded into the kernel, it prints a message **"HELLO WORLD"** to the system log.  
When removed, it prints **"BYE WORLD"**.  

This is typically the first step in learning kernel programming, showing how modules are initialized, executed, and cleaned up.

---

## How It Works
- **Headers**: Includes `linux/init.h`, `linux/module.h`, and `linux/kernel.h` to provide the necessary kernel APIs.  
- **MODULE_LICENSE("GPL")**: Specifies the license, ensuring the kernel does not mark the module as "tainted".  
- **Initialization function (`__init`)**: Executed when the module is inserted with `insmod`. It logs the "HELLO WORLD" message.  
- **Exit function (`__exit`)**: Executed when the module is removed with `rmmod`. It logs the "BYE WORLD" message.  
- **`module_init` and `module_exit` macros**: Register the functions with the kernel for load and unload operations.  
- **`printk(KERN_INFO ...)`**: Used for printing messages to the kernel log. Messages can be viewed using `dmesg`.  

---

## Build Instructions

### 1. Install Kernel Headers
Kernel headers matching the currently running kernel are required to compile modules.  
On most distributions, they can be installed using:

```bash
# For Debian/Ubuntu
sudo apt-get update
sudo apt-get install build-essential linux-headers-$(uname -r)

# For Fedora/RHEL/CentOS
sudo dnf install make gcc kernel-devel kernel-headers
```

## Usage

```bash
# Make
make
# Insert the module
sudo insmod hello.ko

# Remove the module
sudo rmmod hello

# View kernel log messages
dmesg | tail
