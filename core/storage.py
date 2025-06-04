import os
import json
import shutil
from datetime import datetime
# Import thread safety patch
import thread_safe_patch

# Apply thread safety patches
thread_safe_patch.apply_thread_safety_patches()
from tkinter import simpledialog
from core import show_info, show_error

def macro_em_pasta_macros(path_):
    abs_path   = os.path.abspath(path_)
    macros_abs = os.path.abspath(MACROS_DIR)
    # agora considera qualquer JSON dentro de Macros/<nome> como macro existente
    if not abs_path.startswith(macros_abs + os.sep):
        return False
    return os.path.basename(abs_path).lower().endswith(".json")

def _sincronizar_imagens(json_tmp: str, pasta_macro: str):
    """Garante que todas as imagens citadas em *json_tmp* estejam em
    <pasta_macro>/img/  e atualiza os caminhos no próprio JSON."""
    with open(json_tmp, "r", encoding="utf-8") as f:
        data = json.load(f)

    img_dir = os.path.join(pasta_macro, "img")
    os.makedirs(img_dir, exist_ok=True)

    alterado = False
    for blk in data.get("blocks", []):
        p = blk.get("params", {})
        if p.get("type") == "imagem" and p.get("imagem"):
            nome = os.path.basename(p["imagem"])

            # se a imagem ainda está na tmp\ move para a pasta definitiva
            src_tmp = os.path.join(TMP_DIR, nome)
            dst_img = os.path.join(img_dir, nome)
            if os.path.exists(src_tmp):
                shutil.move(src_tmp, dst_img)
                alterado = True

            # garante que o campo armazene  img/<arquivo>
            if p["imagem"] != os.path.join("img", nome):
                p["imagem"] = os.path.join("img", nome)
                alterado = True

    if alterado:
        with open(json_tmp, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

"""
  NOVAS VARIÁVEIS PARA GERENCIAR PASTA TEMPORÁRIA DE CADA MACRO:
  - TMP_DIR continua sendo a pasta “pai” das temporárias.
  - Ao criar/abrir uma macro, criamos um subdiretório exclusivo dentro de TMP_DIR.
    Chamaremos isso de TMP_SUBDIR (um caminho completo).
  - Dentro desse TMP_SUBDIR ficarão:
     • o JSON da macro (sempre com nome fixo “macro.json”)
     • a pasta “img” com imagens temporárias
     • (se houver) outras subpastas de screenshots, etc.
"""
# Diretórios base
TMP_DIR = "tmp"
MACROS_DIR = "Macros"

# Guardamos aqui o caminho completo ao “macro.json” que está em TMP_SUBDIR,
# ou, se já estivermos editando/salvando diretamente em Macros/<nome>/macro.json,
# esse caminho também estará em caminho_arquivo_tmp.
caminho_arquivo_tmp   = None
# Quando abrimos ou salvamos numa pasta definitiva (Macros/<nome>),
# gravamos o caminho real também nesta variável:
caminho_macro_real    = None

# Função NOVA: cria um subdiretório temporário exclusivo para esta macro.
def _criar_tmp_subdir():
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    subdir = os.path.join(TMP_DIR, f"macro_{ts}")
    os.makedirs(subdir, exist_ok=True)
    return subdir

def macro_em_pasta_macros(path_):
    abs_path   = os.path.abspath(path_)
    macros_abs = os.path.abspath(MACROS_DIR)
    # agora considera qualquer JSON dentro de Macros/<nome> como macro existente
    return abs_path.startswith(macros_abs + os.sep) and abs_path.lower().endswith(".json")

def _sincronizar_imagens(json_tmp: str, pasta_macro: str):
    """Garante que todas as imagens citadas em *json_tmp* estejam em
    <pasta_macro>/img/  e atualiza os caminhos no próprio JSON."""
    with open(json_tmp, "r", encoding="utf-8") as f:
        data = json.load(f)

    img_dir = os.path.join(pasta_macro, "img")
    os.makedirs(img_dir, exist_ok=True)

    alterado = False
    for blk in data.get("blocks", []):
        p = blk.get("params", {})
        if p.get("type") == "imagem" and p.get("imagem"):
            nome = os.path.basename(p["imagem"])

            # se a imagem ainda está em TMP_DIR/_subdir_, move para a pasta definitiva
            src_tmp = os.path.join(os.path.dirname(json_tmp), nome)
            dst_img = os.path.join(img_dir, nome)
            if os.path.exists(src_tmp):
                shutil.move(src_tmp, dst_img)
                alterado = True

            # garante que o campo armazene  img/<arquivo>
            if p["imagem"] != os.path.join("img", nome):
                p["imagem"] = os.path.join("img", nome)
                alterado = True

    if alterado:
        with open(json_tmp, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

# ============================================================
# 1) EXPORTAR UMA “MACRO NOVA” PARA TMP/ SUBDIR
# ============================================================

def export_macro_to_tmp(blocks, arrows, macro_name=None):
    """Gera um subdiretório temporário em `tmp/`, dentro do qual:
       • salva “macro.json” (estado atual do fluxo)
       • Eventualmente criará pasta “img/” para imagens temporárias

       *blocks* – lista de blocos (dicts gerados pelo BlocoManager)
       *arrows* – lista de tuplas (origem, destino, branch?, cor?)
    """
    global caminho_arquivo_tmp, caminho_macro_real

    # 1. Cria pasta temporária exclusiva para esta macro:
    os.makedirs(TMP_DIR, exist_ok=True)
    tmp_subdir = _criar_tmp_subdir()
    # 2. Definimos “macro.json” dentro dessa pasta:
    caminho_arquivo_tmp = os.path.join(tmp_subdir, "macro.json")

    data = {
        "macro_name": macro_name,
        "blocks": [],
        "connections": []
    }

    # (a pasta “img/” ainda não existe; será criada quando necessário pelo _sincronizar_imagens)


    # -------- blocos -------------------------------------
    for b in blocks:
        data["blocks"].append({
            "id": b["id"],
            "type": b["text"],
            "params": b.get("acao", {}),
            "x": b["x"],
            "y": b["y"]
        })

    # -------- conexões -----------------------------------
    for item in arrows:
        if len(item) == 4:
            origem, destino, branch_bool, cor = item
        elif len(item) == 3:
            origem, destino, branch_bool = item
            cor = None
        else:
            origem, destino = item
            branch_bool = False
            cor = None

        # Preserva o valor original:
        #   • True  → true   (verde)
        #   • False → false  (vermelho)
        #   • None  → null   (fluxo normal)
        branch = branch_bool  # ← não converte para bool!

        data["connections"].append({
            "from": origem["id"],
            "to": destino["id"],
            "branch": branch,
            "color": cor
        })

    # 3. Grava JSON inicial (sem imagens) em TMP_SUBDIR/macro.json
    with open(caminho_arquivo_tmp, "w", encoding="utf-8") as fp:
        json.dump(data, fp, ensure_ascii=False, indent=2)

    # Nenhuma macro real existe ainda (é uma criação nova), então caminho_macro_real permanece None
    caminho_macro_real = None
    return caminho_arquivo_tmp

# ============================================================
# 2) ABRIR UMA MACRO EXISTENTE – copiar para TMP_SUBDIR
# ============================================================
def abrir_macro_para_tmp(caminho_macro_existente: str):
    """
    Ao abrir uma macro que já existe em Macros/<nome>/macro.json, 
    copiamos toda a pasta (incluindo JSON e subpastas “img/”, etc.) 
    para um TMP_SUBDIR, de modo que o usuário possa editar ali.
    """
    global caminho_arquivo_tmp, caminho_macro_real

    if not macro_em_pasta_macros(caminho_macro_existente):
        show_error("Abrir Macro", "O arquivo selecionado não está dentro de Macros/.")
        return None

    # 1) Determina o diretório “pai” dessa macro (ex: “Macros/<nome>”)
    dir_macro = os.path.dirname(os.path.abspath(caminho_macro_existente))

    # 2) Cria novo TMP_SUBDIR
    os.makedirs(TMP_DIR, exist_ok=True)
    tmp_subdir = _criar_tmp_subdir()

    # 3) Copia todo conteúdo de dir_macro para tmp_subdir
    try:
        shutil.copytree(dir_macro, tmp_subdir, dirs_exist_ok=True)
    except Exception as e:
        show_error("Abrir Macro", f"Erro ao copiar para temporário:\n{e}")
        return None

    # 4) Ajusta as variáveis globais:
    caminho_arquivo_tmp = os.path.join(tmp_subdir, os.path.basename(caminho_macro_existente))
    caminho_macro_real  = caminho_macro_existente
    return caminho_arquivo_tmp

# ============================================================
# Salvar macro (novo ou sobrescrever existente)
# ============================================================

def _sobrescrever_macro(json_tmp, destino):
    """Sobrescreve `destino` com o conteúdo de `json_tmp`."""
    try:
        with open(json_tmp, "r", encoding="utf-8") as fi:
            data = json.load(fi)
        with open(destino, "w", encoding="utf-8") as fo:
            json.dump(data, fo, ensure_ascii=False, indent=2)
    except Exception as exc:
        show_error("Salvar", f"Erro ao sobrescrever macro:\n{exc}")
        return False
    return True


def salvar_macro_gui():
    """Comporta‑se assim:
    1. Se `caminho_arquivo_tmp` é um arquivo *já* dentro de `Macros/<nome>/macro.json`,
       apenas sobrescreve esse arquivo.
    2. Caso contrário, pergunta o nome da macro (se ainda não houver),
       e MOVE TODO O SUBDIR EM TMP/ PARA `Macros/<nome>/`.
    """
    global caminho_arquivo_tmp, caminho_macro_real

    # ---------------- caso 1: já é uma macro existente ----------------
    if caminho_arquivo_tmp and macro_em_pasta_macros(caminho_arquivo_tmp):

        # se já estamos editando “Macros/<nome>/macro.json”, basta sobrescrever esse JSON:
        if _sobrescrever_macro(caminho_arquivo_tmp, caminho_arquivo_tmp):
            show_info("Salvo", f"Macro atualizada em:\n{caminho_arquivo_tmp}")
        return caminho_arquivo_tmp

    # ---------------- caso 2: macro nova ------------------------------
    if not caminho_arquivo_tmp or not os.path.isfile(caminho_arquivo_tmp):
        show_error("Erro", "Nenhuma macro para salvar. Primeiro abra ou crie uma macro.")
        return

    # 1) Carrega JSON para extrair “macro_name”
    with open(caminho_arquivo_tmp, "r", encoding="utf-8") as f:
        data = json.load(f)

    nome = data.get("macro_name")
    if not nome:
        nome = simpledialog.askstring("Salvar macro", "Digite o nome da macro:")
        if not nome:
            return
        data["macro_name"] = nome

    # 2) Define destino final: Macros/<nome>
    destino_dir = os.path.join(MACROS_DIR, nome)
    if os.path.exists(destino_dir):
        show_error("Salvar", f"Já existe uma pasta com nome '{nome}'. Escolha outro nome.")
        return

    # 3) Move TODO O SUBDIR de TMP (onde está “macro.json” e “img/”) para Macros/<nome>:
    tmp_subdir = os.path.dirname(caminho_arquivo_tmp)
    try:
        shutil.move(tmp_subdir, destino_dir)
    except Exception as e:
        show_error("Salvar", f"Erro ao mover pasta temporária para Macros/: \n{e}")
        return

    # 4) Após mover, garante que “img/” e outros subitens sigam dentro de destino_dir
    #    Já está tudo copiado/pasta movida, mas precisamos regravar o JSON final:
    caminho_final = os.path.join(destino_dir, "macro.json")
    try:
        with open(caminho_final, "w", encoding="utf-8") as fo:
            json.dump(data, fo, ensure_ascii=False, indent=2)
    except Exception as e:
        show_error("Salvar", f"Erro ao gravar JSON final: \n{e}")
        return

    # 5) Atualiza variáveis globais para referência futura:
    caminho_arquivo_tmp = caminho_final
    caminho_macro_real  = caminho_final
    show_info("Salvo", f"Macro salva em: {caminho_final}")
    return caminho_final

# ============================================================
# Utilitários
# ============================================================

def limpar_tmp():
    if os.path.isdir(TMP_DIR):
        for f in os.listdir(TMP_DIR):
            path = os.path.join(TMP_DIR, f)
            if os.path.isfile(path):
                os.remove(path)
            elif os.path.isdir(path):
                shutil.rmtree(path, ignore_errors=True)

def rebuild_macro_canvas(path, canvas, bloco_manager, seta_manager, bind_fn):
    """
    Carrega um fluxo de macro do JSON e reconstrói todo o canvas:
      1. Limpa o canvas e os managers de blocos e setas.
      2. Carrega blocks, next_map e start_block via load_macro_flow.
      3. Recria cada bloco com ID e parâmetros originais.
      4. Reconstrói todas as setas.
      5. Centraliza a view no bloco inicial (se disponível).
      6. Rebind dos eventos de UI chamando bind_fn().
    """
    from core.executar import load_macro_flow

    # 1) limpa canvas e managers
    canvas.delete("all")
    bloco_manager.clear()
    seta_manager.clear()

    # 2) carrega o fluxo do JSON
    blocks, next_map, start_block = load_macro_flow(path)

    # 3) recria blocos, com debug passo‑a‑passo
    id_map = {}
    for bid, blk in blocks.items():
        try:
            # 3a) dados mínimos
            if blk is None:
                raise ValueError("blk é None")
            params = blk.get("params", {})
            name   = params.get("custom_name") or params.get("name") or blk.get("type", "")

            # 3b) criar o bloco no canvas
            bloco = bloco_manager.adicionar_bloco_com_id(
     bid,
     blk.get("type", ""),  # tipo original
     params.get("custom_name") or params.get("name") or blk.get("type", ""),
     params
 )
            if bloco is None:
                raise ValueError("adicionar_bloco_com_id retornou None")
            id_map[bid] = bloco

            # 3c) reposicionar
            # — validações antes de usar []
            if "x" not in blk and "x" not in bloco:
                raise KeyError("nenhum campo 'x' disponível em blk ou bloco")
            x = blk.get("x", bloco["x"])
            y = blk.get("y", bloco["y"])
            w = bloco["width"]   # KeyError se não existir
            h = bloco["height"]
            dx = x - bloco["x"]
            dy = y - bloco["y"]

            # retângulo
            canvas.coords(bloco["rect"], x, y, x + w, y + h)
            # ícone, se existir
            if bloco.get("icon"):
                canvas.coords(bloco["icon"], x, y)
            # handles
            for hid in bloco.get("handles", []):
                canvas.move(hid, dx, dy)
            if bloco.get("true_handle"):
                canvas.move(bloco["true_handle"], dx, dy)
            if bloco.get("false_handle"):
                canvas.move(bloco["false_handle"], dx, dy)
            # label de texto
            if bloco.get("label_id"):
                canvas.coords(
                    bloco["label_id"],
                    x + w/2,
                    y + h + 8
                )
            # atualiza posição interna
            bloco["x"], bloco["y"] = x, y

        except Exception as err:
            # mostra exatamente qual bloco falhou e por quê
            show_error(
                "Erro ao reconstruir bloco", 
                f"ID do bloco: {bid}\nDados brutos: {blk}\n\n{err}"
            )
            # pula este bloco e continua com os demais
            continue
        # ícone, se existir
        if bloco.get("icon"):
            canvas.coords(bloco["icon"], x, y)
        # handles
        for hid in bloco.get("handles", []):
            canvas.move(hid, dx, dy)
        if bloco.get("true_handle"):
            canvas.move(bloco["true_handle"], dx, dy)
        if bloco.get("false_handle"):
            canvas.move(bloco["false_handle"], dx, dy)
        # atualiza posição interna
        bloco["x"], bloco["y"] = x, y

    # 4) reconstrói setas com cor/branch originais
    #    assumimos que 'next_map' não carrega metadata de cor/branch,
    #    então vamos recarregar do JSON bruto:
    import json
    raw = json.load(open(path, encoding="utf-8"))
    for conn in raw.get("connections", []):
        src_id   = conn.get("from")
        tgt_id   = conn.get("to")
        branch   = conn.get("branch")      # True / False / None
        cor      = conn.get("color")       # string ou None
        origem   = id_map.get(src_id)
        destino  = id_map.get(tgt_id)
        if not origem or not destino:
            continue
        # O SetaManager já garante que cor e branch fiquem
        # salvos corretamente no novo dicionário _setas_info.
        seta_manager.desenhar_linha(origem, destino,
                                    branch=branch,
                                    cor_override=cor)

    # 5) centraliza a view no bloco inicial e rebind dos eventos
    try:
        canvas.center_on_block(start_block)
    except Exception:
        pass
    bind_fn()

    # 5) centraliza a view no bloco inicial, se disponível
    try:
        canvas.center_on_block(start_block)
    except Exception:
        pass

    # 6) rebind dos eventos da UI (zoom, pan, cliques, etc.)
    bind_fn()


def obter_caminho_macro_atual():
    if caminho_arquivo_tmp:
        return os.path.dirname(os.path.abspath(caminho_arquivo_tmp))
    return None

def macro_existe():
    return caminho_macro_real and os.path.isfile(caminho_macro_real)
