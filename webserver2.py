import asyncio
import websockets
import json
from flask import Flask, render_template 
from flask_socketio import SocketIO
from threading import Thread
from obswebsocket import obsws, requests

app = Flask(__name__)
socketio = SocketIO(app)

switcherEnabled = False

# ftc websocket settings
ftcHost = "localhost"
ftcEventCode = "uspacmp"
finalField = 1

#obs websocket settings
obsHost = "localhost"
obsPort = 4455
obsPassword = "lVjHNHN9sMmQnKOv"
ws = obsws(obsHost, obsPort, obsPassword)

@socketio.on('obsConnect')
def obsConnect():
    print("connecting to obs")
    socketio.emit('obsStatus', {'message': '🟢 Connected'})
    ws.connect()

@socketio.on('obsDisconnect')
def obsDisonnect():
    print("disconnecting from obs")
    socketio.emit('obsStatus', {'message': '🟥 Disconnected'})
    ws.disconnect()

@socketio.on('enable')
def enable():
    global switcherEnabled
    print("turning on")
    socketio.emit('enableStatus', {'message': '🟢 ON'})
    switcherEnabled = True

@socketio.on('disable')
def disable():
    global switcherEnabled
    print("turning off")
    socketio.emit('enableStatus', {'message': '🟥 OFF'})
    switcherEnabled = False

@app.route('/')
def index():
    return render_template('index.html')

@socketio.on('ftc')
def obsConnect():
    print("connecting to ftc live")
    websocket_thread = Thread(target=start_websocket)
    websocket_thread.start()
    
async def websocket_handler():
    url = f"ws://" + ftcHost + "/api/v2/stream/?code=" + ftcEventCode
    print("connecting to ftc live")
    socketio.emit('ftcStatus', {'message': '🟡 Connecting...'})

    async with websockets.connect(url) as websocket:
        print("Connected to ftc live WebSocket")

        while True:
            try:
                message = await websocket.recv()
                socketio.emit('ftcStatus', {'message': '🟢 Connected'})
                print(f"Received message: {message}")

                if(message != "pong"):
                    data = json.loads(message)

                    # Extract values and save to variables
                    updateType = data["updateType"]
                    field = data["payload"]["field"]
                    shortName = data["payload"]["shortName"]

                    #what to do for finals
                    if(field == 0):
                        field = finalField

                    if(field == 1):
                        #send to flast server
                        socketio.emit('Field1', {'shortName': shortName, 'updateType': updateType})
                        if(switcherEnabled == True):
                            print(updateType)
                            #update OBS
                            if(updateType == "SHOW_PREVIEW" or updateType == "SHOW_MATCH" or updateType == "MATCH_ABORT"):
                                switch_to_scene("Field1_noOverlay")
                            if(updateType == "MATCH_START" or updateType == "MATCH_POST"):
                                ws.call(requests.SetCurrentProgramScene(sceneName="Field1"))
                                switch_to_scene("Field1")
                    if(field == 2):
                        socketio.emit('Field2', {'shortName': shortName, 'updateType': updateType})
                        if(switcherEnabled == True):
                            #update OBS
                            if(updateType == "SHOW_PREVIEW" or updateType == "SHOW_MATCH" or updateType == "MATCH_ABORT"):
                                switch_to_scene("Field2_noOverlay")
                            if(updateType == "MATCH_START" or updateType == "MATCH_POST"):
                                switch_to_scene("Field2")

            except websockets.exceptions.ConnectionClosed:
                print("WebSocket connection closed")
                socketio.emit('ftcStatus', {'message': '🟥 Disconnected'})
                break

def switch_to_scene(name):
    try:
        ws.call(requests.SetCurrentProgramScene(sceneName=name))
        print("switcheing to: " + name)

    except KeyboardInterrupt:
        pass

def start_websocket():
    asyncio.set_event_loop(asyncio.new_event_loop())
    asyncio.get_event_loop().run_until_complete(websocket_handler())

if __name__ == '__main__':
    socketio.run(app, debug=True)
