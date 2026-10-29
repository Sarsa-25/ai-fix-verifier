def calc(expr):
    result = {}
    exec(f"value = {expr}", {}, result)
    return result["value"]
