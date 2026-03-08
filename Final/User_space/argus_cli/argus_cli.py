#!/usr/bin/env python3
import os
import sys
import argparse
from argus.utils.config import load_config
from argus.daemon.manager import daemonize, daemon_worker, stop_daemon
from argus.ui.menu import interactive_menu

def main():
    parser = argparse.ArgumentParser(description="Argus Linux Rootkit Detection Framework.")
    parser.add_argument("-t", "--daemon", type=int, metavar="SECONDS",
                        help="Run as a daemon, checking every N seconds.")
    parser.add_argument("--stop", action="store_true",
                        help="Stop the running daemon process.")
    
    args = parser.parse_args()

    if args.stop:
        stop_daemon()
        sys.exit(0)

    if os.geteuid() != 0:
        print("[!] This tool must be run as root to function correctly.")
        sys.exit(1)
    
    try:
        config = load_config()
    except Exception as e:
        print(f"[x] Critical error loading config.json: {e}")
        sys.exit(1)

    if args.daemon:
        if args.daemon <= 0:
            print("[!] Daemon interval must be a positive number of seconds.")
            sys.exit(1)
        print(f"[*] Starting Argus in daemon mode with a {args.daemon} second interval.")
        daemonize()
        daemon_worker(args.daemon, config)
    else:
        interactive_menu(config)

if __name__ == "__main__":
    main()
