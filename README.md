# Global Remote Desktop

A remote desktop application with global connectivity via session codes.

## Setup

### Server (Render)
1. Deploy `server.py` to Render.com
2. Update `SIGNALING_SERVER` in client.py with your Render URL

### Client
```bash
pip install opencv-python pyautogui pillow numpy requests
python client.py