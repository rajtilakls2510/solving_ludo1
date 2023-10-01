import rpyc
from ludo import GameConfig, Ludo, LudoModel
conn = rpyc.connect("localhost", 18861)


print(conn.root.get_nnet_list())
print(conn.root.get_nnet("model3"))