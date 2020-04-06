#!/usr/bin/env bash
git pull --recurse-submodules
source .env
poetry install
poetry run python update_game_data.py
screen -dmS rzepabot bash -c 'RZEPABOT_TOKEN=$RZEPABOT_TOKEN poetry run python -m rzepabot'
