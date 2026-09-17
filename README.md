# desk-status-light

Status light via Philips Hue: shows which computer is active on a USB switch (PC / private laptop / work laptop).

## Setup

1. python -m venv venv
2. venv\Scripts\activate
3. pip install -r requirements.txt
4. cp .env.example .env and fill in your values
5. python get_api_key.py (once per device, after pressing the Hue Bridge link button)
6. python status_light.py