from . import register
import threading, importlib

@register("telegram_command")
def run(params, ctx):
    """
    Pausa a macro até que o usuário envie o comando exato via Telegram.
    Ex.: {"type":"telegram_command", "command":"/closetrade"}
    """
    cmd = params.get("command", "").strip().lower()
    if not cmd:
        raise KeyError("telegram_command requer 'command'")

    # garante que o bot esteja rodando
    importlib.import_module("core.telegram_listener").start_telegram_bot()

    # prepara estrutura global
    storage = importlib.import_module("core.storage")
    storage.remote_waiters = getattr(storage, "remote_waiters", {})

    evt = threading.Event()
    storage.remote_waiters.setdefault(cmd, []).append(evt)

    # espera até o comando chegar (bloqueio sem CPU)
    evt.wait()                      # ou evt.wait(1) dentro de um while

    # limpeza para evitar vazamento de Events
    waiters = storage.remote_waiters.get(cmd, [])
    if evt in waiters:
        waiters.remove(evt)
        if not waiters:
            del storage.remote_waiters[cmd]
