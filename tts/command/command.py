import socket
import argparse
import sys

def _eol_bytes(eol: str) -> bytes:
    if eol.lower() == "crlf":
        return b"\r\n"
    if eol.lower() == "none":
        return b""
    return b"\n"

def send_command(host: str, port: int, command: str, timeout: float = 5.0, eol: str = "lf", receive: bool = True) -> str:
    """
    指定ホスト/ポートに接続し、コマンドを送信。レスポンス（改行まで or 接続終了まで）を返す。
    """
    terminator = _eol_bytes(eol)
    with socket.create_connection((host, port), timeout=timeout) as sock:
        sock.settimeout(timeout)
        data = command.encode("utf-8")
        sock.sendall(data + terminator)
        if not receive:
            return ""
        # 改行区切りで応答を受信（改行が来ない場合はタイムアウトで戻る）
        buf = bytearray()
        try:
            while True:
                chunk = sock.recv(4096)
                if not chunk:
                    break
                buf.extend(chunk)
                if terminator and terminator in buf:
                    break
        except socket.timeout:
            pass
        return buf.decode("utf-8", errors="ignore")

def interactive(host: str, port: int, timeout: float = 5.0, eol: str = "lf"):
    """
    1接続で複数コマンドを送れる対話モード。
    Ctrl+D(EOF) または空行のみで終了。
    """
    terminator = _eol_bytes(eol)
    print(f"Connected to {host}:{port}  (EOL={eol}, timeout={timeout}s)")
    try:
        with socket.create_connection((host, port), timeout=timeout) as sock:
            sock.settimeout(timeout)
            while True:
                try:
                    line = input("> ").rstrip("\n")
                except EOFError:
                    print()
                    break
                if line == "":
                    break
                sock.sendall(line.encode("utf-8") + terminator)
    except ConnectionRefusedError:
        print(f"接続できませんでした: {host}:{port}", file=sys.stderr)
        sys.exit(1)

def main():
    parser = argparse.ArgumentParser(description="TCPコマンドクライアント")
    parser.add_argument("--host", default="nikola-humantracker", help="接続先ホスト名")
    parser.add_argument("--port", type=int, default=8078, help="ポート番号")
    parser.add_argument("--timeout", type=float, default=5.0, help="ソケットタイムアウト秒")
    parser.add_argument("--eol", choices=["lf", "crlf", "none"], default="lf", help="送信時の改行（区切り）")
    parser.add_argument("--no-recv", action="store_true", help="送信のみ（応答を待たない）")
    parser.add_argument("--cmd", help="単発コマンド文字列。指定しない場合は対話モード")
    args = parser.parse_args()

    if args.cmd is None:
        interactive(args.host, args.port, args.timeout, args.eol)
    else:
        resp = send_command(args.host, args.port, args.cmd, args.timeout, args.eol, receive=not args.no_recv)
        if resp:
            print(resp, end="")

if __name__ == "__main__":
    main()