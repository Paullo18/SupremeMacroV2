from util import clicou_em_linha
import os
from PIL import Image, ImageTk

class SetaManager:
    def __init__(self, canvas, blocos):
        self.canvas = canvas
        self.blocos = blocos
        self.setas = []  # Mantém formato (seta_id, origem, destino) para compatibilidade
        self._setas_info = {}  # Dicionário para armazenar informações adicionais: {seta_id: (segmentos, tag)}
        self.bloco_origem = None
        self.conectando = False
        self.ultima_seta_selecionada = None  # ← guarda referência da última seta azul
        self.seta_highlights = {}  # Para armazenar os destaques das setas

        self.linha_temporaria = None

        self.handle_drag = None          # (bloco_origem, linha_temp_id)
        self.alvo_proximo = None         # bloco que está "magnetizado"

        self._cor_original = {}      # {segmento_id: cor_original}
        
        # Registrar callback para atualização de setas quando blocos são movidos
        if hasattr(self.blocos, "register_move_callback"):
            self.blocos.register_move_callback(self.atualizar_setas)

        self.patch_undo()
        self.patch_snapshot()

    def patch_undo(self):
        """
        Depois que um snapshot é restaurado (Ctrl+Z ou Ctrl+Y),
        forçamos o redesenho das setas.
        """
        if hasattr(self.blocos, "desfazer"):
            original_desfazer = self.blocos.desfazer

            def patched_desfazer(self_blocos, *args, **kwargs):
                resultado = original_desfazer(*args, **kwargs)
                # Blocos voltaram para a posição salva ➔ redesenha setas
                self.atualizar_setas()
                return resultado

            # substitui o método
            self.blocos.desfazer = patched_desfazer.__get__(self.blocos,
                                                        type(self.blocos))
    def _obter_segmentos(self, seta_id):
        #info = self._setas_info.get(seta_id)
        #return info[0] if info else [seta_id]
        """
        Devolve a lista de segmentos que compõem essa seta.
        Se a seta for antiga (apenas um segmento), devolve [seta_id].
        """
        if seta_id in self._setas_info:
            return self._setas_info[seta_id][0]      # (segmentos, tag)
        return [seta_id]


    def iniciar_conexao(self, bloco_origem, event, branch=None):
        self.branch = branch  # salva se é true/false
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
        self.canvas.bind("<B1-Motion>", self._arrastando_handle, add="+")
        self.canvas.bind("<ButtonRelease-1>", self._finalizar_handle, add="+")


    def _arrastando_handle(self, event):
        if not self.handle_drag:
            return
        origem, temp = self.handle_drag
        x1, y1 = self._centro_bloco(origem)
        if x1 is None or y1 is None:  # Verificação de segurança
            return
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
                x2, y2 = cx, cy      # "gruda" a linha
        # realça o bloco alvo
        if alvo is not self.alvo_proximo:
            # remove highlight anterior
            if self.alvo_proximo and self.alvo_proximo.get("highlight"):
                self.canvas.delete(self.alvo_proximo["highlight"])
                self.alvo_proximo["highlight"] = None
            self.alvo_proximo = alvo
            if alvo:
                coords = self.canvas.coords(alvo["rect"])
                if len(coords) >= 4:  # Verificação de segurança
                    bx1, by1, bx2, by2 = coords
                    alvo["highlight"] = self.canvas.create_rectangle(
                        bx1-3, by1-3, bx2+3, by2+3,
                        outline="#0a84ff", width=2, dash=(2, 2)
                    )
        if x2 is None or y2 is None:
            return            # ainda não há destino "magnético"

        # atualiza a linha temporária
        self.canvas.coords(temp, x1, y1, x2, y2)

    def _finalizar_handle(self, event):
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
            centro = self._centro_bloco(self.bloco_origem)
            if centro is None:  # Verificação de segurança
                return
            x1, y1 = centro
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
                centro = self._centro_bloco(bloco)
                if centro is None:  # Verificação de segurança
                    return
                x, y = centro
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
        """
        Retorna o centro do bloco ou None se o bloco não existir mais.
        """
        try:
            coords = self.canvas.coords(bloco["rect"])
            if len(coords) < 4:           # retângulo já foi excluído
                return None
            x1, y1, x2, y2 = coords
            return (x1 + x2) / 2, (y1 + y2) / 2
        except (KeyError, TypeError):
            # Bloco não tem a chave "rect" ou não é um dicionário
            return None
    
    def _encontrar_pontos_ancora(self, origem, destino):
        """
        Determina os pontos de ancoragem ideais para a seta entre dois blocos,
        escolhendo as bordas mais apropriadas com base na posição relativa.
        """
        try:
            # Obter coordenadas dos blocos
            coords_origem = self.canvas.coords(origem["rect"])
            coords_destino = self.canvas.coords(destino["rect"])
            
            if len(coords_origem) < 4 or len(coords_destino) < 4:
                return None, None
                
            ox1, oy1, ox2, oy2 = coords_origem
            dx1, dy1, dx2, dy2 = coords_destino
            
            # Calcular centros dos blocos
            centro_origem = ((ox1 + ox2) / 2, (oy1 + oy2) / 2)
            centro_destino = ((dx1 + dx2) / 2, (dy1 + dy2) / 2)
            
            # Calcular diferenças entre os centros
            delta_x = centro_destino[0] - centro_origem[0]
            delta_y = centro_destino[1] - centro_origem[1]
            
            # Verificar se os blocos se sobrepõem em algum eixo
            sobreposicao_x = (ox1 <= dx2 and ox2 >= dx1)
            sobreposicao_y = (oy1 <= dy2 and oy2 >= dy1)
            
            # Determinar qual borda usar com base na posição relativa
            if sobreposicao_y and not sobreposicao_x:
                # Blocos estão alinhados verticalmente
                if delta_x > 0:
                    # Destino à direita
                    ponto_origem = (ox2, centro_origem[1])  # Borda direita da origem
                    ponto_destino = (dx1, centro_destino[1])  # Borda esquerda do destino
                else:
                    # Destino à esquerda
                    ponto_origem = (ox1, centro_origem[1])  # Borda esquerda da origem
                    ponto_destino = (dx2, centro_destino[1])  # Borda direita do destino
            elif sobreposicao_x and not sobreposicao_y:
                # Blocos estão alinhados horizontalmente
                if delta_y > 0:
                    # Destino abaixo
                    ponto_origem = (centro_origem[0], oy2)  # Borda inferior da origem
                    ponto_destino = (centro_destino[0], dy1)  # Borda superior do destino
                else:
                    # Destino acima
                    ponto_origem = (centro_origem[0], oy1)  # Borda superior da origem
                    ponto_destino = (centro_destino[0], dy2)  # Borda inferior do destino
            else:
                # Blocos não estão alinhados, escolher a melhor borda
                # Determinar qual dimensão tem maior diferença
                if abs(delta_x) > abs(delta_y):
                    # Diferença horizontal é maior
                    if delta_x > 0:
                        # Destino à direita
                        ponto_origem = (ox2, centro_origem[1])  # Borda direita da origem
                        ponto_destino = (dx1, centro_destino[1])  # Borda esquerda do destino
                    else:
                        # Destino à esquerda
                        ponto_origem = (ox1, centro_origem[1])  # Borda esquerda da origem
                        ponto_destino = (dx2, centro_destino[1])  # Borda direita do destino
                else:
                    # Diferença vertical é maior
                    if delta_y > 0:
                        # Destino abaixo
                        ponto_origem = (centro_origem[0], oy2)  # Borda inferior da origem
                        ponto_destino = (centro_destino[0], dy1)  # Borda superior do destino
                    else:
                        # Destino acima
                        ponto_origem = (centro_origem[0], oy1)  # Borda superior da origem
                        ponto_destino = (centro_destino[0], dy2)  # Borda inferior do destino
                    
            return ponto_origem, ponto_destino
        except (KeyError, TypeError):
            # Bloco não tem a chave "rect" ou não é um dicionário
            return None, None

    def _verificar_sobreposicao_com_blocos(self, x1, y1, x2, y2):
        """
        Verifica se uma linha entre dois pontos se sobrepõe com algum bloco.
        Retorna True se houver sobreposição, False caso contrário.
        """
        # Verificar apenas se os pontos não estão alinhados (linha não é reta)
        if abs(x1 - x2) < 1 or abs(y1 - y2) < 1:
            return False
            
        for bloco in self.blocos.blocks:
            try:
                coords = self.canvas.coords(bloco["rect"])
                if len(coords) < 4:
                    continue
                    
                bx1, by1, bx2, by2 = coords
                
                # Verificar se a linha horizontal cruza o bloco
                if min(x1, x2) < bx2 and max(x1, x2) > bx1:
                    if y1 > by1 and y1 < by2:
                        return True
                        
                # Verificar se a linha vertical cruza o bloco
                if min(y1, y2) < by2 and max(y1, y2) > by1:
                    if x2 > bx1 and x2 < bx2:
                        return True
            except:
                continue
                
        return False

    def _encontrar_caminho_externo(self, x1, y1, x2, y2, origem, destino):
        """
        Encontra um caminho que contorna os blocos pelo lado externo,
        similar ao caminho vermelho mostrado no exemplo.
        """
        try:
            # Obter coordenadas dos blocos
            coords_origem = self.canvas.coords(origem["rect"])
            coords_destino = self.canvas.coords(destino["rect"])
            
            if len(coords_origem) < 4 or len(coords_destino) < 4:
                return None
                
            ox1, oy1, ox2, oy2 = coords_origem
            dx1, dy1, dx2, dy2 = coords_destino
            
            # Calcular centros dos blocos
            centro_origem = ((ox1 + ox2) / 2, (oy1 + oy2) / 2)
            centro_destino = ((dx1 + dx2) / 2, (dy1 + dy2) / 2)
            
            # Calcular diferenças entre os centros
            delta_x = centro_destino[0] - centro_origem[0]
            delta_y = centro_destino[1] - centro_origem[1]
            
            # Determinar qual borda do bloco de origem estamos usando
            borda_origem = ""
            if abs(x1 - ox1) < 1:  # Borda esquerda
                borda_origem = "esquerda"
            elif abs(x1 - ox2) < 1:  # Borda direita
                borda_origem = "direita"
            elif abs(y1 - oy1) < 1:  # Borda superior
                borda_origem = "superior"
            elif abs(y1 - oy2) < 1:  # Borda inferior
                borda_origem = "inferior"
            
            # Determinar qual borda do bloco de destino estamos usando
            borda_destino = ""
            if abs(x2 - dx1) < 1:  # Borda esquerda
                borda_destino = "esquerda"
            elif abs(x2 - dx2) < 1:  # Borda direita
                borda_destino = "direita"
            elif abs(y2 - dy1) < 1:  # Borda superior
                borda_destino = "superior"
            elif abs(y2 - dy2) < 1:  # Borda inferior
                borda_destino = "inferior"
            
            # Encontrar os limites do canvas (ou usar valores grandes o suficiente)
            canvas_width = self.canvas.winfo_width() or 2000
            canvas_height = self.canvas.winfo_height() or 2000
            
            # Calcular margens para o caminho externo
            margem_x = 30  # Distância horizontal do caminho em relação aos blocos
            margem_y = 20  # Distância vertical do caminho em relação aos blocos
            
            # Encontrar os limites externos (esquerda e direita)
            limite_esquerdo = min(ox1, dx1) - margem_x
            limite_direito = max(ox2, dx2) + margem_x
            
            # Encontrar os limites externos (superior e inferior)
            limite_superior = min(oy1, dy1) - margem_y
            limite_inferior = max(oy2, dy2) + margem_y
            
            # Garantir que os limites estão dentro do canvas
            limite_esquerdo = max(10, limite_esquerdo)
            limite_direito = min(canvas_width - 10, limite_direito)
            limite_superior = max(10, limite_superior)
            limite_inferior = min(canvas_height - 10, limite_inferior)
            
            # Pontos para o caminho
            pontos = [(x1, y1)]  # Ponto inicial
            
            # Determinar o tipo de caminho externo com base nas bordas
            if (borda_origem == "esquerda" and borda_destino == "esquerda") or \
               (borda_origem == "direita" and borda_destino == "direita"):
                # Ambos os blocos têm conexões na mesma lateral
                # Usar um caminho que vai para fora e volta
                if borda_origem == "esquerda":
                    # Ambos na esquerda - ir para a esquerda
                    pontos.append((limite_esquerdo, y1))
                    pontos.append((limite_esquerdo, y2))
                    pontos.append((x2, y2))
                else:
                    # Ambos na direita - ir para a direita
                    pontos.append((limite_direito, y1))
                    pontos.append((limite_direito, y2))
                    pontos.append((x2, y2))
            elif (borda_origem == "superior" and borda_destino == "superior") or \
                 (borda_origem == "inferior" and borda_destino == "inferior"):
                # Ambos os blocos têm conexões na mesma altura
                # Usar um caminho que vai para cima/baixo e volta
                if borda_origem == "superior":
                    # Ambos em cima - ir para cima
                    pontos.append((x1, limite_superior))
                    pontos.append((x2, limite_superior))
                    pontos.append((x2, y2))
                else:
                    # Ambos embaixo - ir para baixo
                    pontos.append((x1, limite_inferior))
                    pontos.append((x2, limite_inferior))
                    pontos.append((x2, y2))
            elif (borda_origem == "esquerda" and borda_destino == "superior") or \
                 (borda_origem == "esquerda" and borda_destino == "inferior"):
                # Origem na esquerda, destino em cima ou embaixo
                # Ir para a esquerda e depois para cima/baixo
                pontos.append((limite_esquerdo, y1))
                pontos.append((limite_esquerdo, y2))
                pontos.append((x2, y2))
            elif (borda_origem == "direita" and borda_destino == "superior") or \
                 (borda_origem == "direita" and borda_destino == "inferior"):
                # Origem na direita, destino em cima ou embaixo
                # Ir para a direita e depois para cima/baixo
                pontos.append((limite_direito, y1))
                pontos.append((limite_direito, y2))
                pontos.append((x2, y2))
            elif (borda_origem == "superior" and borda_destino == "esquerda") or \
                 (borda_origem == "superior" and borda_destino == "direita"):
                # Origem em cima, destino na esquerda ou direita
                # Ir para cima e depois para esquerda/direita
                pontos.append((x1, limite_superior))
                pontos.append((x2, limite_superior))
                pontos.append((x2, y2))
            elif (borda_origem == "inferior" and borda_destino == "esquerda") or \
                 (borda_origem == "inferior" and borda_destino == "direita"):
                # Origem embaixo, destino na esquerda ou direita
                # Ir para baixo e depois para esquerda/direita
                pontos.append((x1, limite_inferior))
                pontos.append((x2, limite_inferior))
                pontos.append((x2, y2))
            else:
                # Caso padrão - usar caminho em L
                if abs(delta_x) > abs(delta_y):
                    # Ir primeiro na horizontal, depois na vertical
                    pontos.append((x2, y1))
                    pontos.append((x2, y2))
                else:
                    # Ir primeiro na vertical, depois na horizontal
                    pontos.append((x1, y2))
                    pontos.append((x2, y2))
                
            return pontos
        except:
            # Em caso de erro, retornar None para usar o caminho padrão
            return None

    def _calcular_pontos_ortogonais(self, x1, y1, x2, y2, origem, destino):
        """
        Calcula os pontos para criar um caminho ortogonal entre dois pontos.
        Retorna uma lista de pontos que formam o caminho.
        """
        # Determinar se é melhor ir primeiro na horizontal ou na vertical
        delta_x = abs(x2 - x1)
        delta_y = abs(y2 - y1)
        
        pontos = []
        pontos.append((x1, y1))  # Ponto inicial
        
        # Se os pontos estão alinhados horizontalmente ou verticalmente, usar linha reta
        if abs(x1 - x2) < 1:  # Alinhados verticalmente (com tolerância)
            pontos.append((x2, y2))  # Linha reta vertical
        elif abs(y1 - y2) < 1:  # Alinhados horizontalmente (com tolerância)
            pontos.append((x2, y2))  # Linha reta horizontal
        else:
            # Obter coordenadas dos blocos para análise
            try:
                coords_origem = self.canvas.coords(origem["rect"])
                coords_destino = self.canvas.coords(destino["rect"])
                
                if len(coords_origem) < 4 or len(coords_destino) < 4:
                    # Fallback para caminho simples se não conseguir obter coordenadas
                    if delta_x > delta_y:
                        # Ir primeiro na horizontal, depois na vertical
                        pontos.append((x2, y1))  # Ponto intermediário
                        pontos.append((x2, y2))  # Ponto final
                    else:
                        # Ir primeiro na vertical, depois na horizontal
                        pontos.append((x1, y2))  # Ponto intermediário
                        pontos.append((x2, y2))  # Ponto final
                    return pontos
                    
                ox1, oy1, ox2, oy2 = coords_origem
                dx1, dy1, dx2, dy2 = coords_destino
                
                # Determinar qual borda do bloco de origem estamos usando
                borda_origem = ""
                if abs(x1 - ox1) < 1:  # Borda esquerda
                    borda_origem = "esquerda"
                elif abs(x1 - ox2) < 1:  # Borda direita
                    borda_origem = "direita"
                elif abs(y1 - oy1) < 1:  # Borda superior
                    borda_origem = "superior"
                elif abs(y1 - oy2) < 1:  # Borda inferior
                    borda_origem = "inferior"
                
                # Determinar qual borda do bloco de destino estamos usando
                borda_destino = ""
                if abs(x2 - dx1) < 1:  # Borda esquerda
                    borda_destino = "esquerda"
                elif abs(x2 - dx2) < 1:  # Borda direita
                    borda_destino = "direita"
                elif abs(y2 - dy1) < 1:  # Borda superior
                    borda_destino = "superior"
                elif abs(y2 - dy2) < 1:  # Borda inferior
                    borda_destino = "inferior"
                
                # Escolher o caminho mais adequado com base nas bordas
                if (borda_origem == "direita" and borda_destino == "esquerda") or \
                   (borda_origem == "esquerda" and borda_destino == "direita"):
                    # Conexão horizontal direta (bordas laterais)
                    # Calcular ponto médio para evitar sobreposição com outros blocos
                    mid_x = (x1 + x2) / 2
                    pontos.append((mid_x, y1))  # Ponto intermediário 1
                    pontos.append((mid_x, y2))  # Ponto intermediário 2
                    pontos.append((x2, y2))  # Ponto final
                elif (borda_origem == "superior" and borda_destino == "inferior") or \
                     (borda_origem == "inferior" and borda_destino == "superior"):
                    # Conexão vertical direta (bordas superior/inferior)
                    # Calcular ponto médio para evitar sobreposição com outros blocos
                    mid_y = (y1 + y2) / 2
                    pontos.append((x1, mid_y))  # Ponto intermediário 1
                    pontos.append((x2, mid_y))  # Ponto intermediário 2
                    pontos.append((x2, y2))  # Ponto final
                elif borda_origem == "direita" and borda_destino == "superior":
                    # Origem à esquerda, destino abaixo - caminho em L
                    pontos.append((x2, y1))  # Ponto intermediário
                    pontos.append((x2, y2))  # Ponto final
                elif borda_origem == "direita" and borda_destino == "inferior":
                    # Origem à esquerda, destino acima - caminho em L
                    pontos.append((x2, y1))  # Ponto intermediário
                    pontos.append((x2, y2))  # Ponto final
                elif borda_origem == "esquerda" and borda_destino == "superior":
                    # Origem à direita, destino abaixo - caminho em L
                    pontos.append((x2, y1))  # Ponto intermediário
                    pontos.append((x2, y2))  # Ponto final
                elif borda_origem == "esquerda" and borda_destino == "inferior":
                    # Origem à direita, destino acima - caminho em L
                    pontos.append((x2, y1))  # Ponto intermediário
                    pontos.append((x2, y2))  # Ponto final
                elif borda_origem == "inferior" and borda_destino == "esquerda":
                    # Origem acima, destino à direita - caminho em L
                    pontos.append((x1, y2))  # Ponto intermediário
                    pontos.append((x2, y2))  # Ponto final
                elif borda_origem == "inferior" and borda_destino == "direita":
                    # Origem acima, destino à esquerda - caminho em L
                    pontos.append((x1, y2))  # Ponto intermediário
                    pontos.append((x2, y2))  # Ponto final
                elif borda_origem == "superior" and borda_destino == "esquerda":
                    # Origem abaixo, destino à direita - caminho em L
                    pontos.append((x1, y2))  # Ponto intermediário
                    pontos.append((x2, y2))  # Ponto final
                elif borda_origem == "superior" and borda_destino == "direita":
                    # Origem abaixo, destino à esquerda - caminho em L
                    pontos.append((x1, y2))  # Ponto intermediário
                    pontos.append((x2, y2))  # Ponto final
                else:
                    # Caso padrão - usar caminho baseado na distância
                    if delta_x > delta_y:
                        # Ir primeiro na horizontal, depois na vertical
                        pontos.append((x2, y1))  # Ponto intermediário
                        pontos.append((x2, y2))  # Ponto final
                    else:
                        # Ir primeiro na vertical, depois na horizontal
                        pontos.append((x1, y2))  # Ponto intermediário
                        pontos.append((x2, y2))  # Ponto final
            except (KeyError, TypeError):
                # Fallback para caminho simples se ocorrer algum erro
                if delta_x > delta_y:
                    # Ir primeiro na horizontal, depois na vertical
                    pontos.append((x2, y1))  # Ponto intermediário
                    pontos.append((x2, y2))  # Ponto final
                else:
                    # Ir primeiro na vertical, depois na horizontal
                    pontos.append((x1, y2))  # Ponto intermediário
                    pontos.append((x2, y2))  # Ponto final
            
        return pontos

    def desenhar_linha(self, origem, destino, cor_override=None):
        """
        Desenha uma linha ortogonal entre dois blocos.
        """
        # Encontrar pontos de ancoragem nas bordas dos blocos
        ponto_origem, ponto_destino = self._encontrar_pontos_ancora(origem, destino)
        
        if ponto_origem is None or ponto_destino is None:
            return
            
        # Determinar a cor da linha
        # verifica se é fork marcado como Nova Thread
        forks  = origem.get("acao", {}).get("forks", {})
        dest_id = destino.get("id")
        if dest_id in forks and forks[dest_id] == "Nova Thread":
            color = "#0a84ff"   # azul
        else:
            # preserva cor antiga, se houver
            if cor_override is not None:
                color = cor_override
            elif getattr(self, "branch", None) == "true":
                color = "green"
            elif getattr(self, "branch", None) == "false":
                color = "red"
            else:
                color = "#000"
        # -------------------------------------
            
        # Criar um identificador único para esta conexão
        origem_id = origem.get("id", id(origem))
        destino_id = destino.get("id", id(destino))
        conexao_tag = f"seta_{origem_id}_{destino_id}"
        
        # Obter coordenadas
        x1, y1 = ponto_origem
        x2, y2 = ponto_destino
        
        # Primeiro, tentar o caminho padrão
        pontos = self._calcular_pontos_ortogonais(x1, y1, x2, y2, origem, destino)
        
        # Verificar se o caminho padrão tem sobreposição com blocos
        tem_sobreposicao = False
        if len(pontos) > 2:  # Se não for uma linha reta
            # Verificar sobreposição do primeiro segmento
            tem_sobreposicao = self._verificar_sobreposicao_com_blocos(
                pontos[0][0], pontos[0][1], pontos[1][0], pontos[1][1]
            )
            
            # Se não tiver sobreposição no primeiro segmento, verificar o segundo
            if not tem_sobreposicao and len(pontos) > 2:
                tem_sobreposicao = self._verificar_sobreposicao_com_blocos(
                    pontos[1][0], pontos[1][1], pontos[2][0], pontos[2][1]
                )
        
        # Se tiver sobreposição, usar o caminho externo
        if tem_sobreposicao:
            caminho_externo = self._encontrar_caminho_externo(x1, y1, x2, y2, origem, destino)
            if caminho_externo:
                pontos = caminho_externo
        
        # Criar os segmentos de linha
        segmentos = []
        
        # Se temos apenas dois pontos (linha reta), criar uma única linha
        if len(pontos) == 2:
            linha_id = self.canvas.create_line(
                pontos[0][0], pontos[0][1], pontos[1][0], pontos[1][1],
                arrow="last", width=2, fill=color,
                tags=("seta", conexao_tag)
            )
            segmentos.append(linha_id)
        else:
            # Criar segmentos intermediários sem seta
            for i in range(len(pontos) - 2):
                seg = self.canvas.create_line(
                    pontos[i][0], pontos[i][1], pontos[i+1][0], pontos[i+1][1],
                    width=2, fill=color,
                    tags=("seta_segmento", conexao_tag)
                )
                segmentos.append(seg)
                
            # Criar o último segmento com seta
            linha_id = self.canvas.create_line(
                pontos[-2][0], pontos[-2][1], pontos[-1][0], pontos[-1][1],
                arrow="last", width=2, fill=color,
                tags=("seta", conexao_tag)
            )
            segmentos.append(linha_id)
        
        # Limpa a flag para a próxima conexão
        self.branch = None
        
        # Armazenar a referência da seta
        if segmentos:
            # Armazenar no formato antigo para compatibilidade
            self.setas.append((segmentos[-1], origem, destino))
            # Armazenar informações adicionais em um dicionário separado
            self._setas_info[segmentos[-1]] = (segmentos, conexao_tag, color)

    def atualizar_setas(self, *args, **kwargs):
        """
        Redesenha todas as setas usando as cores definidas em bloco['acao']['forks']:
          - Fluxo Principal (Continuar Fluxo) → azul  "#0a84ff"
          - Threads Novas    (Nova Thread)     → preto "#000"
        """
        # 1) Guarde todas as conexões atuais
        conexoes = list(self.setas)  # [(seta_id, origem, destino), ...]

        # 2) Apague tudo como antes
        for segs, _, _ in self._setas_info.values():
            for sid in segs:
                self.canvas.delete(sid)
        for seta_id, _, _ in conexoes:
            self.canvas.delete(seta_id)
        self.canvas.update_idletasks()

        # 3) Limpe caches
        self._setas_info.clear()
        self.setas.clear()

        # 4) Recrie cada conexão, pintando só o principal de azul
        for _, origem, destino in conexoes:
            forks = origem.get("acao", {}).get("forks", {})
            escolha = forks.get(destino["id"], "Continuar Fluxo")
        
            # apenas as setas que abrem thread (“Nova Thread”) são azuis
            cor = "#0a84ff" if escolha == "Nova Thread" else "#000"
        
            if (origem and destino 
                and self._centro_bloco(origem) 
                and self._centro_bloco(destino)):
                self.desenhar_linha(origem, destino, cor_override=cor)



    def remover_setas_de_bloco(self, bloco):
        novas_setas = []
        for seta_id, origem, destino in self.setas:
            if origem == bloco or destino == bloco:
                # Obter informações adicionais
                if seta_id in self._setas_info:
                    segmentos, tag, *_ = self._setas_info[seta_id]
                    
                    # Remover todos os segmentos
                    for seg_id in segmentos:
                        try:
                            self.canvas.delete(seg_id)
                        except:
                            pass
                            
                    # Remover todos os itens com essa tag
                    try:
                        for item in self.canvas.find_withtag(tag):
                            self.canvas.delete(item)
                    except:
                        pass
                        
                    # Remover do dicionário de informações
                    del self._setas_info[seta_id]
                else:
                    # Formato antigo, apenas remover a seta
                    try:
                        self.canvas.delete(seta_id)
                    except:
                        pass
            else:
                novas_setas.append((seta_id, origem, destino))
                
        self.setas = novas_setas

    def deletar_seta_por_id(self, seta_id):
        # Obter informações adicionais
        if seta_id in self._setas_info:
            segmentos, tag, *_ = self._setas_info[seta_id]
            
            # Remover todos os segmentos
            for seg_id in segmentos:
                try:
                    self.canvas.delete(seg_id)
                except:
                    pass
                    
            # Remover todos os itens com essa tag
            try:
                for item in self.canvas.find_withtag(tag):
                    self.canvas.delete(item)
            except:
                pass
                
            # Remover do dicionário de informações
            del self._setas_info[seta_id]
        else:
            # Formato antigo, apenas remover a seta
            try:
                self.canvas.delete(seta_id)
            except:
                pass
        
        # Remover a seta da lista
        self.setas = [s for s in self.setas if s[0] != seta_id]

    # Método público para limpar seleção (sem underscore)
    def limpar_selecao(self):
        """Limpa todas as seleções atuais"""
        self._limpar_selecao()

    def _limpar_selecao(self):
        """Limpa todas as seleções atuais (implementação interna)"""
        # Limpar seleção de setas
        for seta_id, _, _ in self.setas:
            for seg in self._obter_segmentos(seta_id):
                if seg in self._cor_original:                 # estava destacado
                    cor = self._cor_original.pop(seg)
                    self.canvas.itemconfig(seg, fill=cor,
                                            width=2, dash=())
                else:                                         # nunca esteve azul
                    self.canvas.itemconfig(seg, width=2, dash=())
            
        # Limpar seleção de blocos
        for bloco in self.blocos.blocks:
            if bloco.get("borda"):
                try:
                    self.canvas.delete(bloco["borda"])
                    bloco["borda"] = None
                except:
                    pass
                
        # Limpar lista de itens selecionados
        if hasattr(self.blocos, "app") and hasattr(self.blocos.app, "itens_selecionados"):
            self.blocos.app.itens_selecionados = []

    def selecionar_item(self, event):
        x, y = self.canvas.canvasx(event.x), self.canvas.canvasy(event.y)
        ctrl = event.state & 0x0004  # Ctrl pressionado

        # Verifica se clicou em uma seta
        for seta_id, origem, destino in self.setas:
            segmentos = self._obter_segmentos(seta_id)
            for seg in segmentos:
                try:
                    if clicou_em_linha(x, y, self.canvas.coords(seg), margem=10):

                        def destacar():
                            for s in segmentos:
                                # guarda a cor só na primeira vez
                                if s not in self._cor_original:
                                    self._cor_original[s] = self.canvas.itemcget(s, "fill")
                                self.canvas.itemconfig(s, fill="#0a84ff", width=3, dash=(4, 2))

                        def remover():
                            for s in segmentos:
                                cor = self._cor_original.pop(s, None)      # devolve e apaga
                                if cor is None:
                                    cor = "black"
                                self.canvas.itemconfig(s, fill=cor, width=2, dash=())

                        if ctrl:
                            if ("seta", seta_id) in self.blocos.app.itens_selecionados:
                                self.blocos.app.itens_selecionados.remove(("seta", seta_id))
                                remover()
                            else:
                                self.blocos.app.itens_selecionados.append(("seta", seta_id))
                                destacar()
                        else:
                            self._limpar_selecao()
                            self.blocos.app.itens_selecionados = [("seta", seta_id)]
                            destacar()
                        return                # já encontrou a seta
                except:
                    continue

        # Verifica se clicou em um bloco
        for bloco in self.blocos.blocks:
            try:
                coords = self.canvas.coords(bloco["rect"])
                if len(coords) >= 4 and coords[0] <= x <= coords[2] and coords[1] <= y <= coords[3]:
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
            except:
                continue

        if not ctrl:
            self._limpar_selecao()

    def deletar_item(self, event):
        if hasattr(self.blocos, "app") and hasattr(self.blocos.app, "item_selecionado"):
            tipo, item = self.blocos.app.item_selecionado

            if tipo == "bloco":
                try:
                    self.canvas.delete(item["rect"])
                    if item.get("icon"):
                        self.canvas.delete(item["icon"])

                    for h in item.get("handles", []):
                        self.canvas.delete(h)

                    # Remove a borda se existir (seleção única)
                    if hasattr(self.blocos, "borda_selecionada") and self.blocos.borda_selecionada:
                        self.canvas.delete(self.blocos.borda_selecionada)
                        self.blocos.borda_selecionada = None

                    # Remove a borda se for de seleção múltipla
                    if item.get("borda"):
                        self.canvas.delete(item["borda"])
                        item["borda"] = None

                    # Remove imagem do cache
                    bloco_id = item.get("id") or item.get("bloco_id")
                    if bloco_id and hasattr(self.blocos, "imagens") and bloco_id in self.blocos.imagens:
                        del self.blocos.imagens[bloco_id]

                    # Remove bloco
                    if item in self.blocos.blocks:
                        self.blocos.blocks.remove(item)
                    if hasattr(self.blocos, "ocupados"):
                        self.blocos.ocupados.discard((item["x"], item["y"]))

                    # Remove setas conectadas
                    self.remover_setas_de_bloco(item)

                    # Limpa seleção múltipla
                    if hasattr(self.blocos, "blocos_selecionados"):
                        self.blocos.blocos_selecionados = [b for b in self.blocos.blocos_selecionados if b != item]
                except:
                    pass

            elif tipo == "seta":
                self.deletar_seta_por_id(item)

            if hasattr(self, "seta_highlights") and item in self.seta_highlights:
                try:
                    self.canvas.delete(self.seta_highlights.pop(item))
                except:
                    pass
            
            self.blocos.app.item_selecionado = None
            
    # Método para adicionar um patch para o método mover_bloco da classe Blocos
    def patch_mover_bloco(self):
        """
        Adiciona um patch para o método mover_bloco da classe Blocos para
        garantir que as setas sejam atualizadas após mover um bloco.
        """
        if hasattr(self.blocos, "mover_bloco"):
            # Salvar referência ao método original
            original_mover_bloco = self.blocos.mover_bloco
            
            # Definir o novo método que chama o original e depois atualiza as setas
            def patched_mover_bloco(self_blocos, *args, **kwargs):
                result = original_mover_bloco(*args, **kwargs)
                # Atualizar as setas após mover o bloco
                self.atualizar_setas()
                return result
                
            # Substituir o método original pelo patched
            self.blocos.mover_bloco = patched_mover_bloco.__get__(self.blocos, type(self.blocos))
            
    # Método para adicionar um patch para o método _snapshot da classe Blocos
    def patch_snapshot(self):
        """
        Adiciona um patch para o método _snapshot da classe Blocos para
        garantir compatibilidade com a nova estrutura de setas.
        """
        if hasattr(self.blocos, "_snapshot"):
            # Salvar referência ao método original
            original_snapshot = self.blocos._snapshot
            
            # Definir o novo método que adapta a estrutura de setas para o formato esperado
            def patched_snapshot(self_blocos):
                # Salvar temporariamente a estrutura atual de setas
                original_setas = self.setas
                
                # Chamar o método original
                result = original_snapshot()
                
                # Restaurar a estrutura original
                self.setas = original_setas
                
                return result
                
            # Substituir o método original pelo patched
            self.blocos._snapshot = patched_snapshot.__get__(self.blocos, type(self.blocos))
