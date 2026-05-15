from __future__ import annotations

import socket
import ssl
from urllib.parse import urlsplit

from bot.config import load_settings, mask_url_credentials


def main() -> int:
    settings = load_settings()
    proxy_url = settings.telegram_proxy_url
    if not proxy_url:
        print("Proxy is not configured.")
        return 1

    parts = urlsplit(proxy_url)
    host = parts.hostname
    port = parts.port
    if not host or port is None:
        print(f"Proxy URL is invalid: {mask_url_credentials(proxy_url)}")
        return 1

    print(f"Proxy: {mask_url_credentials(proxy_url)}")
    phase = "TCP connection"
    try:
        with socket.create_connection((host, port), timeout=5) as sock:
            print(f"TCP connection ok: {host}:{port}")
            if parts.scheme.lower() in {"http", "https"}:
                phase = "HTTP CONNECT"
                request = (
                    "CONNECT api.telegram.org:443 HTTP/1.1\r\n"
                    "Host: api.telegram.org:443\r\n"
                    "User-Agent: activity-bot-check\r\n"
                    "\r\n"
                )
                sock.sendall(request.encode("ascii"))
                sock.settimeout(10)
                response = sock.recv(4096).decode("iso-8859-1", errors="replace")
                first_line = response.splitlines()[0] if response else "<empty response>"
                print(f"CONNECT response: {first_line}")
                if not first_line.startswith("HTTP/1.1 200") and not first_line.startswith("HTTP/1.0 200"):
                    return 1

                phase = "TLS handshake"
                context = ssl.create_default_context()
                sock.settimeout(10)
                with context.wrap_socket(sock, server_hostname="api.telegram.org") as tls_sock:
                    print(f"TLS handshake ok: {tls_sock.version()}")
                    phase = "HTTPS request"
                    tls_sock.sendall(
                        b"HEAD / HTTP/1.1\r\n"
                        b"Host: api.telegram.org\r\n"
                        b"User-Agent: activity-bot-check\r\n"
                        b"Connection: close\r\n"
                        b"\r\n"
                    )
                    http_response = tls_sock.recv(4096).decode("iso-8859-1", errors="replace")
                    http_first_line = (
                        http_response.splitlines()[0] if http_response else "<empty response>"
                    )
                    print(f"HTTPS response: {http_first_line}")
    except OSError as error:
        print(f"Proxy check failed during {phase}: {error}")
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
