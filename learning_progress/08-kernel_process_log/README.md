# Kernel Threads Monitoring Module

This Linux Kernel Module (LKM) creates a `/proc` entry named `/proc/kernel_threads` that lists **all currently running kernel threads**.  
It provides both per-thread details and a total count of kernel threads at the time of reading.

---

## Features
- Creates a `/proc` file: **`/proc/kernel_threads`**
- When read, it displays:
  - **PID**: Process ID of the kernel thread
  - **Command name (`comm`)**: The thread’s name
  - **State**: Current execution state, represented by a single character (`R`, `S`, `D`, `T`, `Z`, etc.)
  - **Total count** of kernel threads at the end
- Uses **RCU locking (`rcu_read_lock/unlock`)** to safely traverse the process list
- Implements output via the **`seq_file` API**, ensuring safe and sequential `/proc` file reads

---

## ⚙ How It Works
1. **Process Iteration**  
   - The module iterates over all tasks using the `for_each_process` macro.
   - Each task has a `task_struct` containing metadata such as `pid`, `comm`, and `flags`.

2. **Kernel Thread Identification**  
   - Normal processes and kernel threads coexist in the same task list.
   - To differentiate, the module checks:
     ```c
     if (p->flags & PF_KTHREAD)
     ```
     If the `PF_KTHREAD` flag is set, the process is a kernel thread.

3. **State Representation**  
   - The function `task_state_to_char()` is used to print a **single-character code** for the process state:
     - `R`: Running
     - `S`: Sleeping (interruptible)
     - `D`: Uninterruptible sleep
     - `T`: Stopped
     - `Z`: Zombie
     - `X`: Dead

4. **/proc Interface**  
   - The `/proc/kernel_threads` file is created using `proc_create`.
   - Read operations (`cat /proc/kernel_threads`) are handled through `seq_file` helpers.

---

## Internals

- **`task_struct`**: Central structure for each process/thread in Linux.
- **`PF_KTHREAD` flag**: Identifies tasks that are kernel threads.
- **RCU (Read-Copy Update)**: Used to safely traverse the task list without blocking writers.
- **`seq_file` API**: Provides a safe way to write sequential data to `/proc`.

---

## Usage
```bash

### 1. Build the Module

make


### 2. Insert the Module

sudo insmod kernel_threads.ko


### 3. Check Kernel Logs

dmesg | tail


### 4. View Kernel Threads

cat /proc/kernel_threads


### 5. Remove the Module

sudo rmmod kernel_threads
```


---


---
