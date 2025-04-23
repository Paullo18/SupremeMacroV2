import pyautogui
import time
import pytesseract
from PIL import ImageGrab, Image
import threading
import keyboard
import os
import json
import traceback
from core.storage import obter_caminho_macro_atual

# Configuração do Tesseract
pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"

# Flags de controle
macro_parar = False
macro_pausar = False


def monitorar_teclas():
    """
    Thread para escutar Ctrl+Q (parar) e Ctrl+P (pausar)
    """
    global macro_parar, macro_pausar
    while True:
        if keyboard.is_pressed("ctrl+q"):
            macro_parar = True
            break
        if keyboard.is_pressed("ctrl+p"):
            macro_pausar = not macro_pausar
            time.sleep(0.5)
        time.sleep(0.05)


def load_macro_flow(json_path):
    """
    Carrega JSON com 'blocks' e 'connections', retorna:
      - dict de blocos por id
      - adjacências: dict id -> lista de ids
      - id do bloco inicial (sem incoming)
    """
    with open(json_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    # mapeia blocos
    blocks = {blk['id']: blk for blk in data.get('blocks', [])}
    # constrói lista de conexões
    adj = {bid: [] for bid in blocks}
    incoming = {bid: 0 for bid in blocks}
    for conn in data.get('connections', []):
        src = conn.get('from')
        dst = conn.get('to')
        if src in blocks and dst in blocks:
            adj[src].append(dst)
            incoming[dst] += 1
    # bloco inicial = in-degree 0
    starts = [bid for bid, deg in incoming.items() if deg == 0]
    if not starts:
        raise ValueError("Nenhum bloco inicial encontrado na macro.")
    return blocks, adj, starts[0]


def executar_macro_flow(json_path, progress_callback=None, label_callback=None):
    """
    Executa macro no formato de fluxo (blocks + connections).
    """
    global macro_parar, macro_pausar
    macro_parar = False
    macro_pausar = False
    threading.Thread(target=monitorar_teclas, daemon=True).start()

    blocks, adj, current = load_macro_flow(json_path)
    loop_stack = []
    step = 0
    total = len(blocks)

    while current is not None:
        if macro_parar:
            print("Macro interrompida pelo usuário.")
            break
        while macro_pausar:
            time.sleep(0.1)

        step += 1
        if progress_callback:
            progress_callback(step, total)
        if label_callback:
            label_callback(f"Executando bloco {current}")

        bloco = blocks[current]
        ac = bloco.get('params', {})
        tipo = ac.get('type', '').lower()

        try:
            # Ações básicas
            if tipo == 'click':
                pyautogui.click(ac['x'], ac['y'])
            elif tipo == 'type':
                pyautogui.write(ac['text'])
            elif tipo == 'delay':
                time.sleep(ac['time'] / 1000)

            # Condicionais: OCR simples, duplo, imagem
            elif tipo in ('ocr', 'ocr_duplo', 'imagem'):
                resultado = False
                if tipo == 'ocr':
                    bbox = (ac['x'], ac['y'], ac['x']+ac['w'], ac['y']+ac['h'])
                    img = ImageGrab.grab(bbox=bbox)
                    detect = pytesseract.image_to_string(img).strip().lower()
                    esperado = ac.get('text','').strip().lower()
                    resultado = (esperado in detect)
                # TODO: implementar OCR Duplo e Imagem similar ao antigo executar.py

                # escolhe próximo bloco: true->adj[0], false->adj[1]
                outs = adj.get(current, [])
                if resultado and len(outs) >= 1:
                    current = outs[0]
                elif not resultado and len(outs) >= 2:
                    current = outs[1]
                else:
                    current = None
                continue

            # LoopStart e LoopEnd podem usar goto via 'connections'
            # GOTO e LABEL podem usar conexões laterais

        except Exception as e:
            print(f"Erro ao executar ação no bloco {current}: {e}")
            traceback.print_exc()

        # padrão: segue primeira conexão, ou finaliza
        nexts = adj.get(current, [])
        current = nexts[0] if nexts else None

    print("Execução da macro concluída.")
