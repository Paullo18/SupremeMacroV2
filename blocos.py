from PIL import Image, ImageTk
import os
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from gui.janela_clique import add_click
from gui.janela_delay import add_delay
from gui.janela_goto import add_goto
from gui.janela_imagem import add_imagem
from gui.janela_label import add_label
from gui.janela_loop import add_loop
from gui.janela_ocr import add_ocr
from gui.janela_ocr_duplo import add_ocr_duplo
from gui.janela_texto import add_texto
from gui.screenshot_janela import add_screenshot
from gui.fork_janela import abrir_fork_dialog
from core.update_list import update_list
import threading, time, pyautogui, keyboard
from tkinter import Toplevel, IntVar, Label, Entry, simpledialog
import pytesseract


class BlocoManager:
    _next_id = 1      # contador de IDs
    def __init__(self, canvas, app):
        self.canvas = canvas
        self.app = app
        # capta duplo‐clique geral no canvas
        self.canvas.bind("<Double-Button-1>", self._on_canvas_double_click, add="+")

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
        # --------------------------------------------------
        # 0) utilidades
        # --------------------------------------------------
        zoom = getattr(self.app, "_zoom_scale", 1.0)        # fator global
        def z(v: float) -> int:                             # arredonda já escalado
            return int(round(v * zoom))

        # --------------------------------------------------
        # 1) gera ID e snapshot p/ undo
        # --------------------------------------------------
        bloco_id = BlocoManager._next_id
        BlocoManager._next_id += 1
        if not self._is_restoring:
            self._undo_stack.append(self._snapshot())
            self._redo_stack.clear()

        # --------------------------------------------------
        # 2) coordenadas (já aplicando zoom)
        # --------------------------------------------------
        x0, y0 = self.encontrar_proxima_posicao()
        x,  y  = z(x0), z(y0)
        self.ocupados.add((x0, y0))     # usa as posições “lógicas”

        # --------------------------------------------------
        # 3) retângulo base
        # --------------------------------------------------
        w0, h0 = self.block_width, self.block_height
        rect = self.canvas.create_rectangle(
            x, y, x + z(w0), y + z(h0),
            outline="", fill=""
        )

        # --------------------------------------------------
        # 4) ícone
        # --------------------------------------------------
        caminho_icone = os.path.join("icons", self._mapear_nome_para_icone(nome))
        if os.path.exists(caminho_icone):
            pil_icon = Image.open(caminho_icone)          # PIL.Image 1×
            tk_size  = (z(self.block_width), z(self.block_height))
            tk_img   = ImageTk.PhotoImage(pil_icon.resize(tk_size, Image.LANCZOS))
            icon = self.canvas.create_image(x, y, anchor="nw", image=tk_img)
            bloco_icon_data = {
                "_pil_orig":   pil_icon.copy(),
                "_icon_scale": self.app._zoom_scale,
                "_icon_ref":   tk_img,
            }
        else:
            icon = None
            bloco_icon_data = {}

        # --------------------------------------------------
        # 5) dicionário do bloco
        # --------------------------------------------------
        pil_base = pil_icon.resize((self.block_width, self.block_height), Image.LANCZOS)
        # define ação para Start/End Thread
        acao = {}
        lt = nome.strip().lower()
        if lt == "start thread":
            acao = {"type":"startthread"}
        elif lt == "end thread":
            acao = {"type":"endthread"}
        bloco = {
            "id": bloco_id,
            "rect": rect,
            "icon": icon,
            "x": x, "y": y,
            "width": self.block_width,
            "height": self.block_height,
            "text": nome,
            "acao": acao,
            "_pil_orig":   pil_base,
            "_icon_scale": self.app._zoom_scale,
            "_icon_ref":   tk_img,
        }

        # --------------------------------------------------
        # 6) tag de grupo p/ mover tudo junto
        # --------------------------------------------------
        group_tag = f"bloco{len(self.blocks)}"
        self.canvas.addtag_withtag(group_tag, rect)
        if icon:
            self.canvas.addtag_withtag(group_tag, icon)
        bloco["group_tag"] = group_tag

        # --------------------------------------------------
        # 7) IF-blocks ou handles “⊕”
        # --------------------------------------------------
        lt = nome.strip().lower()
        if lt in ("se imagem", "ocr", "ocr duplo"):
            cx = x + z(w0) / 2
            r  = z(5)

            h_true = self.canvas.create_oval(
                cx - r, y - 2*r, cx + r, y,
                fill="green", outline=""
            )
            h_false = self.canvas.create_oval(
                cx - r, y + z(h0),
                cx + r, y + z(h0) + 2*r,
                fill="red", outline=""
            )
            bloco["true_handle"]  = h_true
            bloco["false_handle"] = h_false

            self.canvas.addtag_withtag(group_tag, h_true)
            self.canvas.addtag_withtag(group_tag, h_false)

            self.canvas.tag_bind(
                h_true, "<ButtonPress-1>",
                lambda e, b=bloco: self._handle_press_if(b, e, branch="true"))
            self.canvas.tag_bind(
                h_false, "<ButtonPress-1>",
                lambda e, b=bloco: self._handle_press_if(b, e, branch="false"))
        else:
            size = z(10); half = size // 2
            cx = x + z(w0)//2
            cy = y + z(h0)//2
            pontos = [
                (cx, y-half),
                (cx, y + z(h0) + half),
                (x-half, cy),
                (x + z(w0) + half, cy)
            ]
            handles = []
            for hx, hy in pontos:
                h = self.canvas.create_text(
                    hx, hy, text="⊕",
                    fill="#0a84ff",
                    state="hidden",
                    font=("Arial", max(6, int(10*zoom)), "bold"),
                    tags=("fs:10",)          # base font-size
                )
                handles.append(h)
                self.canvas.addtag_withtag("handle", h)
                self.canvas.addtag_withtag(group_tag, h)
                self.canvas.tag_bind(
                    h, "<ButtonPress-1>",
                    lambda e, b=bloco: self._handle_press(b, e))
            bloco["handles"] = handles

            self.canvas.tag_bind(group_tag, "<Enter>",
                                 lambda e, b=bloco: self._show_handles(b))
            self.canvas.tag_bind(group_tag, "<Leave>",
                                 lambda e, b=bloco: self._hide_handles(b))

        # --------------------------------------------------
        # 8) binds de duplo-clique (inalterados)
        # --------------------------------------------------
        if lt == "clique":
            self.canvas.tag_bind(rect, "<Double-Button-1>",
                                 lambda e,b=bloco: self._on_double_click_click(b))
        elif lt == "delay":
            self.canvas.tag_bind(rect, "<Double-Button-1>",
                                 lambda e,b=bloco: self._on_double_click_delay(b))
        elif lt == "goto":
            self.canvas.tag_bind(rect, "<Double-Button-1>",
                                 lambda e,b=bloco: self._on_double_click_goto(b))
        elif lt == "se imagem":
            self.canvas.tag_bind(rect, "<Double-Button-1>",
                                 lambda e,b=bloco: self._on_double_click_imagem(b))
        elif lt == "label":
            self.canvas.tag_bind(rect, "<Double-Button-1>",
                                 lambda e,b=bloco: self._on_double_click_label(b))
        elif lt == "loop":
            self.canvas.tag_bind(rect, "<Double-Button-1>",
                                 lambda e,b=bloco: self._on_double_click_loop(b))
        elif lt == "ocr":
            self.canvas.tag_bind(rect, "<Double-Button-1>",
                                 lambda e,b=bloco: self._on_double_click_ocr(b))
        elif lt == "ocr duplo":
            self.canvas.tag_bind(rect, "<Double-Button-1>",
                                 lambda e,b=bloco: self._on_double_click_ocr_duplo(b))
        elif lt == "texto":
            self.canvas.tag_bind(rect, "<Double-Button-1>",
                                 lambda e,b=bloco: self._on_double_click_texto(b))
        elif lt == "screenshot":
            self.canvas.tag_bind(rect, "<Double-Button-1>",
                                 lambda e,b=bloco: self._on_double_click_screenshot(b))
        elif lt == "start thread":
             self.canvas.tag_bind(rect, "<Double-Button-1>",
                                 lambda e, b=bloco: self._on_double_click_startthread(b)
             )
        elif lt == "end thread":
             self.canvas.tag_bind(rect, "<Double-Button-1>",
                                 lambda e, b=bloco: self._on_double_click_endthread(b)
             )


        # --------------------------------------------------
        # 9) finaliza
        # --------------------------------------------------
        self.blocks.append(bloco)
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))

        # garante que estilos (fonte, largura seta, etc.) sigam o zoom
        if hasattr(self.app, "_rescale_styles"):
            self.app._rescale_styles()

        return bloco



    def _handle_press_if(self, bloco, event, branch):
        """
        Inicia conexão a partir de um IF-block, marcando se é true ou false.
        """
        self.app.setas.iniciar_conexao(bloco, event, branch=branch)
        return "break"


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
            "screenshot":   "screenshot_icon.png",
            "start thread": "thread_icon.png",
            "end thread":   "threadend_icon.png",
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
        # Se o item atual é uma LINHA (seta), deixa o SetaManager cuidar
        # da seleção; não devolve "break" nem executa o resto da rotina.
        if item_atual and self.canvas.type(item_atual) == "line":
            return  # Propaga o evento para outros bindings (SetaManager)
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

                # —— monta seleção e drag_group —— 
                sel = [b for t,b in self.app.itens_selecionados if t=="bloco"]
                if ctrl:
                    # toggle de seleção
                    if ("bloco", bloco) in self.app.itens_selecionados:
                        # desmarcar
                        self.app.itens_selecionados = [
                            p for p in self.app.itens_selecionados 
                            if not (p[0]=="bloco" and p[1] is bloco)
                        ]
                        if bloco.get("borda"):
                            self.canvas.delete(bloco["borda"])
                            bloco["borda"] = None
                    else:
                        # marcar
                        self.app.itens_selecionados.append(("bloco", bloco))
                        if not bloco.get("borda"):
                            bx1,by1,bx2,by2 = self.canvas.coords(bloco["rect"])
                            bloco["borda"] = self.canvas.create_rectangle(
                                bx1-2,by1-2,bx2+2,by2+2,
                                outline="blue", width=2, dash=(4,2)
                            )
                            self.canvas.tag_lower(bloco["borda"], bloco["rect"])
                    # atualiza grupo completo
                    sel = [b for t,b in self.app.itens_selecionados if t=="bloco"]
                    self._drag_group = sel
                else:
                    # clique normal
                    if bloco in sel and len(sel) > 1:
                        # já havia seleção múltipla: mantém o grupo inteiro
                        self._drag_group = sel
                    else:
                        # nova seleção única
                        self.app.setas.limpar_selecao()
                        self.app.itens_selecionados = [("bloco", bloco)]
                        if not bloco.get("borda"):
                            bx1,by1,bx2,by2 = self.canvas.coords(bloco["rect"])
                            bloco["borda"] = self.canvas.create_rectangle(
                                bx1-2,by1-2,bx2+2,by2+2,
                                outline="blue", width=2, dash=(4,2)
                            )
                            self.canvas.tag_lower(bloco["borda"], bloco["rect"])
                        self._drag_group = [bloco]
                # traz todo o drag_group pra frente e remove duplicatas
                for b in self._drag_group:
                    self._bring_to_front(b)
                self.app.itens_selecionados = self._unique(self.app.itens_selecionados)
                return "break"
            
                # mantém a ordem original, mas sem duplicados
                self._drag_group = self._unique(
                    b for t, b in self.app.itens_selecionados if t == "bloco"
                )
                # garante que o bloco sob o mouse (e o grupo selecionado) fique no topo
                self._bring_to_front(bloco)

                # remove duplicatas mantendo a ordem
                self.app.itens_selecionados = self._unique(self.app.itens_selecionados)

                return "break"   # impede que o clique caia no SetaManager
            
            # 2) Clique em área vazia → inicia retângulo de seleção
        self.app.setas.limpar_selecao()
        # 2) remove as bordas de todos os blocos que ainda estavam selecionados
        for tipo, bloco in list(self.app.itens_selecionados):
            if tipo == "bloco" and bloco.get("borda"):
                self.canvas.delete(bloco["borda"])
                bloco["borda"] = None
        # 3) finalmente esvazia a lista de seleção
        self.app.itens_selecionados.clear()

        # agora inicia retângulo de seleção por área
        self.selecao_iniciada = True
        self.sel_start_x, self.sel_start_y = x, y
        self.sel_rect_id = self.canvas.create_rectangle(
            x, y, x, y, outline="blue", dash=(2, 2)
        )
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
        # ───────── early-returns ──────────────────────────────────────
        if getattr(self.app.setas, "handle_drag", None):
            return
        if self.selecao_iniciada:
            self.atualizar_selecao_area(event)
            return
        if not self.arrastando:
            return

        # mantém o(s) bloco(s) acima dos demais
        for b in (self._drag_group or [self.arrastando]):
            self._bring_to_front(b)

        # grava snapshot 1× na primeira movimentação
        if not self._has_moved and not self._is_restoring:
            self._undo_stack.append(self._snapshot())
            self._redo_stack.clear()
            self._has_moved = True

        # ───────── cálculo do deslocamento (dx, dy) ──────────────────
        x = self.canvas.canvasx(event.x)
        y = self.canvas.canvasy(event.y)
        new_x = x - self.offset_x
        new_y = y - self.offset_y
        dx = new_x - self.arrastando["x"]
        dy = new_y - self.arrastando["y"]

        # define o grupo de alvos (seleção múltipla ou bloco único)
        if self._drag_group:
            if self.arrastando not in self._drag_group:
                self._drag_group.insert(0, self.arrastando)
            alvos = self._drag_group
        else:
            sel_blocks = [b for t, b in self.app.itens_selecionados if t == "bloco"]
            if len(sel_blocks) > 1 and self.arrastando in sel_blocks:
                alvos = sel_blocks
                self._drag_group = sel_blocks
            else:
                alvos = [self.arrastando]

        # ───────── move cada item do bloco ───────────────────────────
        for bloco in alvos:
            # rect, ícone e borda
            self.canvas.move(bloco["rect"],  dx, dy)
            if bloco.get("icon"):
                self.canvas.move(bloco["icon"], dx, dy)
            if bloco.get("borda"):
                self.canvas.move(bloco["borda"], dx, dy)

            # handles padrão (⊕) e IF (ovais)
            for h in bloco.get("handles", []):
                self.canvas.move(h, dx, dy)
            if bloco.get("true_handle"):
                self.canvas.move(bloco["true_handle"],  dx, dy)
            if bloco.get("false_handle"):
                self.canvas.move(bloco["false_handle"], dx, dy)

            # rótulo da ação (se existir)
            if bloco.get("label_id"):
                self.canvas.move(bloco["label_id"], dx, dy)

            # actualiza posição lógica
            bloco["x"] += dx
            bloco["y"] += dy

        # actualiza setas conectadas uma única vez
        self.app.setas.atualizar_setas()

        # amplia área de scroll, se necessário
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))

    
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
                # leva o bloco recém-selecionado para frente
                self._bring_to_front(bloco)
                self.app.itens_selecionados.append(("bloco", bloco))

        # remove o retângulo de seleção e reseta flags
        self.canvas.delete(self.sel_rect_id)
        self.sel_rect_id = None
        self.selecao_iniciada = False

        # remove duplicatas mantendo a ordem
        self.app.itens_selecionados = self._unique(self.app.itens_selecionados)
        return "break"

    #  (A) utilitário: snapshot p/ ‘undo’
    def _snapshot(self):
        # agora incluímos também a ação (ou None)
        estado_blocos = [
            (b["text"], b["x"], b["y"], b.get("acao"))
            for b in self.blocks
        ]
        estado_setas = []
        for seta_id, origem, destino in self.app.setas.setas:
            # pega a cor original (preferindo o cache do SetaManager)
            info = self.app.setas._setas_info.get(seta_id)
            if info and len(info) >= 3:
                cor = info[2]
            else:
                cor = self.app.setas.canvas.itemcget(seta_id, "fill") or "#000"

            estado_setas.append((
                self.blocks.index(origem),
                self.blocks.index(destino),
                cor                     # <── salva a cor!
            ))
        return (estado_blocos, estado_setas)


    def _restaurar_snapshot(self, snap):
        """
        Restaura o estado dos blocos e setas a partir de um snapshot.
        Garante que todos os handles (⊕ e IF-block ovals) sejam removidos
        e recriados na posição correta.
        """
        self._is_restoring = True

        blocos_info, setas_info = snap

        # 1) Limpa canvas inteiro de blocos antigos
        for bloco in list(self.blocks):
            # retângulo base
            self.canvas.delete(bloco["rect"])
            # ícone (se houver)
            if bloco.get("icon"):
                self.canvas.delete(bloco["icon"])
            # borda de seleção (se houver)
            if bloco.get("borda"):
                self.canvas.delete(bloco["borda"])
            # handles padrão (⊕)
            for h in bloco.get("handles", []):
                self.canvas.delete(h)
            # handles IF-blocks (ovais verde/vermelho)
            if bloco.get("true_handle"):
                self.canvas.delete(bloco["true_handle"])
            if bloco.get("false_handle"):
                self.canvas.delete(bloco["false_handle"])
            # rótulo de ação (se houver)
            if bloco.get("label_id"):
                self.canvas.delete(bloco["label_id"])

        # esvazia lista de blocos e posições ocupadas
        self.blocks.clear()
        self.ocupados.clear()

        # 2) Limpa setas existentes
        for seta_id, *_ in self.app.setas.setas:
            self.canvas.delete(seta_id)
        self.app.setas.setas.clear()

        # 3) Recria cada bloco
        for text, x, y, acao in blocos_info:
            novo = self.adicionar_bloco(text, "white")

            # reposiciona retângulo e ícone
            self.canvas.coords(novo["rect"],
                               x, y,
                               x + novo["width"], y + novo["height"])
            if novo.get("icon"):
                self.canvas.coords(novo["icon"], x, y)
            novo["x"], novo["y"] = x, y

            # reposiciona handles (ovais e/ou ⊕) na nova posição
            self._recolocar_handles(novo)

            # restaura ação e label, se existia
            if acao:
                novo["acao"] = acao
                # aqui você repete seu código de criação de label:
                tipo = acao.get("type", "").lower()
                if tipo == "click":
                    txt = f"Click @({acao['x']},{acao['y']})"
                elif tipo == "delay":
                    txt = f"Delay: {acao['time']}ms"
                elif tipo == "goto":
                    txt = f"GOTO → {acao['label']}"
                elif tipo == "imagem":
                    txt = f"Img:{acao['imagem']} @({acao['x']},{acao['y']},{acao['w']},{acao['h']})"
                elif tipo == "label":
                    txt = f"Label: {acao['name']}"
                elif tipo == "loopstart":
                    if acao.get("mode") == "quantidade":
                        txt = f"INÍCIO LOOP {acao['count']}x"
                    else:
                        txt = "INÍCIO LOOP INFINITO"
                elif tipo == "ocr":
                    txt = f"OCR: '{acao['text']}'"
                elif tipo == "ocr_duplo":
                    cond = acao.get("condicao", "and").upper()
                    txt = f"OCR Duplo: '{acao['text1']}' {cond} '{acao['text2']}'"
                elif tipo == "text":
                    txt = f'TXT: "{acao["content"][:18]}…"' if len(acao["content"])>20 else f'TXT: "{acao["content"]}"'
                
                else:
                    txt = tipo.upper()
                novo["label_id"] = self.canvas.create_text(
                    x + novo["width"]/2,
                    y + novo["height"] + 8,
                    text=txt,
                    font=("Arial", 9),
                    fill="black"
                )

        # 4) Recria todas as setas entre blocos
        for idx_o, idx_d, cor in setas_info:
            origem  = self.blocks[idx_o]
            destino = self.blocks[idx_d]
            # preserva a cor original
            self.app.setas.desenhar_linha(origem, destino, cor_override=cor)


        self._is_restoring = False



    
    # -----------------------------------------------------------
    #  (B) atalhos públicos chamados por eventos.py
    def selecionar_todos(self, event=None):
        # limpa destaques antigos de setas e blocos
        self.app.setas._limpar_selecao()
        # zera a lista de itens selecionados antes de reapopular
        self.app.itens_selecionados.clear()
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
        # empilha snapshot para undo
        self._undo_stack.append(self._snapshot())
        self._redo_stack.clear()

        for tipo, item in list(self.app.itens_selecionados):
            if tipo == "bloco":
                # remove setas conectadas
                self.app.setas.remover_setas_de_bloco(item)

                # retira rótulo de ação, se existir
                if item.get("label_id"):
                    self.canvas.delete(item["label_id"])

                # retângulo, ícone e borda
                self.canvas.delete(item["rect"])
                if item.get("icon"):
                    self.canvas.delete(item["icon"])
                if item.get("borda"):
                    self.canvas.delete(item["borda"])

                # handles padrão (⊕)
                for h in item.get("handles", []):
                    self.canvas.delete(h)

                # handles IF-blocks (ovais verde/vermelho)
                if item.get("true_handle"):
                    self.canvas.delete(item["true_handle"])
                if item.get("false_handle"):
                    self.canvas.delete(item["false_handle"])

                # remove das estruturas internas
                self.blocks.remove(item)
                self.ocupados.discard((item["x"], item["y"]))

            elif tipo == "seta":
                self.app.setas.deletar_seta_por_id(item)

        # limpa seleção
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

        # 3 – remove realmente os itens (já grava snapshot via deletar_selecionados)
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
        # salva snapshot para undo
        self._undo_stack.append(self._snapshot())
        self._redo_stack.clear()
    
        # ponto base levemente deslocado para não sobrepor original
        base_x, base_y = self.encontrar_proxima_posicao()
        base_x += 20
        base_y += 20
    
        # limpa seleção anterior
        self.app.setas._limpar_selecao()
    
        for text, dx, dy in BlocoManager._clipboard:
            # cria o bloco
            novo = self.adicionar_bloco(text, "white")
    
            # calcula e aplica nova posição
            x = base_x + dx
            y = base_y + dy
            self.canvas.coords(novo["rect"],
                               x, y,
                               x + novo["width"], y + novo["height"])
            if novo.get("icon"):
                self.canvas.coords(novo["icon"], x, y)
            novo["x"], novo["y"] = x, y
    
            # reposiciona todos os handles (⊕ e IF-block ovals)
            self._recolocar_handles(novo)
    
            # desenha borda de seleção ao redor do bloco
            borda = self.canvas.create_rectangle(
                x - 2, y - 2,
                x + novo["width"] + 2, y + novo["height"] + 2,
                outline="blue", width=2, dash=(4, 2)
            )
            self.canvas.tag_lower(borda, novo["rect"])
            novo["borda"] = borda
    
            # adiciona à lista de selecionados
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

        coords = self.canvas.coords(bloco["rect"])
        if len(coords) < 4:
            return                          # retângulo inexistente

        x1, y1, x2, y2 = coords            # ← posição já na escala atual
        cx        = (x1 + x2) / 2          # centro horizontal
        altura    = y2 - y1                # altura real do bloco
        r         = 5                      # raio dos óvalos
        """
        Reposiciona os handles de um bloco:
        - Se for IF-block, reposiciona true_handle (verde) e false_handle (vermelho).
        - Se for bloco normal, reposiciona os 4 handles “⊕”.
        """
        # 1) IF-block: reposiciona os óvais coloridos
        if bloco.get("true_handle"):
            self.canvas.coords(
                bloco["true_handle"],
                cx - r, y1 - 2*r,          # topo
                cx + r, y1
            )

        if bloco.get("false_handle"):
            self.canvas.coords(
                bloco["false_handle"],
                cx - r, y2,                # base
                cx + r, y2 + 2*r
            )

        # 2) Blocos normais: reposiciona os 4 ⊕, se existirem
        if bloco.get("handles"):
            size  = 10
            half  = size // 2
            cy    = (y1 + y2) / 2
    
            novos = [
                (cx,        y1 - half),        # topo
                (cx,        y2 + half),        # base
                (x1 - half, cy),               # esquerda
                (x2 + half, cy)                # direita
            ]
            for h, (hx, hy) in zip(bloco["handles"], novos):
                self.canvas.coords(h, hx, hy)


    def _bring_to_front(self, bloco):
        """Garante que o bloco e seus elementos fiquem acima dos demais."""
        # a tag de grupo foi criada em adicionar_bloco()
        for tag in self.canvas.gettags(bloco["rect"]):
            if tag.startswith("bloco"):
                self.canvas.tag_raise(tag)      # todo o grupo
                break
        # borda (se existir) deve ficar acima de tudo
        if bloco.get("borda"):
            self.canvas.tag_raise(bloco["borda"])
    
    def _unique(self, seq):
        """Devolve lista sem repetição, mantendo ordem. Para tuplos (tipo, obj), deduplica pelo id(obj);  para demais itens, pelo id(item)."""
        seen = set()
        out  = []
        for item in seq:
            obj_id = id(item[1]) if isinstance(item, tuple) else id(item)
            if obj_id not in seen:
                seen.add(obj_id)
                out.append(item)
        return out

    def _on_double_click(self, bloco):
       """
       Reusa exatamente a janela de janela_clique.py para capturar o click,
       e depois aplica a ação ao bloco no canvas.
       """
       # 1) cria um buffer exclusivo para este bloco
       bloco["_click_buffer"] = []
       # 2) define o callback que será chamado
       #    logo após inserir a ação no buffer
       def finish():
           # pega a última ação inserida
           ac = bloco["_click_buffer"][-1]
           # guarda oficialmente em bloco["acao"]
           bloco["acao"] = ac
           # apaga label antigo, se existir
           if bloco.get("label_id"):
               self.canvas.delete(bloco["label_id"])
           # desenha o texto logo abaixo do bloco
           bx, by = bloco["x"], bloco["y"]
           w, h   = bloco["width"], bloco["height"]
           texto = ac.get("name") or ac.get("custom_name") or f"Click @({ac['x']},{ac['y']})"
           label_x = bx + w/2
           label_y = by + h + 8
           bloco["label_id"] = self.canvas.create_text(
               label_x, label_y,
               text=texto, font=("Arial", 9), fill="black"
           )
           # empilha snapshot para permitir undo desta mudança
           if not self._is_restoring:
               self._undo_stack.append(self._snapshot())
               self._redo_stack.clear()
       # 3) chama sua janela existente
       add_click(
           actions     = bloco["_click_buffer"],
           update_list = finish,
           tela        = self.app.root
       )

    def _on_double_click_delay(self, bloco):
        bloco["_delay_buffer"] = []
        def finish():
            # 1) empilha o estado _antes_ de alterar a ação
            if not self._is_restoring:
                self._undo_stack.append(self._snapshot())
                self._redo_stack.clear()
    
            # 2) grava a ação de delay e desenha o label
            ac = bloco["_delay_buffer"][-1]
            bloco["acao"] = ac
            if bloco.get("label_id"):
                self.canvas.delete(bloco["label_id"])
            bx, by = bloco["x"], bloco["y"]
            w, h   = bloco["width"], bloco["height"]
            texto = ac.get("name") or ac.get("custom_name") or f"Delay: {ac['time']}ms"
            bloco["label_id"] = self.canvas.create_text(
                bx + w/2,
                by + h + 8,
                text=texto, font=("Arial", 9), fill="black"
            )
            # (não precisa do snapshot nem aqui)
        add_delay(
            actions     = bloco["_delay_buffer"],
            update_list = finish,
            tela        = self.app.root
        )

    def _on_double_click_goto(self, bloco):
        """
        Abre a janela de goto, grava em bloco['acao'] e desenha o texto abaixo.
        """
        # buffer temporário para undo
        bloco["_goto_buffer"] = []

        def finish():
            # 1) empilha estado ANTES da mudança
            if not self._is_restoring:
                self._undo_stack.append(self._snapshot())
                self._redo_stack.clear()

            # 2) grava a ação e desenha o label
            ac = bloco["_goto_buffer"][-1]
            bloco["acao"] = ac
            if bloco.get("label_id"):
                self.canvas.delete(bloco["label_id"])

            bx, by = bloco["x"], bloco["y"]
            w, h   = bloco["width"], bloco["height"]
            texto = ac.get("name") or ac.get("custom_name") or f"GOTO → {ac['label']}"
            bloco["label_id"] = self.canvas.create_text(
                bx + w/2,
                by + h + 8,
                text=texto,
                font=("Arial", 9),
                fill="black"
            )
            # não é preciso empilhar de novo aqui
        # chama a janela
        add_goto(
            actions     = bloco["_goto_buffer"],
            update_list = finish,
            tela        = self.app.root
        )

    def _on_double_click_imagem(self, bloco):
        """
        Abre a janela de reconhecimento de imagem, grava em bloco['acao']
        e desenha o texto abaixo.
        """
        # ── buffer temporário (serve p/ undo) ───────────────────────────────
        bloco["_img_buffer"] = []

        def finish():
            # 1) snapshot p/ desfazer
            if not self._is_restoring:
                self._undo_stack.append(self._snapshot())
                self._redo_stack.clear()

            # 2) grava a última ação confirmada
            ac = bloco["_img_buffer"][-1]
            bloco["acao"] = ac

            # 3) redesenha o label sob o bloco
            if bloco.get("label_id"):
                self.canvas.delete(bloco["label_id"])
            bx, by = bloco["x"], bloco["y"]
            w, h   = bloco["width"], bloco["height"]
            texto = ac.get("name") or ac.get("custom_name") or f"Img:{ac['imagem']} @({ac['x']},{ac['y']},{ac['w']},{ac['h']})"
            bloco["label_id"] = self.canvas.create_text(
                bx + w / 2, by + h + 8,
                text=texto, font=("Arial", 9), fill="black"
            )

        # ── chama a janela passando a AÇÃO ATUAL como 'initial' ─────────────
        from gui.janela_imagem import add_imagem
        # só encaminha 'initial' se já existir uma imagem configurada
        ac = bloco.get("acao", {})
        add_imagem(
            actions      = bloco["_img_buffer"],
            update_list  = finish,
            tela         = self.app.root,
            initial      = ac if ac.get("imagem") else None
        )


    def _on_double_click_label(self, bloco):
        """
        Abre a janela de Label, grava em bloco['acao']
        e desenha o texto abaixo do bloco.
        """
        # buffer temporário para undo
        bloco["_label_buffer"] = []

        def finish():
            # empilha snapshot antes da mudança
            if not self._is_restoring:
                self._undo_stack.append(self._snapshot())
                self._redo_stack.clear()

            # pega a ação e desenha
            ac = bloco["_label_buffer"][-1]
            bloco["acao"] = ac
            # remove label antigo (se existir)
            if bloco.get("label_id"):
                self.canvas.delete(bloco["label_id"])
            bx, by = bloco["x"], bloco["y"]
            w, h   = bloco["width"], bloco["height"]
            texto  = ac.get("custom_name") or f"Label: {ac['name']}"
            bloco["label_id"] = self.canvas.create_text(
                bx + w/2, by + h + 8,
                text=texto, font=("Arial", 9), fill="black"
            )

        # chama a janela adaptada
        add_label(
            actions     = bloco["_label_buffer"],
            update_list = finish,
            tela        = self.app.root
        )

    def _on_double_click_loop(self, bloco):
        """
        Abre a janela de Loop, grava em bloco['acao']
        e desenha o texto abaixo do bloco.
        """
        # 1) buffer temporário
        bloco["_loop_buffer"] = []

        # 2) callback de finalização
        def finish():
            # empilha snapshot antes de aplicar
            if not self._is_restoring:
                self._undo_stack.append(self._snapshot())
                self._redo_stack.clear()

            ac = bloco["_loop_buffer"][-1]
            bloco["acao"] = ac
            # remove label anterior
            if bloco.get("label_id"):
                self.canvas.delete(bloco["label_id"])
            bx, by = bloco["x"], bloco["y"]
            w, h = bloco["width"], bloco["height"]
            txt = ac.get("name") or ac.get("custom_name") or (
               f"INÍCIO LOOP {ac['count']}x" if ac["mode"]=="quantidade"
               else "INÍCIO LOOP INFINITO"
           )
            bloco["label_id"] = self.canvas.create_text(
                bx + w/2, by + h + 8,
                text=txt, font=("Arial", 9), fill="black"
            )

        # 3) chama a janela adaptada
        add_loop(
            actions     = bloco["_loop_buffer"],
            update_list = finish,
            tela        = self.app.root
        )
    
    def _on_double_click_ocr(self, bloco):
        """
        Abre a janela de OCR simples.
        – Se o bloco já tiver uma ação gravada em bloco['acao'],
          esses dados são enviados como *initial=* para que a janela
          abra exibindo a área, o texto esperado e o flag “vazio”.
        – Ao confirmar, grava a nova ação, push no UNDO e redesenha
          o rótulo abaixo do bloco.
        """
        # buffer temporário onde a janela colocará o dict resultante
        bloco["_ocr_buffer"] = []

        def finish():
            """Callback chamado pela janela quando o utilizador pressiona OK."""
            if not bloco["_ocr_buffer"]:
                return                      # nada foi alterado

            # 1) empilha snapshot (para Ctrl+Z) **antes** da mudança
            if not self._is_restoring:
                self._undo_stack.append(self._snapshot())
                self._redo_stack.clear()

            # 2) grava definitivamente a ação
            ac = bloco["_ocr_buffer"][-1]
            bloco["acao"] = ac

            # 3) (re)desenha o rótulo de descrição
            if bloco.get("label_id"):
                self.canvas.delete(bloco["label_id"])

            # respeita nome customizado se fornecido
            if ac.get("name"):
                lbl_txt = ac["name"]
            else:
                texto_esperado = ac.get("text", "")
                lbl_txt = "OCR: [vazio]" if ac.get("verificar_vazio") \
                        else f"OCR: '{texto_esperado}'"

            bx, by = bloco["x"], bloco["y"]
            w,  h  = bloco["width"], bloco["height"]
            bloco["label_id"] = self.canvas.create_text(
                bx + w / 2, by + h + 8,
                text=lbl_txt, font=("Arial", 9), fill="black"
            )

        # --- abre a janela passando dados atuais (se existirem) -------------
        add_ocr(
        actions     = bloco["_ocr_buffer"],   # onde a janela escreve
        update_list = finish,                 # callback quando OK
        tela        = self.app.root,
        listbox     = None,                   # não usamos listbox aqui
        initial     = bloco.get("acao", {})   # ← modo edição
        )


    def _on_double_click_ocr_duplo(self, bloco):
        """
        Abre a janela de OCR Duplo; grava em bloco['acao'] e
        atualiza o rótulo abaixo do bloco.

        – Se o bloco já possui uma ação gravada, ela é passada em
          `initial=` para que tudo apareça preenchido (áreas, textos,
          condição AND/OR e flags de “vazio”).
        """
        # buffer temporário para receber o dict vindo da janela
        bloco["_od_buffer"] = []

        def finish():
            """Callback disparado pela janela quando o utilizador confirma."""
            if not bloco["_od_buffer"]:
                return                      # nada foi alterado

            # 1) empilha snapshot para UNDO, antes da mudança
            if not self._is_restoring:
                self._undo_stack.append(self._snapshot())
                self._redo_stack.clear()

            # 2) grava a ação definitiva
            ac = bloco["_od_buffer"][-1]
            bloco["acao"] = ac

            # 3) (re)desenha o rótulo de descrição
            if bloco.get("label_id"):
                self.canvas.delete(bloco["label_id"])

            # respeita nome customizado se fornecido
            if ac.get("name"):
                texto = ac["name"]
            else:
                cond = ac.get("condicao", "and").upper()
                texto = f"OCR Duplo: '{ac.get('text1','')}' {cond} '{ac.get('text2','')}'"

            bx, by = bloco["x"], bloco["y"]
            w,  h  = bloco["width"], bloco["height"]
            bloco["label_id"] = self.canvas.create_text(
                bx + w / 2, by + h + 8,
                text=texto, font=("Arial", 9), fill="black"
            )

        # chama a janela passando os dados já existentes para “modo edição”
        add_ocr_duplo(
            actions     = bloco["_od_buffer"],   # onde a janela colocará o dict
            atualizar   = finish,                # callback ao OK
            tela        = self.app.root,
            listbox     = None,                  # não usamos aqui
            initial     = bloco.get("acao", {})  # <- dados atuais (se houver)
        )

    def _on_double_click_texto(self, bloco):
        """
        Abre a janela de Texto, grava em bloco['acao']
        e desenha o conteúdo abaixo do bloco.
        """
        bloco["_txt_buffer"] = []
        def finish():
            # snapshot antes da alteração
            if not self._is_restoring:
                self._undo_stack.append(self._snapshot())
                self._redo_stack.clear()
            ac = bloco["_txt_buffer"][-1]      # {'type':'text', 'content': '...'}
            bloco["acao"] = ac
            # remove label antigo (se existir)
            if bloco.get("label_id"):
                self.canvas.delete(bloco["label_id"])
            # desenha preview do texto abaixo do bloco
            bx, by = bloco["x"], bloco["y"]
            w, h   = bloco["width"], bloco["height"]
            # respeita nome customizado se fornecido
            if ac.get("name"):
                texto = ac["name"]
            else:
                preview = (ac["content"][:18] + "…") if len(ac["content"]) > 20 else ac["content"]
                texto = f'TXT: "{preview}"'
            bloco["label_id"] = self.canvas.create_text(
                bx + w/2, by + h + 8,
                text=texto,
                font=("Arial", 9), fill="black"
            )
        # chama a janela de texto
        add_texto(
            actions     = bloco["_txt_buffer"],
            update_list = finish,
            tela        = self.app.root
        )
    
    def _on_double_click_screenshot(self, bloco):
        """
        Abre a janela de configuração de screenshot, grava em bloco['acao']
        e redesenha o label abaixo do bloco.
        """
        # 1) buffer temporário para undo
        bloco["_screenshot_buffer"] = []

        def finish():
            # snapshot p/ undo
            if not self._is_restoring:
                self._undo_stack.append(self._snapshot())
                self._redo_stack.clear()

            # pega a última ação confirmada
            ac = bloco["_screenshot_buffer"][-1]
            bloco["acao"] = ac

            # apaga label antigo, se houver
            if bloco.get("label_id"):
                self.canvas.delete(bloco["label_id"])

            # formata texto
            # mostrar nome customizado se existir, senão texto padrão
            if ac.get("name"):
                txt = ac["name"]
            elif ac["mode"] == "whole":
                txt = "Screenshot: tela inteira"
            else:
                x,y,w,h = ac["region"].values()
                txt = f"Screenshot: reg ({x},{y},{w}×{h})"

            # desenha o texto
            bx, by   = bloco["x"], bloco["y"]
            bw, bh   = bloco["width"], bloco["height"]
            bloco["label_id"] = self.canvas.create_text(
                bx + bw/2,
                by + bh + 8,
                text=txt,
                font=("Arial", 9),
                fill="black"
            )

        # 2) chama a janela passando o buffer e o callback
        add_screenshot(
            actions     = bloco["_screenshot_buffer"],
            update_list = finish,
            tela        = self.app.root,
            initial     = bloco.get("acao", {})  # pré-preenche se já existia
        )

    def _on_double_click_startthread(self, bloco):
        # 1) Descobre todos os blocos ligados à saída deste Start Thread
        conectar_blocos = [
            destino
            for seta_id, origem, destino in self.app.setas.setas
            if origem is bloco
        ]

        abrir_fork_dialog(
            parent=self.app.root,
            bloco=bloco,
            conectar_ids=conectar_blocos,       # ← agora é lista de dicts de bloco
            salvar_callback=self._salvar_forks
        )


    def _on_double_click_endthread(self, bloco):
        atual = bloco.get("acao", {}).get("thread_name", "")
        nome = simpledialog.askstring(
            "Nome da Thread (fim)", "Este EndThread corresponde à thread:", initialvalue=atual
        )
        if nome is None:
            return
        bloco.setdefault("acao", {})["thread_name"] = nome

        # — lá embaixo, desenha o label igual ao Start Thread —
        # apaga label antigo, se houver
        if bloco.get("label_id"):
            self.canvas.delete(bloco["label_id"])
        bloco["label_id"] = self.canvas.create_text(
            bloco["x"] + bloco["width"]/2,
            bloco["y"] + bloco["height"] + 8,
            text=nome,
            font=("Arial", 9),
            fill="blue"
        )
    
    def _salvar_forks(self, bloco_id, thread_name, config):
        # 1) encontra o bloco
        bloco = next(b for b in self.blocks if b["id"] == bloco_id)

        # 2) salva o nome da thread e o mapa de forks
        ac = bloco.setdefault("acao", {})
        ac["thread_name"] = thread_name
        ac["forks"]      = config

        # → desenha o rótulo sob o bloco Start Thread
        # remove label antigo, se existir
        if bloco.get("label_id"):
            self.canvas.delete(bloco["label_id"])
        bx, by = bloco["x"], bloco["y"]
        w,  h  = bloco["width"], bloco["height"]
        bloco["label_id"] = self.canvas.create_text(
            bx + w/2,
            by + h + 8,
            text=thread_name,
            font=("Arial", 9),
            fill="blue"
        )

        # 3) redesenha para aplicar estilos nas setas
        self.app.setas.atualizar_setas()
        
    def _salvar_fork_config(self, bloco_id, config):
        # grava no próprio bloco, por ex:
        for b in self.blocks:
            if b["id"] == bloco_id:
                b.setdefault("acao", {})["forks"] = config
                break
        # redesenha setas para aplicar cor nova
        self.app.setas.atualizar_setas()


    def _on_canvas_double_click(self, event):
        # coordenadas do clique no canvas
        x, y = self.canvas.canvasx(event.x), self.canvas.canvasy(event.y)
    
        # percorre todos os blocos
        for bloco in list(self.blocks):          # list() p/ permitir remover
            coords = self.canvas.coords(bloco["rect"])
    
            # — proteção contra retângulos já apagados —
            if len(coords) < 4:
                # remove o “bloco órfão” da lista interna e segue p/ o próximo
                self.blocks.remove(bloco)
                continue
            
            x1, y1, x2, y2 = coords
            if not (x1 <= x <= x2 and y1 <= y <= y2):
                continue                         # clique não é neste bloco
            
            # ---------- achamos o bloco clicado ----------
            tipo = bloco["text"].strip().lower()
    
            mapa = {
                "clique"     : self._on_double_click,
                "delay"      : self._on_double_click_delay,
                "goto"       : self._on_double_click_goto,
                "se imagem"  : self._on_double_click_imagem,
                "label"      : self._on_double_click_label,
                "loop"       : self._on_double_click_loop,
                "ocr"        : self._on_double_click_ocr,
                "ocr duplo"  : self._on_double_click_ocr_duplo,
                "texto"      : self._on_double_click_texto,
                "screenshot" : self._on_double_click_screenshot,
                "start thread": self._on_double_click_startthread,
                "end thread"  : self._on_double_click_endthread,
            }
    
            if tipo in mapa:
                return mapa[tipo](bloco)         # abre a janela certa
            return                               # tipo desconhecido → nada
    
        # se nenhum bloco foi clicado, simplesmente não faz nada

