import socket
import argparse

def _eol_bytes(eol: str) -> bytes:
    eol = eol.lower()
    if eol == "crlf":
        return b"\r\n"
    if eol == "none":
        return b""
    return b"\n"

def run_server(host: str = "0.0.0.0", port: int = 8078, eol: str = "lf"):
    term = _eol_bytes(eol)
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as ls:
        ls.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        ls.bind((host, port))
        ls.listen(5)
        print(f"Echo server listening on {host}:{port} (EOL={eol})")
        while True:
            conn, addr = ls.accept()
            print(f"Accepted from {addr}")
            with conn:
                buf = bytearray()
                while True:
                    data = conn.recv(4096)
                    if not data:
                        break
                    buf.extend(data)
                    # 区切りがない場合は受け取ったら即ACKする
                    if not term:
                        conn.sendall(b"ACK " + bytes(buf))
                        buf.clear()
                        continue
                    # 区切りまでを1行としてECHO
                    while term and term in buf:
                        line, _, rest = buf.partition(term)
                        buf = bytearray(rest)
                        text = line.decode("utf-8", errors="ignore")
                        print(f"< {text}")
                        resp = f"ECHO: {text}".encode("utf-8") + term
                        conn.sendall(resp)

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--host", default="0.0.0.0")
    ap.add_argument("--port", type=int, default=8078)
    ap.add_argument("--eol", choices=["lf", "crlf", "none"], default="lf")
    args = ap.parse_args()
    run_server(args.host, args.port, args.eol)