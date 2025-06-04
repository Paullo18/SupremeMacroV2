from . import register
import time
import core.executor.macro_executor as _executor
from datetime import datetime
from core.utils.thread_utils import schedule_on_main_thread

@register("delay")
@register("schedule")
def run(params, ctx):
    """
    Atraso interrompível, pausável ou agendamento de hora.
    Se params['type']=="delay": suspende por params['time'] (milissegundos).
    Se params['type']=="schedule": suspende até params['date'] às params['hour':'minute':'second'].
    """
    # Determina o tempo total em segundos
    if params.get("type") == "schedule":
        date_str = params.get("date", "")
        hour = params.get("hour", 0)
        minute = params.get("minute", 0)
        second = params.get("second", 0)
        try:
            # Converte "yyyy-mm-dd" → datetime, então substitui hora/minuto/segundo
            target = datetime.strptime(date_str, "%Y-%m-%d")
            target = target.replace(hour=hour, minute=minute, second=second)
            now = datetime.now()
            total = (target - now).total_seconds()
            # Se horário passado, não aguarda nada
            if total < 0:
                total = 0
        except Exception:
            # Se falhar ao parsear data, não aguarda
            total = 0
    else:
        total = params.get("time", 0) / 1000.0

    step = 1.0  # 1 segundo por iteração para a contagem regressiva
    remaining = total

    thread_name = ctx.get("thread_name")
    stop_event  = ctx.get("stop_event")
    # safe_label emite o label no thread principal
    def safe_label(name, text):
        schedule_on_main_thread(ctx.get("label_callback"), name, text)

    # Loop de contagem regressiva: atualiza a cada segundo
    while remaining > 0:
        # Se o usuário solicitou parada, sai imediatamente
        if (stop_event and stop_event.is_set()) or _executor._macro_parar:
            break

        # Se estiver pausado (Ctrl+P), aguarda até retomar
        while _executor._macro_pausar:
            time.sleep(0.1)

        # Atualiza o label na UI para mostrar quantos segundos restam
        safe_label(thread_name, f"Delay ({int(remaining)}s)")
        time.sleep(1.0)
        remaining -= 1.0

    # Na saída do loop, se não parou via stop_event, exibe “0s”
    if not ((stop_event and stop_event.is_set()) or _executor._macro_parar):
        safe_label(thread_name, "Delay (0s)")