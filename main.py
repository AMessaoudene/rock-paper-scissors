from guizero import App, Text, TextBox, PushButton

app = App(title="Rock, Paper, Scissors", layout="grid")

host_label = Text(app, text="Host:", grid=[0, 0])
host_input = TextBox(app, width="fill", grid=[1, 0])
connect_button = PushButton(app, height=0.5, text="Connect", grid=[2, 0])

app.display()
