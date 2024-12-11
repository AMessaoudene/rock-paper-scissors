from guizero import App, Text, TextBox, PushButton
import threading
import socket

# Host IP address and port
HOST = "127.0.0.1"
PORT = 5555

# State management flags
game_state = {
    "server_running": False,
    "client_running": False,
    "round_exit": threading.Event(),
    "choice_set": threading.Event()
}

# Player choice
game_choices = {
    "user_choice": None,
    "opponent_choice": None
}

# Winning scenarios
WINNING_CASES = [
    ["scissors", "paper"],
    ["rock", "scissors"],
    ["paper", "rock"]
]

def start_server():
    if not game_state["server_running"]:
        threading.Thread(target=server_thread, daemon=True).start()

def start_client():
    if not game_state["client_running"]:
        threading.Thread(target=client_thread, daemon=True).start()

def server_thread():
    setup_game_ui("server")
    game_state["server_running"] = True
    connection_status_text.value = "Waiting for connections..."

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as server_socket:
        server_socket.bind((HOST, PORT))
        server_socket.listen()
        conn, _ = server_socket.accept()

        with conn:
            handle_connection(conn, role="server")

    reset_game_ui()
    game_state["server_running"] = False

def client_thread():
    setup_game_ui("client")
    game_state["client_running"] = True
    connection_status_text.value = "Connecting..."

    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as client_socket:
            client_socket.connect((host_input.value, PORT))
            handle_connection(client_socket, role="client")
    except ConnectionRefusedError:
        connection_status_text.value = f"Couldn't connect to {host_input.value}"
    except OSError:
        connection_status_text.value = "Invalid address entered"

    reset_game_ui()
    game_state["client_running"] = False

def handle_connection(conn, role):
    local_name = name_input.value or "Default"

    if role == "server":
        conn.sendall(local_name.encode())
        opponent_name = conn.recv(1024).decode()
    else:
        conn.sendall(local_name.encode())
        opponent_name = conn.recv(1024).decode()

    connection_status_text.value = f"Connected to {opponent_name}"

    game_state["choice_set"].wait()
    game_state["choice_set"].clear()

    conn.sendall(game_choices["user_choice"].encode())
    game_choices["opponent_choice"] = conn.recv(1024).decode()

    display_results()

    game_state["round_exit"].wait()
    game_state["round_exit"].clear()

def set_choice(choice):
    game_choices["user_choice"] = choice
    game_state["choice_set"].set()
    toggle_choice_buttons(False)
    choice_text.value = "Waiting for opponent to make their choice..."

def evaluate_winner():
    user = game_choices["user_choice"]
    opponent = game_choices["opponent_choice"]

    if user == opponent:
        return "The game was a tie!"
    elif [user, opponent] in WINNING_CASES:
        return "You won the game!"
    else:
        return "You lost the game!"

def display_results():
    result_message = evaluate_winner()
    connection_status_text.value = result_message
    choice_text.value = f"You chose {game_choices['user_choice']}, opponent chose {game_choices['opponent_choice']}"
    exit_button.show()

def setup_game_ui(role):
    toggle_ui_elements(False)
    toggle_choice_buttons(True)
    if role == "server":
        host_label.hide()
        host_input.hide()

def reset_game_ui():
    toggle_ui_elements(True)
    toggle_choice_buttons(False)
    connection_status_text.value = "Not connected right now"
    choice_text.value = ""

def toggle_ui_elements(visible):
    elements = [host_label, host_input, name_label, name_input, connect_button, wait_for_connection_button]
    for element in elements:
        if visible:
            element.show()
        else:
            element.hide()

def toggle_choice_buttons(visible):
    buttons = [rock_button, paper_button, scissors_button]
    for button in buttons:
        if visible:
            button.show()
        else:
            button.hide()

def exit_round():
    game_state["round_exit"].set()
    exit_button.hide()

# GUI Setup
app = App(title="Rock, Paper, Scissors", layout="grid", width=700, height=400)

ip_text = Text(app, text=f"Your IP: {HOST}", grid=[0, 0])
connection_status_text = Text(app, text="Not connected right now", grid=[0, 1])
choice_text = Text(app, text="", grid=[0, 2])

host_label = Text(app, text="Host:", grid=[0, 3])
host_input = TextBox(app, width="fill", grid=[1, 3])
connect_button = PushButton(app, text="Connect", grid=[2, 3], command=start_client)
wait_for_connection_button = PushButton(app, text="Wait for Connection", grid=[3, 3], command=start_server)

rock_button = PushButton(app, text="Rock", grid=[0, 5], command=lambda: set_choice("rock"), visible=False)
paper_button = PushButton(app, text="Paper", grid=[1, 5], command=lambda: set_choice("paper"), visible=False)
scissors_button = PushButton(app, text="Scissors", grid=[2, 5], command=lambda: set_choice("scissors"), visible=False)

name_label = Text(app, text="Name:", grid=[0, 4])
name_input = TextBox(app, width="fill", grid=[1, 4], text="Default")

exit_button = PushButton(app, text="Exit", grid=[0, 6], command=exit_round, visible=False)

app.display()