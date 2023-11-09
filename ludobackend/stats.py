from pathlib import Path
import os
import json
import pandas as pd


""" This file is used to calculate the statistics (Wins and Losses ) for a player """
log_path = Path("runs") / "run1" / "logs_to_elo"
AGENT_NAMES = os.listdir(log_path)
# AGENT_NAMES = ["2023_Nov_01_03_09_10_819920"]  # The Checkpoint name of the agent
info = {"agent": [], "wins": [], "losses": []}
for AGENT_NAME in AGENT_NAMES:
    agent_log_path = log_path / AGENT_NAME

    wins = 0
    losses = 0
    for file in os.listdir(agent_log_path):
        with open(agent_log_path / file, mode='r', encoding="utf-8") as f:
            if json.loads(f.read())["player_won"] == 1:
                wins += 1
            else:
                losses += 1
    info["agent"].append(AGENT_NAME)
    info["wins"].append(wins)
    info["losses"].append(losses)
    print(f"AGENT: {AGENT_NAME} \t W: {wins} \t L: {losses}")
    pd.DataFrame(info).to_csv("results.csv", index=False)

