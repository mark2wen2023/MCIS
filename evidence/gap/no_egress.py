"""Audit-only pytest plugin: reject IP socket connections, permit local socketpairs."""
import socket
_original_connect = socket.socket.connect
_original_connect_ex = socket.socket.connect_ex

def blocked_connect(self, address):
    if self.family in (socket.AF_INET, socket.AF_INET6):
        raise AssertionError('audit forbids IP network/model connections')
    return _original_connect(self, address)

def blocked_connect_ex(self, address):
    if self.family in (socket.AF_INET, socket.AF_INET6):
        raise AssertionError('audit forbids IP network/model connections')
    return _original_connect_ex(self, address)

socket.socket.connect = blocked_connect
socket.socket.connect_ex = blocked_connect_ex
