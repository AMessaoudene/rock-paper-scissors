from guizero import App, Text, TextBox, PushButton
import threading
import socket

# Host IP address
HOST = socket.gethostbyname(socket.gethostname())
# Port number
PORT = 5555
# Store if the server or client is running
server_running = False
client_running = False
# Event to store if the choice has been set
choice_set = threading.Event()
# Event to store if the round should be exited
exit_round = threading.Event()

# Method to call the server as a thread
def call_server():
    # Don't call the server if it's already running
    if server_running == False:
        server_thread = threading.Thread(target=server)
        server_thread.daemon = True
        server_thread.start()

# Method to call the client as a thread
def call_client():
    # Don't call the client if it's already running
    if client_running == False:
        client_thread = threading.Thread(target=client)
        client_thread.daemon = True
        client_thread.start()

# The server method to wait for client connections
def server():
    # Toggle some of the UI elements to start the game
    start_game_ui()
    # The server has started running
    global server_running
    server_running = True
    # Display a waiting for connections message
    connection_status_text.value = "Waiting for connections..."
    # Run the server on the IP address of this machine and the port
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind((HOST, PORT))
        s.listen()
        # Accept the first connection from a client
        conn, _ = s.accept()
        with conn:
            # Receive the client's name
            client_name_raw = conn.recv(1024)
            client_name = client_name_raw.decode('utf-8')
            # Display a message that a connection was established with the client
            connection_status_text.value = f"Connected to {client_name}"
            # Get the user's name from the text box
            name = name_input.value
            # If the user did not input a name, use "Default" instead
            if name_input.value == "":
                name = "Default"
            # Send the server's name to the client
            conn.sendall(name.encode('utf-8'))
            # Receive the client's choice
            client_choice_raw = conn.recv(1024)
            client_choice = client_choice_raw.decode('utf-8')
            # Wait for the user to make their choice
            choice_set.wait()
            choice_set.clear()
            # Display a message with the user's choice and the client's choice
            choice_text.value = f"You chose {choice}, opponent chose {client_choice}"
            # Send the server's choice to the client
            conn.sendall(choice.encode('utf-8'))
            # Evaluate the winner of the game
            evaluate_winner(choice, client_choice)
            # Wait for the round to exit
            exit_round.wait()
            exit_round.clear()
    # Toggle some of the UI elements to reset the game
    reset_game_ui()
    # The server is no longer running
    server_running = False

# The client method to connect to a server
def client():
    # Toggle some of the UI elements to start the game
    start_game_ui()
    # The client has started running
    global client_running
    client_running = True
    # Display a connecting message
    connection_status_text.value = "Connecting..."
    try:
        # Connect to the server with the specified host IP address and port
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as conn:
            conn.connect((host_input.value, PORT))
            # Get the user's name from the text box
            name = name_input.value
            # If the user did not input a name, use "Default" instead
            if name_input.value == "":
                name = "Default"
            # Send the client's name to the server
            conn.sendall(name.encode('utf-8'))
            # Receive the server's name
            server_name_raw = conn.recv(1024)
            server_name = server_name_raw.decode('utf-8')
            # Display a message that a connection was established with the server
            connection_status_text.value = f"Connected to {server_name}"
            # Wait for the user to make their choice
            choice_set.wait()
            choice_set.clear()
            # Send the client's choice to the server
            conn.sendall(choice.encode('utf-8'))
            # Receive the server's choice
            server_choice_raw = conn.recv(1024)
            server_choice = server_choice_raw.decode('utf-8')
            # Display a message with the user's choice and the server's choice
            choice_text.value = f"You chose {choice}, opponent chose {server_choice}"
            # Evaluate the winner of the game
            evaluate_winner(choice, server_choice)
            # Wait for the round to exit
            exit_round.wait()
            exit_round.clear()
    # If the connection was refused, the specified host IP was unavailable
    except ConnectionRefusedError:
        connection_status_text.value = f"Couldn't connect to {host_input.value}"
    # If there was another error, IP address was invalid
    except OSError:
        connection_status_text.value = "An invalid address was entered"
    # Toggle some of the UI elements to reset the game
    reset_game_ui()
    # The client is no longer running
    client_running = False

# A method to return a message based on the game's outcome
def evaluate_winner(user_choice, opponent_choice):

    # Different possible winning scenarios
    WINNING_CASES = [
        ["scissors", "paper"],
        ["rock", "scissors"],
        ["paper", "rock"]
    ]
    global message
    message = ""
    # If the user and opponent have the same choice, the game is a tie
    if user_choice == opponent_choice:
        message = "Tie game!"
    # If the user's scenario is one of the winning cases, the user wins
    elif [user_choice, opponent_choice] in WINNING_CASES:
        message = "You win!"
    # Otherwise, the opponent wins
    else:
        message = "You lose!"
    # Display the winner
    connection_status_text.value = message
    # Make the exit button visible
    exit_button.show()

# A method for the user to set their choice
def set_choice(action_choice):
    # Hide all of the choice buttons
    rock_button.hide()
    paper_button.hide()
    scissors_button.hide()
    # Set the user's choice
    global choice
    choice = action_choice
    # Display a waiting for opponent's choice message
    choice_text.value = "Waiting for opponent to make their choice..."
    # Set the event to notify the server or client that the choice has been set
    choice_set.set()

# Hide certain UI elements when the game has begun
def start_game_ui():
    # Hide the host address input
    host_label.hide()
    host_input.hide()
    # Hide the name input
    name_label.hide()
    name_input.hide()
    # Hide the connection buttons
    connect_button.hide()
    wait_for_connection_button.hide()
    # Show the choice buttons
    rock_button.show()
    paper_button.show()
    scissors_button.show()

def reset_game_ui():
    # Show the host address input
    host_label.show()
    host_input.show()
    # Show the name input
    name_label.show()
    name_input.show()
    # Show the connection buttons
    connect_button.show()
    wait_for_connection_button.show()
    # Hide the choice buttons
    rock_button.hide()
    paper_button.hide()
    scissors_button.hide()
    # Reset the connection status text
    connection_status_text.value = "Not connected right now"

# A method to set the round to be exited
def exit_round_setup():
    # Set the exit event
    exit_round.set()
    # Hide the exit button
    exit_button.hide()

# The main app that contains all of the UI
app = App(title="Rock, Paper, Scissors", layout="grid", width=700, height=300)

ip_text = Text(app, text=HOST, grid=[0, 0])
connection_status_text = Text(app, text="Not connected right now", grid=[0, 1])
choice_text = Text(app, text="", grid=[0, 2], visible=False)

host_label = Text(app, text="Host:", grid=[0, 3])
host_input = TextBox(app, width="fill", grid=[1, 3])
connect_button = PushButton(app, text="Connect", grid=[2, 3], command=call_client)
wait_for_connection_button = PushButton(app, text="Wait for connection", grid=[3, 3], command=call_server)

rock_button = PushButton(app, text="Rock", grid=[0, 5], command=lambda: set_choice("rock"), visible=False)
paper_button = PushButton(app, text="Paper", grid=[1, 5], command=lambda: set_choice("paper"), visible=False)
scissors_button = PushButton(app, text="Scissors", grid=[2, 5], command=lambda: set_choice("scissors"), visible=False)

name_label = Text(app, text="Name:", grid=[0, 4])
name_input = TextBox(app, width="fill", text="Default", grid=[1, 4])

exit_button = PushButton(app, text="Exit", grid=[0, 5], visible=False, command=exit_round_setup)

app.display()
