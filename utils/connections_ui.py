# connection_ui.py (novo módulo)
# ---------------------------------------------------
# Gerencia a interação de UI para criar conexões via arraste de handle.
class ConnectionUI:
    """
    Controla o fluxo de interação para criar setas arrastando
    do handle de um bloco até outro.
    """
    def __init__(self, canvas, blocos, setas_manager):
        self.canvas = canvas
        self.blocos = blocos
        self.setas_manager = setas_manager
        self._dragging = False
        self._start_block = None
        self._temp_line = None

        # Bind dos events para handles e movimentação do mouse
        self.canvas.tag_bind('handle', '<ButtonPress-1>', self.iniciar_conexao)
        self.canvas.bind('<Motion>', self._on_drag)
        self.canvas.bind('<ButtonRelease-1>', self._on_release)

    def iniciar_conexao(self, event):
        # Identifica bloco de origem pelo handle clicado
        item = event.widget.find_withtag('current')[0]
        block = self.blocos.get_bloco_por_handle(item)
        if block:
            self._dragging = True
            self._start_block = block
            x, y = event.x, event.y
            self._temp_line = self.canvas.create_line(x, y, x, y, dash=(4, 2))

    def _on_drag(self, event):
        if not self._dragging or not self._temp_line:
            return
        # Atualiza a linha temporária conforme o cursor
        x0, y0, _, _ = self.canvas.coords(self._temp_line)
        self.canvas.coords(self._temp_line, x0, y0, event.x, event.y)

    def _on_release(self, event):
        if not self._dragging:
            return
        # Remove a linha temporária
        self.canvas.delete(self._temp_line)
        self._dragging = False
        # Identifica bloco destino pela posição do mouse
        dest = self.blocos.get_bloco_por_pos(event.x, event.y)
        if dest and dest != self._start_block:
            self.setas_manager.desenhar_linha(self._start_block, dest)
        self._temp_line = None