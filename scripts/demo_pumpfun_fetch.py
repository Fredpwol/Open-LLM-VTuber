import asyncio
import json
import websockets
import re
import time
from loguru import logger

ROOM_ID = "DHS1JnKrzmaxGScdcNigkgBRpY4pNeLeoTaoPZhipump"  # Example room ID
LIMIT = 5

async def pumpfun_ws_demo(room_id, limit=20):
    ws_url = "wss://livechat.pump.fun/socket.io/?EIO=4&transport=websocket"
    last_timestamp = int(time.time() * 1000)
    try:
        async with websockets.connect(ws_url) as ws:
            await ws.send("40")  # Socket.io handshake
            await asyncio.sleep(0.5)
            print("Connected")
            # Join the room
            join_room = ["joinRoom", {"roomId": room_id, "username": ""}]
            await ws.send(f'420{json.dumps(join_room)}')
            await asyncio.sleep(0.2)
            print("room joined")
            # Request message history
            req = ["getMessageHistory", {"roomId": room_id, "before": last_timestamp, "limit": limit}]
            await ws.send(f'421{json.dumps(req)}')
            while True:
                try:
                    msg = await asyncio.wait_for(ws.recv(), timeout=10)

                    match = re.match(r'^(\d+)(.*)', msg)
                    if match:
                        number = match.group(1)  # '430'
                        rest = match.group(2) 
                    body = json.loads(rest)
                    messages = []
                    if type(body) == list:
                        if "messages" in body[0] and type(body[0]) == dict:
                            messages = body[0]["messages"]
                            pass
                        elif type(body[0]) == list and all([msgkey in body[0][0] for msgkey in ["username", "id", "userAddress", "roomId", "message", "messageType"]]):
                            print("get message response:", "\n\n\n")
                            messages = body[0]
                
                            

                    for message in messages:
                        user = message.get("username")
                        text = message.get("message")
                        logger.info(f"{user}: {text}")
                        await asyncio.sleep(0.5)
                except asyncio.TimeoutError:
                    continue
    except Exception as e:
        logger.error(f"Error in demo fetch: {e}")

if __name__ == "__main__":
    asyncio.run(pumpfun_ws_demo(ROOM_ID, LIMIT))
