import os
import sys
import time
import signal
from ..utils.constants import PID_FILE
from ..utils.alerting import send_udp_alert
from ..core.process import run_process_scan
from ..core.modules import run_module_scan
from ..core.ports import run_port_scan
from ..core.filesystem import run_fs_scan
from ..core.integrity import check_syscall_integrity

def signal_handler(signum, frame):
    print("Daemon shutting down...")
    try:
        if os.path.exists(PID_FILE):
            os.remove(PID_FILE)
    except OSError as e:
        print(f"Error removing PID file: {e}", file=sys.stderr)
    sys.exit(0)

def daemon_worker(interval, config):
    signal.signal(signal.SIGTERM, signal_handler)
    signal.signal(signal.SIGINT, signal_handler)
    
    print(f"[*] Argus daemon started (PID: {os.getpid()}). Running scans every {interval} seconds.")
    while True:
        original_stdout = sys.stdout
        try:
            all_findings = []
            with open(os.devnull, 'w') as devnull:
                sys.stdout = devnull
                
                all_findings.extend(run_process_scan())
                all_findings.extend(run_module_scan())
                all_findings.extend(run_port_scan())
                all_findings.extend(run_fs_scan())
                all_findings.extend(check_syscall_integrity(config, interactive=False)) 
            
            # sys.stdout is restored by the finally block below
            
            if all_findings:
                # We need to print this to the original stdout (which might be redirected to a log)
                # But since we are in a daemon, it probably goes to /dev/null unless configured otherwise.
                # Use sys.__stdout__ or restore it first.
                sys.stdout = original_stdout
                print(f"[{time.ctime()}] Daemon detected {len(all_findings)} anomalies. Sending alert.")
                send_udp_alert(all_findings, config)

        except Exception as e:
            sys.stdout = original_stdout
            print(f"[!] Error in daemon loop: {e}", file=sys.stderr)
        finally:
            sys.stdout = original_stdout
        
        time.sleep(interval)


def daemonize():
    if os.path.exists(PID_FILE):
        try:
            with open(PID_FILE, 'r') as f:
                old_pid = int(f.read().strip())
            os.kill(old_pid, 0)
            sys.stderr.write(f"Daemon is already running with PID {old_pid}. Aborting.\n")
            sys.exit(1)
        except (OSError, ValueError):
            os.remove(PID_FILE)

    try:
        pid = os.fork()
        if pid > 0:
            sys.exit(0)
    except OSError as e:
        sys.stderr.write(f"fork #1 failed: {e}\n")
        sys.exit(1)

    os.chdir("/")
    os.setsid()
    os.umask(0)

    try:
        pid = os.fork()
        if pid > 0:
            sys.exit(0)
    except OSError as e:
        sys.stderr.write(f"fork #2 failed: {e}\n")
        sys.exit(1)

    try:
        with open(PID_FILE, 'w') as f:
            f.write(str(os.getpid()))
    except OSError as e:
        sys.stderr.write(f"Unable to write PID file {PID_FILE}: {e}\n")
        sys.exit(1)

    sys.stdout.flush()
    sys.stderr.flush()
    si = open(os.devnull, 'r')
    so = open(os.devnull, 'a+')
    se = open(os.devnull, 'a+')
    os.dup2(si.fileno(), sys.stdin.fileno())
    os.dup2(so.fileno(), sys.stdout.fileno())
    os.dup2(se.fileno(), sys.stderr.fileno())

def stop_daemon():
    if not os.path.exists(PID_FILE):
        sys.stderr.write("Daemon is not running (PID file not found).\n")
        return

    try:
        with open(PID_FILE, 'r') as f:
            pid = int(f.read().strip())
    except (ValueError, IOError) as e:
        sys.stderr.write(f"Error reading PID file: {e}\n")
        os.remove(PID_FILE)
        return

    try:
        print(f"Stopping daemon with PID {pid}...")
        os.kill(pid, signal.SIGTERM)
        time.sleep(1)
        os.kill(pid, 0) 
        print("Daemon did not stop gracefully, sending SIGKILL.")
        os.kill(pid, signal.SIGKILL)
    except OSError:
        print("Daemon stopped successfully.")
    finally:
        if os.path.exists(PID_FILE):
            os.remove(PID_FILE)
