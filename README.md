
## Setup

### Server (Render)
1. Deploy the `server/` folder to Render
2. Build Command: `cd server && pip install -r requirements.txt`
3. Start Command: `cd server && gunicorn server:app`

### Client
1. Install dependencies: `pip install requests pillow pyautogui`
2. Run: `python client.py`
3. Update `SERVER_URL` in client.py to your Render URL

## Usage
1. **Host**: Enter name/password → "Start Sharing" → Share the code
2. **Client**: "View Available Servers" → Double-click to connect