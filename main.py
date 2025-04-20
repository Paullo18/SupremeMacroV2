import tkinter as tk
from tkinter import simpledialog

class FlowchartApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Flowchart Macro Editor")

        self.canvas = tk.Canvas(root, bg="white")
        self.canvas.pack(side="right", fill="both", expand=True)

        self.menu_frame = tk.Frame(root, width=150, bg="#f0f0f0")
        self.menu_frame.pack(side="left", fill="y")

        self.setas = []
        self.bloco_origem = None
        self.conectando = False

        self.blocks = []
        self.ocupados = set()

        self.block_width = 120
        self.block_height = 50
        self.margem_topo = 20
        self.espaco_vertical = 20

        self.blocos_disponiveis = [
            ("Início", "green"),
            ("Se Imagem", "orange"),
            ("Clique", "lightblue"),
            ("Delay", "lightgrey"),
            ("Fim", "red"),
        ]

        for nome, cor in self.blocos_disponiveis:
            btn = tk.Label(self.menu_frame, text=nome, bg=cor, width=15, relief="raised", bd=2, cursor="hand2")
            btn.pack(pady=5, padx=5)
            btn.bind("<Button-1>", lambda e, n=nome, c=cor: self.adicionar_bloco(n, c))

        btn_conectar = tk.Label(self.menu_frame, text="➕ Conectar", bg="#ddd", width=15, relief="raised", bd=2, cursor="hand2")
        btn_conectar.pack(pady=10)
        btn_conectar.bind("<Button-1>", lambda e: self.ativar_conexao())

        self.arrastando = None
        self.offset_x = 0
        self.offset_y = 0

        self.canvas.bind("<Button-1>", self.canvas_clique)
        self.canvas.bind("<B1-Motion>", self.mover_bloco)
        self.canvas.bind("<ButtonRelease-1>", self.finalizar_arrasto)

    def encontrar_proxima_posicao(self):
        x = 20
        y = self.margem_topo

        # Procurar o primeiro espaço livre (x fixo, y variável)
        while True:
            ocupado = False
            for bloco in self.blocks:
                if bloco["x"] == x and bloco["y"] == y:
                    ocupado = True
                    break
            if not ocupado:
                return x, y
            y += self.block_height + self.espaco_vertical


    def adicionar_bloco(self, nome, cor):
        x, y = self.encontrar_proxima_posicao()
        self.ocupados.add((x, y))

        rect = self.canvas.create_rectangle(x, y, x + self.block_width, y + self.block_height, fill=cor, outline="black")
        label = self.canvas.create_text(x + self.block_width // 2, y + self.block_height // 2, text=nome)

        bloco = {
            "rect": rect,
            "label": label,
            "x": x,
            "y": y,
            "width": self.block_width,
            "height": self.block_height
        }
        self.blocks.append(bloco)
        return bloco

    def canvas_clique(self, event):
        x, y = self.canvas.canvasx(event.x), self.canvas.canvasy(event.y)

        for bloco in self.blocks:
            coords = self.canvas.coords(bloco["rect"])
            if coords[0] <= x <= coords[2] and coords[1] <= y <= coords[3]:
                if self.conectando:
                    if not self.bloco_origem:
                        self.bloco_origem = bloco
                        return
                    else:
                        self.desenhar_linha(self.bloco_origem, bloco)
                        self.bloco_origem = None
                        self.conectando = False
                        return
                else:
                    self.arrastando = bloco
                    self.offset_x = x - coords[0]
                    self.offset_y = y - coords[1]
                    return

    def desenhar_linha(self, origem, destino):
        coords_origem = self.canvas.coords(origem["rect"])
        coords_destino = self.canvas.coords(destino["rect"])

        ox1, oy1, ox2, oy2 = coords_origem
        dx1, dy1, dx2, dy2 = coords_destino

        # Centro dos blocos
        centro_origem = ((ox1 + ox2) / 2, (oy1 + oy2) / 2)
        centro_destino = ((dx1 + dx2) / 2, (dy1 + dy2) / 2)

        # Diferença entre blocos
        dx = centro_destino[0] - centro_origem[0]
        dy = centro_destino[1] - centro_origem[1]

        # Decide ponto de saída e entrada baseado na direção
        if abs(dx) > abs(dy):  # Movimento mais horizontal
            if dx > 0:
                # seta da direita do origem para esquerda do destino
                x1 = ox2
                y1 = centro_origem[1]
                x2 = dx1
                y2 = centro_destino[1]
            else:
                # seta da esquerda do origem para direita do destino
                x1 = ox1
                y1 = centro_origem[1]
                x2 = dx2
                y2 = centro_destino[1]
        else:  # Movimento mais vertical
            if dy > 0:
                # seta de baixo do origem para topo do destino
                x1 = centro_origem[0]
                y1 = oy2
                x2 = centro_destino[0]
                y2 = dy1
            else:
                # seta de cima do origem para base do destino
                x1 = centro_origem[0]
                y1 = oy1
                x2 = centro_destino[0]
                y2 = dy2

        linha = self.canvas.create_line(x1, y1, x2, y2, arrow=tk.LAST, width=2)
        self.setas.append((linha, origem, destino))


    def ativar_conexao(self):
        self.conectando = True
        self.bloco_origem = None

    def mover_bloco(self, event):
        if self.arrastando:
            x = self.canvas.canvasx(event.x)
            y = self.canvas.canvasy(event.y)
            novo_x1 = x - self.offset_x
            novo_y1 = y - self.offset_y
            novo_x2 = novo_x1 + self.block_width
            novo_y2 = novo_y1 + self.block_height

            self.canvas.coords(self.arrastando["rect"], novo_x1, novo_y1, novo_x2, novo_y2)
            self.canvas.coords(self.arrastando["label"], (novo_x1 + novo_x2) // 2, (novo_y1 + novo_y2) // 2)

            self.arrastando["x"] = novo_x1
            self.arrastando["y"] = novo_y1

            self.atualizar_setas()

    def finalizar_arrasto(self, event):
        self.arrastando = None

    def atualizar_setas(self):
        for seta_id, origem, destino in self.setas:
            coords_origem = self.canvas.coords(origem["rect"])
            coords_destino = self.canvas.coords(destino["rect"])

            ox1, oy1, ox2, oy2 = coords_origem
            dx1, dy1, dx2, dy2 = coords_destino

            centro_origem = ((ox1 + ox2) / 2, (oy1 + oy2) / 2)
            centro_destino = ((dx1 + dx2) / 2, (dy1 + dy2) / 2)

            dx = centro_destino[0] - centro_origem[0]
            dy = centro_destino[1] - centro_origem[1]

            if abs(dx) > abs(dy):  # movimento horizontal
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
            else:  # movimento vertical
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

        # Seleção de itens
        self.item_selecionado = None
        self.canvas.bind("<Button-1>", self.selecionar_item, add="+")
        self.root.bind("<Delete>", self.deletar_item)

    def selecionar_item(self, event):
        x, y = self.canvas.canvasx(event.x), self.canvas.canvasy(event.y)
        self.item_selecionado = None

        # Verifica se clicou em uma seta
        for seta_id, origem, destino in self.setas:
            coords = self.canvas.coords(seta_id)
            if self._clicou_em_linha(x, y, coords):
                self.item_selecionado = ("seta", seta_id)
                return

        # Verifica se clicou em um bloco
        for bloco in self.blocks:
            coords = self.canvas.coords(bloco["rect"])
            if coords[0] <= x <= coords[2] and coords[1] <= y <= coords[3]:
                self.item_selecionado = ("bloco", bloco)
                return

    def deletar_item(self, event):
        if self.item_selecionado:
            tipo, item = self.item_selecionado
            if tipo == "bloco":
                self.canvas.delete(item["rect"])
                self.canvas.delete(item["label"])
                self.blocks.remove(item)
                self.ocupados.discard((item["x"], item["y"]))
                # Remove setas conectadas a esse bloco
                self.setas = [
                    (s, o, d) for (s, o, d) in self.setas if o != item and d != item
                ]
                self.canvas.delete("all")
                for bloco in self.blocks:
                    self.canvas.create_rectangle(
                        bloco["x"], bloco["y"],
                        bloco["x"] + bloco["width"], bloco["y"] + bloco["height"],
                        fill=self.canvas.itemcget(bloco["rect"], "fill"), outline="black"
                    )
                    bloco["rect"] = self.canvas.find_all()[-1]
                    bloco["label"] = self.canvas.create_text(
                        bloco["x"] + bloco["width"] // 2,
                        bloco["y"] + bloco["height"] // 2,
                        text=self.canvas.itemcget(bloco["label"], "text")
                    )
                for linha, o, d in self.setas:
                    self.desenhar_linha(o, d)

            elif tipo == "seta":
                self.canvas.delete(item)
                self.setas = [s for s in self.setas if s[0] != item]

            self.item_selecionado = None

    def _clicou_em_linha(self, x, y, coords, margem=5):
        """Verifica se o clique está próximo da linha"""
        if len(coords) < 4:
            return False
        x1, y1, x2, y2 = coords[:4]
        if min(x1, x2) - margem <= x <= max(x1, x2) + margem and min(y1, y2) - margem <= y <= max(y1, y2) + margem:
            # Aproximação simples
            dx, dy = x2 - x1, y2 - y1
            if dx == 0:
                return abs(x - x1) < margem
            m = dy / dx
            b = y1 - m * x1
            y_estimado = m * x + b
            return abs(y - y_estimado) < margem
        return False

# Início do app
root = tk.Tk()
app = FlowchartApp(root)
root.mainloop()
