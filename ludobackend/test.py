import rpyc
from ludo import GameConfig, Ludo, LudoModel
conn = rpyc.connect("localhost", 18861)


print(conn.root.get_log_filenames(10))
print(conn.root.get_log_file(["run1", "logs", "2023_Oct_02_17_10_17_863343.json"]))

conn.close()