#core/actions/endthread.py

from . import register
 
@register("endthread")
def run(params, ctx):

    """
    Ação “endthread”: sinaliza o stop_event e encerra esta thread imediatamente.
    """
    # 1) Sinaliza o evento de parada associado a esta thread (caso exista)
    stop_event = ctx.get("stop_event")
    if stop_event:
        stop_event.set()

    # 2) Faz com que o executor interrompa o laço desta thread
    ctx["set_current"](None)