from util import clicou_em_linha
import os
from PIL import Image, ImageTk

class SetaManager:
    def __init__(self, canvas, blocos):
        self.canvas = canvas
        self.blocos = blocos
        self.setas = []
        self.bloco_origem = None
        self.conectando = False
        self.ultima_seta_selecionada = None  # ← guarda referência da última seta azul

    def _mapear_nome_para_icone(self, nome):
        nome = nome.strip().lower()
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
        return mapa.get(nome, "default.png")
    
    def ativar_conexao(self):
        self.conectando = True
        self.bloco_origem = None

    def clicar_em_bloco(self, bloco):
        if self.conectando:
            if not self.bloco_origem:
                self.bloco_origem = bloco
            else:
                self.desenhar_linha(self.bloco_origem, bloco)
                self.conectando = False
                self.bloco_origem = None

    def desenhar_linha(self, origem, destino):
        coords_origem = self.canvas.coords(origem["rect"])
        coords_destino = self.canvas.coords(destino["rect"])

        ox1, oy1, ox2, oy2 = coords_origem
        dx1, dy1, dx2, dy2 = coords_destino

        centro_origem = ((ox1 + ox2) / 2, (oy1 + oy2) / 2)
        centro_destino = ((dx1 + dx2) / 2, (dy1 + dy2) / 2)

        dx = centro_destino[0] - centro_origem[0]
        dy = centro_destino[1] - centro_origem[1]

        if abs(dx) > abs(dy):
            if dx > 0:
                x1 = ox2
                y1 = centro_origem[1]
                x2 = dx1
                y2 = centro_destino[1]
            else:
                x1 = ox1
                y1 = centro_origem[1]
                x2 = dx2
                y2 = centro_destino[1]
        else:
            if dy > 0:
                x1 = centro_origem[0]
                y1 = oy2
                x2 = centro_destino[0]
                y2 = dy1
            else:
                x1 = centro_origem[0]
                y1 = oy1
                x2 = centro_destino[0]
                y2 = dy2

        linha = self.canvas.create_line(x1, y1, x2, y2, arrow="last", width=2)
        self.setas.append((linha, origem, destino))

    def atualizar_setas(self):
        for seta_id, origem, destino in self.setas:
            self._atualizar_uma_seta(seta_id, origem, destino)

    def _atualizar_uma_seta(self, seta_id, origem, destino):
        coords_origem = self.canvas.coords(origem["rect"])
        coords_destino = self.canvas.coords(destino["rect"])

        ox1, oy1, ox2, oy2 = coords_origem
        dx1, dy1, dx2, dy2 = coords_destino

        centro_origem = ((ox1 + ox2) / 2, (oy1 + oy2) / 2)
        centro_destino = ((dx1 + dx2) / 2, (dy1 + dy2) / 2)

        dx = centro_destino[0] - centro_origem[0]
        dy = centro_destino[1] - centro_origem[1]

        if abs(dx) > abs(dy):
            if dx > 0:
                x1 = ox2
                y1 = centro_origem[1]
                x2 = dx1
                y2 = centro_destino[1]
            else:
                x1 = ox1
                y1 = centro_origem[1]
                x2 = dx2
                y2 = centro_destino[1]
        else:
            if dy > 0:
                x1 = centro_origem[0]
                y1 = oy2
                x2 = centro_destino[0]
                y2 = dy1
            else:
                x1 = centro_origem[0]
                y1 = oy1
                x2 = centro_destino[0]
                y2 = dy2

        self.canvas.coords(seta_id, x1, y1, x2, y2)

    def remover_setas_de_bloco(self, bloco):
        novas_setas = []
        for seta_id, origem, destino in self.setas:
            if origem == bloco or destino == bloco:
                self.canvas.delete(seta_id)
            else:
                novas_setas.append((seta_id, origem, destino))
        self.setas = novas_setas

    def deletar_seta_por_id(self, seta_id):
        self.canvas.delete(seta_id)
        self.setas = [s for s in self.setas if s[0] != seta_id]

    def selecionar_item(self, event):
        x, y = self.canvas.canvasx(event.x), self.canvas.canvasy(event.y)

        # Reseta visual da seta anterior (se houver)
        if self.ultima_seta_selecionada:
            self.canvas.itemconfig(self.ultima_seta_selecionada, fill="black")
            self.ultima_seta_selecionada = None

        # Reseta visual do bloco anterior (se houver)
        if self.blocos.borda_selecionada:
            self.canvas.delete(self.blocos.borda_selecionada)
            self.blocos.borda_selecionada = None

        # Limpa seleção lógica
        self.blocos.app.item_selecionado = None

        # Verifica se clicou em uma seta
        for seta_id, origem, destino in self.setas:
            coords = self.canvas.coords(seta_id)
            if clicou_em_linha(x, y, coords):
                self.blocos.app.item_selecionado = ("seta", seta_id)
                self.canvas.itemconfig(seta_id, fill="blue")
                self.ultima_seta_selecionada = seta_id  # ← registra seta azul
                return

        # Verifica se clicou em um bloco
        for bloco in self.blocos.blocks:
            coords = self.canvas.coords(bloco["rect"])
            if coords[0] <= x <= coords[2] and coords[1] <= y <= coords[3]:
                self.blocos.app.item_selecionado = ("bloco", bloco)
                self.blocos.destacar_bloco(bloco)
                return

    def deletar_item(self, event):
        if self.blocos.app.item_selecionado:
            tipo, item = self.blocos.app.item_selecionado
    
            if tipo == "bloco":
                self.canvas.delete(item["rect"])
                if item.get("icon"):
                    self.canvas.delete(item["icon"])
    
                # Remove a borda se existir
                if self.blocos.borda_selecionada:
                    self.canvas.delete(self.blocos.borda_selecionada)
                    self.blocos.borda_selecionada = None
    
                # Remove imagem do cache
                bloco_id = item.get("id")
                if bloco_id and bloco_id in self.blocos.imagens:
                    del self.blocos.imagens[bloco_id]
    
                # Remove bloco
                if item in self.blocos.blocks:
                    self.blocos.blocks.remove(item)
                self.blocos.ocupados.discard((item["x"], item["y"]))
    
                # Remove setas conectadas
                novas_setas = []
                for seta_id, origem, destino in self.setas:
                    if origem == item or destino == item:
                        self.canvas.delete(seta_id)
                    else:
                        novas_setas.append((seta_id, origem, destino))
                self.setas = novas_setas
    
            elif tipo == "seta":
                self.canvas.delete(item)
                self.setas = [s for s in self.setas if s[0] != item]
    
            self.blocos.app.item_selecionado = None



    def _desenhar_linha_visual(self, origem, destino):
        """Desenha a linha visualmente sem adicionar novamente à lista de setas"""
        coords_origem = self.canvas.coords(origem["rect"])
        coords_destino = self.canvas.coords(destino["rect"])
    
        ox1, oy1, ox2, oy2 = coords_origem
        dx1, dy1, dx2, dy2 = coords_destino
    
        centro_origem = ((ox1 + ox2) / 2, (oy1 + oy2) / 2)
        centro_destino = ((dx1 + dx2) / 2, (dy1 + dy2) / 2)
    
        dx = centro_destino[0] - centro_origem[0]
        dy = centro_destino[1] - centro_origem[1]
    
        if abs(dx) > abs(dy):
            if dx > 0:
                x1 = ox2
                y1 = centro_origem[1]
                x2 = dx1
                y2 = centro_destino[1]
            else:
                x1 = ox1
                y1 = centro_origem[1]
                x2 = dx2
                y2 = centro_destino[1]
        else:
            if dy > 0:
                x1 = centro_origem[0]
                y1 = oy2
                x2 = centro_destino[0]
                y2 = dy1
            else:
                x1 = centro_origem[0]
                y1 = oy1
                x2 = centro_destino[0]
                y2 = dy2
    
        self.canvas.create_line(x1, y1, x2, y2, arrow="last", width=2)