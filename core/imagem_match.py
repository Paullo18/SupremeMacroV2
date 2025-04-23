import cv2
import numpy as np
import pyautogui

def encontrar_imagem(template_path, threshold=0.8):
    # Captura a tela
    screenshot = pyautogui.screenshot()
    tela = cv2.cvtColor(np.array(screenshot), cv2.COLOR_RGB2BGR)

    # Carrega o template
    template = cv2.imread(template_path, cv2.IMREAD_COLOR)
    if template is None:
        print("Erro ao carregar template.")
        return False

    res = cv2.matchTemplate(tela, template, cv2.TM_CCOEFF_NORMED)
    loc = np.where(res >= threshold)

    return len(list(zip(*loc[::-1]))) > 0  # Se encontrou, retorna True
