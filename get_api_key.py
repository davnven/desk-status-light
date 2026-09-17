import requests

BRIDGE_IP = "192.168.1.105"

response = requests.post(
    f"http://{BRIDGE_IP}/api",
    json={"devicetype": "statuslicht#hier-gerätename-einsetzen"} #Teil nach # ändern
)

print(response.json())