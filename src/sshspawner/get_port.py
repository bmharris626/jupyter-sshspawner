"""Return an ephemeral local IP/port pair for remote spawning."""

import socket


def get_local_ip():
    """Return a concrete local IP suitable for inbound connections.

    Falls back to loopback if no non-loopback interface can be inferred.
    """
    probe = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        probe.connect(("8.8.8.8", 80))
        return probe.getsockname()[0]
    except OSError:
        return "127.0.0.1"
    finally:
        probe.close()


def get_free_port():
    """Reserve and return a free local socket bind tuple."""
    ip = get_local_ip()
    s = socket.socket()
    s.bind((ip, 0))
    _, port = s.getsockname()
    s.close()
    return ip, port


def main():
    """Print ``<ip> <port>`` for compatibility with SSHSpawner."""
    ip, port = get_free_port()
    print(f"{ip} {port}")


if __name__ == "__main__":
    main()
