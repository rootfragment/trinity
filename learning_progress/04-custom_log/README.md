# custlog Kernel Module

This Linux kernel module creates a custom `/proc` entry that displays system and process information when read.  
It is a simple example of how the `/proc` filesystem can be extended for logging and monitoring purposes.  

---

## Features
- Creates a `/proc/custlog` file when loaded.  
- When read, it prints:
  - A simple "alive" message.  
  - System uptime (in seconds).  
  - The process name of the reader.  
  - The PID of the reader.  
- Removes the `/proc` entry cleanly when unloaded.  

---

## Core Functionality

### 1. Show Function (`custlog_show`)
- Runs when `/proc/custlog` is read.  
- Prints system uptime and information about the reading process.  

### 2. Open Function (`custlog_open`)
- Uses `single_open` to connect the proc entry with `custlog_show`.  

### 3. Proc Operations (`myops`)
- Defines how the proc entry behaves (`open`, `read`, `lseek`, `release`).  

### 4. Module Init (`custlog_init`)
- Creates `/proc/custlog` on module load.  
- Logs messages in the kernel log.  

### 5. Module Exit (`custlog_exit`)
- Removes `/proc/custlog` on module unload.  
- Logs exit messages.  

---


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

