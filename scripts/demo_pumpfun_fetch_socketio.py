import asyncio
import socketio
from loguru import logger
import time

ROOM_ID = "DHS1JnKrzmaxGScdcNigkgBRpY4pNeLeoTaoPZhipump"
LIMIT = 20

async def main():
    sio = socketio.AsyncClient()
    last_timestamp = int(time.time() * 1000)

    @sio.event
    async def connect():
        logger.info("Connected to pump.fun socket.io server")
        # Join the room
        await sio.emit("joinRoom", {
            "roomId": ROOM_ID,
            "username": ""
        })
        # Request message history
        await sio.emit("getMessageHistory", {
            "roomId": ROOM_ID,
            "before": last_timestamp,
            "limit": LIMIT
        })

    @sio.on("messages")
    async def on_messages(data):
        # data is a list of message dicts
        for message in data:
            user = message.get("username")
            text = message.get("message")
            logger.info(f"{user}: {text}")
        await sio.disconnect()

    @sio.event
    async def disconnect():
        logger.info("Disconnected from pump.fun socket.io server")

    await sio.connect(
        "https://livechat.pump.fun",
        transports=["websocket"],
        headers={"origin": "https://pump.fun"}
    )
    await sio.wait()

if __name__ == "__main__":
    asyncio.run(main())
