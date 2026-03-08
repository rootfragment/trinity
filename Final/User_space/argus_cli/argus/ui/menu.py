import threading
import time
from .banner import display_banner
from ..core.process import run_process_scan
from ..core.modules import run_module_scan
from ..core.ports import run_port_scan
from ..core.filesystem import run_fs_scan
from ..core import integrity
from ..utils.scanner_base import run_full_scan
from ..utils.alerting import send_udp_alert

syscall_monitor_thread = None

def display_menu(stat):
    print("\n" + "#"*60)
    print(" "*23 +"ARGUS Scan Menu")
    print("#"*60)
    print("\n"+"[1] Compare Processes (Kernel vs /bin/ps)")
    print("[2] Compare Kernel Modules (Kernel vs /proc/modules)")
    print("[3] Compare Network Ports (Kernel vs /bin/ss)")
    print("[4] Perform Syscall Integrity Scan") 
    print("[5] Perform Full Scan (All checks)") 
    print("[6] Perform Filesystem Scan")
    print(f"[7] Toggle udp alert (Currently : {'ON' if stat else 'OFF'})" ) 
    print("\n[99] Exit")
    print("-"*15)

def interactive_menu(config):
    global syscall_monitor_thread
    stat = False
    display_banner()

    def syscall_monitor_loop():
        while True:
            previous_state = integrity.syscall_currently_hooked
            
            integrity.check_syscall_integrity(
                config,
                interactive=False,
                is_background_check=True
            )
            
            # Use the module-level state to detect a fresh change
            if integrity.syscall_currently_hooked and not previous_state:
                print("\n\033[1m[CRITICAL] Syscall tampering detected!\033[0m")
                print("Run option [4] to view detailed hook information.")
                print("Argus > ", end="", flush=True)

            time.sleep(3)
            
    if syscall_monitor_thread is None or not syscall_monitor_thread.is_alive():
        syscall_monitor_thread = threading.Thread(target=syscall_monitor_loop, daemon=True)
        syscall_monitor_thread.start()
        print("[+] Syscall integrity monitoring started in background (every 3 seconds).")

    while True:
        # Check if the event was set (for completeness, though the thread now prints)
        if integrity.syscall_tampering_detected.is_set():
            integrity.syscall_tampering_detected.clear()

        display_menu(stat)
        try:
            choice = input("Argus > ")
            if choice == '1':
                findings = run_process_scan()
                if stat and findings:
                    send_udp_alert(findings, config)
            elif choice == '2':
                findings = run_module_scan()
                if stat and findings:
                    send_udp_alert(findings, config)
            elif choice == '3':
                findings = run_port_scan()
                if stat and findings:
                    send_udp_alert(findings, config)
            elif choice == '4': 
                print("\n" + "="*25)
                print("  Running Syscall Integrity Scan")
                print("="*25)
                
                findings = integrity.check_syscall_integrity(config, interactive=True) 
                if findings:
                    if stat:
                        send_udp_alert(findings, config)
                else :
                    print("Syscall table is intact since argus started.")
                print("="*25)
                print("  Syscall Scan Complete")
                print("="*25)
            elif choice == '5': 
                findings = run_full_scan(config)
                if stat and findings:
                    send_udp_alert(findings, config)
            elif choice == '6':
                findings = run_fs_scan()
                if stat and findings:
                    send_udp_alert(findings, config)
            elif choice == '7':
                stat = not stat
                print(f"[+] UDP alerts {'ENABLED' if stat else 'DISABLED'}")
            elif choice == '99':
                print("System observation terminated." + "\n" +"ARGUS sleeps")
                break
            else:
                print(f"Unknown command: {choice}")
        except KeyboardInterrupt:
            print("\nSystem observation terminated. ARGUS sleeps.")
            break
        except Exception as e:
            print(f"\nAn unexpected error occurred: {e}")

if __name__ == "__main__":
    # This file is intended to be imported, but we'll leave this here
    pass
