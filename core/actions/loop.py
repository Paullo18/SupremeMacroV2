from . import register

@register("loopstart")
def run(params, ctx):
    # Não re-empilha se acabamos de saltar de volta aqui
    current = ctx.get("current_id")
    if getattr(ctx, "_loop_stack", []) and ctx._loop_stack[-1]["start"] == current:
        return
    # params deve conter pelo menos: { 'type': 'loopstart', 'count': N }
    ctx.push_loop(params)

@register("loopend")
def run(params, ctx):
    # só processa se houver um loop aberto na pilha
    stack = getattr(ctx, "_loop_stack", [])
    if not stack:
        return

    # pega início e contagem restante (None => infinito)
    start_id, remaining = ctx.peek_loop()

    # modo infinito → sempre repete
    if remaining is None:
        ctx.jump_to(start_id)
        return

    # modo quantidade → decrementar até 1
    if remaining > 1:
        ctx.update_loop_count(remaining - 1)
        ctx.jump_to(start_id)
    else:
        # última iteração: sai do loop
        ctx.pop_loop()