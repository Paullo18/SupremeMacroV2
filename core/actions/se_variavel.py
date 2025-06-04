# core/actions/se_variavel.py

from core.actions import register

@register("se variavel")
def run_se_variavel(params, ctx):
    """
    Handler para o bloco 'se variavel'.
    params contém:
      - var_name     (string): nome da variável a verificar
      - operator     (string): um dos '=', '!=', '<', '<=', '>', '>='
      - compare_value(string): o valor literal para comparar
    ctx possui:
      - ctx["vars"]  (dict)   : dicionário de variáveis definidas até agora
      - ctx["next_map"]: mapa de fluxos; ctx["next_map"][current_id]["true"] lista de IDs
                        para o caso verdadeiro
                        ctx["next_map"][current_id]["false"] lista de IDs para falso
    """
    var_name = params.get("var_name", "").strip()
    op       = params.get("operator", "").strip()
    cmp_val  = params.get("compare_value", "").strip()

    # Obtém o valor atual da variável (string). Se não existir, fica "".
    vars_dict = ctx.get("vars", {})
    val_atual = vars_dict.get(var_name, "")

    def compara(a: str, b: str, operador: str) -> bool:
        # Tenta comparar como float; se falhar, compara como string
        try:
            fa = float(a)
            fb = float(b)
            if operador == "=":
                return fa == fb
            elif operador == "!=":
                return fa != fb
            elif operador == "<":
                return fa < fb
            elif operador == "<=":
                return fa <= fb
            elif operador == ">":
                return fa > fb
            elif operador == ">=":
                return fa >= fb
        except ValueError:
            # comparar como texto
            if operador == "=":
                return a == b
            elif operador == "!=":
                return a != b
            elif operador == "<":
                return a < b
            elif operador == "<=":
                return a <= b
            elif operador == ">":
                return a > b
            elif operador == ">=":
                return a >= b
        return False

    resultado = compara(val_atual, cmp_val, op)

    # Opcional: mostrar na UI se quiser
    thread_name = ctx.get("thread_name")
    if ctx.get("label_callback"):
        texto_label = f"SeVariável: {var_name} {op} {cmp_val} → {resultado}"
        ctx["label_callback"](thread_name, texto_label)

    # Determina o próximo bloco (true ou false)
    current_id = ctx.get("current_id")
    nm = ctx.get("next_map", {})
    ramais = nm.get(current_id, {})

    if resultado:
        destinos = ramais.get("true", [])
    else:
        destinos = ramais.get("false", [])

    prox_id = destinos[0] if destinos else None
    ctx["set_current"](prox_id)
