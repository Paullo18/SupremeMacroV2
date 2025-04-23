from PIL import Image, ImageTk
import os

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

    def finalizar_arrasto(self, event):
        # encerra arrasto OU seleção
        if self.arrastando:
            self.arrastando = None
        elif self.selecao_iniciada:
            self.finalizar_selecao_area(event)


    def encontrar_proxima_posicao(self):
        x = 20
        y = self.margem_topo
        while True:
            if all(bloco["x"] != x or bloco["y"] != y for bloco in self.blocks):
                return x, y
            y += self.block_height + self.espaco_vertical

    def adicionar_bloco(self, nome, cor):
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
        self.blocks.append(bloco)
        return bloco

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
        x, y = self.canvas.canvasx(event.x), self.canvas.canvasy(event.y)

        # resetar estado de arrasto e remover destaque antigo
        self.arrastando = None
        if self.borda_selecionada:
            self.canvas.delete(self.borda_selecionada)
            self.borda_selecionada = None

        # teste de clique em blocos
        for bloco in self.blocks:
            x1, y1, x2, y2 = self.canvas.coords(bloco["rect"])
            if x1 <= x <= x2 and y1 <= y <= y2:
                # inicia arrasto
                self.arrastando = bloco
                self.offset_x = x - bloco["x"]
                self.offset_y = y - bloco["y"]

                # criar borda de seleção
                self.borda_selecionada = self.canvas.create_rectangle(
                    bloco["x"] - 2, bloco["y"] - 2,
                    bloco["x"] + bloco["width"] + 2,
                    bloco["y"] + bloco["height"] + 2,
                    outline="blue", width=2, dash=(4, 2)
                )
                self.canvas.tag_lower(self.borda_selecionada, bloco["rect"])
                return

        # clique fora de qualquer bloco → inicia seleção por área
        self.selecao_iniciada = True
        self.sel_start_x, self.sel_start_y = x, y
        # retângulo de seleção visível
        self.sel_rect_id = self.canvas.create_rectangle(
            x, y, x, y, outline="blue", dash=(2, 2)
        )
        # limpa seleção anterior (usa o helper que já existe no SetaManager)
        self.app.setas._limpar_selecao()
        return

    def mover_bloco(self, event):
        if not self.arrastando:
            # caso seja apenas uma seleção por área
            self.atualizar_selecao_area(event)
            return

        # --- cálculo da nova posição ---
        x = self.canvas.canvasx(event.x)
        y = self.canvas.canvasy(event.y)
        new_x = x - self.offset_x
        new_y = y - self.offset_y
        dx = new_x - self.arrastando["x"]
        dy = new_y - self.arrastando["y"]

        bloco = self.arrastando
        bx1 = bloco["x"] + dx
        by1 = bloco["y"] + dy
        bx2 = bx1 + bloco["width"]
        by2 = by1 + bloco["height"]

        # move retângulo principal e ícone
        self.canvas.coords(bloco["rect"], bx1, by1, bx2, by2)
        if bloco.get("icon"):
            self.canvas.coords(bloco["icon"], bx1, by1)

        # 1) borda criada pelo BlocoManager (seleção única)
        if self.borda_selecionada:
            self.canvas.coords(self.borda_selecionada,
                               bx1 - 2, by1 - 2, bx2 + 2, by2 + 2)

        # 2) borda criada pelo SetaManager (seleção única ou múltipla)
        if bloco.get("borda"):
            self.canvas.coords(bloco["borda"],
                               bx1 - 2, by1 - 2, bx2 + 2, by2 + 2)

        # atualiza posição interna
        bloco["x"], bloco["y"] = bx1, by1

        # atualiza setas conectadas
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
