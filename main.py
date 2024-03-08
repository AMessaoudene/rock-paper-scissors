from guizero import App, Text, TextBox, PushButton
import threading
import socket

HOST = socket.gethostbyname(socket.gethostname())
PORT = 5555
server_running = False

def call_server():
    if server_running == False:
        server_thread = threading.Thread(target=server)
        server_thread.daemon = True
        server_thread.start()

def server():
    global server_running
    server_running = True
    connected_to_text.value = "Waiting for connections..."
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind((HOST, PORT))
        s.listen()
        conn, _ = s.accept()
        with conn:
            while True:
                data = conn.recv(1024)
                if data.decode('utf-8'):
                    connected_to_text.value = f"Connected to {data.decode('utf-8')}"
                name = name_input.value
                if name_input.value == "":
                    name = "Default"
                if not data:
                    break
                conn.sendall(name.encode('utf-8'))
    server_running = False

def client():
    connected_to_text.value = "Connecting..."
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.connect((host_input.value, PORT))
            name = name_input.value
            if name_input.value == "":
                name = "Default"
            s.sendall(name.encode('utf-8'))
            data = s.recv(1024)
            connected_to_text.value = f"Connected to {data.decode('utf-8')}"
    except ConnectionRefusedError:
        connected_to_text.value = f"Couldn't connect to {host_input.value}"
    except OSError:
        connected_to_text.value = "An invalid address was entered"

app = App(title="Rock, Paper, Scissors", layout="grid", width=700, height=300)

ip_text = Text(app, text=HOST, grid=[0, 0])
connected_to_text = Text(app, text="Not connected right now", grid=[0, 1])

host_label = Text(app, text="Host:", grid=[0, 2])
host_input = TextBox(app, width="fill", grid=[1, 2])
connect_button = PushButton(app, text="Connect", grid=[2, 2], command=client)
wait_for_connection_button = PushButton(app, text="Wait for connection", grid=[3, 2], command=call_server)

name_label = Text(app, text="Name:", grid=[0, 3])
name_input = TextBox(app, width="fill", text="Default", grid=[1, 3])

app.display()
