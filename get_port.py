#!/usr/bin/env python

import socket

def get_free_port():
    s = socket.socket()
    s.bind(('', 0))
    ip, port = s.getsockname()
    s.close()
    return ip, port

ip, port = get_free_port()
print(f"{ip} {port}")
