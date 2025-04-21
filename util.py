# util.py

def clicou_em_linha(x, y, coords, margem=5):
    """Verifica se o clique está próximo da linha"""
    if len(coords) < 4:
        return False
    x1, y1, x2, y2 = coords[:4]
    if min(x1, x2) - margem <= x <= max(x1, x2) + margem and min(y1, y2) - margem <= y <= max(y1, y2) + margem:
        dx, dy = x2 - x1, y2 - y1
        if dx == 0:
            return abs(x - x1) < margem
        m = dy / dx
        b = y1 - m * x1
        y_estimado = m * x + b
        return abs(y - y_estimado) < margem
    return False
