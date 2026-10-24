import socket, base64, os, json, struct
host, port = 'node', 10087
s = socket.create_connection((host, port), timeout=8)
key = base64.b64encode(os.urandom(16)).decode()
req = (f"GET /ws HTTP/1.1\r\nHost: {host}:{port}\r\nUpgrade: websocket\r\nConnection: Upgrade\r\n"
       f"Sec-WebSocket-Key: {key}\r\nSec-WebSocket-Version: 13\r\n\r\n")
s.sendall(req.encode())
resp = s.recv(4096).decode(errors='replace')
print("HANDSHAKE:", resp.splitlines()[0] if resp else "EMPTY")
def send_msg(sock, payload):
    header = bytearray([0x81]); mask = os.urandom(4); n = len(payload)
    if n < 126: header.append(0x80 | n)
    elif n < 65536: header.append(0x80 | 126); header += struct.pack('>H', n)
    else: header.append(0x80 | 127); header += struct.pack('>Q', n)
    header += mask
    sock.sendall(bytes(header) + bytes(b ^ mask[i % 4] for i, b in enumerate(payload)))
def recv_msg(sock):
    def read(n):
        buf = b''
        while len(buf) < n:
            c = sock.recv(n - len(buf))
            if not c: raise EOFError
            buf += c
        return buf
    b1, b2 = read(2); op = b1 & 0x0f; n = b2 & 0x7f
    if n == 126: n = struct.unpack('>H', read(2))[0]
    elif n == 127: n = struct.unpack('>Q', read(8))[0]
    return op, read(n)
for method in ["lyquid_list", "lyquid_info", "lyquid_call"]:
    payload = json.dumps({"jsonrpc":"2.0","id":1,"method":method,"params":[]}).encode()
    try:
        send_msg(s, payload)
        op, data = recv_msg(s)
        print("== %s (op=%s) ==" % (method, op)); print(data[:400].decode(errors='replace'))
    except Exception as e:
        print("== %s ERROR: %s ==" % (method, e)); break
s.close()
