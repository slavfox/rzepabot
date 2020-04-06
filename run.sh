#!/usr/bin/env bash
screen -dmS rzepabot bash -c 'source .env; poetry run python -m rzepabot; exec bash'
