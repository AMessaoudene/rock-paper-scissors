import sqlite3
import hashlib
from guizero import App, Text, TextBox, PushButton, Window
import threading
import socket

# Database setup
def setup_database():
    conn = sqlite3.connect("users.db")
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            username TEXT PRIMARY KEY,
            password TEXT NOT NULL
        )
    """)
    conn.commit()
    conn.close()

# Utility function for hashing passwords
def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

# Authentication functions
def register_user():
    username = username_input.value
    password = password_input.value

    if username and password:
        hashed_password = hash_password(password)
        conn = sqlite3.connect("users.db")
        cursor = conn.cursor()
        try:
            cursor.execute("INSERT INTO users (username, password) VALUES (?, ?)", (username, hashed_password))
            conn.commit()
            auth_status.value = "Registration successful!"
        except sqlite3.IntegrityError:
            auth_status.value = "Username already exists."
        conn.close()
    else:
        auth_status.value = "Please fill in both fields."

def login_user():
    username = username_input.value
    password = password_input.value

    hashed_password = hash_password(password)
    conn = sqlite3.connect("users.db")
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE username = ? AND password = ?", (username, hashed_password))
    user = cursor.fetchone()
    conn.close()

    if user:
        auth_window.hide()
        main_window.show()
    else:
        auth_status.value = "Invalid username or password."

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
app = App(title="Rock, Paper, Scissors", width=700, height=400, visible=False)

# Authentication window
auth_window = Window(app, title="Login", width=400, height=300)
auth_window.when_closed = app.destroy

Text(auth_window, text="Username:")
username_input = TextBox(auth_window, width="fill")
Text(auth_window, text="Password:")
password_input = TextBox(auth_window, width="fill", hide_text=True)

auth_status = Text(auth_window, text="")
PushButton(auth_window, text="Login", command=login_user)
PushButton(auth_window, text="Register", command=register_user)

# Main game window (hidden until login)
main_window = Window(app, title="Rock, Paper, Scissors", width=700, height=400, visible=False)

ip_text = Text(main_window, text=f"Your IP: {HOST}", grid=[0, 0])
connection_status_text = Text(main_window, text="Not connected right now", grid=[0, 1])
choice_text = Text(main_window, text="", grid=[0, 2])

host_label = Text(main_window, text="Host:", grid=[0, 3])
host_input = TextBox(main_window, width="fill", grid=[1, 3])
connect_button = PushButton(main_window, text="Connect", grid=[2, 3], command=start_client)
wait_for_connection_button = PushButton(main_window, text="Wait for Connection", grid=[3, 3], command=start_server)

rock_button = PushButton(main_window, text="Rock", grid=[0, 5], command=lambda: set_choice("rock"), visible=False)
paper_button = PushButton(main_window, text="Paper", grid=[1, 5], command=lambda: set_choice("paper"), visible=False)
scissors_button = PushButton(main_window, text="Scissors", grid=[2, 5], command=lambda: set_choice("scissors"), visible=False)

name_label = Text(main_window, text="Name:", grid=[0, 4])
name_input = TextBox(main_window, width="fill", text="Default")

exit_button = PushButton(main_window, text="Exit", grid=[0, 6], command=exit_round, visible=False)

auth_window.show()
setup_database()
app.display()
