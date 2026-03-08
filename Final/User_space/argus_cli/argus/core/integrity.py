import os
import sys
import threading
from ..utils.constants import PROC_SYSCALLS_FILE
from ..utils.alerting import send_udp_alert

syscall_tampering_detected = threading.Event()
syscall_currently_hooked = False

def handle_syscall_tampering(hooked_syscall_details: list[str], config, interactive: bool):
    findings_messages = []
    for detail in hooked_syscall_details:
        original, new = [s.strip() for s in detail.split('|')]
        findings_messages.append(f"Syscall integrity compromised: '{original}' hooked with '{new}'")
    
    send_udp_alert(findings_messages, config)

    if interactive:
        print("\033[1m\nCRITICAL BREACH: Syscall integrity failed! Syscall hooks detected for the given syscalls:\033[0m")
        for detail in hooked_syscall_details:
            original, new = [s.strip() for s in detail.split('|')]
            print(f"  -> Original: {original}, Hooked with: {new}")

        while True:
            choice = input("\nDo you want to continue to the menu? (y/n): ").lower().strip()
            if choice == 'y':
                print("Continuing to main menu...")
                break
            elif choice == 'n':
                print("Exiting.")
                sys.exit(0)
            else:
                print("Invalid choice. Please enter 'y' or 'n'.")

def check_syscall_integrity(config, interactive: bool, is_background_check: bool = False):
    global syscall_currently_hooked

    findings = []

    if not os.path.exists(PROC_SYSCALLS_FILE):
        if not is_background_check:
            print(f"[!] Kernel proc file '{PROC_SYSCALLS_FILE}' not found. Is the kernel module loaded?", file=sys.stderr)
        return findings

    try:
        with open(PROC_SYSCALLS_FILE, 'r') as f:
            lines = f.readlines()
    except Exception as e:
        if not is_background_check:
            print(f"[x] Error reading {PROC_SYSCALLS_FILE}: {e}", file=sys.stderr)
        return findings

    if not lines:
        return findings

    status = lines[0].strip()

    if is_background_check:
        if status == "-1":
            if not syscall_currently_hooked:
                syscall_currently_hooked = True
                syscall_tampering_detected.set()
        elif status == "0":
            syscall_currently_hooked = False
        return []

    if status == "-1":
        hooked_syscall_details = [line.strip() for line in lines[1:] if line.strip()]
        if hooked_syscall_details:
            handle_syscall_tampering(hooked_syscall_details, config, interactive)
            for detail in hooked_syscall_details:
                original, new = [s.strip() for s in detail.split('|')]
                findings.append(f"Syscall Integrity: Original '{original}' hooked with '{new}'")

    return findings
