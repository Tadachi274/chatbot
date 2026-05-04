# chatbot/robot_style_editor/clients/dummy_robot_server.py

import socket
import threading


HOST = "127.0.0.1"
PORT = 5000
BUFFER_SIZE = 4096


def handle_client(conn, addr):
    print(f"[DummyRobotServer] connected: {addr}")

    buffer = ""

    try:
        with conn:
            while True:
                data = conn.recv(BUFFER_SIZE)

                if not data:
                    print(f"[DummyRobotServer] disconnected: {addr}")
                    break

                text = data.decode("utf-8", errors="replace")
                buffer += text

                while "\n" in buffer:
                    line, buffer = buffer.split("\n", 1)
                    command = line.strip()

                    if command:
                        print(f"[DummyRobotServer] command: {command}")

                # eol が none の場合の保険
                if "\n" not in text and buffer.strip().startswith("/"):
                    print(f"[DummyRobotServer] command: {buffer.strip()}")
                    buffer = ""

    except Exception as e:
        print(f"[DummyRobotServer] client error: {e}")


def main():
    print(f"[DummyRobotServer] starting on {HOST}:{PORT}")

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as server:
        server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        server.bind((HOST, PORT))
        server.listen()

        print("[DummyRobotServer] ready")

        while True:
            conn, addr = server.accept()
            thread = threading.Thread(
                target=handle_client,
                args=(conn, addr),
                daemon=True,
            )
            thread.start()


if __name__ == "__main__":
    main()