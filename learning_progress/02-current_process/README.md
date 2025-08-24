# Current Process Info Kernel Module

## Overview
This kernel module prints information about the **current process** at the time the module is loaded.  
It demonstrates how to access the `task_struct` of the process that inserts the module (usually the process running `insmod`).  

When the module is inserted:
- A log message **"MODULE LOADED"** is printed.  
- The **process name** (`comm`) and **process ID** (`pid`) of the current process are logged.  

When the module is removed:
- A log message **"MODULE UNLOADED"** is printed.  

---

## How It Works
- **Headers**:
  - `<linux/kernel.h>`, `<linux/init.h>`, `<linux/module.h>` provide basic kernel functions and macros.  
  - `<linux/sched.h>` provides access to process-related structures (`task_struct`).  
- **`current`**: A kernel macro that returns a pointer to the `task_struct` of the process currently executing in the kernel.  
- **`current->comm`**: The command name of the process.  
- **`current->pid`**: The process ID.  
- **`printk(KERN_INFO ...)`**: Used to print messages to the kernel log.  

This shows how kernel modules can query and log information about processes interacting with them.

---

