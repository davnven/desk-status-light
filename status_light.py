import os
import socket
import requests
import wmi
import time
from dotenv import load_dotenv

load_dotenv()

BRIDGE_IP = os.getenv("HUE_BRIDGE_IP")
LIGHT_ID = os.getenv("HUE_LIGHT_ID")

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
        print(f"Unbekannte Farbe: {color_name}")
        return

    url = f"http://{BRIDGE_IP}/api/{api_key}/lights/{LIGHT_ID}/state"
    payload = {"on": True, "hue": color["hue"], "sat": color["sat"], "bri": 127}

    try:
        resp = requests.put(url, json=payload, timeout=5)
        resp.raise_for_status()
        print(f"Lampe auf '{color_name}' gesetzt.")
    except requests.RequestException as e:
        print(f"Fehler beim Setzen der Lampe: {e}")


def is_input_device(caption: str) -> bool:
    caption = caption.lower()
    return "keyboard" in caption or "mouse" in caption or "hid" in caption


def watch_usb_events(device):
    c = wmi.WMI()
    watcher = c.Win32_PnPEntity.watch_for(notification_type="Creation")

    print(f"Warte auf USB-Connect-Events für Gerät '{device['name']}' ...")
    last_trigger = 0
    debounce_seconds = 3

    while True:
        try:
            new_device = watcher()
            if is_input_device(new_device.Caption or ""):
                now = time.time()
                if now - last_trigger > debounce_seconds:
                    print(f"Eingabegerät erkannt: {new_device.Caption}")
                    set_light_color(device["api_key"], device["color"])
                    last_trigger = now
        except wmi.x_wmi_timed_out:
            continue


def main():
    hostname = socket.gethostname()
    device_map = build_device_map()
    device = device_map.get(hostname)

    if device is None:
        print(f"Hostname '{hostname}' ist in der .env nicht bekannt. Abbruch.")
        return

    print(f"Gerät erkannt: {device['name']} (Hostname: {hostname})")
    set_light_color(device["api_key"], device["color"])
    watch_usb_events(device)


if __name__ == "__main__":
    main()