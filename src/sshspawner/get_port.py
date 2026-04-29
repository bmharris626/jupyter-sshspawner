"""Return an ephemeral local IP/port pair for remote spawning."""

import socket


def get_free_port():
    """Reserve and return a free local socket bind tuple."""
    s = socket.socket()
    s.bind(("", 0))
    ip, port = s.getsockname()
    s.close()
    return ip, port


def main():
    """Print ``<ip> <port>`` for compatibility with SSHSpawner."""
    ip, port = get_free_port()
    print(f"{ip} {port}")


if __name__ == "__main__":
    main()
