import os
import json
import shutil
from datetime import datetime
from tkinter import messagebox, simpledialog, filedialog
import copy

TMP_DIR = "tmp"
MACROS_DIR = "Macros"

caminho_arquivo_tmp = None  # Caminho do JSON temporário da macro em edição

def criar_macro_temporaria(actions):
    global caminho_arquivo_tmp
    if not os.path.exists(TMP_DIR):
        os.makedirs(TMP_DIR)
    limpar_tmp()
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    caminho_arquivo_tmp = os.path.join(TMP_DIR, f"macro_{timestamp}.json")
    with open(caminho_arquivo_tmp, "w", encoding="utf-8") as f:
        json.dump(actions, f, indent=2)
    return caminho_arquivo_tmp

def salvar_macro_gui(actions):
    print("[DEBUG] Salvando macro com ações:", len(actions))
    print(json.dumps(actions, indent=2))
    global caminho_arquivo_tmp
    if not caminho_arquivo_tmp:
        messagebox.showerror("Erro", "Nenhuma macro em edição.")
        return

    # Verifica se o arquivo já é um macro salvo em disco
    if os.path.isfile(caminho_arquivo_tmp) and os.path.basename(caminho_arquivo_tmp) == "macro.json":
        destino_macro_dir = os.path.dirname(caminho_arquivo_tmp)
        destino_img_dir = os.path.join(destino_macro_dir, "img")
        os.makedirs(destino_img_dir, exist_ok=True)

        for acao in actions:
            if acao.get("type") == "imagem" and "imagem" in acao:
                nome_arquivo = os.path.basename(acao["imagem"])
                origem_tmp = os.path.join(TMP_DIR, nome_arquivo)
                destino = os.path.join(destino_img_dir, nome_arquivo)

                if os.path.exists(origem_tmp):
                    try:
                        shutil.move(origem_tmp, destino)
                        print(f"[INFO] Imagem movida da TMP: {origem_tmp} -> {destino}")
                    except Exception as e:
                        print(f"[ERRO] Falha ao mover imagem da TMP: {e}")
                elif not os.path.exists(destino):
                    print(f"[ERRO] Imagem não encontrada nem na TMP nem no destino: {nome_arquivo}")

                acao["imagem"] = f"img/{nome_arquivo}"

        with open(caminho_arquivo_tmp, "w", encoding="utf-8") as f:
            json.dump(actions, f, indent=2)

        limpar_tmp()
        messagebox.showinfo("Salvo", f"Macro atualizado: {caminho_arquivo_tmp}")
        return

    # Caso contrário, salvar como novo
    nome_macro = simpledialog.askstring("Salvar macro", "Digite o nome da macro:")
    if not nome_macro:
        return

    destino_macro_dir = os.path.join(MACROS_DIR, nome_macro)
    destino_img_dir = os.path.join(destino_macro_dir, "img")
    os.makedirs(destino_img_dir, exist_ok=True)

    actions_salvas = copy.deepcopy(actions)

    for acao in actions_salvas:
        if acao.get("type") == "imagem" and "imagem" in acao:
            nome_arquivo = os.path.basename(acao["imagem"])
            origem_tmp = os.path.join(TMP_DIR, nome_arquivo)
            destino = os.path.join(destino_img_dir, nome_arquivo)

            if os.path.exists(origem_tmp):
                try:
                    shutil.move(origem_tmp, destino)
                    print(f"[INFO] Imagem movida da TMP: {origem_tmp} -> {destino}")
                except Exception as e:
                    print(f"[ERRO] Falha ao mover imagem da TMP: {e}")
            elif not os.path.exists(destino):
                print(f"[ERRO] Imagem não encontrada nem na TMP nem no destino: {nome_arquivo}")

            acao["imagem"] = f"img/{nome_arquivo}"

    with open(os.path.join(destino_macro_dir, "macro.json"), "w", encoding="utf-8") as f:
        json.dump(actions_salvas, f, indent=2)

    caminho_arquivo_tmp = os.path.join(destino_macro_dir, "macro.json")
    limpar_tmp()
    messagebox.showinfo("Salvo", f"Macro salvo em: {destino_macro_dir}")

def limpar_tmp():
    if os.path.exists(TMP_DIR):
        for f in os.listdir(TMP_DIR):
            caminho = os.path.join(TMP_DIR, f)
            if os.path.isfile(caminho):
                os.remove(caminho)

def novo_projeto(update_list, actions):
    resposta = messagebox.askyesnocancel("Novo Projeto", "Deseja salvar a macro atual antes de criar uma nova?")
    if resposta is None:
        return
    elif resposta:
        salvar_macro_gui(actions)

    actions.clear()
    criar_macro_temporaria(actions)
    update_list()

def carregar(update_list, actions):
    global caminho_arquivo_tmp  # ← necessário!

    caminho = filedialog.askopenfilename(
        initialdir=MACROS_DIR,
        title="Abrir macro",
        filetypes=[("macro.json", "macro.json")]
    )
    if caminho:
        try:
            with open(caminho, "r", encoding="utf-8") as f:
                actions.clear()
                actions.extend(json.load(f))
            caminho_arquivo_tmp = caminho  # ← ESSENCIAL!
            update_list()
        except Exception as e:
            messagebox.showerror("Erro ao carregar", str(e))

def obter_caminho_macro_atual():
    if caminho_arquivo_tmp:
        return os.path.dirname(os.path.abspath(caminho_arquivo_tmp))
    return None

