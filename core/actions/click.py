from . import register
import pyautogui, random, time, unicodedata
from pyautogui import ImageNotFoundException

@register("click")
def run(params, ctx):
    """
    params esperados:
        mode : "fixo" | "aleatorio"
        x, y, w, h : ints
        btn : "left" | "right" | "middle"
    """
    # remove acentos e converte para minúsculas
    raw_mode = params.get("mode", "fixo")
    mode = unicodedata.normalize("NFD", raw_mode).encode("ascii", "ignore").decode().lower()
    btn  = params.get("btn", "left")
    if mode == "aleatorio":
        x = random.randint(params["x"], params["x"] + params["w"] - 1)
        y = random.randint(params["y"], params["y"] + params["h"] - 1)
    elif mode == "imagem":
        # localiza template dentro da região definida
        template = params.get("template_path")
        region   = (params["x"], params["y"], params["w"], params["h"])
        try:
            loc = pyautogui.locateOnScreen(template, region=region, confidence=0.8)
        except ImageNotFoundException:
            # não encontrou a imagem → aborta silenciosamente
            return
        # se locateOnScreen retornar None, também aborta
        if not loc:
            return
        # calcula o centro da área encontrada
        x = loc.left + loc.width // 2
        y = loc.top  + loc.height // 2
    else:
        x, y = params["x"], params["y"]
    # move o mouse para as coordenadas desejadas
    pyautogui.moveTo(x, y)
    # aguarda 50 ms para garantir que o movimento foi concluído
    time.sleep(0.05)
    # então dispara o clique
    pyautogui.click(x, y, button=btn)
