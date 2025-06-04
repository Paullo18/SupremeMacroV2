from tkinter import simpledialog
from core.inserir import inserir_acao  # Caminho correto

def add_label(actions, update_list, tela, initial=None):
    """
    Cria/edita um bloco Label.
    - initial: dict opcional com {'name': ...} já salvo no bloco.
    """
    current = (initial or {}).get("name", "")
    nome = simpledialog.askstring(
        "Label", "Digite o nome da Label:",
        parent=tela,
        initialvalue=current           # ← pré-preenche
    )
    if nome is None:          # usuário cancelou
        return

    actions.clear()           # substitui eventual valor antigo
    actions.append({"type": "label", "name": nome})
    update_list()
