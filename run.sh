#!/bin/bash
source venv/bin/activate
export PYTHONPATH=.
python3 -m chatbot_flask.app
