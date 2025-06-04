# path_utils.py (novo módulo)
# ---------------------------------------------------
# Funções para cálculo de rotas ortogonais e verificação de sobreposição de setas.
# Extraídas de SetaManager em setas.py para modularização.
from typing import List, Tuple, Optional


def verificar_sobreposicao(
    x1: float, y1: float, x2: float, y2: float,
    blocos
) -> bool:
    """
    Verifica se a linha (x1,y1)->(x2,y2) sobrepõe qualquer bloco.
    Retorna True se houver sobreposição, False caso contrário.
    """
    # Não considera sobreposição se o segmento for quase reto
    if abs(x1 - x2) < 1 or abs(y1 - y2) < 1:
        return False

    canvas = blocos.canvas
    for bloco in blocos.blocks:
        try:
            bx1, by1, bx2, by2 = canvas.coords(bloco["rect"])
            # Segmento horizontal?
            if abs(y1 - y2) < 1:
                y = y1
                x_start, x_end = sorted((x1, x2))
                if by1 <= y <= by2 and x_end >= bx1 and x_start <= bx2:
                    return True
            # Segmento vertical?
            elif abs(x1 - x2) < 1:
                x = x1
                y_start, y_end = sorted((y1, y2))
                if bx1 <= x <= bx2 and y_end >= by1 and y_start <= by2:
                    return True
        except Exception:
            continue
    return False


def calcular_pontos_ortogonais(
    x1: float, y1: float, x2: float, y2: float,
    origem, destino, canvas
) -> List[Tuple[float, float]]:
    """
    Gera um caminho ortogonal padrão entre dois pontos:
    primeiro em um eixo, depois no outro (formato 'L').
    """
    delta_x = abs(x2 - x1)
    delta_y = abs(y2 - y1)
    pontos: List[Tuple[float, float]] = [(x1, y1)]

    # Se já alinhados, conexão direta
    if delta_x < 1 or delta_y < 1:
        pontos.append((x2, y2))
        return pontos

    try:
        coords_origem = canvas.coords(origem["rect"])
        coords_destino = canvas.coords(destino["rect"])
        if len(coords_origem) == 4 and len(coords_destino) == 4:
            # Escolhe eixo maior primeiro
            if delta_x > delta_y:
                pontos.append((x2, y1))
            else:
                pontos.append((x1, y2))
        else:
            # Fallback simples
            if delta_x > delta_y:
                pontos.append((x2, y1))
            else:
                pontos.append((x1, y2))
    except Exception:
        # Fallback geral
        if delta_x > delta_y:
            pontos.append((x2, y1))
        else:
            pontos.append((x1, y2))

    pontos.append((x2, y2))
    return pontos


def encontrar_caminho_externo(
    x1: float, y1: float, x2: float, y2: float,
    origem, destino, canvas
) -> Optional[List[Tuple[float, float]]]:
    """
    Gera um caminho alternativo contornando completamente os blocos,
    seguindo a lógica de SetaManager._encontrar_caminho_externo.
    Retorna None se ocorrer erro ou não houver coordenadas válidas,
    para cair de volta no caminho ortogonal padrão.
    """
    try:
        # 1) pegar retângulos
        coords_origem = canvas.coords(origem["rect"])
        coords_destino = canvas.coords(destino["rect"])
        if len(coords_origem) < 4 or len(coords_destino) < 4:
            return None

        ox1, oy1, ox2, oy2 = coords_origem
        dx1, dy1, dx2, dy2 = coords_destino

        # 2) centros
        cx1, cy1 = (ox1 + ox2) / 2, (oy1 + oy2) / 2
        cx2, cy2 = (dx1 + dx2) / 2, (dy1 + dy2) / 2
        delta_x = cx2 - cx1
        delta_y = cy2 - cy1

        # 3) limites com margem
        m = 20
        sup = min(oy1, dy1) - m
        inf = max(oy2, dy2) + m
        esq = min(ox1, dx1) - m
        dir = max(ox2, dx2) + m

        pontos: List[Tuple[float, float]] = [(x1, y1)]

        # 4) bordas
        if abs(x1 - ox1) < 1:
            bo = "esquerda"
        elif abs(x1 - ox2) < 1:
            bo = "direita"
        elif abs(y1 - oy1) < 1:
            bo = "superior"
        elif abs(y1 - oy2) < 1:
            bo = "inferior"
        else:
            bo = ""

        if abs(x2 - dx1) < 1:
            bd = "esquerda"
        elif abs(x2 - dx2) < 1:
            bd = "direita"
        elif abs(y2 - dy1) < 1:
            bd = "superior"
        elif abs(y2 - dy2) < 1:
            bd = "inferior"
        else:
            bd = ""

        # 5) casos principais
        if bo == "direita" and bd == "esquerda":
            pontos += [(dir, y1), (dir, y2), (x2, y2)]
        elif bo == "esquerda" and bd == "direita":
            pontos += [(esq, y1), (esq, y2), (x2, y2)]
        elif bo == "inferior" and bd == "superior":
            pontos += [(x1, inf), (x2, inf), (x2, y2)]
        elif bo == "superior" and bd == "inferior":
            pontos += [(x1, sup), (x2, sup), (x2, y2)]
        elif bo == bd and bo in ("esquerda","direita"):
            lateral = esq if bo == "esquerda" else dir
            pontos += [(lateral, y1), (lateral, y2), (x2, y2)]
        elif bo == bd and bo in ("superior","inferior"):
            horizontal = sup if bo == "superior" else inf
            pontos += [(x1, horizontal), (x2, horizontal), (x2, y2)]
        else:
            # padrão em L pelo maior deslocamento
            if abs(delta_x) > abs(delta_y):
                pontos += [(x2, y1), (x2, y2)]
            else:
                pontos += [(x1, y2), (x2, y2)]

        return pontos

    except Exception:
        return None