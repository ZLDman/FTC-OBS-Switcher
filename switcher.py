import asyncio
import websockets
import json
import sys
import time

#import logging
#logging.basicConfig(level=logging.DEBUG)

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
ws.connect()

async def connect_to_websocket():
    url = f"ws://" + ftcHost + "/api/v2/stream/?code=" + ftcEventCode

    async with websockets.connect(url) as websocket:
        print("Connected to WebSocket")

        # Create a new event loop
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        while True:
            try:
                message = await websocket.recv()
                #print(f"Received message: {message}")
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
        
if __name__ == "__main__":
    asyncio.get_event_loop().run_until_complete(connect_to_websocket())