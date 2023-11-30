import ludoc

try:
    model = ludoc.LudoModel(ludoc.GameConfig([["red"],[ "yellow"], ["green"], ["blue"]]))
    # print(model.config)
    state = ludoc.State()
except Exception as e:
    print(e)