import os
from pathlib import Path
import datetime
DIRECTORY = Path("runs")
TRAIN_DIRECTORY = DIRECTORY / "run1" / "experience_store"

for i in range(256):
    file = os.listdir(TRAIN_DIRECTORY)[0]
    with open(TRAIN_DIRECTORY / (datetime.datetime.now().strftime("%Y_%b_%d_%H_%M_%S_%f")+".json"), "w", encoding="utf-8") as g:
        with open(TRAIN_DIRECTORY / file, "r", encoding="utf-8") as f:
            g.write(f.read())