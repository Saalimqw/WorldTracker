#!/bin/bash
# Start the OSINT background simulation engine
python simulator.py &
# Start the USGS earthquake scraper
python scraper.py &
# Start the Flask API on the port provided by the host
gunicorn server:app -b 0.0.0.0:$PORT
