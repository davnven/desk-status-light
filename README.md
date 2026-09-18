# Desk Status Light

A Philips Hue lamp that shows which computer is currently active on a shared USB switch (PC / private laptop / work laptop). Each machine runs a small Python script that detects when it becomes the active device (via USB keyboard/mouse connect events) and sets a dedicated color on a Hue light. A separate n8n workflow (running on a Raspberry Pi) receives periodic heartbeats and automatically turns the light off if no device has been active for a while.

## How it works

1. All computers share one keyboard/mouse through a USB switch.
2. Each computer runs `status_light.py`, which watches for USB input device connect events (via WMI on Windows).
3. When enough input devices are detected at once (a "burst"), the script assumes the switch was flipped to this machine and sets the Hue light to that machine's assigned color.
4. While active, the script sends a heartbeat (HTTP request) to an n8n webhook every N seconds.
5. n8n tracks the timestamp of the last heartbeat. If no heartbeat arrives for more than 5 minutes, n8n turns the light off automatically.

## Project structure

```
desk-status-light/
├── status_light.py
├── get_api_key.py
├── test_heartbeat.py
├── n8n/
│   └── desk-status-light-heartbeat.json
├── .env
├── .env.example
├── requirements.txt
├── .gitignore
├── LICENSE
└── README.md
```

## Requirements

- Python 3.10+
- A Philips Hue Bridge on the local network
- A Hue light (or Hue Go) dedicated to this purpose
- Windows (USB detection uses `wmi`/`pywin32`)
- (Optional, for auto-off) A Raspberry Pi running n8n via Docker

## Setup

### 1. Clone and create a virtual environment

```
git clone <repo-url>
cd desk-status-light
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Get a Hue API key (once per computer)

1. Press the physical link button on the Hue Bridge.
2. Within ~30 seconds, edit `get_api_key.py` and set a unique `devicetype` (ASCII only), e.g. `"statuslicht#pc"`.
3. Run it:

```
python get_api_key.py
```

4. On success you'll get:

```
[{'success': {'username': 'your-new-api-key'}}]
```

### 3. Find your light's ID

Using any working API key:

```
import requests

BRIDGE_IP = "192.168.1.105"
API_KEY = "your-api-key"

lights = requests.get(f"http://{BRIDGE_IP}/api/{API_KEY}/lights").json()
for light_id, info in lights.items():
    print(light_id, "-", info["name"])
```

### 4. Configure `.env`

Copy `.env.example` to `.env` and fill in real values:

Get each hostname by running `hostname` in PowerShell on that machine. Each machine needs the full `.env` (all devices, not just its own) — the script matches its own hostname automatically. Adding a device later: just append it to `DEVICES` and add its three lines, no code changes needed.

### 5. Run it

```
python status_light.py
```

## Running in the background (Windows)

### Option A — Task Scheduler (needs admin rights)

1. Open Task Scheduler → Create Task
2. General: name it, "Run only when user is logged on"
3. Triggers → New → "At log on"
4. Actions → New → Start a program:
   - Program: `...\desk-status-light\venv\Scripts\pythonw.exe`
   - Arguments: `status_light.py`
   - Start in: `...\desk-status-light`
5. Conditions: uncheck "Start only if on AC power" (for laptops)

### Option B — Startup folder (no admin rights needed)

1. `Win + R` → `shell:startup` → Enter
2. Create `start_status_light.bat`:

```
@echo off
cd /d "C:\path\to\desk-status-light"
"venv\Scripts\pythonw.exe" status_light.py
```

`pythonw.exe` runs without a visible console window.

## Auto-off via n8n (Raspberry Pi)

### Raspberry Pi setup

1. Flash Raspberry Pi OS (Lite) with Raspberry Pi Imager, enabling SSH and Wi-Fi in advanced options.
2. `ssh <user>@<pi-hostname>.local`
3. `sudo apt update && sudo apt full-upgrade -y`
4. Install Docker:

```
curl -fsSL https://get.docker.com | sh
sudo usermod -aG docker $USER
```

5. Run n8n:

```
docker run -d --name n8n \
  -p 5678:5678 \
  -v n8n_data:/home/node/.n8n \
  --restart unless-stopped \
  docker.n8n.io/n8nio/n8n
```

6. Open `http://<pi-ip>:5678` and set up the admin account.

### Import the workflow

1. n8n → ⋯ menu → Import from File → select the workflow JSON.
2. Open "Turn Light Off" node → replace `HUE_BRIDGE_IP`, `HUE_API_KEY`, `HUE_LIGHT_ID` with real values.
3. Activate the workflow.
4. Click "Heartbeat In" → copy the **Production URL** (not the Test URL).
5. Set it as `N8N_WEBHOOK_URL` in `.env` on every computer, then restart `status_light.py`.

### Testing the webhook independently

```
python test_heartbeat.py
```

Check n8n's Executions tab to confirm heartbeats arrive.

## Configuration reference (`.env`)

| Variable | Description |
|---|---|
| `HUE_BRIDGE_IP` | Local IP of the Hue Bridge |
| `HUE_LIGHT_ID` | ID of the light to control |
| `LIGHT_BRIGHTNESS` | Brightness, 1–254 (127 ≈ 50%) |
| `DEVICES` | Comma-separated list of device keys |
| `HOSTNAME_<KEY>` | Windows hostname of that device |
| `HUE_API_KEY_<KEY>` | Hue API key for that device |
| `DEVICE_COLOR_<KEY>` | Color name for that device |
| `MIN_DEVICE_COUNT` | Minimum devices in a burst to count as a real switch event |
| `SETTLE_SECONDS` | Wait time before evaluating a burst |
| `PI_IP` | IP of the Raspberry Pi |
| `N8N_WEBHOOK_URL` | Production webhook URL from n8n |
| `HEARTBEAT_INTERVAL` | Seconds between heartbeat pings |

## Troubleshooting

- **ModuleNotFoundError** — check `sys.executable` to confirm which Python is running; install the package into that same interpreter.
- **invalid value ... devicetype** — `devicetype` must be plain ASCII, no umlauts.
- **Heartbeats not arriving** — use the Production URL, not the Test URL, and make sure the workflow is Active.
- **Light doesn't turn off** — confirm n8n is still running and the "Turn Light Off" node has real values, not placeholders.

## Future ideas

- Battery level monitoring for Hue Go via Hue CLIP v2 `device_power`