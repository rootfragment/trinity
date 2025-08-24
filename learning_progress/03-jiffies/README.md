# jiffies Kernel Module

This kernel module demonstrates how to use the `jiffies` counter in Linux to measure system uptime and the duration that a module stays loaded.

---

## Features
- Prints the value of `jiffies` when the module is loaded.  
- Prints the system uptime in seconds (`jiffies / HZ`).  
- On removal, calculates how long the module was online by comparing start and end `jiffies`.  

---

## Core Concepts

### Jiffies
- `jiffies` is a global kernel variable that represents the number of **ticks** since the system booted.  
- It is continuously incremented by the kernel timer interrupt.  
- Its value is **monotonic** (always increasing) and is commonly used for measuring time intervals inside the kernel.  

### HZ
- `HZ` is a kernel constant that defines how many **ticks per second** occur.  
- For example:
  - If `HZ = 1000`, then one tick = 1 millisecond.  
  - If `HZ = 250`, then one tick = 4 milliseconds.  
- Therefore, system uptime in seconds can be calculated as:
uptime_seconds = jiffies / HZ


## Usage

```bash
# Make
make

# Insert the module
sudo insmod 04-jiffies.ko

# Remove the module
sudo rmmod 04-jiffies

# View kernel log messages
dmesg | tail

```
---
## Note
- Remove the module after some time to calculate the time the module was loaded.
