import asyncio
import websockets
import json
import sys
from flask import Flask, render_template
from flask_socketio import SocketIO, emit
import time
from threading import Thread

app = Flask(__name__)
socketio = SocketIO(app)

timer_thread = None
match_duration = 150  # 2 minutes and 30 seconds in seconds
abort_flag = False

sys.path.append('../')
from obswebsocket import obsws, requests  # noqa: E402

#obs websocket settings
obsHost = "localhost"
obsPort = 4455
obsPassword = "lVjHNHN9sMmQnKOv"

#ftc websocket settings
ftcHost = "localhost"
ftcEventCode = "test"

ws = obsws(obsHost, obsPort, obsPassword)

@app.route('/')
def index():
    return render_template('index.html')

 

@socketio.on('obsConnect')
def obsConnect():
    print("connecting to obs")
    ws.connect()

@socketio.on('obsDisconnect')
def obsDisonnect():
    print("disconnecting from obs")
    ws.disconnect()

@socketio.on('start_match')
def start_match():
    global timer_thread, abort_flag
    if timer_thread and timer_thread.is_alive():
        emit('match_running', {'status': True})
    else:
        abort_flag = False
        timer_thread = Thread(target=timer_function)
        timer_thread.start()

@socketio.on('abort_match')
def abort_match():
    global abort_flag
    if timer_thread and timer_thread.is_alive():
        abort_flag = True
        emit('match_aborted')

def timer_function():
    global timer_thread, abort_flag
    remaining_time = match_duration
    while remaining_time > 0 and not abort_flag:
        socketio.emit('update_timer', {'time': remaining_time})
        time.sleep(1)
        remaining_time -= 1

    timer_thread = None
    if abort_flag:
        socketio.emit('match_aborted')
    else:
        socketio.emit('match_complete')
    
async def connect_to_websocket():
    url = f"ws://" + ftcHost + "/api/v2/stream/?code=" + ftcEventCode
    print("connecting to ftc live2")

    async with websockets.connect(url) as websocket:
        print("Connected to ftc live WebSocket")

        # Create a new event loop
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        while True:
            try:
                message = await websocket.recv()
                print(f"Received message: {message}")
                # Parse the JSON data
                
                if(message != "pong"):
                    data = json.loads(message)

                    # Extract values and save to variables
                    update_type = data["updateType"]
                    field_number = data["payload"]["field"]
                    
                    switch_to_scene(update_type,field_number)
                
            except websockets.exceptions.ConnectionClosed:
                print("WebSocket connection closed")
                break
                
def switch_to_scene(updateType, field):
    try:
        name = ""
        if(updateType == "SHOW_PREVIEW" and field == 1):
            name = "Field 1"
        if(updateType == "SHOW_PREVIEW" and field == 2):
            name = "Field 2"
        if(updateType == "SHOW_MATCH" and field == 1):
            name = "Field 1"
        if(updateType == "SHOW_MATCH" and field == 2):
            name = "Field 2"
        if(updateType == "MATCH_START" and field == 1):
            name = "Field 1"
        if(updateType == "MATCH_START" and field == 2):
            name = "Field 2"
            
        if(name != ""):
            ws.call(requests.SetCurrentProgramScene(sceneName=name))
            print("switcheing to: " + name)

    except KeyboardInterrupt:
        pass

if __name__ == '__main__':
    asyncio.get_event_loop().run_until_complete(connect_to_websocket())
    socketio.run(app, debug=True)