from ..core.process import run_process_scan
from ..core.modules import run_module_scan
from ..core.ports import run_port_scan
from ..core.filesystem import run_fs_scan
from ..core.integrity import check_syscall_integrity

def analyze_findings(all_findings):
    print("\n" + "#"*25)
    print("  Full Scan Analysis")
    print("#"*25)
    if not all_findings:
        print("\n[***] System appears clean. No anomalies detected across all scans.")
        return
    
    has_hidden_procs = any("Hidden Process" in f for f in all_findings)
    has_hidden_mods = any("Hidden Module" in f for f in all_findings)
    has_hidden_ports = any("Hidden Port" in f for f in all_findings)
    has_syscall_tampering = any("Syscall Integrity" in f for f in all_findings)

    print("\n[!] Potential threats detected. Summary based on findings:")
    
    if has_syscall_tampering:
        print("""
    - Type: Syscall Hooking Rootkit
    - Details: The system call table has been modified, indicating a potential rootkit
      that is intercepting system calls to hide its presence or alter system behavior.
""")
    if has_hidden_procs and not has_hidden_mods:
        print("""
    - Type: Process-Hiding Rootkit
    - Details: The malware is actively hiding its processes from standard tools like 'ps'.
      This is common for user-land rootkits that modify /proc or intercept system calls.
""")
    if has_hidden_mods:
        print("""
    - Type: Kernel-Level Rootkit (LKM)
    - Details: A Loadable Kernel Module (LKM) is hiding itself from 'lsmod'. This is a
      strong indicator of a sophisticated rootkit operating with kernel privileges. It may
      also be responsible for hiding processes and ports.
""")
    if has_hidden_ports and not has_hidden_mods:
        print("""
    - Type: Hidden Backdoor / Service
    - Details: A service is listening on a port but is hiding from standard tools like 'ss'.
      This could be a standalone backdoor or part of a larger malware framework.
""")
    if has_hidden_procs and has_hidden_mods and has_hidden_ports and has_syscall_tampering:
        print("""
    - Type: Advanced Kernel-Level Rootkit (Comprehensive)
    - Details: The malware exhibits multiple stealth capabilities, including syscall hooking,
      hiding its kernel module, its processes, and its network listeners. This indicates a
      full-featured rootkit with deep system integration and evasion techniques.
""")
    elif has_hidden_procs or has_hidden_mods or has_hidden_ports or has_syscall_tampering:
        print("""
    - Type: Combination Rootkit / Malware
    - Details: Multiple indicators of compromise suggest a sophisticated threat, potentially
      combining different evasion and malicious functionalities.
""")
    print("#"*25)

def run_full_scan(config):
    all_findings = []
    all_findings.extend(run_process_scan())
    all_findings.extend(run_module_scan())
    all_findings.extend(run_port_scan())
    all_findings.extend(run_fs_scan())
    all_findings.extend(check_syscall_integrity(config, interactive=False)) 
    analyze_findings(all_findings)
    return all_findings
