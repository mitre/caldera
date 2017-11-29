"""
Caldera

Usage:
    caldera.py
    caldera.py -d | --debug
    caldera.py -h | --help


Options:
    -h --help           Show this screen
    -d --debug          Enable debug mode
"""
import sys
import logging
from app import server

if __name__ == '__main__':
    logging.basicConfig(level=logging.DEBUG)
    if '--help' in sys.argv or '-h' in sys.argv:
        print(__doc__)
        exit()
    debug = '--debug' in sys.argv or '-d' in sys.argv
    server.run(debug=debug)
