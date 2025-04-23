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

        self.linha_temporaria = None

        self.handle_drag = None          # (bloco_origem, linha_temp_id)
        self.alvo_proximo = None         # bloco que está “magnetizado”


    #  setas.py  ─ dentro da classe SetaManager
    def iniciar_conexao(self, bloco_origem, event):
        #  ⬇  pega o centro do bloco; se não existir, aborta silenciosamente
        centro = self._centro_bloco(bloco_origem)
        if centro is None:
            return                      # bloco foi removido → nada a fazer
    
        x1, y1 = centro
        x2, y2 = self.canvas.canvasx(event.x), self.canvas.canvasy(event.y)
    
        temp = self.canvas.create_line(
            x1, y1, x2, y2,
            fill="#0a84ff", dash=(4, 2), width=2
        )
        self.handle_drag = (bloco_origem, temp)
        #self.canvas.bind("<B1-Motion>", self._arrastando_handle)
        self.canvas.bind("<B1-Motion>", self._arrastando_handle, add="+")
        self.canvas.bind("<ButtonRelease-1>", self._finalizar_handle, add="+")


    def _arrastando_handle(self, event):
        if not self.handle_drag:
            return
        origem, temp = self.handle_drag
        x1, y1 = self._centro_bloco(origem)
        x2, y2 = self.canvas.canvasx(event.x), self.canvas.canvasy(event.y)

        # procura bloco mais próximo (centro) dentro de 25 px
        alvo, dist2 = None, 25**2
        for bloco in self.blocos.blocks:
            if bloco is origem:
                continue
            c = self._centro_bloco(bloco)
            if c is None:
                continue          # ignora blocos órfãos
            cx, cy = c
            d2 = (cx - x2)**2 + (cy - y2)**2
            if d2 < dist2:
                alvo, dist2 = bloco, d2
                x2, y2 = cx, cy      # “gruda” a linha
        # realça o bloco alvo
        if alvo is not self.alvo_proximo:
            # remove highlight anterior
            if self.alvo_proximo and self.alvo_proximo.get("highlight"):
                self.canvas.delete(self.alvo_proximo["highlight"])
                self.alvo_proximo["highlight"] = None
            self.alvo_proximo = alvo
            if alvo:
                bx1, by1, bx2, by2 = self.canvas.coords(alvo["rect"])
                alvo["highlight"] = self.canvas.create_rectangle(
                    bx1-3, by1-3, bx2+3, by2+3,
                    outline="#0a84ff", width=2, dash=(2, 2)
                )
        if x2 is None or y2 is None:
            return            # ainda não há destino “magnético”

        # atualiza a linha temporária
        self.canvas.coords(temp, x1, y1, x2, y2)

    def _finalizar_handle(self, event):
        #self.canvas.unbind("<B1-Motion>")
        #self.canvas.unbind("<ButtonRelease-1>")
        if not self.handle_drag:
            return
        origem, temp = self.handle_drag
        self.canvas.delete(temp)
        self.handle_drag = None

        destino = self.alvo_proximo
        # limpa highlight
        if destino and destino.get("highlight"):
            self.canvas.delete(destino["highlight"])
            destino["highlight"] = None
        self.alvo_proximo = None

         # ------------ BLINDAGENS ------------
        if not destino:                 # soltou fora de qualquer bloco
            return
        if destino is origem:           # evita seta origem→origem
            return
        if self._centro_bloco(destino) is None:
            return                      # destino foi removido no meio do arrasto
        # ------------------------------------
        if destino:
            self.desenhar_linha(origem, destino)

    def atualizar_linha_temporaria(self, event):
        if self.linha_temporaria and self.bloco_origem:
            x1, y1 = self._centro_bloco(self.bloco_origem)
            x2, y2 = self.canvas.canvasx(event.x), self.canvas.canvasy(event.y)
            self.canvas.coords(self.linha_temporaria, x1, y1, x2, y2)


    def atualizar_linha_temp_evento(self, event):
        x = self.canvas.canvasx(event.x)
        y = self.canvas.canvasy(event.y)
        self.atualizar_linha_temp(x, y)

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
                x, y = self._centro_bloco(bloco)
                self.linha_temporaria = self.canvas.create_line(x, y, x, y, fill="gray", dash=(4, 2), width=2)
                self.canvas.bind("<Motion>", self.atualizar_linha_temporaria)
            else:
                self.canvas.unbind("<Motion>")
                if self.linha_temporaria:
                    self.canvas.delete(self.linha_temporaria)
                    self.linha_temporaria = None
                self.desenhar_linha(self.bloco_origem, bloco)
                self.bloco_origem = None
                self.conectando = False

    def _centro_bloco(self, bloco):
        coords = self.canvas.coords(bloco["rect"])
        if len(coords) < 4:           # retângulo já foi excluído
            return None
        x1, y1, x2, y2 = coords
        return (x1 + x2) / 2, (y1 + y2) / 2


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
        ctrl = event.state & 0x0004  # Ctrl pressionado

        # Verifica se clicou em uma seta
        for seta_id, origem, destino in self.setas:
            coords = self.canvas.coords(seta_id)
            if clicou_em_linha(x, y, coords, margem=10):
                # helpers locais ----------------------------------
                def _destacar(sid):
                    self.canvas.itemconfig(
                        sid,
                        fill="#0a84ff",  # azul
                        width=3,
                        dash=(4, 2)
                    )

                def _remover_destaque(sid):
                    self.canvas.itemconfig(
                        sid,
                        fill="black",
                        width=2,
                        dash=()          # sem tracejado
                    )

                if ctrl:
                    if ("seta", seta_id) in self.blocos.app.itens_selecionados:
                        self.blocos.app.itens_selecionados.remove(("seta", seta_id))
                        _remover_destaque(seta_id)
                    else:
                        self.blocos.app.itens_selecionados.append(("seta", seta_id))
                        _destacar(seta_id)
                else:
                    self._limpar_selecao()
                    self.blocos.app.itens_selecionados = [("seta", seta_id)]
                    _destacar(seta_id)
                return

        # Verifica se clicou em um bloco
        for bloco in self.blocos.blocks:
            coords = self.canvas.coords(bloco["rect"])
            if coords[0] <= x <= coords[2] and coords[1] <= y <= coords[3]:
                if ctrl:
                    if ("bloco", bloco) in self.blocos.app.itens_selecionados:
                        self.blocos.app.itens_selecionados.remove(("bloco", bloco))
                        if bloco.get("borda"):
                            self.canvas.delete(bloco["borda"])
                            bloco["borda"] = None
                    else:
                        borda = self.canvas.create_rectangle(
                            coords[0]-2, coords[1]-2, coords[2]+2, coords[3]+2,
                            outline="blue", width=2, dash=(4, 2)
                        )
                        self.canvas.tag_lower(borda, bloco["rect"])
                        bloco["borda"] = borda
                        self.blocos.app.itens_selecionados.append(("bloco", bloco))
                else:
                    self._limpar_selecao()
                    borda = self.canvas.create_rectangle(
                        coords[0]-2, coords[1]-2, coords[2]+2, coords[3]+2,
                        outline="blue", width=2, dash=(4, 2)
                    )
                    self.canvas.tag_lower(borda, bloco["rect"])
                    bloco["borda"] = borda
                    self.blocos.app.itens_selecionados = [("bloco", bloco)]
                return

        if not ctrl:
            self._limpar_selecao()

    def deletar_item(self, event):
        if self.blocos.app.item_selecionado:
            tipo, item = self.blocos.app.item_selecionado

            if tipo == "bloco":
                self.canvas.delete(item["rect"])
                if item.get("icon"):
                    self.canvas.delete(item["icon"])

                for h in item.get("handles", []):
                    self.canvas.delete(h)

                # Remove a borda se existir (seleção única)
                if self.blocos.borda_selecionada:
                    self.canvas.delete(self.blocos.borda_selecionada)
                    self.blocos.borda_selecionada = None

                # Remove a borda se for de seleção múltipla
                if item.get("borda"):
                    self.canvas.delete(item["borda"])
                    item["borda"] = None

                # Remove imagem do cache
                bloco_id = item.get("id") or item.get("bloco_id")
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

                # Limpa seleção múltipla
                self.blocos.blocos_selecionados = [b for b in self.blocos.blocos_selecionados if b != item]

            if item in self.seta_highlights:
                self.canvas.delete(self.seta_highlights.pop(item))
            self.canvas.itemconfig(item, fill="black")

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

    def _limpar_selecao(self):
        for tipo, item in self.blocos.app.itens_selecionados:
            if tipo == "bloco" and item.get("borda"):
                self.canvas.delete(item["borda"])
                item["borda"] = None
            elif tipo == "seta":
                # restaura configurações-padrão da linha
                self.canvas.itemconfig(item, fill="black", width=2, dash=())
    limpar_selecao = _limpar_selecao