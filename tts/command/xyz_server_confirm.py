import socket

SERVER_IP = "nikola-audiotracker"   # 受信したい相手のIP
SERVER_PORT = 7890          # ポート番号
BUFFER_SIZE = 4096          # 1回で受け取る最大サイズ（bytes）
N_FIELDS = 18

def parse_numeric_line(line: bytes):
    s = line.decode("utf-8").strip()
    parts = s.split(",")
    if len(parts) != N_FIELDS:
        return None
    try:
        return [int(p) for p in parts]
    except ValueError:
        return None

with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
    sock.connect((SERVER_IP, SERVER_PORT))
    sock.settimeout(0.5)  # Ctrl+C を効かせやすくする
    print("connected")

    buf = b""

    try:
        while True:
            try:
                chunk = sock.recv(BUFFER_SIZE)
                if not chunk:
                    print("connection closed")
                    break
                buf += chunk
            except socket.timeout:
                continue

            while b"\n" in buf:
                line, buf = buf.split(b"\n", 1)

                values = parse_numeric_line(line)
                if values is None:
                    continue
                
                print(values)
                # timestamp = values[0]
                # x = values[5]
                # y = values[6]
                # z = values[7]
                # humanId = values[16]

                # print(timestamp, x, y, z, humanId)

    except KeyboardInterrupt:
        print("stopped")
