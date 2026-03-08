# System Paths
PROC_SYSCALLS_FILE = "/proc/rk_syscalls"
PROC_FS_FILE = "/proc/rk_fs"
PROC_PS_FILE = "/proc/rk_ps"
PROC_MODS_FILE = "/proc/rk_mods"
PROC_SOCKETS_FILE = "/proc/rk_sockets"
PROC_MODULES = "/proc/modules"

# Configuration and State
CONFIG_FILE = "config.json"
DIR_LIST_FILE = "dir_list.txt"
PID_FILE = "/tmp/argus_daemon.pid"

# Default Configuration
DEFAULT_CONFIG = {
    "listener_list": [
        {
            "ip": "127.0.0.1",
            "port": 12345,
            "enabled": True,
        }
    ]
}
