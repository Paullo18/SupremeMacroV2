import os

import threading
import asyncio

from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes

from telegram.ext import MessageHandler, filters

import core.storage as storage

from core.executor import execute_macro as run_macro
from core.config_manager import ConfigManager

# ---------------- helpers -----------------
# (re)carrega settings e atualiza globais
def _reload_settings():
    global _SETTINGS, tg_cmd_cfg, bots, selected_name, TOKEN

    _SETTINGS  = ConfigManager.load()
    tg_cmd_cfg = _SETTINGS.get("telegram_commands", {"enabled": True})
    bots       = _SETTINGS.get("telegram", [])

    # qual bot usar?
    selected_name = tg_cmd_cfg.get("bot", bots[0]["name"] if bots else "")
    bot_row = next(
        (b for b in bots if b.get("name") == selected_name),
        bots[0] if bots else {}
    )
    TOKEN = bot_row.get("token")

# primeira carga
_reload_settings()

# ---------------- estado global do listener ----------------
APPLICATION      = None   # referência ao objeto Application
APPLICATION_LOOP = None   # loop da thread do listener
_BOT_THREAD      = None   # thread onde o polling roda
_SHUTTING_DOWN   = False  # evita start enquanto o stop não terminou


# Evento global para controle de parada de macro
_current_stop_event = None

async def _on_startmacro(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Recarrega config e interrompe se comandos desativados
    _reload_settings()
    if not tg_cmd_cfg.get("enabled", False):
        return
    global _current_stop_event
    chat_id = update.effective_chat.id

    # 1) Recarrega config e, se desativado, ignora esse comando
    _reload_settings()
    if not tg_cmd_cfg.get("enabled", False):
        return

    # Previne EXECUÇÃO DUPLICADA (tanto UI quanto headless)
    if getattr(storage, 'macro_running', False) \
       or (_current_stop_event and not _current_stop_event.is_set()):
        await context.bot.send_message(chat_id, "⚠️ Macro já em execução.")
        return

    # Marca estado de execução antes de disparar
    storage.macro_running = True

    await context.bot.send_message(chat_id, "✅ Iniciando macro…")

    # 1) Se a UI estiver rodando, enfileira execução na thread principal do Tk
    app_inst = getattr(storage, 'app', None)
    if app_inst:
        storage.macro_running = True
        app_inst.post_ui(app_inst.executar_macro)        # ⬅ usa a fila definida em FlowchartApp :contentReference[oaicite:0]{index=0}
        await context.bot.send_message(chat_id, "▶️ Macro enfileirada para execução na UI.")
        return

    # 2) Fallback headless: escolhe o JSON salvo ou temporário
    real_path = getattr(storage, 'caminho_macro_real', None)
    tmp_path  = getattr(storage, 'caminho_arquivo_tmp', None)
    macro_path = real_path if real_path and os.path.isfile(real_path) else tmp_path

    # Debug dos caminhos
    await context.bot.send_message(
        chat_id,
        f"📂 caminhos:\n  real: {real_path}\n  tmp:  {tmp_path}\n→ escolhido: {macro_path}"
    )

    # Valida existência do arquivo
    if not macro_path or not os.path.isfile(macro_path):
        await context.bot.send_message(chat_id, "⚠️ Nenhuma macro válida encontrada para execução.")
        return

    # Inicia execução headless com controle de parada
    stop_evt = threading.Event()
    _current_stop_event = stop_evt
    threading.Thread(
        target=lambda: run_macro(macro_path, None, None, stop_evt),
        daemon=True
    ).start()
    # marca estado de execução (headless)
    storage.macro_running = True
    await context.bot.send_message(chat_id, f"▶️ Macro iniciada: {os.path.basename(macro_path)}")

async def _on_stopmacro(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Recarrega config e interrompe se comandos desativados
    _reload_settings()
    if not tg_cmd_cfg.get("enabled", False):
        return
    global _current_stop_event
    chat_id = update.effective_chat.id

    # 1) Recarrega config e, se desativado, ignora esse comando
    _reload_settings()
    if not tg_cmd_cfg.get("enabled", False):
        return

    # sinaliza parada global
    try:
        import core.executar as executor
        executor.macro_parar = True
    except ImportError:
        pass

    # Qualquer macro em execução (UI ou headless)
    if getattr(storage, 'macro_running', False):
        # desarma flag e, se existir evento headless, sinaliza
        storage.macro_running = False
        if _current_stop_event and not _current_stop_event.is_set():
            _current_stop_event.set()
        await context.bot.send_message(chat_id, "✅ Macro parada com sucesso.")
        return

    # Se não havia macro nenhuma
    await context.bot.send_message(chat_id, "⚠️ Nenhuma macro em execução para parar.")

# Handler para disparar remote_control
async def _on_command(update, context):
    """
    Libera blocos `telegram_command` quando o texto do comando
    coincidir com o configurado na macro – funciona em chat privado
    e em grupos (onde o Telegram adiciona "@BotUserName").
    """
    # Recarrega config e interrompe se comandos desativados
    _reload_settings()
    if not tg_cmd_cfg.get("enabled", False):
        return
    # 1) Recarrega config e, se desativado, ignora esse comando
    _reload_settings()
    if not tg_cmd_cfg.get("enabled", False):
        return
    if not update.message:          # segurança contra updates sem texto
        return

    raw = update.message.text.strip()

    # ── 1) pegue só a primeira 'palavra'
    #     (ex.: "/closetrade@BOT arg1 arg2" → "/closetrade@BOT")
    token = raw.split()[0]

    # ── 2) remova "@UserName" se existir e normalize p/ minúsculas
    cmd = token.split("@")[0].lower()

    # ── 3) acione os waiters correspondentes
    import core.storage as storage
    if hasattr(storage, "remote_waiters") and cmd in storage.remote_waiters:
        for evt in list(storage.remote_waiters[cmd]):
            evt.set()

        await context.bot.send_message(
            update.effective_chat.id,
            f"✅ Comando remoto '{cmd}' recebido!"
        )

    # Registra comandos de início e parada

def start_telegram_bot():
    """Liga o polling se ainda não estiver rodando e se estiver habilitado."""
    global APPLICATION, APPLICATION_LOOP, _BOT_THREAD, _SHUTTING_DOWN

    if _SHUTTING_DOWN:            # ainda finalizando
        return


    _reload_settings()   # usa configurações mais recentes
    if APPLICATION or not tg_cmd_cfg.get("enabled", True) or not TOKEN:
        return

    def _thread_target():
        global APPLICATION_LOOP
        # cada thread precisa de seu próprio loop
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        APPLICATION_LOOP = loop

        # cria aplicação e handlers
        global APPLICATION
        APPLICATION = ApplicationBuilder().token(TOKEN).build()
        APPLICATION.add_handler(CommandHandler("startmacro", _on_startmacro))
        APPLICATION.add_handler(CommandHandler("stopmacro",  _on_stopmacro))
        APPLICATION.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, _on_command))
        APPLICATION.add_handler(MessageHandler(filters.COMMAND, _on_command))

        # 1) suprime conflitos de getUpdates criando um error handler
        from telegram.error import Conflict
        async def _handle_errors(update, context):
            err = context.error
            if isinstance(err, Conflict):
                print("⚠️ Telegram polling conflict ignorado.")
            else:
                print(f"📲 Erro no handler de Telegram: {err}")
        APPLICATION.add_error_handler(_handle_errors)

        print("📲 Telegram listener iniciado.")
        # 2) bloco principal de polling, com try/except para Conflict
        try:
            APPLICATION.run_polling(stop_signals=None)
        except Conflict:
            print("⚠️ Telegram polling conflict ignorado.")
        except Exception as e:
            print(f"📲 Telegram polling error: {e}")

    _BOT_THREAD = threading.Thread(
        target=_thread_target,
        name="TelegramListener",
        daemon=True
    )
    _BOT_THREAD.start()

def stop_telegram_bot():
    """Desliga o polling (se estiver ativo) sem travar a UI."""
    global APPLICATION, APPLICATION_LOOP, _BOT_THREAD

    global APPLICATION, APPLICATION_LOOP, _BOT_THREAD, _SHUTTING_DOWN

    if not APPLICATION or _SHUTTING_DOWN:
        return  # já parado ou já em processo de parada

    _SHUTTING_DOWN = True

    async def _shutdown():
        await APPLICATION.stop()
        print("📲 Telegram listener parado.")

    # agenda o shutdown no loop do listener
    asyncio.run_coroutine_threadsafe(_shutdown(), APPLICATION_LOOP)

    # espera o término em background sem travar a UI (não bloqueia pra sempre)
    import time
    def _wait_and_cleanup():
        global APPLICATION, APPLICATION_LOOP, _BOT_THREAD, _SHUTTING_DOWN
        if _BOT_THREAD and _BOT_THREAD.is_alive():
            # aguarda até 5 segundos pelo polling encerrar, mas não trava indefinidamente
            _BOT_THREAD.join(timeout=5)
        # mesmo que o polling ainda esteja vivo, força o cleanup
        APPLICATION      = None
        APPLICATION_LOOP = None
        _BOT_THREAD      = None
        _SHUTTING_DOWN   = False       # libera novo start

    threading.Thread(
        target=_wait_and_cleanup,
        name="TL_Cleanup",
        daemon=True
    ).start()