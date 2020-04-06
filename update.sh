#!/usr/bin/env bash
git pull --recurse-submodules
poetry install
source .env
poetry run python update_game_data.py
./run.sh
