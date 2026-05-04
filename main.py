import asyncio
import json
import os
import time
import requests
import websockets

TOKEN = os.getenv("TOKEN")
STATUS = os.getenv("STATUS", "online")
CUSTOM_STATUS = ""
RPC_JSON_PATH = "rpc.json"
GATEWAY_URI = "wss://gateway.discord.gg/?v=10&encoding=json"
DISCORD_API_URL = "https://discord.com/api/v10/users/@me"
OS_PROPERTY = "windows"
BROWSER_PROPERTY = "chrome"
DEVICE_PROPERTY = "pc"
RPC_POLL_INTERVAL = 30
RECONNECT_DELAY = 5
RPC_ACTIVITY_TYPE = 0
RPC_ACTIVITY_NAME = "Visual Studio Code"
CUSTOM_STATUS_ACTIVITY_NAME = "Custom Status"
CUSTOM_STATUS_ACTIVITY_TYPE = 4
CUSTOM_STATUS_ACTIVITY_ID = "custom"

if not TOKEN:
    print("ERROR: token is missing")
    exit()

r = requests.get(DISCORD_API_URL, headers={"Authorization": TOKEN})
if r.status_code != 200:
    print("ERROR: token not valid")
    exit()

user = r.json()
print(f"Logged in as {user['username']} ({user['id']})")

custom_status_activity = {
    "name": CUSTOM_STATUS_ACTIVITY_NAME,
    "type": CUSTOM_STATUS_ACTIVITY_TYPE,
    "state": CUSTOM_STATUS,
    "id": CUSTOM_STATUS_ACTIVITY_ID
}

def load_rpc_activity(start_time: int) -> dict | None:
    if not os.path.exists(RPC_JSON_PATH):
        return None

    with open(RPC_JSON_PATH, "r") as f:
        cfg = json.load(f)

    activity = {
        "type": RPC_ACTIVITY_TYPE,
        "name": RPC_ACTIVITY_NAME,
        "application_id": cfg["application_id"],
        "details": cfg["primary_text"],
    }

    if cfg.get("secondary_text"):
        activity["state"] = cfg["secondary_text"]

    if cfg.get("start_timestamp", False):
        activity["timestamps"] = {"start": start_time}

    assets = {}
    if cfg.get("large_image"):
        assets["large_image"] = cfg["large_image"]
    if cfg.get("large_text"):
        assets["large_text"] = cfg["large_text"]
    if cfg.get("small_image"):
        assets["small_image"] = cfg["small_image"]
    if cfg.get("small_text"):
        assets["small_text"] = cfg["small_text"]
    if assets:
        activity["assets"] = assets

    return activity

async def discord_gateway():
    start_time = int(time.time())

    async with websockets.connect(GATEWAY_URI) as ws:
        hello = json.loads(await ws.recv())
        heartbeat_interval = hello["d"]["heartbeat_interval"]

        async def heartbeat():
            while True:
                await asyncio.sleep(heartbeat_interval / 1000)
                await ws.send(json.dumps({"op": 1, "d": None}))

        asyncio.create_task(heartbeat())

        activities = [custom_status_activity]
        rpc = load_rpc_activity(start_time)
        if rpc:
            activities.append(rpc)

        identify = {
            "op": 2,
            "d": {
                "token": TOKEN,
                "properties": {
                    "$os": OS_PROPERTY,
                    "$browser": BROWSER_PROPERTY,
                    "$device": DEVICE_PROPERTY
                },
                "presence": {
                    "status": STATUS,
                    "afk": False,
                    "activities": activities
                }
            }
        }
        await ws.send(json.dumps(identify))
        print(f"Presence set — status: {STATUS}, activities: {len(activities)}")

        last_rpc = rpc

        async def rpc_watcher():
            nonlocal last_rpc
            while True:
                await asyncio.sleep(RPC_POLL_INTERVAL)
                current_rpc = load_rpc_activity(start_time)
                if current_rpc != last_rpc:
                    last_rpc = current_rpc
                    updated_activities = [custom_status_activity]
                    if current_rpc:
                        updated_activities.append(current_rpc)
                    presence_update = {
                        "op": 3,
                        "d": {
                            "status": STATUS,
                            "afk": False,
                            "activities": updated_activities,
                            "since": None
                        }
                    }
                    await ws.send(json.dumps(presence_update))
                    print("RPC updated via op:3")

        asyncio.create_task(rpc_watcher())

        while True:
            try:
                msg = await ws.recv()
                data = json.loads(msg)
                if data.get("op") == 11:
                    pass

            except Exception as e:
                print("Connection lost, reconnecting...", e)
                break

while True:
    asyncio.run(discord_gateway())
    time.sleep(RECONNECT_DELAY)
