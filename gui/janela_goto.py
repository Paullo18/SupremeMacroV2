from tkinter import simpledialog

def add_goto(actions, update_list, tela):
    """
    Pergunta ao usuário o nome do label e insere direto em actions,
    disparando update_list() para desenhar o label no canvas.
    """
    nome = simpledialog.askstring("GOTO", "Ir para qual Label?", parent=tela)
    if nome:
        actions.append({"type": "goto", "label": nome})
        update_list()