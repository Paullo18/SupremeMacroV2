from . import register
from utils.image_ops import grab_and_ocr


@register("ocr_duplo")
def run(params, ctx):
    """
    Aceita dois formatos:

      • Formato novo:
          {
             "area1": {x,y,w,h,"pattern": "..."},
             "area2": {x,y,w,h,"pattern": "..."},
             "logic": "and"/"or"
          }

      • Formato legado (como no seu JSON):
          {
             x1,y1,w1,h1,text1,
             x2,y2,w2,h2,text2,
             "condicao": "and"/"or",
             "vazio1": bool   # se true, condição é texto **vazio**
          }
    """

    # ---------- normalizar áreas ---------------------------------
    if "area1" in params and "area2" in params:             # formato novo
        a = params["area1"].copy()
        b = params["area2"].copy()
        logic = params.get("logic", params.get("condicao", "and")).lower()
    else:                                                   # formato legado
        a = {
            "x": params["x1"], "y": params["y1"],
            "w": params["w1"], "h": params["h1"],
            "pattern": params.get("text1", ""),
            "vazio": params.get("vazio1", False)
        }
        b = {
            "x": params["x2"], "y": params["y2"],
            "w": params["w2"], "h": params["h2"],
            "pattern": params.get("text2", ""),
            "vazio": params.get("vazio2", False)
        }
        logic = params.get("condicao", "and").lower()

    # ---------- OCR nas duas áreas -------------------------------
    txt1 = grab_and_ocr(a).lower()
    txt2 = grab_and_ocr(b).lower()

    ok1 = (txt1 == "") if a.get("vazio") else (a["pattern"].lower() in txt1)
    ok2 = (txt2 == "") if b.get("vazio") else (b["pattern"].lower() in txt2)

    cond = (ok1 and ok2) if logic == "and" else (ok1 or ok2)

    # ---------- direciona fluxo ----------------------------------
    cur  = ctx["current_id"]
    dest = ctx["next_map"][cur]["true"] if cond else ctx["next_map"][cur]["false"]
    if dest:
        ctx["set_current"](dest[0])