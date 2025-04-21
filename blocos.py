from PIL import Image, ImageTk
import os
# blocos.py

class BlocoManager:
    def __init__(self, canvas, app):
        self.canvas = canvas
        self.app = app
        self.blocks = []
        self.ocupados = set()
        self.block_width = 60
        self.block_height = 60
        self.margem_topo = 20
        self.espaco_vertical = 20
        self.arrastando = None
        self.item_selecionado = None
        self.borda_selecionada = None
        self.offset_x = 0
        self.offset_y = 0
        self.imagens = {}  # ← cache para manter referências dos ícones

    def encontrar_proxima_posicao(self):
        x = 20
        y = self.margem_topo
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
    
        nome_arquivo = self._mapear_nome_para_icone(nome)
        caminho_icone = os.path.join("icons", nome_arquivo)
    
        # Cria retângulo invisível só para detecção de clique
        rect = self.canvas.create_rectangle(
            x, y, x + self.block_width, y + self.block_height,
            outline="", fill=""
        )
    
        # 🔧 DEFINE O ID ANTES DE USAR
        bloco_id = f"{nome}_{len(self.blocks)}"
    
        # Carrega imagem e insere
        if os.path.exists(caminho_icone):
            img = Image.open(caminho_icone).resize((self.block_width, self.block_height), Image.Resampling.LANCZOS)
            tk_img = ImageTk.PhotoImage(img)
            self.imagens[bloco_id] = tk_img  # ← cache com ID único
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
            "fill": cor,
            "text": nome,
            "id": bloco_id  # ← SALVA O ID DENTRO DO BLOCO
        }
        self.blocks.append(bloco)
        return bloco


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

    def canvas_clique(self, event):
        x, y = self.canvas.canvasx(event.x), self.canvas.canvasy(event.y)

        self.arrastando = None
        self.app.item_selecionado = None
        self.remover_destaque()

        for bloco in self.blocks:
            coords = self.canvas.coords(bloco["rect"])
            if coords[0] <= x <= coords[2] and coords[1] <= y <= coords[3]:
                if self.app.setas.conectando:
                    if not self.app.setas.bloco_origem:
                        self.app.setas.bloco_origem = bloco
                        return
                    else:
                        self.app.setas.desenhar_linha(self.app.setas.bloco_origem, bloco)
                        self.app.setas.bloco_origem = None
                        self.app.setas.conectando = False
                        return
                else:
                    self.arrastando = bloco

                    if bloco.get("icon"):
                        coords_img = self.canvas.coords(bloco["icon"])
                        self.offset_x = x - coords_img[0]
                        self.offset_y = y - coords_img[1]
                    else:
                        # fallback para centro do retângulo invisível
                        coords_rect = self.canvas.coords(bloco["rect"])
                        self.offset_x = x - coords_rect[0]
                        self.offset_y = y - coords_rect[1]

                    self.app.item_selecionado = ("bloco", bloco)
                    self.destacar_bloco(bloco)
                    return

        self.app.setas.selecionar_item(event)

    
    def mover_bloco(self, event):
        if self.arrastando:
            x = self.canvas.canvasx(event.x)
            y = self.canvas.canvasy(event.y)
            novo_x1 = x - self.offset_x
            novo_y1 = y - self.offset_y
            novo_x2 = novo_x1 + self.block_width
            novo_y2 = novo_y1 + self.block_height

            self.canvas.coords(self.arrastando["rect"], novo_x1, novo_y1, novo_x2, novo_y2)
            if self.arrastando["icon"]:
                self.canvas.coords(self.arrastando["icon"], novo_x1, novo_y1)


            self.arrastando["x"] = novo_x1
            self.arrastando["y"] = novo_y1

            if self.borda_selecionada:
                self.canvas.coords(self.borda_selecionada, novo_x1 - 2, novo_y1 - 2, novo_x2 + 2, novo_y2 + 2)

            self.app.setas.atualizar_setas()


    def finalizar_arrasto(self, event):
        self.arrastando = None

    def remover_destaque(self):
        if self.borda_selecionada:
            self.canvas.delete(self.borda_selecionada)
            self.borda_selecionada = None

        if self.app.item_selecionado and self.app.item_selecionado[0] == "seta":
            seta_antiga_id = self.app.item_selecionado[1]
            self.canvas.itemconfig(seta_antiga_id, fill="black")  # volta a cor original
    def selecionar_bloco(self, bloco):
        # Remove borda anterior
        if self.borda_selecionada:
            self.canvas.delete(self.borda_selecionada)
            self.borda_selecionada = None

        self.app.item_selecionado = ("bloco", bloco)

        x1 = bloco["x"] - 2
        y1 = bloco["y"] - 2
        x2 = bloco["x"] + bloco["width"] + 2
        y2 = bloco["y"] + bloco["height"] + 2

        self.borda_selecionada = self.canvas.create_rectangle(
            x1, y1, x2, y2, outline="blue", width=2, dash=(4, 2)
        )
        self.canvas.tag_lower(self.borda_selecionada, bloco["rect"])

    def destacar_bloco(self, bloco):
        self.selecionar_bloco(bloco)
