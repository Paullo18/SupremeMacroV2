# core/actions/variavel.py
from . import register
import time
import pyautogui
import tkinter  # para clipboard

@register("variavel")
def run_variavel(params, ctx):
    """
    Handler de execução para o bloco 'variavel'.
    Recebe em params:
      - var_name : nome da variável (string)
      - mode     : "manual" ou "ocr_region"
      - var_value: valor (string)
      - region   : (se mode=="ocr_region") dict {x,y,w,h}
    Armazena em ctx["vars"][var_name] = var_value para uso futuro.
    """
    nome = params.get("var_name", "").strip()
    mode = params.get("mode", "manual")

    # Inicializa o dicionário de variáveis, se ainda não existir
    if "vars" not in ctx:
        ctx["vars"] = {}
    if mode == "manual":
        # Modo manual: apenas grava o valor diretamente
        valor = params.get("var_value", "")
        ctx["vars"][nome] = valor
        thread_name = ctx.get("thread_name")
        if ctx.get("label_callback"):
            ctx["label_callback"](thread_name, f"Variável '{nome}' = '{valor}'")
    else:
        # Modo selecionar texto na tela: simular seleção e copiar para o clipboard
        reg = params.get("region", {})
        x = reg.get("x", 0)
        y = reg.get("y", 0)
        w = reg.get("w", 0)
        h = reg.get("h", 0)

        # 1) Move o cursor ao canto superior‐esquerdo da região
        pyautogui.moveTo(x, y)
        time.sleep(0.1)
        # 2) Pressiona e arrasta até (x+w, y+h)
        pyautogui.mouseDown(x, y, button='left')
        pyautogui.moveTo(x + w, y + h, duration=0.2)
        pyautogui.mouseUp(x + w, y + h, button='left')
        time.sleep(0.1)
        # 3) Pressiona Ctrl+C para copiar
        pyautogui.hotkey('ctrl', 'c')
        time.sleep(0.2)  # aguarda o clipboard atualizar

        # 4) Lê o texto do clipboard
        try:
            clip = tkinter.Tk()
            clip.withdraw()
            valor_copiado = clip.clipboard_get()
            clip.destroy()
        except:
            valor_copiado = ""
        ctx["vars"][nome] = valor_copiado
        thread_name = ctx.get("thread_name")
        if ctx.get("label_callback"):
            ctx["label_callback"](thread_name, f"Variável '{nome}' ← selecionado: '{valor_copiado[:20]}…'")

    # Continua para o próximo bloco
    ctx["set_current"](ctx["next_block_id"])
