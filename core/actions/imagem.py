from pathlib import Path
from . import register
from utils.image_ops import match_template


@register("imagem")
def run(params, ctx):
    """
    Detecta template numa região da tela.

    Chaves aceitas (qualquer uma):
      • template_path  • template  • imagem  • img  • arquivo
    Região:
      • search_box = {x,y,w,h}
      • ou x,y,w,h soltos
    """

    # -------- 1. normalizar caminho do template -------------------
    aliases = ("template_path", "template", "imagem", "img", "arquivo")
    for key in aliases:
        if key in params:
            params["template_path"] = params[key]
            break
    else:
        raise KeyError("Bloco 'imagem' precisa de template_path / imagem / img")

    # -------- 2. normalizar search_box ----------------------------
    if "search_box" not in params:
        if all(k in params for k in ("x", "y", "w", "h")):
            params["search_box"] = {k: int(params[k]) for k in ("x", "y", "w", "h")}
        else:
            raise KeyError("Faltam coordenadas x,y,w,h ou search_box completo")

    # -------- 3. alias legacy threshold ---------------------------
    if "threshold" not in params and "th" in params:
        params["threshold"] = params["th"]

    # -------- 4. resolver caminho relativo ------------------------
    tpl_path = Path(params["template_path"])
    macro_dir = Path(ctx["json_path"]).parent

    if not tpl_path.is_absolute():
        tpl_path = (macro_dir / tpl_path).resolve()

    # 4a) se ainda não existe, tenta <macro>/img/<nome>
    if not tpl_path.exists():
        alt_path = (macro_dir / "img" / tpl_path.name).resolve()
        if alt_path.exists():
            tpl_path = alt_path
        else:
            # 4b) varre todas as subpastas de Macros/ atrás do arquivo
            macros_root = macro_dir.parent / "Macros"
            for p in (macros_root.rglob(tpl_path.name)
                      if macros_root.exists() else []):
                tpl_path = p.resolve()
                break

    if not tpl_path.exists():
        raise FileNotFoundError(
            f"Template não encontrado após varrer Macros/: {tpl_path}"
        )

    params["template_path"] = str(tpl_path)

    # -------- 5. executar detecção --------------------------------
    found = match_template(params)

    # -------- direciona fluxo (true/false) ------------------------
    cur   = ctx["current_id"]
    nmap  = ctx["next_map"]
    dests = nmap[cur]["true"] if found else nmap[cur]["false"]
    if dests:
        ctx["set_current"](dests[0])    # salta para o bloco destino
    # caso não exista saída específica, o executor seguirá pelo 'default'
