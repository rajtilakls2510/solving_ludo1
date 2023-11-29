import ludoc

try:
    model = ludoc.LudoModel(ludoc.GameConfig([["red"],[ "yellow"], ["green"], ["blue"]]))
    print(model.config)
except Exception as e:
    print(e)