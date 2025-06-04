from . import register
import pyautogui
import time

@register("text")
def run(params, ctx):
    """
    params esperados:
      content: string com o texto a digitar
    """
    texto = params.get("content", "")
    # move um breve delay entre caracteres, se quiser:
    pyautogui.write(texto)  
    time.sleep(0.05)
