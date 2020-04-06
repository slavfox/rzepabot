#!/usr/bin/env bash
pyenv shell 3.8.2
poetry run python update_game_data.py
screen -dmS rzepabot bash -c 'pyenv shell 3.8.2; source .env; poetry run python -m rzepabot'
