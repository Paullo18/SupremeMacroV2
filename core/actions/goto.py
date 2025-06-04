from . import register

@register("goto")
def run(params, ctx):
    label = params["label"]
    # procura o bloco cujo custom_name ou name corresponda ao label
    for bid, blk in ctx["blocks"].items():
        name = blk.get("params", {}).get("custom_name") or blk.get("params", {}).get("name")
        if name == label:
            ctx["set_current"](bid)
            return
    # se não encontrar, opcional: logar aviso
    print(f"[WARN] goto: label '{label}' não encontrada.")
