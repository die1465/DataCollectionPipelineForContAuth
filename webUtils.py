from Utils import *

sio = socketio.Client()
 

with open("quotes.json", "r") as file:
    data = json.load(file)

# Extract the "quotes" array
quotes_list = data["quotes"]
# print(quotes_list)

rooms = {}

def generate_unique_code(length):
    while True:
        code = ""
        for _ in range(length):
            code += random.choice(ascii_uppercase)
        
        if code not in rooms:
            break
    
    return code


sio.connect(
        "http://localhost:5001",
        headers={"device-type": "website"}  # Add custom headers here
    )