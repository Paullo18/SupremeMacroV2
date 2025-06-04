# selection_manager.py (novo módulo)
# ---------------------------------------------------
class SelectionManager:
    """
    Gerencia a seleção de itens (blocos e setas) no canvas.
    """
    def __init__(self, canvas, setas_manager):
        self.canvas = canvas
        self.setas_manager = setas_manager
        self.selected_items = []  # lista de IDs selecionados
        # Bind de evento de clique para seleção
        self.canvas.bind('<Button-1>', self._on_click)

    def _on_click(self, event):
        # Detecta item sob o cursor
        item = event.widget.find_closest(event.x, event.y)[0]
        self.clear_selection()
        self.select_item(item)

    def select_item(self, item_id):
        # Adiciona destaque visual (ex: change outline)
        self.selected_items.append(item_id)
        self._highlight(item_id)

    def clear_selection(self):
        # Remove destaque de todos os itens selecionados
        for item in self.selected_items:
            self._unhighlight(item)
        self.selected_items.clear()

    def _highlight(self, item_id):
        # Implementar lógica de destaque (ex: alterar cor de borda)
        pass

    def _unhighlight(self, item_id):
        # Reverte o destaque
        pass