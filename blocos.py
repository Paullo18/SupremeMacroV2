from PIL import Image, ImageTk
import os
import tkinter as tk

class BlocoManager:
    def __init__(self, canvas, app):
        self.canvas = canvas
        self.app = app
        self.blocks = []
        self.ocupados = set()
        self.block_width = 112
        self.block_height = 40
        self.margem_topo = 20
        self.espaco_vertical = 20

        # estado de arrasto
        self.arrastando = None
        self.offset_x = 0
        self.offset_y = 0

        # --- seleção por arrasto ---
        self.selecao_iniciada = False
        self.sel_start_x = 0
        self.sel_start_y = 0
        self.sel_rect_id = None

        # destaque de seleção única
        self.borda_selecionada = None

        # para futura seleção múltipla (mesmo que ainda não seja usada)
        self.blocos_selecionados = []

        # cache de imagens para evitar GC
        self.imagens = {}

        # ▼ pilhas de desfazer/refazer
        self._undo_stack = []
        self._redo_stack = []
        # ▼ usado para arrastar grupo
        self._drag_group = None   # lista de blocos movidos juntos

        self._is_restoring = False   # evita snapshots enquanto restaura

        self._has_moved = False

    def finalizar_arrasto(self, event):

         # rotina já existente
        if self.arrastando:
            self.arrastando = None
        elif self.selecao_iniciada:
            self.finalizar_selecao_area(event)
        self._drag_group = None


    def encontrar_proxima_posicao(self):
        x = 20
        y = self.margem_topo
        while True:
            if all(bloco["x"] != x or bloco["y"] != y for bloco in self.blocks):
                return x, y
            y += self.block_height + self.espaco_vertical

    def adicionar_bloco(self, nome, cor):
        # só registra snapshot se NÃO estiver restaurando
        if not self._is_restoring:
            self._undo_stack.append(self._snapshot())
            self._redo_stack.clear()

        x, y = self.encontrar_proxima_posicao()
        self.ocupados.add((x, y))

        # retângulo invisível para clique
        rect = self.canvas.create_rectangle(
            x, y, x + self.block_width, y + self.block_height,
            outline="", fill=""
        )

        # ícone
        nome_arquivo = self._mapear_nome_para_icone(nome)
        caminho_icone = os.path.join("icons", nome_arquivo)
        if os.path.exists(caminho_icone):
            img = Image.open(caminho_icone).resize(
                (self.block_width, self.block_height),
                Image.Resampling.LANCZOS
            )
            tk_img = ImageTk.PhotoImage(img)
            self.imagens[nome + str(len(self.blocks))] = tk_img
            icon = self.canvas.create_image(x, y, anchor="nw", image=tk_img)
        else:
            icon = None

        bloco = {
            "rect": rect,
            "icon": icon,
            "x": x,
            "y": y,
            "width": self.block_width,
            "height": self.block_height,
            "text": nome
        }
        
        if icon is not None:                                   #  ← nova
            self.canvas.tag_bind(icon, "<Enter>",              #  ← nova
                                 lambda e, b=bloco: self._show_handles(b))  #  ← nova
            self.canvas.tag_bind(icon, "<Leave>",
                                 lambda e, b=bloco: self._hide_handles(b))
        # --- pequenos "+" que só aparecem no hover --------------------------
        size = 10      # Largura/altura do quadradinho
        half = size // 2
        cx, cy = x + self.block_width // 2, y + self.block_height // 2
        # coordenadas dos 4 lados
        pontos = [
            (cx, y - half),                      # topo
            (cx, y + self.block_height - half), # base
            (x - half, cy),                      # esquerda
            (x + self.block_width - half, cy)    # direita
        ]

        group_tag = f"bloco{len(self.blocks)}"
        self.canvas.addtag_withtag(group_tag, rect)          # retângulo base
        if icon is not None:
            self.canvas.addtag_withtag(group_tag, icon)      # imagem
        # “handles” (⊕) são criados logo abaixo; vamos guardar suas IDs
        handles = []
        for hx, hy in pontos:
            h = self.canvas.create_text(hx, hy, text="⊕", fill="#0a84ff",
                                         state="hidden", font=("Arial", 10, "bold"))
            handles.append(h)
            self.canvas.addtag_withtag("handle", h)
            self.canvas.tag_bind(h, "<ButtonPress-1>",
                                 lambda e, b=bloco: self._handle_press(b, e))
            self.canvas.addtag_withtag(group_tag, h)

        bloco["handles"] = handles

        self.canvas.tag_bind(group_tag, "<Enter>",
                         lambda e, b=bloco: self._show_handles(b))
        self.canvas.tag_bind(group_tag, "<Leave>",
                         lambda e, b=bloco: self._hide_handles(b))
    
        self.blocks.append(bloco)
        return bloco

    def _handle_press(self, bloco, event):
        """Clique no ⊕ inicia a conexão e impede arrasto do bloco."""
        # garante que nenhum bloco entre em modo de arrasto
        self.arrastando = None
        self.app.setas.iniciar_conexao(bloco, event)
        return "break"
        

    def _mapear_nome_para_icone(self, nome):
        mapa = {
            "clique": "click_icon.png",
            "texto": "text_icon.png",
            "delay": "delay_icon.png",
            "label": "label_icon.png",
            "goto": "goto_icon.png",
            "ocr": "ocr_icon.png",
            "ocr duplo": "doubleocr_icon.png",
            "se imagem": "ifimage_icon.png",
            "loop": "loop_icon.png",
            "fim loop": "endloop_icon.png",
            "sair loop": "exit_loop.png",
            "fim se": "endif_icon.png",
            "se nao": "else_icon.png"
        }
        return mapa.get(nome.strip().lower(), "default.png")

    def canvas_clique(self, event):
        if getattr(self.app.setas, "handle_drag", None):
            return "break"
        item_atual = self.canvas.find_withtag("current")
        if item_atual and "handle" in self.canvas.gettags(item_atual[0]):
            return "break"          # ignora completamente cliques sobre ⊕
        x, y = self.canvas.canvasx(event.x), self.canvas.canvasy(event.y)
        ctrl = event.state & 0x0004 
        
        self.arrastando = None

        # teste de clique em blocos
        for bloco in self.blocks:
            x1, y1, x2, y2 = self.canvas.coords(bloco["rect"])
            if x1 <= x <= x2 and y1 <= y <= y2:
                # ---------- inicia arrasto ----------
                self.arrastando = bloco
                self._has_moved = False
                self.offset_x = x - bloco["x"]
                self.offset_y = y - bloco["y"]

                # garante que a borda do bloco permaneça
                if not bloco.get("borda"):
                    bloco["borda"] = self.canvas.create_rectangle(
                        bloco["x"] - 2, bloco["y"] - 2,
                        bloco["x"] + bloco["width"] + 2,
                        bloco["y"] + bloco["height"] + 2,
                        outline="blue", width=2, dash=(4, 2)
                    )
                    self.canvas.tag_lower(bloco["borda"], bloco["rect"])
                self.borda_selecionada = bloco["borda"]

                # monta grupo a arrastar
                if ("bloco", bloco) not in self.app.itens_selecionados:
                    if not ctrl:          # clique normal → seleção única
                        self.app.setas.limpar_selecao()
                        self.app.itens_selecionados = [("bloco", bloco)]
                    else:                 # Ctrl-click adiciona
                        self.app.itens_selecionados.append(("bloco", bloco))

                self._drag_group = [b for t, b in self.app.itens_selecionados if t == "bloco"]

                return "break"   # impede que o clique caia no SetaManager
            
            # 2) Clique em área vazia → inicia retângulo de seleção
        if self.borda_selecionada:
            self.canvas.delete(self.borda_selecionada)
            self.borda_selecionada = None

        self.selecao_iniciada = True
        self.sel_start_x, self.sel_start_y = x, y
        self.sel_rect_id = self.canvas.create_rectangle(
            x, y, x, y, outline="blue", dash=(2, 2)
        )
        self.app.setas.limpar_selecao()
        return "break"
            

        # clique fora de qualquer bloco → inicia seleção por área
        self.selecao_iniciada = True
        self.sel_start_x, self.sel_start_y = x, y
        # retângulo de seleção visível
        self.sel_rect_id = self.canvas.create_rectangle(
            x, y, x, y, outline="blue", dash=(2, 2)
        )
        # limpa seleção anterior (usa o helper que já existe no SetaManager)
        self.app.setas._limpar_selecao()
        return "break"

    def mover_bloco(self, event):
        if getattr(self.app.setas, "handle_drag", None):
            return
        if self.selecao_iniciada:
            self.atualizar_selecao_area(event)
            return
        if not self.arrastando:
            return
        
        if not self._has_moved and not self._is_restoring:
            self._undo_stack.append(self._snapshot())
            self._redo_stack.clear()
            self._has_moved = True

        x = self.canvas.canvasx(event.x)
        y = self.canvas.canvasy(event.y)
        new_x = x - self.offset_x
        new_y = y - self.offset_y
        dx = new_x - self.arrastando["x"]
        dy = new_y - self.arrastando["y"]

        alvos = self._drag_group if self._drag_group else [self.arrastando]
        for bloco in alvos:
            bx1 = bloco["x"] + dx
            by1 = bloco["y"] + dy
            bx2 = bx1 + bloco["width"]
            by2 = by1 + bloco["height"]

            self.canvas.coords(bloco["rect"], bx1, by1, bx2, by2)
            if bloco.get("icon"):
                self.canvas.coords(bloco["icon"], bx1, by1)
            if bloco.get("borda"):
                self.canvas.coords(bloco["borda"],
                                   bx1-2, by1-2, bx2+2, by2+2)
            bloco["x"], bloco["y"] = bx1, by1
            self._recolocar_handles(bloco)


        # atualiza setas 1× (não precisa por bloco)
        self.app.setas.atualizar_setas()
    
    def atualizar_selecao_area(self, event):
        if not self.selecao_iniciada:
            return
        x = self.canvas.canvasx(event.x)
        y = self.canvas.canvasy(event.y)
        self.canvas.coords(self.sel_rect_id,
                           self.sel_start_x, self.sel_start_y, x, y)

    def finalizar_selecao_area(self, event):
        # só executa se realmente havia seleção ativa
        if not self.selecao_iniciada:
            return

        # normaliza coordenadas do retângulo
        x1, y1, x2, y2 = self.canvas.coords(self.sel_rect_id)
        if x2 < x1:
            x1, x2 = x2, x1
        if y2 < y1:
            y1, y2 = y2, y1

        # percorre todos os blocos e seleciona os totalmente contidos
        for bloco in self.blocks:
            bx1, by1, bx2, by2 = self.canvas.coords(bloco["rect"])
            if bx1 >= x1 and by1 >= y1 and bx2 <= x2 and by2 <= y2:
                borda = self.canvas.create_rectangle(
                    bx1-2, by1-2, bx2+2, by2+2,
                    outline="blue", width=2, dash=(4, 2)
                )
                self.canvas.tag_lower(borda, bloco["rect"])
                bloco["borda"] = borda
                self.app.itens_selecionados.append(("bloco", bloco))

        # remove o retângulo de seleção e reseta flags
        self.canvas.delete(self.sel_rect_id)
        self.sel_rect_id = None
        self.selecao_iniciada = False
        return "break"

    #  (A) utilitário: snapshot p/ ‘undo’
    def _snapshot(self):
        estado_blocos = [
            (b["text"], b["x"], b["y"]) for b in self.blocks
        ]
        estado_setas = [
            (self.blocks.index(o), self.blocks.index(d))  # índices
            for _, o, d in self.app.setas.setas
        ]
        return (estado_blocos, estado_setas)

    def _restaurar_snapshot(self, snap):
        self._is_restoring = True          # ↓↓↓     evita pushes internos

        blocos_info, setas_info = snap

        # --- limpa canvas atual ---
        for bloco in list(self.blocks):    # cópia para não alterar enquanto itera
            # bloco base
            self.canvas.delete(bloco["rect"])
            # ícone, borda e TODOS os handles (+)
            if bloco.get("icon"):
                self.canvas.delete(bloco["icon"])
            if bloco.get("borda"):
                self.canvas.delete(bloco["borda"])
            for h in bloco.get("handles", []):
                self.canvas.delete(h)

        self.blocks.clear()
        self.ocupados.clear()

        # setas existentes
        for seta_id, *_ in self.app.setas.setas:
            self.canvas.delete(seta_id)
        self.app.setas.setas.clear()

        # --- recria blocos ---
        for text, x, y in blocos_info:
            novo = self.adicionar_bloco(text, "white")   # não empilha snapshot
            self.canvas.coords(novo["rect"], x, y,
                               x+novo["width"], y+novo["height"])
            if novo.get("icon"):
                self.canvas.coords(novo["icon"], x, y)
            novo["x"], novo["y"] = x, y

        # --- recria setas ---
        for idx_o, idx_d in setas_info:
            self.app.setas.desenhar_linha(self.blocks[idx_o],
                                          self.blocks[idx_d])

        self._is_restoring = False          # ↑↑↑     restaura comportamento normal


    
    # -----------------------------------------------------------
    #  (B) atalhos públicos chamados por eventos.py
    def selecionar_todos(self, event=None):
        self.app.setas._limpar_selecao()
        for bloco in self.blocks:
            bx1, by1, bx2, by2 = self.canvas.coords(bloco["rect"])
            borda = self.canvas.create_rectangle(
                bx1-2, by1-2, bx2+2, by2+2,
                outline="blue", width=2, dash=(4, 2)
            )
            self.canvas.tag_lower(borda, bloco["rect"])
            bloco["borda"] = borda
            self.app.itens_selecionados.append(("bloco", bloco))

    def deletar_selecionados(self, event=None):
        if not self.app.itens_selecionados:
            return
        self._undo_stack.append(self._snapshot());  self._redo_stack.clear()
        for tipo, item in list(self.app.itens_selecionados):
            if tipo == "bloco":
                self.app.setas.remover_setas_de_bloco(item)
                self.canvas.delete(item["rect"])
                if item.get("icon"):
                    self.canvas.delete(item["icon"])
                if item.get("borda"):
                    self.canvas.delete(item["borda"])
                for h in item.get("handles", []):
                    self.canvas.delete(h)
                self.blocks.remove(item)
            elif tipo == "seta":
                self.app.setas.deletar_seta_por_id(item)
        self.app.itens_selecionados.clear()

    def recortar_selecionados(self, event=None):
        """Ctrl+X – coloca os blocos selecionados no clipboard e os remove."""
        # 1 – pega todos os blocos atualmente selecionados
        blocos = [b for t, b in self.app.itens_selecionados if t == "bloco"]
        if not blocos:
            return

        # 2 – gera dados relativos (mesma lógica de copiar)
        min_x = min(b["x"] for b in blocos)
        min_y = min(b["y"] for b in blocos)
        BlocoManager._clipboard = [
            (b["text"], b["x"] - min_x, b["y"] - min_y) for b in blocos
        ]

        # 3 – remove realmente os itens  (isso já grava snapshot para undo)
        self.deletar_selecionados()


    def desfazer(self, event=None):
        if not self._undo_stack:
            return
        self._redo_stack.append(self._snapshot())
        snap = self._undo_stack.pop()
        self._restaurar_snapshot(snap)

    def refazer(self, event=None):
        if not self._redo_stack:
            return
        self._undo_stack.append(self._snapshot())
        snap = self._redo_stack.pop()
        self._restaurar_snapshot(snap)
        # === clipboard simples (texto + deslocamento) =========================
    _clipboard = None   # [(text, dx, dy), ...]

    def copiar_selecionados(self, event=None):
        blocos = [b for t, b in self.app.itens_selecionados if t == "bloco"]
        if not blocos:
            return
        # origem relativa (canto superior-esquerdo)
        min_x = min(b["x"] for b in blocos)
        min_y = min(b["y"] for b in blocos)
        BlocoManager._clipboard = [
            (b["text"], b["x"] - min_x, b["y"] - min_y) for b in blocos
        ]

    def colar_selecionados(self, event=None):
        if not BlocoManager._clipboard:
            return
        self._undo_stack.append(self._snapshot()); self._redo_stack.clear()

        # ponto base levemente deslocado para não sobrepor original
        base_x, base_y = self.encontrar_proxima_posicao()
        base_x += 20
        base_y += 20

        self.app.setas._limpar_selecao()
        for text, dx, dy in BlocoManager._clipboard:
            novo = self.adicionar_bloco(text, "white")
            # reposiciona
            x = base_x + dx
            y = base_y + dy
            self.canvas.coords(novo["rect"], x, y,
                               x+novo["width"], y+novo["height"])
            if novo.get("icon"):
                self.canvas.coords(novo["icon"], x, y)
            novo["x"], novo["y"] = x, y
            # borda de seleção
            borda = self.canvas.create_rectangle(
                x-2, y-2, x+novo["width"]+2, y+novo["height"]+2,
                outline="blue", width=2, dash=(4, 2)
            )
            self.canvas.tag_lower(borda, novo["rect"])
            novo["borda"] = borda
            self.app.itens_selecionados.append(("bloco", novo))

    def _show_handles(self, bloco):
        self._recolocar_handles(bloco)
        for h in bloco.get("handles", []):
            try:
                self.canvas.itemconfigure(h, state="normal")
            except tk.TclError:
                pass          # handle já foi destruído

    def _hide_handles(self, bloco):
        for h in bloco.get("handles", []):
            try:
                self.canvas.itemconfigure(h, state="hidden")
            except tk.TclError:
                pass

    def _recolocar_handles(self, bloco):
        """Reposiciona os ⊕ de acordo com a posição atual do bloco."""
        if not bloco.get("handles"):
            return
        size  = 10
        half  = size // 2
        x1, y1, x2, y2 = self.canvas.coords(bloco["rect"])
        cx  = (x1 + x2) / 2
        cy  = (y1 + y2) / 2
        novos = [
            (cx,        y1 - half),   # topo
            (cx,        y2 - half),   # base
            (x1 - half, cy),          # esquerda
            (x2 - half, cy)           # direita
        ]
        for h, (hx, hy) in zip(bloco["handles"], novos):
            self.canvas.coords(h, hx, hy)