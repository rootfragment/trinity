# kernel_list Kernel Module

This Linux kernel module creates a `/proc` entry that lists all running processes from the kernel’s perspective.  
It demonstrates how the `/proc` filesystem can be extended for process inspection and monitoring.  

---

## Features
- Creates a `/proc/kernel_list` file when loaded.  
- When read, it lists **all running processes** with details:  
  - **PID**: Process ID  
  - **PPID**: Parent Process ID  
  - **COMM**: Command (process name)  
  - **STATE**: Internal state of the process  
- Cleans up and removes the entry when unloaded.  

---

## Core Functionality

### 1. Process Listing (`show_task`)
- Iterates over all processes using the kernel macro `for_each_process`.  
- Uses `seq_printf` to print information about each process.  
- Protected by `rcu_read_lock()` and `rcu_read_unlock()` to safely traverse task structures.  

### 2. Open Function (`task_open`)
- Links the proc entry to `show_task` using `single_open`.  
- Ensures proper output formatting during read operations.  

### 3. Proc Operations (`myops`)
- Defines how the proc file behaves:  
  - **proc_open**: Handles opening  
  - **proc_read**: Allows sequential reading  
  - **proc_lseek**: Supports seeking  
  - **proc_release**: Cleans up after reading  

### 4. Module Init (`advanced_init`)
- Creates `/proc/kernel_list` using `proc_create`.  
- Logs messages when the module is successfully loaded.  

### 5. Module Exit (`advanced_exit`)
- Removes the `/proc/kernel_list` entry with `proc_remove`.  
- Logs a message when the module is unloaded.  

---

## Usage

```bash
# Make
make

# Insert the module
sudo insmod 05-advanced_log.ko

# Remove the module
sudo rmmod 05-advanced_log

# View kernel log messages
dmesg | tail

# View /proc file
cat /proc/kernel_list
