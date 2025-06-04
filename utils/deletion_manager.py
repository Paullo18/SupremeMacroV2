# deletion_manager.py (novo módulo)
# ---------------------------------------------------
class DeletionManager:
    """
    Gerencia deleção de itens selecionados usando tecla Delete.
    """
    def __init__(self, canvas, selection_manager, setas_manager):
        self.canvas = canvas
        self.selection_manager = selection_manager
        self.setas_manager = setas_manager
        self.canvas.bind_all('<Delete>', self._on_delete)

    def _on_delete(self, event):
        for item in list(self.selection_manager.selected_items):
            # Deleta do canvas
            self.canvas.delete(item)
            # Remove conexões associadas
            self.setas_manager.deletar_seta_por_id(item)
        self.selection_manager.clear_selection()