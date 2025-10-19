import socket
import time

class ASRMockServer:
    def __init__(self, host='localhost', port=8888):
        self.host = host
        self.port = port
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_socket.bind((self.host, self.port))
        self.server_socket.listen(1)
        print(f"ASR Mock Server is running on {self.host}:{self.port}")

    def send_test_data(self, conn):
        test_data = [
            "interimresult: こんにちは、これはテストです。",
            "confidence: 0.95",
            "result: こんにちは",
            "confidence: 0.98"
        ]
        for data in test_data:
            conn.sendall((data + "\n").encode('utf-8'))
            time.sleep(1)  # 1秒待機してから次のデータを送信

    def start(self):
        print("Waiting for a connection...")
        conn, addr = self.server_socket.accept()
        print(f"Connection from {addr}")
        try:
            self.send_test_data(conn)
        finally:
            conn.close()
            print("Connection closed.")

if __name__ == "__main__":
    server = ASRMockServer()
    server.start()