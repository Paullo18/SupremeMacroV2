import os
import json
import shutil
from datetime import datetime
from tkinter import messagebox, simpledialog

# Diretórios base
TMP_DIR = "tmp"
MACROS_DIR = "Macros"

# Caminho do JSON temporário da macro em edição
caminho_arquivo_tmp = None


def export_macro_to_tmp(blocks, arrows, macro_name=None):
    """
    Serializa blocos e conexões (setas) no formato:
    {
      "macro_name": <nome>,
      "blocks": [{"id":..., "type":..., "params":..., "x":..., "y":...}, ...],
      "connections": [{"from":id_origem, "to":id_destino}, ...]
    }
    e salva em TMP_DIR / "macro_<timestamp>.json".
    """
    global caminho_arquivo_tmp
    os.makedirs(TMP_DIR, exist_ok=True)
    # nome do arquivo temporário
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"macro_{timestamp}.json"
    caminho_arquivo_tmp = os.path.join(TMP_DIR, filename)

    data = {
        "macro_name": macro_name,
        "blocks": [],
        "connections": []
    }
    # serializa blocos
    for bloco in blocks:
        data["blocks"].append({
            "id": bloco["id"],
            "type": bloco["text"],
            "params": bloco.get("acao", {}),
            "x": bloco["x"],
            "y": bloco["y"]
        })
    # serializa conexões
    for _, origem, destino in arrows:
        data["connections"].append({
            "from": origem["id"],
            "to": destino["id"]
        })
    # grava JSON temporário
    with open(caminho_arquivo_tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    return caminho_arquivo_tmp


def salvar_macro_gui():
    """
    Move o JSON e imagens de TMP_DIR para MACROS_DIR/<macro_name>/
    Pergunta nome da macro se ainda não existir.
    """
    global caminho_arquivo_tmp
    if not caminho_arquivo_tmp or not os.path.isfile(caminho_arquivo_tmp):
        messagebox.showerror("Erro", "Nenhuma macro para salvar. Primeiro exporte a macro.")
        return

    # carrega dados para obter nome e identificar imagens
    with open(caminho_arquivo_tmp, "r", encoding="utf-8") as f:
        data = json.load(f)

    nome = data.get("macro_name")
    # se não há nome definido, solicita
    if not nome:
        nome = simpledialog.askstring("Salvar macro", "Digite o nome da macro:")
        if not nome:
            return

    # define pastas de destino
    destino_dir = os.path.join(MACROS_DIR, nome)
    destino_img_dir = os.path.join(destino_dir, "img")
    os.makedirs(destino_img_dir, exist_ok=True)

    # move imagens referenciadas em params
    for bloco in data.get("blocks", []):
        params = bloco.get("params", {})
        if params.get("type") == "imagem" and params.get("imagem"):
            img_name = os.path.basename(params["imagem"])
            tmp_img = os.path.join(TMP_DIR, img_name)
            dest_img = os.path.join(destino_img_dir, img_name)
            if os.path.exists(tmp_img):
                shutil.move(tmp_img, dest_img)
            elif not os.path.exists(dest_img):
                print(f"[Aviso] Imagem não encontrada: {img_name}")
            # atualiza caminho no JSON
            params["imagem"] = os.path.join("img", img_name)

    # salva JSON final em destino_dir/macro.json
    final_path = os.path.join(destino_dir, "macro.json")
    with open(final_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    # limpa tmp
    limpar_tmp()

    caminho_arquivo_tmp = final_path
    messagebox.showinfo("Salvo", f"Macro salva em: {final_path}")
    return final_path


def limpar_tmp():
    """
    Remove todos os arquivos em TMP_DIR.
    """
    if os.path.isdir(TMP_DIR):
        for f in os.listdir(TMP_DIR):
            caminho = os.path.join(TMP_DIR, f)
            try:
                if os.path.isfile(caminho):
                    os.remove(caminho)
                elif os.path.isdir(caminho):
                    shutil.rmtree(caminho)
            except Exception:
                pass


def obter_caminho_macro_atual():
    """
    Retorna o diretório da última macro salva (ou None).
    """
    if caminho_arquivo_tmp:
        return os.path.dirname(os.path.abspath(caminho_arquivo_tmp))
    return None
