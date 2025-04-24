import os
import json
import shutil
from datetime import datetime
from tkinter import messagebox, simpledialog

def macro_em_pasta_macros(path_):
    abs_path   = os.path.abspath(path_)
    macros_abs = os.path.abspath(MACROS_DIR)
    return abs_path.endswith(os.sep + "macro.json") and abs_path.startswith(macros_abs + os.sep)

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


# Diretórios base
TMP_DIR = "tmp"
MACROS_DIR = "Macros"

# Caminho do JSON temporário da macro em edição
caminho_arquivo_tmp = None

# Caminhos atuais
caminho_arquivo_tmp   = None      # sempre muda: último JSON salvo em tmp/
caminho_macro_real    = None      # fica fixo: .../Macros/<nome>/macro.json

# ============================================================
# Exporta estado (blocos + setas) para um JSON em tmp/
# ============================================================

def export_macro_to_tmp(blocks, arrows, macro_name=None):
    """Gera um arquivo JSON em `tmp/` com o estado atual do fluxo.

    *blocks* – lista de blocos (dicts gerados pelo BlocoManager)
    *arrows* – lista de tuplas (origem, destino, branch?, cor?)
    """
    global caminho_arquivo_tmp

    os.makedirs(TMP_DIR, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    caminho_arquivo_tmp = os.path.join(TMP_DIR, f"macro_{ts}.json")

    data = {
        "macro_name": macro_name,
        "blocks": [],
        "connections": []
    }

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
            origem, destino, branch, cor = item
        elif len(item) == 3:
            origem, destino, branch = item; cor = None
        else:
            origem, destino = item; branch = cor = None
        data["connections"].append({
            "from": origem["id"],
            "to": destino["id"],
            "branch": branch,
            "color": cor
        })

    with open(caminho_arquivo_tmp, "w", encoding="utf-8") as fp:
        json.dump(data, fp, ensure_ascii=False, indent=2)
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
        messagebox.showerror("Salvar", f"Erro ao sobrescrever macro:\n{exc}")
        return False
    return True


def salvar_macro_gui():
    """Comporta‑se assim:
    1. Se `caminho_arquivo_tmp` é um arquivo *já* dentro de `Macros/<nome>/macro.json`,
       apenas sobrescreve esse arquivo.
    2. Caso contrário, pergunta o nome da macro (se ainda não houver) e
       move o JSON + imagens para a pasta `Macros/<nome>/`.
    """
    global caminho_arquivo_tmp

    # ---------------- caso 1: já é uma macro existente ----------------
    if caminho_arquivo_tmp and macro_em_pasta_macros(caminho_arquivo_tmp):

        # se houver um JSON mais recente em tmp/ usa‑o; senão o próprio arquivo
        json_tmp = caminho_arquivo_tmp
        tmp_files = [os.path.join(TMP_DIR, f) for f in os.listdir(TMP_DIR) if f.endswith('.json')]
        if tmp_files:
            json_tmp = max(tmp_files, key=os.path.getmtime)

        if _sobrescrever_macro(json_tmp, caminho_arquivo_tmp):
            limpar_tmp()
            messagebox.showinfo("Salvo", f"Macro atualizada em:\n{caminho_arquivo_tmp}")
        return caminho_arquivo_tmp

    # ---------------- caso 2: macro nova ------------------------------
    if not caminho_arquivo_tmp or not os.path.isfile(caminho_arquivo_tmp):
        messagebox.showerror("Erro", "Nenhuma macro para salvar. Primeiro exporte a macro.")
        return

    # carrega dados para obter nome e identificar imagens
    with open(caminho_arquivo_tmp, "r", encoding="utf-8") as f:
        data = json.load(f)
        

    nome = data.get("macro_name")
    if not nome:
        nome = simpledialog.askstring("Salvar macro", "Digite o nome da macro:")
        if not nome:
            return
        data["macro_name"] = nome

    destino_dir = os.path.join(MACROS_DIR, nome)
    destino_img_dir = os.path.join(destino_dir, "img")
    os.makedirs(destino_img_dir, exist_ok=True)

    # move imagens referenciadas
    for b in data.get("blocks", []):
        p = b.get("params", {})
        if p.get("type") == "imagem" and p.get("imagem"):
            img_name = os.path.basename(p["imagem"])
            tmp_img  = os.path.join(TMP_DIR, img_name)
            dest_img = os.path.join(destino_img_dir, img_name)
            if os.path.exists(tmp_img):
                shutil.move(tmp_img, dest_img)
            elif not os.path.exists(dest_img):
                print(f"[Aviso] Imagem não encontrada: {img_name}")
            p["imagem"] = os.path.join("img", img_name)

    # grava macro.json
    final_path = os.path.join(destino_dir, "macro.json")
    limpar_tmp()
    caminho_arquivo_tmp = final_path
    caminho_macro_real  = final_path      # <<< NOVO
    messagebox.showinfo("Salvo", f"Macro salva em: {final_path}")
    os.makedirs(destino_dir, exist_ok=True)
    with open(final_path, "w", encoding="utf-8") as fo:
        json.dump(data, fo, ensure_ascii=False, indent=2)

    limpar_tmp()
    caminho_arquivo_tmp = final_path
    messagebox.showinfo("Salvo", f"Macro salva em: {final_path}")
    return final_path

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


def obter_caminho_macro_atual():
    if caminho_arquivo_tmp:
        return os.path.dirname(os.path.abspath(caminho_arquivo_tmp))
    return None

def macro_existe():
    return caminho_macro_real and os.path.isfile(caminho_macro_real)
