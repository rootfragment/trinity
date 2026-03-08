import socket

def send_udp_alert(findings, config):
    if not findings:
        return
    message = "\n".join(findings)
    sent_count = 0
    for listener in config.get("listener_list", []):
        if not listener.get("enabled", False):
            continue
        ip = listener["ip"]
        port = listener["port"]
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
                s.sendto(message.encode('utf-8'), (ip, port))
            sent_count += 1
        except Exception as e:
            print(f"[!] UDP send failed ({ip}:{port}): {e}")
    if sent_count > 0:
        print(f"[+] UDP alert sent to {sent_count} listener(s).")
