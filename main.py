import asyncio
import json
import os
import time
import requests
import websockets

# ── Auth ─────────────────────────────────────────────────────────────────────
TOKEN = os.getenv("TOKEN")
STATUS = os.getenv("STATUS", "online")  # fallback to online if not set

if not TOKEN:
    print("No TOKEN env var set!")
    exit()

# ── Validate token ────────────────────────────────────────────────────────────
r = requests.get("https://discord.com/api/v10/users/@me", headers={"Authorization": TOKEN})
if r.status_code != 200:
    print("Invalid token!")
    exit()

user = r.json()
print(f"Logged in as {user['username']} ({user['id']})")

# ── Custom status (the "Hey!" bubble on your profile) ─────────────────────────
CUSTOM_STATUS = "Hey!"

custom_status_activity = {
    "name": "Custom Status",
    "type": 4,
    "state": CUSTOM_STATUS,
    "id": "custom"
}

# ── RPC config ────────────────────────────────────────────────────────────────
RPC_JSON_PATH = "rpc.json"

def load_rpc_activity(start_time: int) -> dict | None:
    """Read rpc.json and build the activity dict. Returns None if file missing."""
    if not os.path.exists(RPC_JSON_PATH):
        return None

    with open(RPC_JSON_PATH, "r") as f:
        cfg = json.load(f)

    activity = {
        "type": 0,  # "Playing"
        "name": "Visual Studio Code",
        "application_id": cfg["application_id"],
        "details": cfg["primary_text"],       # bold top line
    }

    if cfg.get("secondary_text"):
        activity["state"] = cfg["secondary_text"]

    # Timestamps — shows elapsed timer if enabled
    if cfg.get("start_timestamp", False):
        activity["timestamps"] = {"start": start_time}

    # Images
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

# ── Gateway ───────────────────────────────────────────────────────────────────
async def discord_gateway():
    uri = "wss://gateway.discord.gg/?v=10&encoding=json"
    start_time = int(time.time())

    async with websockets.connect(uri) as ws:
        hello = json.loads(await ws.recv())
        heartbeat_interval = hello["d"]["heartbeat_interval"]

        # Heartbeat loop
        async def heartbeat():
            while True:
                await asyncio.sleep(heartbeat_interval / 1000)
                await ws.send(json.dumps({"op": 1, "d": None}))

        asyncio.create_task(heartbeat())

        # Build initial activity list
        activities = [custom_status_activity]
        rpc = load_rpc_activity(start_time)
        if rpc:
            activities.append(rpc)

        # Identify
        identify = {
            "op": 2,
            "d": {
                "token": TOKEN,
                "properties": {
                    "$os": "windows",
                    "$browser": "chrome",
                    "$device": "pc"
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

        # RPC watcher — checks rpc.json every 30s, sends op:3 if changed
        last_rpc = rpc

        async def rpc_watcher():
            nonlocal last_rpc
            while True:
                await asyncio.sleep(30)
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

        # Main receive loop
        while True:
            try:
                msg = await ws.recv()
                data = json.loads(msg)
                if data.get("op") == 11:
                    pass  # heartbeat ACK, ignore
            except Exception as e:
                print("Connection lost, reconnecting...", e)
                break

# ── Run ───────────────────────────────────────────────────────────────────────
while True:
    asyncio.run(discord_gateway())
    time.sleep(5)
