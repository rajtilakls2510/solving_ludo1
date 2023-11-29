import ludoc

all_blocks = ludoc.AllBlocks()
try:
    model = ludoc.LudoModel(ludoc.GameConfig([["red"],[ "yellow"], ["green"], ["blue"]]))
except Exception as e:
    print(e)