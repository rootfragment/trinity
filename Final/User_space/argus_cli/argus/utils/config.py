import os
import json
import sys
from .constants import CONFIG_FILE, DEFAULT_CONFIG

def create_config():
    is_sudo = os.getuid() == 0 and 'SUDO_UID' in os.environ
    try:
        if is_sudo:
            original_uid = int(os.environ['SUDO_UID'])
            original_gid = int(os.environ['SUDO_GID'])
            root_euid = os.geteuid()
            root_egid = os.getegid()
            
            try:
                os.setegid(original_gid)
                os.seteuid(original_uid)
                with open(CONFIG_FILE, "w") as f:
                    json.dump(DEFAULT_CONFIG, f, indent=4)
            except OSError as e:
                print(f"[!] Error: Could not create config file for the user {original_uid}: {e}")
            finally:
                os.seteuid(root_euid)
                os.setegid(root_egid)
        else:
            with open(CONFIG_FILE, "w") as f:   
                json.dump(DEFAULT_CONFIG, f, indent=4)
        print("[*] Created a sample config file since no configuration file was found. Edit the file and rerun the program")
    except OSError as e:
        print(f"[x] Error: Could not create config file: {e}")
    except KeyError:
        print("[x] Error: SUDO_UID or SUDO_GID not found in environment. Cannot determine the user.")
    sys.exit(0)

def load_config():
    if not os.path.exists(CONFIG_FILE):
        create_config()
    with open(CONFIG_FILE, "r") as f:
        return json.load(f)
