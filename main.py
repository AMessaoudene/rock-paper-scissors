import sqlite3
import hashlib
from guizero import App, Text, TextBox, PushButton, Window, ListBox
import threading
import socket
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Database setup
def setup_database():
    logging.info("Setting up the database.")
    conn = sqlite3.connect("users.db")
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            username TEXT PRIMARY KEY,
            password TEXT NOT NULL,
            score INTEGER DEFAULT 0,
            games_played INTEGER DEFAULT 0,
            wins INTEGER DEFAULT 0,
            losses INTEGER DEFAULT 0,
            ties INTEGER DEFAULT 0
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS games (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            player1 TEXT NOT NULL,
            player2 TEXT NOT NULL,
            winner TEXT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(player1) REFERENCES users(username),
            FOREIGN KEY(player2) REFERENCES users(username)
        )
    """)
    conn.commit()
    conn.close()

def setup_invitations_table():
    logging.info("Setting up invitations table.")
    conn = sqlite3.connect("users.db")
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS invitations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            sender TEXT NOT NULL,
            recipient TEXT NOT NULL,
            status TEXT DEFAULT 'pending',
            FOREIGN KEY(sender) REFERENCES users(username),
            FOREIGN KEY(recipient) REFERENCES users(username)
        )
    """)
    conn.commit()
    conn.close()
# Update user statistics after a game
def update_user_stats(username, result):
    logging.info(f"Updating stats for user {username} with result: {result}.")
    conn = sqlite3.connect("users.db")
    cursor = conn.cursor()
    stats_update = {
        'win': "wins = wins + 1, score = score + 1",
        'loss': "losses = losses + 1, score = score - 1",
        'tie': "ties = ties + 1"
    }
    query = f"""
        UPDATE users SET games_played = games_played + 1, {stats_update[result]} WHERE username = ?
    """
    cursor.execute(query, (username,))
    conn.commit()
    conn.close()

# Record a game in the database
def record_game(player1, player2, winner):
    logging.info(f"Recording game: {player1} vs {player2}, winner: {winner}.")
    conn = sqlite3.connect("users.db")
    cursor = conn.cursor()
    cursor.execute("INSERT INTO games (player1, player2, winner) VALUES (?, ?, ?)", (player1, player2, winner))
    conn.commit()
    conn.close()

# Display leaderboard
def show_leaderboard():
    logging.info("Displaying leaderboard.")
    leaderboard_list.clear()
    conn = sqlite3.connect("users.db")
    cursor = conn.cursor()
    cursor.execute("SELECT username, score, games_played FROM users ORDER BY score DESC")
    for row in cursor.fetchall():
        leaderboard_list.append(f"{row[0]}: {row[1]} points, {row[2]} games played")
    conn.close()

# Evaluate game result
def evaluate_winner():
    user = game_choices["user_choice"]
    opponent = game_choices["opponent_choice"]

    if user == opponent:
        logging.info("Game was a tie.")
        return "The game was a tie!", "tie"
    elif [user, opponent] in WINNING_CASES:
        logging.info("User won the game.")
        return "You won the game!", "win"
    else:
        logging.info("User lost the game.")
        return "You lost the game!", "loss"

# Display game results
def display_results():
    result_message, result = evaluate_winner()
    connection_status_text.value = result_message
    choice_text.value = f"You chose {game_choices['user_choice']}, opponent chose {game_choices['opponent_choice']}"
    update_user_stats(current_user, result)
    record_game(current_user, "Opponent", current_user if result == "win" else ("Opponent" if result == "loss" else None))
    exit_button.show()

# Utility function for hashing passwords
def hash_password(password):
    logging.debug("Hashing password.")
    return hashlib.sha256(password.encode()).hexdigest()

# Authentication functions
def register_user():
    username = username_input.value
    password = password_input.value

    logging.info(f"Attempting to register user: {username}")

    if username and password:
        hashed_password = hash_password(password)
        conn = sqlite3.connect("users.db")
        cursor = conn.cursor()
        try:
            cursor.execute("INSERT INTO users (username, password) VALUES (?, ?)", (username, hashed_password))
            conn.commit()
            auth_status.value = "Registration successful!"
            logging.info(f"User {username} registered successfully.")
        except sqlite3.IntegrityError:
            auth_status.value = "Username already exists."
            logging.warning(f"Registration failed. Username {username} already exists.")
        conn.close()
    else:
        auth_status.value = "Please fill in both fields."
        logging.warning("Registration failed. Missing username or password.")

def login_user():
    username = username_input.value
    password = password_input.value

    logging.info(f"Attempting to log in user: {username}")

    hashed_password = hash_password(password)
    conn = sqlite3.connect("users.db")
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE username = ? AND password = ?", (username, hashed_password))
    user = cursor.fetchone()
    conn.close()

    if user:
        global current_user
        current_user = username
        auth_window.hide()
        main_window.show()
        logging.info(f"User {username} logged in successfully.")
    else:
        auth_status.value = "Invalid username or password."
        logging.warning(f"Login failed for user {username}.")

# Update score after the game
def update_score(username, delta):
    logging.info(f"Updating score for user {username} by {delta}.")
    conn = sqlite3.connect("users.db")
    cursor = conn.cursor()
    cursor.execute("UPDATE users SET score = score + ? WHERE username = ?", (delta, username))
    conn.commit()
    conn.close()

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
        logging.info("Starting server thread.")
        threading.Thread(target=server_thread, daemon=True).start()

def start_client():
    if not game_state["client_running"]:
        logging.info("Starting client thread.")
        threading.Thread(target=client_thread, daemon=True).start()

def server_thread():
    logging.info("Server thread started.")
    setup_game_ui("server")
    game_state["server_running"] = True
    connection_status_text.value = "Waiting for connections..."

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as server_socket:
        server_socket.bind((HOST, PORT))
        server_socket.listen()
        conn, _ = server_socket.accept()

        logging.info("Client connected to the server.")

        with conn:
            handle_connection(conn, role="server")

    reset_game_ui()
    game_state["server_running"] = False
    logging.info("Server thread stopped.")

def client_thread():
    logging.info("Client thread started.")
    setup_game_ui("client")
    game_state["client_running"] = True
    connection_status_text.value = "Connecting..."

    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as client_socket:
            client_socket.connect((host_input.value, PORT))
            logging.info("Client connected to the server.")
            handle_connection(client_socket, role="client")
    except ConnectionRefusedError:
        connection_status_text.value = f"Couldn't connect to {host_input.value}"
        logging.error(f"Connection refused to {host_input.value}.")
    except OSError:
        connection_status_text.value = "Invalid address entered"
        logging.error("Invalid address entered.")

    reset_game_ui()
    game_state["client_running"] = False
    logging.info("Client thread stopped.")

def handle_connection(conn, role):
    local_name = name_input.value or "Default"

    logging.info(f"Handling connection as {role}.")

    if role == "server":
        conn.sendall(local_name.encode())
        opponent_name = conn.recv(1024).decode()
    else:
        conn.sendall(local_name.encode())
        opponent_name = conn.recv(1024).decode()

    logging.info(f"Connected to opponent: {opponent_name}")

    connection_status_text.value = f"Connected to {opponent_name}"

    game_state["choice_set"].wait()
    game_state["choice_set"].clear()

    conn.sendall(game_choices["user_choice"].encode())
    game_choices["opponent_choice"] = conn.recv(1024).decode()

    logging.info(f"User choice: {game_choices['user_choice']}, Opponent choice: {game_choices['opponent_choice']}.")

    display_results()

    game_state["round_exit"].wait()
    game_state["round_exit"].clear()

def set_choice(choice):
    logging.info(f"User selected choice: {choice}")
    game_choices["user_choice"] = choice
    game_state["choice_set"].set()
    toggle_choice_buttons(False)
    choice_text.value = "Waiting for opponent to make their choice..."

def evaluate_winner():
    user = game_choices["user_choice"]
    opponent = game_choices["opponent_choice"]

    if user == opponent:
        logging.info("Game was a tie.")
        return "The game was a tie!", 0
    elif [user, opponent] in WINNING_CASES:
        logging.info("User won the game.")
        return "You won the game!", 1
    else:
        logging.info("User lost the game.")
        return "You lost the game!", -1

def display_results():
    result_message, score_delta = evaluate_winner()
    connection_status_text.value = result_message
    choice_text.value = f"You chose {game_choices['user_choice']}, opponent chose {game_choices['opponent_choice']}"
    update_score(current_user, score_delta)
    exit_button.show()

def setup_game_ui(role):
    logging.info(f"Setting up game UI for {role}.")
    toggle_ui_elements(False)
    toggle_choice_buttons(True)
    if role == "server":
        host_label.hide()
        host_input.hide()

def reset_game_ui():
    logging.info("Resetting game UI.")
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
    logging.info("Exiting round.")
    game_state["round_exit"].set()
    exit_button.hide()

# Invitation system
def invite_player():
    logging.info("Opening invite player window.")
    invite_list.clear()
    conn = sqlite3.connect("users.db")
    cursor = conn.cursor()
    cursor.execute("SELECT username FROM users WHERE username != ?", (current_user,))
    users = cursor.fetchall()
    conn.close()

    for user in users:
        invite_list.append(user[0])

    invite_window.show()

def send_invite():
    selected_user = invite_list.value
    if selected_user:
        conn = sqlite3.connect("users.db")
        cursor = conn.cursor()
        cursor.execute("INSERT INTO invitations (sender, recipient) VALUES (?, ?)", (current_user, selected_user))
        conn.commit()
        conn.close()
        logging.info(f"Invitation sent from {current_user} to {selected_user}.")
        invitation_status.value = f"Invitation sent to {selected_user}!"
    else:
        invitation_status.value = "Please select a user to invite."

def show_received_invitations():
    logging.info("Fetching received invitations.")
    received_invitations_list.clear()
    conn = sqlite3.connect("users.db")
    cursor = conn.cursor()
    cursor.execute("""
        SELECT sender, status 
        FROM invitations 
        WHERE recipient = ? AND status IN ('pending', 'accepted')
    """, (current_user,))
    for row in cursor.fetchall():
        received_invitations_list.append(f"Invite from {row[0]} ({row[1]})")
    conn.close()
    received_invitations_window.show()

def accept_invite():
    """
    Accept an invitation and start the match.
    The inviter becomes the server, and the invitee becomes the client.
    """
    selected_invitation = received_invitations_list.value
    if selected_invitation:
        sender = selected_invitation.split("(")[0].strip().replace("Invite from ", "")
        conn = sqlite3.connect("users.db")
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE invitations 
            SET status = 'accepted' 
            WHERE sender = ? AND recipient = ? AND status = 'pending'
        """, (sender, current_user))
        conn.commit()
        conn.close()
        
        logging.info(f"Invitation from {sender} accepted by {current_user}.")
        received_invitations_window.hide()
        
        # Start the match - invitee connects to inviter
        start_match(opponent=sender, is_inviter=False)
    else:
        logging.warning("No invitation selected to accept.")

def start_match(opponent, is_inviter):
    """
    Initiate the match between two players.
    The inviter starts the server, and the invitee starts the client.
    """
    logging.info(f"Starting match between {current_user} and {opponent}.")
    
    if is_inviter:
        # Current user is the inviter, start as server
        logging.info(f"{current_user} is the inviter, starting as server.")
        start_server()
    else:
        # Current user is the invitee, start as client
        logging.info(f"{current_user} is the invitee, starting as client.")
        
        # Use a predefined host address for the inviter (could be dynamic in a real app)
        host_input.value = HOST  # Replace HOST with inviter's IP if dynamic IPs are used
        start_client()

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
PushButton(main_window, text="Invite Player", grid=[0, 8], command=invite_player)

# Leaderboard window
leaderboard_window = Window(app, title="Leaderboard", width=400, height=300, visible=False)
leaderboard_list = ListBox(leaderboard_window, items=[], width="fill", height="fill")
PushButton(leaderboard_window, text="Close", command=leaderboard_window.hide)
PushButton(main_window, text="Leaderboard", grid=[0, 7], command=lambda: [leaderboard_window.show(), show_leaderboard()])

# Game Stats window
stats_window = Window(app, title="Game Stats", width=400, height=300, visible=False)
stats_list = ListBox(stats_window, items=[], width="fill", height="fill")
PushButton(stats_window, text="Close", command=stats_window.hide)

# Function to display game stats
def show_game_stats():
    logging.info("Displaying game stats for the user.")
    stats_list.clear()
    conn = sqlite3.connect("users.db")
    cursor = conn.cursor()
    cursor.execute("""
        SELECT games_played, wins, losses, ties, score 
        FROM users 
        WHERE username = ?
    """, (current_user,))
    stats = cursor.fetchone()
    conn.close()
    
    if stats:
        stats_list.append(f"Games Played: {stats[0]}")
        stats_list.append(f"Wins: {stats[1]}")
        stats_list.append(f"Losses: {stats[2]}")
        stats_list.append(f"Ties: {stats[3]}")
        stats_list.append(f"Score: {stats[4]}")
    else:
        stats_list.append("No stats available for the user.")

# Add "Game Stats" button to main window
PushButton(main_window, text="Game Stats", grid=[2, 7], command=lambda: [stats_window.show(), show_game_stats()])

# Invite player window
invite_window = Window(app, title="Invite Player", width=400, height=300, visible=False)
invite_list = ListBox(invite_window, items=[], width="fill", height="fill")
invitation_status = Text(invite_window, text="")
PushButton(invite_window, text="Send Invite", command=send_invite)
PushButton(invite_window, text="Close", command=invite_window.hide)

# Received invitations window
received_invitations_window = Window(app, title="Received Invitations", width=400, height=300, visible=False)
received_invitations_list = ListBox(received_invitations_window, items=[], width="fill", height="fill")
PushButton(received_invitations_window, text="Close", command=received_invitations_window.hide)
PushButton(received_invitations_window, text="Accept Invite", command=accept_invite)
PushButton(main_window, text="View Invitations", grid=[1, 8], command=show_received_invitations)

auth_window.show()
setup_database()
setup_invitations_table()
app.display()
