# Pass Arguments Kernel Module

This Linux kernel module demonstrates how to **pass arguments** to a module at load time using `insmod`.  
It also exposes these arguments through **sysfs**, so they can be viewed and changed at runtime.
The letter parameter does not accept direct characters (e.g., letter='b' will not work).
You must always provide the ASCII value instead. `letter` is declared as byte, so you must pass its ASCII code.

---

## Features

- Defines three module parameters:
  - **Integer** → `number`
  - **String** → `name`
  - **Byte** → `letter` (stored as `unsigned char`)
- Prints the values of these parameters when the module is loaded.
- Provides access to parameters through `/sys/module/pass_args/parameters/`.

---

## Core Functionality

- Defines three module parameters:
  - `number` → **integer**
  - `name` → **string**
  - `letter` → **unsigned char (byte)**

-These module parameters can be changed at runtime while using the `insmod` command.

##Usage 

```bash
# Make
make

# Insert the module with default values
sudo insmod 06-pass_args.ko

# Insert the module with custom values 
sudo insmod 06-pass_args.ko number=69 name="neo" letter=66

# Remove the module
sudo rmmod 06-pass_args

# View kernel log messages
dmesg | tail
