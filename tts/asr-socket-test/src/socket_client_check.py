import socket

def main():
    host = 'localhost'  # モックサーバーのホスト名
    port = 8888         # モックサーバーのポート番号

    # ソケットを作成
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        try:
            # サーバーに接続
            sock.connect((host, port))
            print(f"サーバー {host}:{port} に接続しました。")

            # サーバーからのデータを受信
            while True:
                data = sock.recv(1024)
                if not data:
                    print("サーバーからの接続が切れました。")
                    break
                print(f"受信データ: {data.decode('utf-8')}")

        except ConnectionRefusedError:
            print(f"サーバー {host}:{port} への接続に失敗しました。サーバーが起動していることを確認してください。")
        except Exception as e:
            print(f"エラーが発生しました: {e}")

if __name__ == "__main__":
    main()