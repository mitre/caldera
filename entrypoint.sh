#!/bin/bash
# Start Xvfb on display 99
Xvfb :99 -screen 0 1024x768x16 &

# Export DISPLAY variable
export DISPLAY=:99

touch /root/.Xauthority

exec python3 server.py --build
