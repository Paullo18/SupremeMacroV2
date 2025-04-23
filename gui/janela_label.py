from tkinter import simpledialog
from core.inserir import inserir_acao  # Caminho correto

def add_label(actions, update_list, tela):
    nome = simpledialog.askstring("Label", "Digite o nome da Label:", parent=tela)
    if nome:
        # grava no buffer e dispara callback
        actions.append({"type": "label", "name": nome})
        update_list()