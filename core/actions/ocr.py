from . import register
from utils.image_ops import grab_and_ocr   #  ⇠  crie util se ainda não existir

@register("ocr")
def run(params, ctx):
    """
    params esperados:
        x,y,w,h
        pattern  | texto | palavra   ← alias
    O fluxo segue para a seta TRUE (verde) se o texto aparecer,
    ou para a seta FALSE (vermelha) caso contrário.
    """
    # 1. localizar chave do padrão
    for key in ("pattern", "text", "texto", "palavra"):
        if key in params:
            alvo = params[key].lower()
            break
    else:
        raise KeyError("Bloco OCR precisa de 'pattern' / 'texto' / 'palavra'")

    # 2. executar OCR
    txt   = grab_and_ocr(params).lower()
    found = alvo in txt

    # 3. direcionar fluxo
    cur  = ctx["current_id"]
    nmap = ctx["next_map"]
    dest = nmap[cur]["true"] if found else nmap[cur]["false"]
    if dest:
        ctx["set_current"](dest[0])
