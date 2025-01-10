import asyncio
import websockets
import json
from flask import Flask, render_template
from flask_socketio import SocketIO
from threading import Thread
import threading
from obswebsocket import obsws, requests
import json
import os
import time

app = Flask(__name__)
socketio = SocketIO(app)

def save_ftc_rules(rules, filename='ftc.json'):
    with open(filename, 'w') as file:
        json.dump(rules, file)

def load_ftc_rules(filename='ftc.json'):
    if os.path.exists(filename):
        with open(filename, 'r') as file:
            return json.load(file)
    return []

def save_obs_rules(rules, filename='obs.json'):
    print(f"Settings saved: {rules}")
    with open(filename, 'w') as file:
        json.dump(rules, file)

def load_obs_rules(filename='obs.json'):
    if os.path.exists(filename):
        with open(filename, 'r') as file:
            return json.load(file)
    return {}

def save_switching_rules(rules, filename='switching_rules.json'):
    with open(filename, 'w') as file:
        json.dump(rules, file)

def load_switching_rules(filename='switching_rules.json'):
    if os.path.exists(filename):
        with open(filename, 'r') as file:
            return json.load(file)
    return []

# Initialize a list to keep track of running timers
running_timers = []

switcherEnabled = False
dynamic_switching_rules = load_switching_rules()
obs_settings = load_obs_rules()
ftc_settings = load_ftc_rules()
ws = obsws(obs_settings['host'], obs_settings['port'], obs_settings['password'])

ftc_connection_active = False
obs_connection_active = False
ftc_websocket = None

@socketio.on('obsConnect')
def obsConnect():
    global obs_connection_active
    print("Connecting to OBS")
    try:
        ws.connect()
        socketio.emit('obsStatus', {'message': '🟢 Connected'})
        obs_connection_active = True
    except Exception as e:
        print(f"Failed to connect to OBS: {e}")
        socketio.emit('obsStatus', {'message': '🟥 Disconnected'})
        obs_connection_active = False

@socketio.on('obsDisconnect')
def obsDisconnect():
    print("Disconnecting from OBS")
    try:
        ws.disconnect()
        socketio.emit('obsStatus', {'message': '🟥 Disconnected'})
        obs_connection_active = False
    except Exception as e:
        print(f"Failed to disconnect from OBS: {e}")

@socketio.on('enable')
def enable():
    global switcherEnabled
    print("Enabling switcher")
    socketio.emit('enableStatus', {'message': '🟢 ON'})
    switcherEnabled = True

@socketio.on('disable')
def disable():
    global switcherEnabled
    print("Disabling switcher")
    socketio.emit('enableStatus', {'message': '🟥 OFF'})
    switcherEnabled = False

#@socketio.on('update_switching_rules')
#def update_switching_rules(rules):
#    global dynamic_switching_rules
#    dynamic_switching_rules = rules
#    print("Updated switching rules:", dynamic_switching_rules)

@app.route('/')
def index():
    return render_template('index.html')  

@socketio.on('pageLoad')
def pageLoad():
    global ftc_connection_active
    if ftc_connection_active:
        socketio.emit('ftcStatus', {'message': '🟢 Connected'})
    else:
        socketio.emit('ftcStatus', {'message': '🟥 Disconnected'})
    if obs_connection_active:
        socketio.emit('obsStatus', {'message': '🟢 Connected'})
    else:
        socketio.emit('obsStatus', {'message': '🟥 Disconnected'})
    if switcherEnabled:
        socketio.emit('enableStatus', {'message': '🟢 ON'})
    else:
        socketio.emit('enableStatus', {'message': '🟥 OFF'})

@socketio.on('ftcConnect')
def ftcConnect():
    global ftc_connection_active
    if not ftc_connection_active:
        print("Connecting to FTC Live")
        ftc_connection_active = True
        websocket_thread = Thread(target=start_websocket)
        websocket_thread.start()
    else:
        print("Already connected to FTC Live")
        socketio.emit('ftcStatus', {'message': '🟠 Already Connected'})

@socketio.on('ftcDisconnect')
def ftcDisconnect():
    global ftc_connection_active, ftc_websocket
    if ftc_connection_active and ftc_websocket:
        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            loop.run_until_complete(close_websocket(ftc_websocket))
            loop.close()
            print("Disconnecting from FTC Live")
            socketio.emit('ftcStatus', {'message': '🟥 Disconnected'})
            ftc_connection_active = False
            ftc_websocket = None
        except:
            print("error disconnecting")
    else:
        print("Not connected to FTC Live")
        socketio.emit('ftcStatus', {'message': '🟠 Not Connected'})

@socketio.on('update_switching_rules')
def update_switching_rules(rules):
    global dynamic_switching_rules
    dynamic_switching_rules = rules
    save_switching_rules(dynamic_switching_rules)
    print("Updated switching rules:", dynamic_switching_rules)

@socketio.on('update_ftc_rules')
def handle_update_ftc_settings(rules):
    global ftc_settings
    ftc_settings['host'] = rules['ftcHost']
    ftc_settings['event_code'] = rules['eventCode']
    ftc_settings['finals_field'] = rules['finalsField']
    save_ftc_rules(ftc_settings)
    print(f"Updated FTC settings: {ftc_settings}")

@socketio.on('update_obs_rules')
def handle_update_obs_settings(rules):
    global obs_settings, ws
    obs_settings['host'] = rules['obsHost']
    obs_settings['port'] = rules['obsPort']
    obs_settings['password'] = rules['obsPassword']
    save_obs_rules(obs_settings)
    print(f"Updated OBS settings: {obs_settings}")
    
    # Reconnect to OBS with new settings
    ws = obsws(obs_settings['host'], obs_settings['port'], obs_settings['password'])


@socketio.on('fetch_ftc_rules')
def fetch_ftc_rules():
    socketio.emit('update_ftc_rules', ftc_settings)

@socketio.on('fetch_obs_rules')
def fetch_obs_rules():
    socketio.emit('update_obs_rules', obs_settings)

@socketio.on('fetch_switching_rules')
def fetch_switching_rules():
    socketio.emit('update_switching_rules', dynamic_switching_rules)

async def websocket_handler():
    global ftc_connection_active, ftc_websocket
    url = f"ws://" + ftc_settings['host'] + "/api/v2/stream/?code=" + ftc_settings['event_code']

    print("Connecting to FTC Live WebSocket")

    async with websockets.connect(url) as websocket:
        ftc_websocket = websocket
        print("Connected to FTC Live WebSocket")
        socketio.emit('ftcStatus', {'message': '🟢 Connected'})

        try:
            while True:
                message = await websocket.recv()
                print(f"Received message: {message}")

                socketio.emit('ftcStatus', {'message': '🟢 Connected'})

                if message != "pong":
                    data = json.loads(message)
                    updateType = data["updateType"]
                    field = data["payload"]["field"]
                    shortName = data["payload"]["shortName"]

                    if field == 0:
                        field = ftc_settings['finals_field']

                    process_field_update(field, updateType, shortName)
        except websockets.exceptions.ConnectionClosed:
            print("WebSocket connection closed")
            socketio.emit('ftcStatus', {'message': '🟥 Disconnected'})
            ftc_connection_active = False
            ftc_websocket = None

async def close_websocket(websocket):
    await websocket.close()

def cancel_timers():
    """Cancel all running timers."""
    for timer in running_timers:
        if timer.is_alive():
            timer.cancel()
    running_timers.clear()

def timer_function(wait_time, switch_to):
    """Function to switch scenes after waiting."""
    try:
        print("wait_time:" + str(wait_time) + "switch_to:" + str(switch_to))
        #time.sleep(wait_time)
        switch_to_scene(switch_to)
    except ValueError:
        print("Invalid wait time value")

def process_field_update(field, updateType, shortName):
    global running_timers

    if switcherEnabled:
        # Cancel any running timers
        cancel_timers()
        
        for rule in dynamic_switching_rules:
            if rule['on'] in ['field1', 'field2', 'any'] and (rule['on'] == f'field{field}' or rule['on'] == 'any'):
                if updateType == rule['when']:
                    try:
                        wait_time = float(rule['wait'])
                        timer = threading.Timer(wait_time, timer_function, [wait_time, rule['switchTo']])
                        timer.start()
                        running_timers.append(timer)
                        print(running_timers)
                    except ValueError:
                        print("Invalid wait time value")


def switch_to_scene(name):
    try:
        ws.call(requests.SetCurrentProgramScene(sceneName=name))
        print(f"Switching to: {name}")
    except Exception as e:
        print(f"Failed to switch scene: {e}")

def start_websocket():
    asyncio.set_event_loop(asyncio.new_event_loop())
    asyncio.get_event_loop().run_until_complete(websocket_handler())

if __name__ == '__main__':
    socketio.run(app, debug=True)
