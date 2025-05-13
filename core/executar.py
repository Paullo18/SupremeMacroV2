import json
import time
import threading
import traceback
import os, sys
import cv2
import numpy as np
import keyboard
import pyautogui
import pytesseract
import random
from PIL import ImageGrab, Image
import io
import win32clipboard
import tempfile
import datetime
from datetime import datetime
from utils.telegram_util import send_photo
from utils.google_sheet_util import append_next_row
import core.storage as storage
import time

# ────────────────────────────────────────────────────────────
# SETTINGS (settings.json)
#   • Carrega uma única vez e provê helpers para valores padrão
# ────────────────────────────────────────────────────────────

_SETTINGS_PATH = os.path.join(os.path.dirname(__file__), "..", "settings.json")

def _load_settings():
    try:
        with open(_SETTINGS_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        return {}

_SETTINGS = _load_settings()

def _default_bot():
    """Retorna {'token': str, 'chat_id': str} do primeiro bot ou dos campos legacy."""
    bots = _SETTINGS.get("telegram") or _SETTINGS.get("telegram_bots") or []
    if bots:
        return bots[0]               # primeiro bot configurado
    return {
        "token":   _SETTINGS.get("telegram_token",  ""),
        "chat_id": _SETTINGS.get("telegram_chat_id", ""),
    }

def _default_sheet_id():
    gs = _SETTINGS.get("google_sheets", [])
    return gs[0]["id"] if gs else None

energy_level = _SETTINGS.get("energy_saving_level", "Desligado")

_grab_lock      = threading.Lock()  # para ImageGrab / screenshot
_tess_lock      = threading.Lock()  # para pytesseract
_clipboard_lock = threading.Lock()  # para win32clipboard
_io_lock        = threading.Lock()  # para salvar em disco

# # Caminho do Tesseract (ajuste se necessário)
# # ─── Definição dinâmica do caminho do Tesseract ───────────────
# import sys
# if getattr(sys, "frozen", False):
#     # Quando empacotado pelo PyInstaller, tesseract.exe ficará em _MEIPASS
#     base_dir = sys._MEIPASS
# else:
#     # Em modo script, fica ao lado deste .py
#     base_dir = os.path.dirname(__file__)

# # Ajusta o comando para usar o executável incluído no pacote
# pytesseract.pytesseract.tesseract_cmd = os.path.join(base_dir, "tesseract.exe")
# ────────────────────────────────────────────────────────────
pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"

# -------------- flags globais de controle ------------------
macro_parar: bool = False
macro_pausar: bool = False

# ------------------------------------------------------------------
# Contador global ( thread‑safe ) de threads ativas
# ------------------------------------------------------------------
_active_threads = 0
_active_lock    = threading.Lock()


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
                progress_callback, label_callback,
                stop_event: threading.Event | None = None,
                thread_name: str | None = None,
                status_win=None):
    global _active_threads
    with _active_lock:
        _active_threads += 1

    step, total = 0, len(blocks)

    #print(f"[DEBUG] Entrando no _run_branch com thread_name = {thread_name}")

    # Define explicitamente o nome amigável da thread
    if thread_name is None:
        # Tenta pegar o nome a partir do bloco atual, se for um startthread
        bloco = blocks.get(start_block, {})
        tipo = bloco.get("params", {}).get("type", "").lower()
        if tipo == "startthread":
            thread_name = bloco.get("params", {}).get("thread_name", f"Thread-{start_block}")
        else:
            thread_name = "Thread Principal"

    disp_name = thread_name
    try:
        current = start_block
        while current is not None:
            # interrupção imediata se alguém clicou em Stop
            if stop_event.is_set():
                print(f"[DEBUG][{disp_name}] stop_event set — interrompendo fluxo")
                break
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
                    child_evt = threading.Event()
                    th = threading.Thread(
                        target=_run_branch,
                        name=internal_name,
                        args=(
                            blocks, next_map, json_path,
                            dest,
                            progress_callback,
                            label_callback,
                            child_evt,
                            display_name,
                            status_win
                        ),
                        daemon=True
                    )
                    th.start()
                    #_workers.append(th)

                    if status_win:
                        # liga botão Stop/Play da thread filha
                        status_win.register_stop_event(display_name, child_evt)

                        def restart_child(name, new_evt,
                                          _dest=dest, _disp=display_name):
                            threading.Thread(
                                target=_run_branch,
                                name=internal_name,
                                args=(
                                    blocks, next_map, json_path,
                                    _dest,
                                    progress_callback,
                                    label_callback,
                                    new_evt,
                                    _disp,
                                    status_win
                                ),
                                daemon=True
                            ).start()
                            status_win.register_stop_event(name, new_evt)

                        status_win.register_restart_callback(display_name, restart_child)

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
                # 1) qual o tipo do bloco?
                tipo = ac.get("type", "").lower()

                # 2) pega primeiro o nome customizado/name, se houver
                label_text = ac.get("custom_name") or ac.get("name")

                # 3) se não tiver, monta um fallback de delay ou simplesmente capitaliza o tipo
                if not label_text:
                    if tipo == "delay":
                        ms = ac.get("time", 0)
                        label_text = f"Delay: {ms}ms"
                    else:
                        # você pode tratar outros casos especiais aqui, ex: run_macro, click, etc.
                        label_text = tipo.capitalize()

                # 4) dispara usando o mesmo formato "LABEL ID"
                label_callback(disp_name, f"{label_text} {current}")

                # checagem extra após executar o bloco
                if stop_event.is_set():
                    print(f"[DEBUG][{disp_name}] stop_event set após bloco — saindo")
                    break

            #bloco = blocks[current]
            #ac = bloco.get("params", {})   # params gravado no JSON
            #tipo = str(ac.get("type", "")).lower()

            try:
                # -------- AÇÕES BÁSICAS ----------------------------------
                if tipo == "click":
                    # Modo Aleatório: escolhe ponto random dentro da região
                    if ac.get("mode", "").lower() == "aleatório":
                        x0, y0 = ac["x"], ac["y"]
                        w, h = ac["w"], ac["h"]
                        x = random.randint(x0, x0 + w - 1)
                        y = random.randint(y0, y0 + h - 1)
                        pyautogui.click(x, y)
                    else:
                        # Modo Simples
                        pyautogui.click(ac["x"], ac["y"])

                texto = ac.get("text") or ac.get("content", "")
                if tipo in ("type","text") or (texto and tipo == ""):
                    print(f"[DEBUG][{disp_name}] Escrevendo no bloco {current}: '{texto}'")
                    #time.sleep(1)  # se quiser dar um tempinho pra você focar
                    pyautogui.write(texto)

                # atalho de teclado (hotkey) ---------------------------
                elif tipo == "hotkey":
                    combo = ac.get("command", "")            # ex: "Ctrl+S"
                    # quebra em teclas individuais, normaliza para pyautogui
                    keys = [k.strip().lower() for k in combo.split("+") if k.strip()]
                    if keys:
                        # dispara o atalho
                        pyautogui.hotkey(*keys)


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

                # ───────────────────────────────────────────
                # Agendar Hora (“schedule”): espera até o momento configurado
                # ───────────────────────────────────────────
                elif tipo == "schedule":
                    # 1) Extrai data e hora do bloco
                    date_str = ac.get("date", "")
                    hour     = ac.get("hour", 0)
                    minute   = ac.get("minute", 0)
                    second   = ac.get("second", 0)

                    try:
                        # 2) Constrói datetime alvo e calcula intervalo
                        #    usa a classe datetime importada diretamente
                        target_date = datetime.strptime(date_str, "%Y-%m-%d")
                        target      = target_date.replace(
                            hour=hour, minute=minute, second=second, microsecond=0
                        )
                        now         = datetime.now()
                        delta_s     = (target - now).total_seconds()

                        # 3) Aguarda até o horário, com suporte a pausa/interrupção
                        if delta_s > 0:
                            deadline = time.time() + delta_s
                            while True:
                                rem = deadline - time.time()
                                if rem <= 0 or (stop_event and stop_event.is_set()):
                                    break
                                # respeita pausa
                                while macro_pausar:
                                    time.sleep(0.1)
                                # dorme em fatias de até 1 s para responsividade
                                time.sleep(min(rem, 1))
                    except Exception as e:
                        print(f"[ERROR][schedule] Falha ao agendar: {e}")

                    # 4) Avança para o próximo bloco
                    default_outs = next_map[current].get("default", [])
                    current = default_outs[0] if default_outs else None
                    continue
                
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
                        # delays conforme nível
                        if energy_level == "Nível 1":
                            time.sleep(0.100)
                        elif energy_level == "Nível 2":
                            time.sleep(0.200)
                        elif energy_level == "Nível 3":
                            time.sleep(0.400)
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
                        # delays conforme nível
                        if energy_level == "Nível 1":
                            time.sleep(0.150)
                        elif energy_level == "Nível 2":
                            time.sleep(0.300)
                        elif energy_level == "Nível 3":
                            time.sleep(0.600)
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
                        # delays conforme nível
                        if energy_level == "Nível 1":
                            time.sleep(0.050)
                        elif energy_level == "Nível 2":
                            time.sleep(0.100)
                        elif energy_level == "Nível 3":
                            time.sleep(0.200)
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

                elif tipo in ("remote_control", "telegram_command"):
                    esperado = ac.get("command", "").strip()
                    if not esperado:
                        print(f"[WARN][{disp_name}] Comando vazio — segue fluxo.")
                    else:
                        print(f"[DEBUG][{disp_name}] Aguardando comando remoto '{esperado}'…")

                        if not hasattr(storage, "remote_waiters"):
                            storage.remote_waiters = {}

                        evt = threading.Event()
                        storage.remote_waiters.setdefault(esperado, []).append(evt)

                        # Aguarda até que (_on_command) dispare evt.set()
                        while not evt.is_set():
                            if (stop_event and stop_event.is_set()) or macro_parar:
                                break
                            time.sleep(0.1)

                        # Remove o waiter da lista
                        try:
                            storage.remote_waiters[esperado].remove(evt)
                        except (KeyError, ValueError):
                            pass

                    # segue para o próximo bloco
                    outs = next_map[current].get("default", [])
                    current = outs[0] if outs else None
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
                            bot_token = ac.get("token")   or _default_bot()["token"],
                            chat_id   = ac.get("chat_id") or _default_bot()["chat_id"],
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

                elif tipo == "text_to_sheet":
                    # 1) captura da região ----------------------
                    bx, by = ac.get("x", 0), ac.get("y", 0)
                    bw, bh = ac.get("w", 0), ac.get("h", 0)
                    with _grab_lock:
                        img = ImageGrab.grab(bbox=(bx, by, bx + bw, by + bh))

                    # 2) aplica escala se >1 --------------------
                    s = ac.get("scale", 1)
                    if s > 1:
                        img = img.resize((img.width * s, img.height * s), Image.LANCZOS)

                    # 3) OCR ------------------------------------
                    with _tess_lock:
                        texto = pytesseract.image_to_string(img).strip()

                    # 4) envia para o Sheets --------------------
                    try:
                        #   sheet_id -> ID (ou nome) da planilha
                        #   tab_id   -> índice da aba      (0 = primeira)
                        #   column   -> **apenas letras**  (A, B, …)
                        #   values   -> lista‑de‑listas

                        sheet_id = (
                            ac.get("sheet_id")            # preferencial
                            or ac.get("sheet")            # compat. legacy
                            or _default_sheet_id()        # fallback settings.json
                        )

                        # Extrai só as letras da coluna (remove algarismos, se vier "O1", "A5", …)
                        import re
                        col_raw = ac.get("column", "A")
                        column_letter = re.sub(r"\d+", "", col_raw).upper() or "A"

                        append_next_row(
                            sheet_id,                     # 1º
                            int(ac.get("tab_id", 0)),     # 2º
                            column_letter,                # 3º (só letras)
                            [[texto]]                     # 4º (lista‑de‑listas)
                        )

                    except Exception as e:
                        print(f"[ERROR][text_to_sheet] Falha ao enviar: {e}")

                    # segue para o próximo bloco
                    default_outs = next_map[current].get("default", [])
                    current = default_outs[0] if default_outs else None
                    continue

                # ───── Run Macro (aninhada) ─────
                elif tipo == "run_macro":
                    nested = ac.get("path", "").strip()
                    if nested and os.path.isfile(nested):
                        print(f"[DEBUG][{disp_name}] Executando macro aninhada inline: {nested}")
                        # 1) carrega o fluxo da macro filha
                        blocks2, next_map2, start2 = load_macro_flow(nested)
                        # 2) executa INLINE, reaproveitando o mesmo nome de thread (disp_name)
                        _run_branch(
                            blocks2,
                            next_map2,
                            nested,
                            start2,
                            progress_callback, label_callback,
                            stop_event, disp_name, status_win
                        )
                    else:
                        print(f"[WARN][{disp_name}] Caminho de macro inválido: {nested}")
                    # após a filha, continua o fluxo do macro atual
                    default_outs = next_map[current].get("default", [])
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
    finally:
        if stop_event:
            stop_event.set()
        with _active_lock:
            _active_threads -= 1

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
caminho_macro_real = None
caminho_arquivo_tmp = None
# ------------------------------------------------------------------
#  Função principal (ponto de entrada)
# ------------------------------------------------------------------
def executar_macro_flow(json_path: str, progress_callback=None,
                        label_callback=None, stop_event=None,
                        status_win=None):

    # lista global para todos os workers deste fluxo
    # ===== zera contador global de threads =====
    global _active_threads
    with _active_lock:
        _active_threads = 0
    import core.storage as storage
    # Se estiver sendo executado do diretório tmp -> atualiza caminho temporário
    parts = os.path.normpath(json_path).split(os.sep)
    if 'tmp' in parts:
        storage.caminho_arquivo_tmp = json_path
    else:
        # Caso contrário, é um macro salvo
        storage.caminho_macro_real = json_path
    # Carrega o fluxo da macro
    blocks, next_map, start = load_macro_flow(json_path)
    global macro_parar, macro_pausar
    macro_parar = macro_pausar = False
    threading.Thread(target=_monitorar_teclas, daemon=True).start()

    # rótulo amigável da thread raiz
    params = blocks[start].get("params", {})
    main_label = params.get("thread_name", "Thread Principal")

    th_evt = stop_event or threading.Event()          # Event da raiz

    # nome interno ÚNICO para evitar colisões ao reiniciar
    root_internal_name = f"Thread-Root-{int(time.time()*1000)}"

    th = threading.Thread(
        target=_run_branch,
        name=root_internal_name,
        args=(
            blocks, next_map, json_path, start,
            progress_callback, label_callback,
            th_evt, main_label, status_win
        ),
        daemon=True
    )
    th.start()
    if status_win:
        status_win.register_stop_event(main_label, th_evt)

    # --- callback Play da thread principal -------------
    if status_win:
        def restart_main(name, new_evt):
            """Recria a Thread‑Root quando o usuário clica em Play."""
            new_internal = f"Thread-Root-{int(time.time()*1000)}"

            t = threading.Thread(
                target=_run_branch,
                name=new_internal,
                args=(
                    blocks, next_map, json_path, start,
                    progress_callback, label_callback,
                    new_evt, main_label, status_win
                ),
                daemon=True
            )
            t.start()
            status_win.register_stop_event(name, new_evt)

        status_win.register_restart_callback(main_label, restart_main)

   # Espera até que TODAS as threads de macro tenham terminado
    while True:
        with _active_lock:
            if _active_threads == 0:
                break
        time.sleep(0.1)

    print("Execução da macro concluída.")