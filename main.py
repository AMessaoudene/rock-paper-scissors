from guizero import App, Text, TextBox, PushButton
import threading
import socket

HOST = socket.gethostbyname(socket.gethostname())
PORT = 5555
server_running = False
client_running = False
choice = ""
choice_set = threading.Event()

def call_server():
    if server_running == False:
        server_thread = threading.Thread(target=server)
        server_thread.daemon = True
        server_thread.start()

def call_client():
    if client_running == False:
        client_thread = threading.Thread(target=client)
        client_thread.daemon = True
        client_thread.start()

def server():
    global server_running
    server_running = True
    connected_to_text.value = "Waiting for connections..."
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind((HOST, PORT))
        s.listen()
        conn, _ = s.accept()
        with conn:
            # Receive the name
            data = conn.recv(1024)
            connected_to_text.value = f"Connected to {data.decode('utf-8')}"
            # Send name
            name = name_input.value
            if name_input.value == "":
                name = "Default"
            conn.sendall(name.encode('utf-8'))
            # Receive the choice
            new_data = conn.recv(1024)
            choice_set.wait()
            choice_set.clear()
            choice_text.value = f"You chose {choice}, Opponent chose {new_data.decode('utf-8')}"
            conn.sendall(choice.encode('utf-8'))
            evaluate_winner(choice, new_data.decode('utf-8'))
    server_running = False

def client():
    connected_to_text.value = "Connecting..."
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.connect((host_input.value, PORT))
            # Send name
            name = name_input.value
            if name_input.value == "":
                name = "Default"
            s.sendall(name.encode('utf-8'))
            # Receive name
            data = s.recv(1024)
            connected_to_text.value = f"Connected to {data.decode('utf-8')}"
            # Send the choice
            choice_set.wait()
            choice_set.clear()
            s.sendall(choice.encode('utf-8'))
            data = s.recv(1024)
            choice_text.value = f"You chose {choice}, Opponent chose {data.decode('utf-8')}"
            evaluate_winner(choice, data.decode('utf-8'))
    except ConnectionRefusedError:
        connected_to_text.value = f"Couldn't connect to {host_input.value}"
    except OSError:
        connected_to_text.value = "An invalid address was entered"

def evaluate_winner(user_choice, opponent_choice):
    WINNING_CASES = [
        ["scissors", "paper"],
        ["rock", "scissors"],
        ["paper", "rock"]
    ]
    global message
    message = ""
    if user_choice == opponent_choice:
        message = "Tie game!"
    elif [user_choice, opponent_choice] in WINNING_CASES:
        message = "You win!"
    else:
        message = "You lose!"
    connected_to_text.value = message

def set_choice(action_choice):
    global choice
    choice = action_choice
    choice_text.value = "Waiting for opponent to make their choice..."
    choice_set.set()

app = App(title="Rock, Paper, Scissors", layout="grid", width=700, height=300)

ip_text = Text(app, text=HOST, grid=[0, 0])
connected_to_text = Text(app, text="Not connected right now", grid=[0, 1])
choice_text = Text(app, text="", grid=[0, 2])

host_label = Text(app, text="Host:", grid=[0, 3])
host_input = TextBox(app, width="fill", grid=[1, 3])
connect_button = PushButton(app, text="Connect", grid=[2, 3], command=call_client)
wait_for_connection_button = PushButton(app, text="Wait for connection", grid=[3, 3], command=call_server)

rock_button = PushButton(app, text="Rock", grid=[0, 5], command=lambda: set_choice("rock"))
paper_button = PushButton(app, text="Paper", grid=[1, 5], command=lambda: set_choice("paper"))
scissors_button = PushButton(app, text="Scissors", grid=[2, 5], command=lambda: set_choice("scissors"))

name_label = Text(app, text="Name:", grid=[0, 4])
name_input = TextBox(app, width="fill", text="Default", grid=[1, 4])

app.display()
