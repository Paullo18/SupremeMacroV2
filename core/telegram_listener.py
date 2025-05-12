import os
import json
import threading
import asyncio

from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes

from telegram.ext import MessageHandler, filters

# Paths
_BASE_DIR = os.path.dirname(os.path.dirname(__file__))  # raiz do projeto
_SETTINGS_PATH = os.path.join(_BASE_DIR, "settings.json")

# Carrega configurações gerais
with open(_SETTINGS_PATH, "r", encoding="utf-8") as f:
    _SETTINGS = json.load(f)

# Token do bot (primeiro configurado)
bots = _SETTINGS.get("telegram", [])
if not bots:
    raise RuntimeError("Nenhum bot Telegram configurado em settings.json")
TOKEN = bots[0]["token"]

# Importa storage para controle de caminhos e UI instance
import core.storage as storage

# Função principal de execução headless
from core.executar import executar_macro_flow as run_macro

# Evento global para controle de parada de macro
_current_stop_event = None

async def _on_startmacro(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global _current_stop_event
    chat_id = update.effective_chat.id

    # Previne EXECUÇÃO DUPLICADA (tanto UI quanto headless)
    if getattr(storage, 'macro_running', False) \
       or (_current_stop_event and not _current_stop_event.is_set()):
        await context.bot.send_message(chat_id, "⚠️ Macro já em execução.")
        return

    # Marca estado de execução antes de disparar
    storage.macro_running = True

    await context.bot.send_message(chat_id, "✅ Iniciando macro…")

    # 1) Se a UI estiver rodando, aciona o mesmo fluxo de "Executar" (UI)
    app_inst = getattr(storage, 'app', None)
    if app_inst:
        # marca estado de execução e dispara UI
        storage.macro_running = True
        app_inst.root.after(0, app_inst.executar_macro)
        await context.bot.send_message(chat_id, "▶️ Macro iniciada.")
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
    global _current_stop_event
    chat_id = update.effective_chat.id

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
    txt = update.message.text.strip()
    import core.storage as storage
    if hasattr(storage, "remote_waiters") and txt in storage.remote_waiters:
        # desenfileira todos os eventos esperando por este comando
        for evt in list(storage.remote_waiters[txt]):
            evt.set()
        await context.bot.send_message(update.effective_chat.id,
            f"✅ Comando remoto '{txt}' recebido! Continuando macro...")


    # Registra comandos de início e parada

def start_telegram_bot():
    """Inicializa o bot Telegram e começa o polling em thread separada."""
    # Cria e define novo loop de eventos para esta thread
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    # Constrói a aplicação Telegram
    application = (
        ApplicationBuilder()
        .token(TOKEN)
        .build()
    )
    application.add_handler(CommandHandler("startmacro", _on_startmacro))
    application.add_handler(CommandHandler("stopmacro",  _on_stopmacro))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, _on_command))
    application.add_handler(MessageHandler(filters.COMMAND, _on_command))
    print("📲 Telegram listener rodando (pressione Ctrl+C para parar).")
    application.run_polling()