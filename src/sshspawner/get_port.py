import socket


def get_free_port():
    s = socket.socket()
    s.bind(("", 0))
    ip, port = s.getsockname()
    s.close()
    return ip, port


def main():
    ip, port = get_free_port()
    print(f"{ip} {port}")


if __name__ == "__main__":
    main()
