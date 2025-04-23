import os
import shutil
import json
from datetime import datetime

TMP_DIR = "tmp"
MACROS_DIR = "Macros"

def criar_macro_temporaria(actions):
    """Cria um arquivo JSON temporário com as ações da macro."""
    os.makedirs(TMP_DIR, exist_ok=True)
    limpar_tmp()
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    caminho_json = os.path.join(TMP_DIR, f"macro_{timestamp}.json")
    with open(caminho_json, "w", encoding="utf-8") as f:
        json.dump(actions, f, indent=4)
    return caminho_json

def salvar_macro(nome_macro, caminho_arquivo_tmp):
    """Move o JSON e as imagens da pasta tmp para a estrutura definitiva em Macros/nome_macro."""
    # Criar pasta da macro e img
    destino_macro_dir = os.path.join(MACROS_DIR, nome_macro)
    destino_img_dir = os.path.join(destino_macro_dir, "img")
    os.makedirs(destino_img_dir, exist_ok=True)

    # Carregar JSON temporário
    with open(caminho_arquivo_tmp, "r", encoding="utf-8") as f:
        actions = json.load(f)

    # Atualizar caminhos de imagem e mover imagens
    for acao in actions:
        if acao.get("type") == "imagem" and "imagem" in acao:
            nome_arquivo = os.path.basename(acao["imagem"])
            origem = os.path.join(TMP_DIR, nome_arquivo)
            destino = os.path.join(destino_img_dir, nome_arquivo)
            if os.path.exists(origem):
                shutil.move(origem, destino)
                acao["imagem"] = f"img/{nome_arquivo}"

    # Salvar JSON definitivo
    caminho_final = os.path.join(destino_macro_dir, "macro.json")
    with open(caminho_final, "w", encoding="utf-8") as f:
        json.dump(actions, f, indent=4)

    # Limpar tmp
    limpar_tmp()

def limpar_tmp():
    """Remove todos os arquivos da pasta tmp."""
    if os.path.exists(TMP_DIR):
        for nome_arquivo in os.listdir(TMP_DIR):
            caminho = os.path.join(TMP_DIR, nome_arquivo)
            if os.path.isfile(caminho):
                os.remove(caminho)
