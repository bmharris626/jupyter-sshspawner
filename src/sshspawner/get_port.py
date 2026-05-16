"""Return an ephemeral local IP/port pair for remote spawning."""

import argparse
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


def get_free_port(ip=None):
    """Reserve and return a free local socket bind tuple."""
    ip = ip or get_local_ip()
    s = socket.socket()
    s.bind((ip, 0))
    _, port = s.getsockname()
    s.close()
    return ip, port


def parse_args(argv=None):
    """Parse command line arguments."""
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--ip",
        choices=("0.0.0.0", "localhost"),
        help="IP address to print and use when reserving a free port.",
    )
    return parser.parse_args(argv)


def main():
    """Print ``<ip> <port>`` for compatibility with SSHSpawner."""
    args = parse_args()
    ip, port = get_free_port(args.ip)
    print(f"{ip} {port}")


if __name__ == "__main__":
    main()
