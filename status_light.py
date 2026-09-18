import os
import socket
import threading
import time
import requests
import wmi
from dotenv import load_dotenv

load_dotenv()

BRIDGE_IP = os.getenv("HUE_BRIDGE_IP")
LIGHT_ID = os.getenv("HUE_LIGHT_ID")
BRIGHTNESS = int(os.getenv("LIGHT_BRIGHTNESS", 127))

MIN_DEVICE_COUNT = int(os.getenv("MIN_DEVICE_COUNT", 6))
SETTLE_SECONDS = float(os.getenv("SETTLE_SECONDS", 1.5))

N8N_WEBHOOK_URL = os.getenv("N8N_WEBHOOK_URL")
HEARTBEAT_INTERVAL = int(os.getenv("HEARTBEAT_INTERVAL", 20))

COLOR_MAP = {
    "green":  {"hue": 25500, "sat": 254},
    "purple": {"hue": 50000, "sat": 254},
    "blue":   {"hue": 46920, "sat": 254},
    "red":    {"hue": 0,     "sat": 254},
}


def build_device_map():
    device_map = {}
    for key in os.getenv("DEVICES", "").split(","):
        key = key.strip()
        if not key:
            continue
        hostname = os.getenv(f"HOSTNAME_{key}")
        if hostname:
            device_map[hostname] = {
                "name": key,
                "api_key": os.getenv(f"HUE_API_KEY_{key}"),
                "color": os.getenv(f"DEVICE_COLOR_{key}"),
            }
    return device_map


def set_light_color(api_key: str, color_name: str):
    color = COLOR_MAP.get(color_name)
    if not color:
        print(f"Unknown color: {color_name}")
        return

    url = f"http://{BRIDGE_IP}/api/{api_key}/lights/{LIGHT_ID}/state"
    payload = {"on": True, "hue": color["hue"], "sat": color["sat"], "bri": BRIGHTNESS}

    try:
        resp = requests.put(url, json=payload, timeout=5)
        resp.raise_for_status()
        print(f"Light set to '{color_name}'.")
    except requests.RequestException as e:
        print(f"Error setting the light: {e}")


def is_input_device(caption: str) -> bool:
    caption = caption.lower()
    return "keyboard" in caption or "mouse" in caption or "hid" in caption


def send_heartbeat(device_name: str, color: str):
    if not N8N_WEBHOOK_URL:
        return None  # n8n not set up yet
    while True:
        try:
            requests.post(
                N8N_WEBHOOK_URL,
                json={"device": device_name, "color": color},
                timeout=3,
            )
        except requests.RequestException:
            pass
        time.sleep(HEARTBEAT_INTERVAL)


def watch_usb_events(device):
    c = wmi.WMI()
    watcher = c.Win32_PnPEntity.watch_for(notification_type="Creation")

    print(f"Waiting for USB connect events for device '{device['name']}' ...")

    lock = threading.Lock()
    state = {"count": 0, "timer": None}

    def evaluate_burst():
        with lock:
            count = state["count"]
            state["count"] = 0
            state["timer"] = None

        print(f"{count} input devices detected in this burst.")
        if count >= MIN_DEVICE_COUNT:
            print("Looks like your switch setup -> setting color.")
            set_light_color(device["api_key"], device["color"])
        else:
            print("Too few devices, probably not your switch -> ignored.")

    while True:
        try:
            new_device = watcher()
            if is_input_device(new_device.Caption or ""):
                with lock:
                    state["count"] += 1
                    if state["timer"]:
                        state["timer"].cancel()
                    state["timer"] = threading.Timer(SETTLE_SECONDS, evaluate_burst)
                    state["timer"].daemon = True
                    state["timer"].start()
        except wmi.x_wmi_timed_out:
            continue


def main():
    hostname = socket.gethostname()
    device_map = build_device_map()
    device = device_map.get(hostname)

    if device is None:
        print(f"Hostname '{hostname}' is not known in .env. Aborting.")
        return

    print(f"Device detected: {device['name']} (Hostname: {hostname})")

    set_light_color(device["api_key"], device["color"])

    threading.Thread(
        target=send_heartbeat,
        args=(device["name"], device["color"]),
        daemon=True,
    ).start()

    watch_usb_events(device)


if __name__ == "__main__":
    main()