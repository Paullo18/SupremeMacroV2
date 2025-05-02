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
import tempfile
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
    ids_existentes = [blk["id"] for blk in data.get("blocks", [])]
    

    # blocos por id
    blocks = {blk["id"]: blk for blk in data.get("blocks", [])}

    # saídas: agora “true” e “false” são listas
    next_map = {
        bid: {"default": [], "true": [], "false": [], "fork": []}
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
            next_map[src]["true"].append(dst)
        elif branch == "false":
            next_map[src]["false"].append(dst)
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

def _run_branch(blocks, next_map, json_path, start_block,
                progress_callback, label_callback, stop_event=None,
                thread_name=None):
    step, total = 0, len(blocks)
    current = start_block

    #print(f"[DEBUG] Entrando no _run_branch com thread_name = {thread_name}")

    # Define explicitamente o nome amigável da thread
    if thread_name is None:
        # Tenta pegar o nome a partir do bloco atual, se for um startthread
        bloco = blocks.get(start_block, {})
        tipo = bloco.get("params", {}).get("type", "").lower()
        if tipo == "startthread":
            thread_name = bloco.get("params", {}).get("thread_name", f"Thread-{start_block}")
        else:
            thread_name = "Thread Principalasdasd"

    disp_name = thread_name

    while current is not None:
        bloco = blocks[current]
        ac    = bloco.get("params", {})
        tipo  = ac.get("type", "").lower()
        print(f"[DEBUG][{disp_name}] Entrou no bloco {current} (tipo={tipo}), params={ac}")

        if tipo == "startthread":
            branches  = ["default", "true", "false"]
            raw_forks = ac.get("forks", {})
            forks     = { int(k): v for k, v in raw_forks.items() }
            main_dest = None
            novas_threads = []

            # Classifica destinos: qual será o fluxo principal e quais virarão threads
            for br in branches:
                for dest in next_map[current].get(br, []):
                    escolha = forks.get(dest, "Continuar Fluxo")
                    if escolha == "Nova Thread":
                        novas_threads.append(dest)
                    elif main_dest is None:
                        main_dest = dest

            # ✅ Continua o fluxo principal primeiro (se existir)
            current = main_dest

            # ✅ Depois cria as threads paralelas
            for dest in novas_threads:
                params_destino = blocks.get(dest, {}).get("params", {})
                base_name = params_destino.get("thread_name", f"Thread-{dest}")
                display_name = base_name
                internal_name = f"{base_name}-{dest}"

                #print(f"[DEBUG] Iniciando thread '{display_name}' para bloco {dest}")
                th = threading.Thread(
                    target=_run_branch,
                    name=internal_name,
                    args=(
                        blocks, next_map, json_path,
                        dest,
                        progress_callback,
                        label_callback,
                        stop_event or threading.Event(),
                        display_name
                    ),
                    daemon=True
                )
                th.start()

            # ✅ Mesmo se não tiver main_dest, current será None e isso encerra o loop
            continue





        if (stop_event and stop_event.is_set()) or macro_parar:
            print("Macro interrompida pelo usuário (Ctrl+Q).")
            break
        while macro_pausar:
            time.sleep(0.1)

        step += 1
        if progress_callback:
            progress_callback(disp_name, step, total)
        if label_callback:
            label_callback(disp_name, f"Executando bloco {current}")

        #bloco = blocks[current]
        #ac = bloco.get("params", {})   # params gravado no JSON
        #tipo = str(ac.get("type", "")).lower()

        try:
            # -------- AÇÕES BÁSICAS ----------------------------------
            if tipo == "click":
                pyautogui.click(ac["x"], ac["y"])

            texto = ac.get("text") or ac.get("content", "")
            if tipo in ("type","text") or (texto and tipo == ""):
                print(f"[DEBUG][{disp_name}] Escrevendo no bloco {current}: '{texto}'")
                #time.sleep(1)  # se quiser dar um tempinho pra você focar
                pyautogui.write(texto)
                

            elif tipo == "delay":
                ms_total   = ac.get("time", 0)
                deadline   = time.monotonic() + ms_total / 1000.0   # instante-fim
                base_step  = step - 1        # blocos que já terminaram
                last_sent  = 0.0             # último progresso despachado (0-1)
            
                while True:
                    restante = deadline - time.monotonic()
                    if restante <= 0:
                        break                    # tempo cumprido
                    
                    # –– interrupções ––
                    if macro_parar or (stop_event and stop_event.is_set()):
                        print(f"[DEBUG][{disp_name}] Delay interrompido por stop")
                        break
                    
                    while macro_pausar and not (stop_event and stop_event.is_set()):
                        time.sleep(0.1)
            
                    # –– calcula fração concluída (0-1) ––
                    frac = 1.0 - (restante * 1000) / ms_total
                    # só manda update se mudou pelo menos 1 % para evitar flood
                    if progress_callback and frac - last_sent >= 0.01:
                        progress_callback(disp_name, base_step + frac, total)
                        last_sent = frac
            
                    # dorme no máx. 0,5 s, mas acorda antes se stop_event disparar
                    fatia = min(restante, 0.5)
                    if stop_event:
                        stop_event.wait(fatia)
                    else:
                        time.sleep(fatia)
            
                # garante que a barra chegue ao passo inteiro quando o delay acaba
                if progress_callback:
                    progress_callback(disp_name, base_step + 1, total)


            
            elif tipo == "goto":
                alvo = ac.get("label")  # nome do Label para onde voltar
                # varre todos os blocos procurando um Label com esse name
                print(f"[DEBUG] GoTo encontrado, alvo = {alvo!r}")
                for bid, blk in blocks.items():
                    p = blk.get("params",{})
                    if p.get("type","").lower() == "label" and p.get("name") == alvo:
                        current = bid
                        break
                else:
                    print(f"[WARN] Label '{alvo}' não encontrado → encerrando.")
                    current = None
                continue

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
                
            
                # escolhe ramo e lista de destinos
                ramo = "true" if resultado else "false"
                destinos = next_map[current][ramo]

                # segue primeiro destino de true/false, ou default se não houver
                if destinos:
                    current = destinos[0]
                elif next_map[current]["default"]:
                    current = next_map[current]["default"][0]
                else:
                    current = None
                continue
            
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
                elif st == 'telegram':
                    # ① captura já está em `img`
                    # ② cria arquivo temporário só para a API do Telegram
                    with tempfile.NamedTemporaryFile(delete=False, suffix=".png") as tmp:
                        temp_path = tmp.name
                    safe_save(img, temp_path)                 # grava a imagem
                
                    # ③ envia via Telegram (API continua igual; usa caminho temporário)
                    send_photo(
                        bot_token = ac['token'],
                        chat_id   = ac['chat_id'],
                        photo_path = temp_path,
                        caption   = ac.get('custom_message', '')
                    )
                
                    # ④ apaga o temp depois do envio
                    try:
                        os.remove(temp_path)
                    except OSError:
                        pass
                # segue para próximo bloco
                default_outs = next_map[current]['default']
                current = default_outs[0] if default_outs else None
                continue
            
            # (outros tipos como loopstart/loopend/goto/label
            #  podem ser implementados usando next_map)

        except Exception as exc:
            print(f"Erro no bloco {current}: {exc}")
            traceback.print_exc()

        # -------- fluxo normal – pega primeiro default após executar a ação ----
        outs = next_map[current]
        default_outs = next_map[current].get("default", [])
        if not default_outs:
            break
        #next_default = default_outs[0]

        # segue para o próximo bloco automaticamente
        current = default_outs[0]

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

def executar_macro_flow(json_path: str, progress_callback=None,
                        label_callback=None, stop_event=None):
    blocks, next_map, start = load_macro_flow(json_path)
    global macro_parar, macro_pausar
    macro_parar = macro_pausar = False
    threading.Thread(target=_monitorar_teclas, daemon=True).start()

    # Pegando nome da thread principal a partir do bloco inicial
    params = blocks[start].get("params", {})
    main_name = params.get("thread_name", "Thread Principal")

    # Cria a thread principal com nome técnico visível nos logs
    th = threading.Thread(
        target=_run_branch,
        name=main_name,  # nome real da thread no sistema
        args=(
            blocks, next_map, json_path, start,
            progress_callback, label_callback, stop_event,
            main_name
        ),
        daemon=True
    )
    th.start()
    th.join()

    print("Execução da macro concluída.")

