# Kernel Module: User-Space Program Execution

This Linux kernel module demonstrates how to **execute a user-space program from within the kernel** using the `call_usermodehelper()` function.  
It provides a bridge between kernel space and user space, allowing a kernel module to trigger user applications.

---

## Core Idea

- Normally, kernel code is **separate from user applications**.
- This module shows how the kernel can launch a user program directly.


---

## Key Components

### 1. `argv`
- Stands for **argument vector** (similar to `argv` in C `main()`).
- In this module:
  ```c
  char *argv[] = { path, NULL };
  ```
  - `path` → full path to the executable.
  - `NULL` → marks the end of the argument list.
- It tells the kernel what program to run and what arguments to pass.

---

### 2. `envp`
- Stands for **environment pointer array**.
- Used to set environment variables for the new process.
- In this module:
  ```c
  char *envp[] = {
      "HOME=/",
      "PATH=/sbin:/bin:/usr/sbin:/usr/bin",
      NULL
  };
  ```
- Explanation:
  - `HOME=/` → sets the home directory for the process.
  - `PATH=...` → ensures the executable can find system binaries if needed.
  - `NULL` → marks the end of the environment list.

---

### 3. `call_usermodehelper()`
- The kernel API used to start a user-space program.
- Signature:
  ```c
  int call_usermodehelper(char *path, char **argv, char **envp, int wait);
  ```
- Parameters:
  - `path` → program to run (`/path/to/file`).
  - `argv` → arguments array.
  - `envp` → environment variables.
  - `UMH_WAIT_EXEC` → tells the kernel to wait until execution finishes (synchronous execution).

---

### 4. `ret`
- Holds the **return value** of `call_usermodehelper()`.
- Used to check whether execution succeeded or failed:
  - `0` → success.
  - Non-zero → failure (error codes from the kernel).
- In this module:
  ```c
  if (ret)
      pr_info("Program exec failed, return code = %d\n", ret);
  else
      pr_info("Program executed successfully\n");
  ```

---

## Module Lifecycle

1. **On Load (`process_init`)**
   - Prints a log: `"USER_SPACE_CALL MODULE LOADED"`.
   - Prepares `argv` and `envp`.
   - Calls `call_usermodehelper()` to launch the user-space program.
   - Logs whether execution succeeded or failed.

2. **On Unload (`process_exit`)**
   - Prints a log: `"UNLOADED THE MODULE"`.

---

## Notes & Limitations

- The path **must point to an existing executable file**.
- The module **runs as root**, so the program inherits elevated privileges.
- The `PATH` variable in `envp` must include the directories containing required binaries if the user program depends on them.
- Using `UMH_WAIT_EXEC` blocks until the program starts — for asynchronous execution, different flags can be used (`UMH_NO_WAIT`, `UMH_WAIT_PROC`).

---
