import json
import time
import threading
import traceback
import os
import cv2
import numpy as np
import keyboard
import pyautogui
import pytesseract
from PIL import ImageGrab, Image
import io
import win32clipboard
import requests
from datetime import datetime
from utils.telegram_util import send_photo

_grab_lock      = threading.Lock()  # para ImageGrab / screenshot
_tess_lock      = threading.Lock()  # para pytesseract
_clipboard_lock = threading.Lock()  # para win32clipboard
_io_lock        = threading.Lock()  # para salvar em disco

# Caminho do Tesseract (ajuste se necessário)
pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"

# -------------- flags globais de controle ------------------
macro_parar: bool = False
macro_pausar: bool = False


# -----------------------------------------------------------
# Helper: monitorar Ctrl+Q (parar) e Ctrl+P (pausar)
# -----------------------------------------------------------

def _monitorar_teclas():
    global macro_parar, macro_pausar
    while True:
        if keyboard.is_pressed("ctrl+q"):
            macro_parar = True
            break
        if keyboard.is_pressed("ctrl+p"):
            macro_pausar = not macro_pausar
            time.sleep(0.5)  # debounce
        time.sleep(0.05)


# -----------------------------------------------------------
# Carrega o fluxo da macro (blocos + conexões)
# Mantém, para cada bloco, até TRÊS saídas possíveis:
#   - default   : lista (ordem original) de conexões sem branch
#   - true      : conexão originada de handle verde   (if-true)
#   - false     : conexão originada de handle vermelho (if-false)
# Se você já salva "branch": "true|false" ótimo; se não,
# detectamos pela cor (green / red).
# -----------------------------------------------------------

def load_macro_flow(json_path: str):
    """Retorna (blocks_dict, next_map, id_inicial)."""
    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    # blocos por id
    blocks = {blk["id"]: blk for blk in data.get("blocks", [])}
    # saídas
    next_map = {
        bid: {"default": [], "true": None, "false": None}
        for bid in blocks
    }
    incoming = {bid: 0 for bid in blocks}

    for conn in data.get("connections", []):
        src = conn.get("from")
        dst = conn.get("to")
        if src not in blocks or dst not in blocks:
            continue

        # ① identifica se a conexão é branch true/false
        branch = conn.get("branch")
        color = str(conn.get("color", "")).lower()
        if branch is None:
            if color in ("green", "#00ff00", "#0f0", "#00ff00ff"):
                branch = "true"
            elif color in ("red", "#ff0000", "#f00", "#ff0000ff"):
                branch = "false"

        if branch == "true":
            next_map[src]["true"] = dst
        elif branch == "false":
            next_map[src]["false"] = dst
        else:
            next_map[src]["default"].append(dst)

        incoming[dst] += 1

    # bloco inicial = grau de entrada 0 (pega o primeiro)
    start_nodes = [bid for bid, deg in incoming.items() if deg == 0]
    if not start_nodes:
        raise ValueError("Nenhum bloco inicial encontrado na macro.")

    return blocks, next_map, start_nodes[0]


# -----------------------------------------------------------
# Executor principal
# -----------------------------------------------------------

def _run_branch(blocks, next_map, json_path, start_block, progress_callback, label_callback):
    step = 0
    total = len(blocks)
    current = start_block
    while current is not None:
        bloco = blocks[current]
        ac = bloco.get("params", {})
        tipo = ac.get("type", "").lower()

        outs = list(next_map[current]["default"])
        if next_map[current]["true"]  is not None: outs.append(next_map[current]["true"])
        if next_map[current]["false"] is not None: outs.append(next_map[current]["false"])

        if len(outs) > 1:
            threads = []
            for destino in outs:
                t = threading.Thread(
                    target=_run_branch,
                    args=(blocks, next_map, json_path, destino, progress_callback, label_callback),
                    daemon=True
                )
                t.start()
                threads.append(t)
            for t in threads:
                t.join()
            return
            
        
        if macro_parar:
            print("Macro interrompida pelo usuário (Ctrl+Q).")
            break
        while macro_pausar:
            time.sleep(0.1)

        step += 1
        if progress_callback:
            progress_callback(step, total)
        if label_callback:
            label_callback(f"Executando bloco {current}")

        #bloco = blocks[current]
        #ac = bloco.get("params", {})   # params gravado no JSON
        #tipo = str(ac.get("type", "")).lower()

        try:
            # -------- AÇÕES BÁSICAS ----------------------------------
            if tipo == "click":
                pyautogui.click(ac["x"], ac["y"])

            elif tipo in ("type", "text"):
                texto = ac.get("text") or ac.get("content", "")
                pyautogui.write(texto)

            elif tipo == "delay":
                time.sleep(ac.get("time", 0) / 1000)

            # -------- CONDICIONAIS ----------------------------------
            elif tipo in ("ocr", "ocr_duplo", "imagem"):
                resultado = False

                if tipo == "ocr":
                    # ------------ OCR simples -------------
                    bbox = (ac["x"], ac["y"],
                            ac["x"] + ac["w"], ac["y"] + ac["h"])
                    img = safe_grab(bbox=bbox)
                    detectado = safe_ocr(img).strip().lower()

                    esperado   = ac.get("text", "").strip().lower()
                    if ac.get("vazio"):
                        resultado = detectado == ""
                    else:
                        resultado = esperado in detectado

                elif tipo == "ocr_duplo":
                    # ------------ OCR duplo ---------------
                    def _lê(bx, by, bw, bh):
                        img = safe_grab(bbox=(bx, by, bx+bw, by+bh))
                        return safe_ocr(img).strip().lower()

                    t1 = _lê(ac["x1"], ac["y1"], ac["w1"], ac["h1"])
                    t2 = _lê(ac["x2"], ac["y2"], ac["w2"], ac["h2"])

                    if ac.get("vazio1"):
                        ok1 = t1 == ""
                    else:
                        ok1 = ac["text1"].strip().lower() in t1

                    if ac.get("vazio2"):
                        ok2 = t2 == ""
                    else:
                        ok2 = ac["text2"].strip().lower() in t2

                    cond = ac.get("condicao", "and").lower()
                    resultado = (ok1 and ok2) if cond == "and" else (ok1 or ok2)

                elif tipo == "imagem":
                    # ------------ Matching de imagem -----------------
                    # 1) nome vindo do JSON (pode ser só o nome, um path
                    #    relativo tipo "img/…" ou já absoluto)
                    raw = ac["imagem"]

                    # 2) lista de lugares onde procurar, em ordem
                    candidatos = []

                    # 2.1) se veio absoluto, testa primeiro
                    if os.path.isabs(raw):
                        candidatos.append(raw)

                    # 2.2) relativo à pasta do JSON (tmp\ ou Macros\<nome>\)
                    candidatos.append(os.path.join(os.path.dirname(json_path), raw))

                    # 2.3) dentro de Macros\<macro>\img\arquivo
                    try:
                        with open(json_path, "r", encoding="utf-8") as f:
                            macro_name = json.load(f).get("macro_name")
                        if macro_name:
                            candidatos.append(os.path.join("Macros", macro_name,
                                                           "img", os.path.basename(raw)))
                    except Exception:
                        pass  # se não conseguir abrir, segue adiante
                    
                    # 3) pega o primeiro que existir
                    for tpl in candidatos:
                        if os.path.isfile(tpl):
                            break
                    else:
                        raise FileNotFoundError(f"Template não encontrado em: {candidatos}")

                    # ------------ Faz o match ------------------------


                    # área de busca (se veio do diálogo) ou tela inteira
                    if all(k in ac for k in ("x", "y", "w", "h")) and ac["w"] > 0 and ac["h"] > 0:
                        bbox = (ac["x"], ac["y"],
                                ac["x"] + ac["w"], ac["y"] + ac["h"])
                        base = safe_grab(bbox=bbox)
                    else:
                        base = pyautogui.screenshot()

                    base = cv2.cvtColor(np.array(base), cv2.COLOR_RGB2BGR)
                    templ = cv2.imread(tpl, cv2.IMREAD_COLOR)

                    res = cv2.matchTemplate(base, templ, cv2.TM_CCOEFF_NORMED)
                    _, max_val, _, _ = cv2.minMaxLoc(res)
                    th = ac.get("threshold", 0.80)
                    resultado = max_val >= th
                
            
                # decide próximo bloco com base no resultado
                ramo = "true" if resultado else "false"
                destino = next_map[current][ramo]
                if destino is None:
                    # fallback → primeira saída default (se existir)
                    destino = next_map[current]["default"][:1] or [None]
                    destino = destino[0]
                current = destino
                continue  # vai para o próximo loop da WHILE
            
            elif tipo == 'screenshot':
                # captura da screenshot
                if ac.get('mode') == 'whole':
                    img = safe_grab()
                else:
                    r = ac.get('region', {})
                    img = safe_grab(bbox=(r['x'], r['y'], r['x']+r['w'], r['y']+r['h']))
                # destino
                st = ac.get('save_to')
                if st == 'disk':
                    base = ac.get('custom_path') if ac.get('path_mode') == 'custom' else os.getcwd()
                    fname = f"screenshot_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
                    full_path = os.path.join(base, fname)
                    print(f"[DEBUG] Salvando screenshot em {full_path}")
                    safe_save(img, full_path)
                elif st == 'clipboard':
                    buf = io.BytesIO()
                    img.convert('RGB').save(buf, 'BMP')
                    data = buf.getvalue()[14:]
                    buf.close()
                    safe_clipboard_set(data)
                elif st == 'telegram':
                    # salva temporariamente no disco
                    base = ac.get('custom_path') if ac.get('path_mode')=='custom' else os.getcwd()
                    fname = f"screenshot_{datetime.now():%Y%m%d_%H%M%S}.png"
                    full_path = os.path.join(base, fname)
                    safe_save(img, full_path)

                    # envia via Telegram
                    send_photo(
                        bot_token = ac['token'],
                        chat_id  = ac['chat_id'],
                        photo_path = full_path,
                        caption = ac.get('custom_message', '')
                    )
                # segue para próximo bloco
                default_outs = next_map[current]['default']
                current = default_outs[0] if default_outs else None
                continue
            
            # (outros tipos como loopstart/loopend/goto/label
            #  podem ser implementados usando next_map)

        except Exception as exc:
            print(f"Erro no bloco {current}: {exc}")
            traceback.print_exc()

        # -------- fluxo normal --------------------------------------
        default_outs = next_map[current]["default"]
        current = default_outs[0] if default_outs else None
def safe_grab(bbox=None):
    with _grab_lock:
        return ImageGrab.grab(bbox=bbox)
def safe_ocr(img):
    with _tess_lock:
        return pytesseract.image_to_string(img)
def safe_save(img, path):
    with _io_lock:
        img.save(path)
def safe_clipboard_set(data_bytes):
    with _clipboard_lock:
        win32clipboard.OpenClipboard()
        win32clipboard.EmptyClipboard()
        win32clipboard.SetClipboardData(win32clipboard.CF_DIB, data_bytes)
        win32clipboard.CloseClipboard()

def executar_macro_flow(json_path: str, progress_callback=None, label_callback=None):
    blocks, next_map, start = load_macro_flow(json_path)
    global macro_parar, macro_pausar
    macro_parar = macro_pausar = False
    threading.Thread(target=_monitorar_teclas, daemon=True).start()
    _run_branch(blocks, next_map, json_path, start, progress_callback, label_callback)
    print("Execução da macro concluída.")