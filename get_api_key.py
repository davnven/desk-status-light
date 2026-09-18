import requests

BRIDGE_IP = "192.168.1.105"

response = requests.post(
    f"http://{BRIDGE_IP}/api",
    json={"devicetype": "statuslicht#"} #Insert Devicetype after #
)

print(response.json())