import pyautogui
import time
import pytesseract
from PIL import ImageGrab, Image
import threading
import keyboard
import os
import json
from core.storage import obter_caminho_macro_atual
import traceback  # no início do arquivo

pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"

macro_parar = False
macro_pausar = False

def executar_macro(actions, progress_callback=None, label_callback=None):
    global macro_parar, macro_pausar
    macro_parar = False
    macro_pausar = False

    print("[DEBUG] Conteúdo atual das actions:")
    print(json.dumps(actions, indent=2))

    def monitorar_teclas():
        global macro_parar, macro_pausar
        while True:
            if keyboard.is_pressed("ctrl+q"):
                macro_parar = True
                break
            if keyboard.is_pressed("ctrl+p"):
                macro_pausar = not macro_pausar
                time.sleep(0.5)
            time.sleep(0.05)

    threading.Thread(target=monitorar_teclas, daemon=True).start()

    i = 0
    loop_stack = []

    while i < len(actions):
        if macro_parar:
            print("Macro interrompida.")
            break
        while macro_pausar:
            time.sleep(0.1)

        if progress_callback:
            progress_callback(i + 1, len(actions))
        if label_callback:
            label_callback(f"Executando: {actions[i]['type'].upper()}")

        action = actions[i]

        if action['type'] == 'click':
            pyautogui.click(action['x'], action['y'])

        elif action['type'] == 'type':
            pyautogui.write(action['text'])

        elif action['type'] == 'delay':
            time.sleep(action['time'] / 1000)

        elif action['type'] == 'ocr':
            bbox = (action['x'], action['y'], action['x'] + action['w'], action['y'] + action['h'])
            img = ImageGrab.grab(bbox=bbox)
            texto_detectado = pytesseract.image_to_string(img).strip().lower()
            texto_esperado = action['text'].strip().lower()
            verificar_vazio = action.get('verificar_vazio', False)

            if (verificar_vazio and not texto_detectado) or (not verificar_vazio and texto_esperado and texto_esperado in texto_detectado):
                i += 1
                continue
            else:
                profundidade = 1
                i += 1
                while i < len(actions):
                    tipo = actions[i]['type']
                    if tipo in ('ocr', 'ocr_duplo', 'imagem'):
                        profundidade += 1
                    elif tipo == 'endif':
                        profundidade -= 1
                        if profundidade == 0:
                            break
                    elif tipo == 'else' and profundidade == 1:
                        i += 1
                        break
                    i += 1
                continue

        elif action['type'] == 'ocr_duplo':
            bbox1 = (action['x1'], action['y1'], action['x1'] + action['w1'], action['y1'] + action['h1'])
            bbox2 = (action['x2'], action['y2'], action['x2'] + action['w2'], action['y2'] + action['h2'])
            texto1 = action['text1'].strip().lower()
            texto2 = action['text2'].strip().lower()
            vazio1 = action.get("vazio1", False)
            vazio2 = action.get("vazio2", False)

            img1 = ImageGrab.grab(bbox=bbox1)
            img2 = ImageGrab.grab(bbox=bbox2)
            detectado1_raw = pytesseract.image_to_string(img1).strip().lower()
            detectado2_raw = pytesseract.image_to_string(img2).strip().lower()

            detectado1 = (not detectado1_raw) if vazio1 else (texto1 and texto1 in detectado1_raw)
            detectado2 = (not detectado2_raw) if vazio2 else (texto2 and texto2 in detectado2_raw)

            condicao = action.get("condicao", "and").lower()
            condicao_satisfeita = (detectado1 and detectado2) if condicao == "and" else (detectado1 or detectado2)

            if condicao_satisfeita:
                i += 1
                continue
            else:
                profundidade = 1
                i += 1
                while i < len(actions):
                    tipo = actions[i]['type']
                    if tipo in ('ocr', 'ocr_duplo', 'imagem'):
                        profundidade += 1
                    elif tipo == 'endif':
                        profundidade -= 1
                        if profundidade == 0:
                            break
                    elif tipo == 'else' and profundidade == 1:
                        i += 1
                        break
                    i += 1
                continue

        elif action['type'] == 'imagem':
            area = (action['x'], action['y'], action['x'] + action['w'], action['y'] + action['h'])
            imagem_relativa = action.get("imagem", "").replace("\\", "/")
            nome_imagem = os.path.basename(imagem_relativa)

            caminho_tmp = os.path.join("tmp", nome_imagem)

            caminho_macro_json = obter_caminho_macro_atual()
            macro_dir = caminho_macro_json if caminho_macro_json else ""
            macro_img_path = os.path.join(macro_dir, "img", nome_imagem) if macro_dir else None

            print("[DEBUG] Buscando imagem:")
            print(" - Relativo:", imagem_relativa)
            print(" - TMP:", caminho_tmp)
            print(" - Macro (absoluto):", macro_img_path)

            if os.path.exists(caminho_tmp):
                caminho_final = caminho_tmp
            elif macro_img_path and os.path.exists(macro_img_path):
                caminho_final = macro_img_path
            else:
                print(f"[ERRO] Imagem '{imagem_relativa}' não encontrada em tmp ou na macro salva.")
                caminho_final = None
            encontrado = None
            try:
                img_area = ImageGrab.grab(bbox=area)
                if caminho_final:
                    with Image.open(caminho_final) as img_ref:
                        try:
                            encontrado = pyautogui.locate(img_ref, img_area, confidence=0.8)
                        except pyautogui.ImageNotFoundException:
                            print("[INFO] Imagem não localizada com a confiança exigida.")
            except Exception as e:
                print(f"[ERRO] Falha ao processar imagem: {e}")
                traceback.print_exc()


            if encontrado:
                i += 1
                continue
            else:
                profundidade = 1
                i += 1
                while i < len(actions):
                    tipo = actions[i]['type']
                    if tipo in ('ocr', 'ocr_duplo', 'imagem'):
                        profundidade += 1
                    elif tipo == 'endif':
                        profundidade -= 1
                        if profundidade == 0:
                            break
                    elif tipo == 'else' and profundidade == 1:
                        i += 1
                        break
                    i += 1

                continue

        elif action['type'] == 'else':
            profundidade = 1
            i += 1
            while i < len(actions) and profundidade > 0:
                tipo = actions[i]['type']
                if tipo in ('ocr', 'ocr_duplo', 'imagem'):
                    profundidade += 1
                elif tipo == 'endif':
                    profundidade -= 1
                i += 1
            continue

        elif action['type'] == 'endif':
            pass

        elif action['type'] == 'loopstart':
            if not loop_stack or loop_stack[-1]["index"] != i:
                loop_stack.append({
                    "index": i,
                    "mode": action.get("mode", "quantidade"),
                    "count": action.get("count", 0),
                    "remaining": action.get("count", 0)
                })

        elif action['type'] == 'loopend':
            if loop_stack:
                loop = loop_stack[-1]
                if loop["mode"] == "infinito":
                    i = loop["index"]
                    continue
                elif loop["mode"] == "quantidade":
                    loop["remaining"] -= 1
                    if loop["remaining"] > 0:
                        i = loop["index"]
                        continue
                    else:
                        loop_stack.pop()

        elif action['type'] == 'loopcancel':
            if loop_stack:
                loop_stack.pop()

        elif action['type'] == 'goto':
            destino = action.get("label", "")
            achou = False
            for j, acao in enumerate(actions):
                if acao.get('type') == 'label' and acao.get('name') == destino:
                    i = j
                    achou = True
                    break
            if not achou:
                print(f"[GOTO] Label '{destino}' não encontrada.")
                break
            continue

        i += 1
