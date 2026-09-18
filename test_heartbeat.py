import os
import time
import requests
from dotenv import load_dotenv

load_dotenv()

N8N_WEBHOOK_URL = os.getenv("N8N_WEBHOOK_URL")
DEVICE_NAME = "TEST"
COLOR = "green"
INTERVAL = 5  # seconds, faster than the real 20s interval for testing

if not N8N_WEBHOOK_URL:
    print("N8N_WEBHOOK_URL is missing in .env")
    exit(1)

print(f"Sending heartbeats to: {N8N_WEBHOOK_URL}")
print("Press Ctrl+C to stop")

try:
    while True:
        try:
            resp = requests.post(
                N8N_WEBHOOK_URL,
                json={"device": DEVICE_NAME, "color": COLOR},
                timeout=3,
            )
            print(f"Sent - Status: {resp.status_code} - Response: {resp.text}")
        except requests.RequestException as e:
            print(f"Error: {e}")

        time.sleep(INTERVAL)
except