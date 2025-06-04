"""
Macro executor for Supreme Macro.
Provides the main execution logic for macros.
"""

import threading
import time
import json
import traceback
from core.actions import REGISTRY

from core.utils.logger import get_or_create_logger
from core.utils.thread_utils import is_main_thread, schedule_on_main_thread
from core.executor.context import ExecContext

# Get logger
logger = get_or_create_logger("macro_executor")

# Global flags for control
_macro_parar = False
_macro_pausar = False

# Thread counter
_active_threads = 0
_active_lock = threading.Lock()
    
def pre_register_all_threads(blocks, next_map, json_path, progress_callback, label_callback, status_win):
    """
    Varre todos os blocos procurando por 'Start Thread' e pré‐registra
    cada futura sub‐thread (destino com forks == "Nova Thread") no status_win.

    Assim, as caixas de status aparecerão desde o início, com events placeholders.
    """
    if status_win is None:
        return
    
    print(">>> entramos em pre_register_all_threads – total de blocos:", len(blocks))

    # Para permitir que o callback de restart tenha acesso a json_path, progress_callback etc.,
    # capturamos essas variáveis em um escopo acessível pelos closures:
    global_json_path = json_path
    global_progress = progress_callback
    global_label = label_callback

    # Dicionário para guardar todos os placeholders: display_name -> threading.Event
    placeholder_dict = {}

    # Percorra cada bloco para achar os Start Thread
    for block_id, block in blocks.items():
        # Detecta "Start Thread" pelo parâmetro interno ou pelo tipo do bloco
        params = block.get("params", {})
        action_type = ""
        if isinstance(params.get("type"), str) and params["type"].strip():
            action_type = params["type"].strip().lower()
        else:
            action_type = block.get("type", "").strip().lower()
            print(f"   Bloco {block_id}: action_type = '{action_type}'")

        if action_type != "startthread":
            continue

        # Resgata o thread_name deste Start Thread (pai)
        parent_label = params.get("thread_name") or "Thread Principal"

        # Constrói dicionário {dest_id: escolha}
        raw_forks = params.get("forks", {}) or {}
        forks = {int(k): v for k, v in raw_forks.items()}

        # Conta quantas sub‐threads esse Start Thread terá (para regra de "– ramo")
        count_forks = 0
        for br in ["default", "true", "false"]:
            for dest in next_map.get(block_id, {}).get(br, []):
                if forks.get(dest) == "Nova Thread":
                    count_forks += 1

        # Agora, registre cada destino marcado como "Nova Thread"
        for br in ["default", "true", "false"]:
            for dest in next_map.get(block_id, {}).get(br, []):
                if forks.get(dest) != "Nova Thread":
                    continue

                # Parâmetros do bloco-filho
                child_block = blocks.get(dest, {})
                child_params = child_block.get("params", {})

                # Escolhe o base_name:
                if child_params.get("thread_name"):
                    base_name = child_params["thread_name"]
                elif child_params.get("name"):
                    base_name = child_params["name"]
                else:
                    if count_forks == 1:
                        # Uma única sub‐thread → herda o nome do pai
                        base_name = parent_label
                    else:
                        # Várias sub‐threads → precisa diferenciar pelo ID
                        base_name = f"{parent_label} – ramo {dest}"

                display_name = base_name

                # Cria um evento placeholder (não dispara _run_branch ainda)
                placeholder_evt = threading.Event()
                placeholder_dict[display_name] = placeholder_evt

                # Registra no status_win: botão Stop/Play, mas a thread ainda não rodou.
                status_win.register_stop_event(display_name, placeholder_evt)

                # Prepare o callback de restart: se clicarem em "Play" antes da execução,
                # vamos rodar a thread normalmente.
                def make_restart(_disp=display_name, _dest=dest, _bid=block_id):
                    def restart_child(name, new_evt):
                        # Esse closure terá acesso a global_json_path, global_progress, global_label
                        t2 = threading.Thread(
                            target=_run_branch,
                            name=_disp,
                            args=(
                                blocks,
                                next_map,
                                global_json_path,
                                _dest,
                                global_progress,
                                global_label,
                                new_evt,
                                _disp,
                                status_win
                            ),
                            daemon=True
                        )
                        t2.start()
                        # Registra de volta o stop_event + restart callback
                        status_win.register_stop_event(_disp, new_evt)
                        status_win.register_restart_callback(_disp, restart_child)
                    return restart_child

                status_win.register_restart_callback(display_name, make_restart())

    # 1) Atribui IMEDIATAMENTE (sem agendar) para que seu DEBUG em execute_macro funcione
    status_win._placeholder_events = placeholder_dict
    # 2) Agenda, no main thread do Tk, apenas o preload (criação dos widgets)
    status_win.win.after(0, lambda: status_win.preload_threads(list(placeholder_dict.keys())))
    return

def load_macro_flow(json_path):
    """
    Load a macro flow from a JSON file.
    
    Args:
        json_path: Path to the JSON file
        
    Returns:
        Tuple of (blocks_dict, next_map, start_block_id)
    """
    logger.info(f"Loading macro flow from {json_path}")
    
    try:
        with open(json_path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception as e:
        logger.error(f"Error loading macro JSON: {e}")
        raise ValueError(f"Failed to load macro: {e}")
    
    # Get blocks by ID
    blocks = {blk["id"]: blk for blk in data.get("blocks", [])}
    
    if not blocks:
        logger.error("No blocks found in macro")
        raise ValueError("No blocks found in macro")
    
    # Initialize next map
    next_map = {
        bid: {"default": [], "true": [], "false": [], "fork": []}
        for bid in blocks
    }
    
    # Track incoming connections for each block
    incoming = {bid: 0 for bid in blocks}
    
    # Process connections
    for conn in data.get("connections", []):
        src = conn.get("from")
        dst = conn.get("to")
        
        if src not in blocks or dst not in blocks:
            continue
        
        # Determine branch type
        branch = conn.get("branch")
        color = str(conn.get("color", "")).lower()
        
        # Convert boolean branch to string
        if isinstance(branch, bool):
            branch = "true" if branch else "false"
        
        # Infer branch from color if not specified
        if branch is None:
            if color in ("green", "#006600", "#0f0", "#00ff00ff"):
                branch = "true"
            elif color in ("red", "#ff0000", "#f00", "#ff0000ff"):
                branch = "false"
        
        # Add to appropriate branch in next_map
        if branch == "true":
            next_map[src]["true"].append(dst)
        elif branch == "false":
            next_map[src]["false"].append(dst)
        else:
            next_map[src]["default"].append(dst)
        
        # Increment incoming count
        incoming[dst] += 1
    
    # Find start block (first block with no incoming connections)
    start_nodes = [bid for bid, count in incoming.items() if count == 0]
    
    if not start_nodes:
        # Fallback: use first block in the JSON
        blocks_raw = data.get("blocks", [])
        # Determina start node(s) como todos os blocos que não têm incoming connections
        start_candidates = [bid for bid, cnt in incoming.items() if cnt == 0]
        if start_candidates:
            start_nodes = start_candidates
        else:
            # Se tudo tiver incoming > 0 (teoria rara), cai para o primeiro de blocks_raw
            if blocks_raw:
                first_id = blocks_raw[0].get("id")
                start_nodes = [first_id] if first_id in blocks else [next(iter(blocks.keys()))]
            else:
                logger.error("No blocks found in macro")
                raise ValueError("No blocks found in macro")
    logger.info(f"Macro loaded: {len(blocks)} blocks, starting at {start_nodes[0]}")
    return blocks, next_map, start_nodes[0]


def execute_macro(json_path, progress_callback=None, label_callback=None,
                  stop_event=None, status_win=None,
                  thread_name: str = "Thread Principal"):
    """
    Execute a macro from a JSON file.
    
    Args:
        json_path: Path to the JSON file
        progress_callback: Callback for progress updates
        label_callback: Callback for label updates
        stop_event: Event to signal stopping
        status_win: Status window object
        
    Returns:
        True if execution completed successfully, False otherwise
    """
    global _macro_parar, _macro_pausar, _active_threads
    
    logger.info(f"Starting macro execution: {json_path}")
    
    # Reset global flags
    _macro_parar = False
    _macro_pausar = False
    
    # Create stop event if not provided
    if stop_event is None:
        stop_event = threading.Event()
    
    try:
        # Load the macro flow
        blocks, next_map, start_block = load_macro_flow(json_path)
        
        # ─── Pré‐registro de THREADS antes de qualquer execução ─────────────────────────
        pre_register_all_threads(blocks, next_map, json_path, progress_callback, label_callback, status_win)
        # DEBUG: Como agora atribuímos _placeholder_events imediatamente, este print não virá mais vazio
        try:
            print("DEBUG: Placeholders pré‐registrados:", list(status_win._placeholder_events.keys()))
        except Exception:
            pass

        # ─── SINCRONAMENTE crie todos os widgets de placeholder imediatamente ────────────
        if status_win:
            # (1) mantemos o dicionário de placeholder_events dentro de status_win
            status_win._placeholder_events = status_win._placeholder_events
            # (2) Cria imediatamente cada “caixa” para o placeholder de thread,
            #     garantindo que apareçam antes de continuar no fluxo
            status_win.preload_threads(list(status_win._placeholder_events.keys()))
            # (3) Ainda agendamos um after(0,…) como “seguro” para o loop do Tkinter processar
            status_win.win.after(
                0,
                lambda: status_win.preload_threads(list(status_win._placeholder_events.keys()))
            )

        # ─── Agora registre o stop_event da Thread Principal (ela só existirá depois) ─────
        if status_win:
            def restart_root(name, new_evt):
                """
                Essa função será chamada ao clicar em 'Play' na UI para a Thread Principal.
                Ela recria um Thread que executa _run_branch() a partir do mesmo start_block.
                """
                t = threading.Thread(
                    target=_run_branch,
                    name=name,
                    args=(
                        blocks,
                        next_map,
                        json_path,
                        start_block,
                        progress_callback,
                        label_callback,
                        new_evt,
                        name,
                        status_win
                    ),
                    daemon=True
                )
                t.start()
                # Re‐registra o stop_event + callback de restart para a Thread Principal
                status_win.register_stop_event(name, new_evt, restart_root)

            status_win.register_stop_event("Thread Principal", stop_event, restart_root)
            # Agende o primeiro auto_close_check apenas para cuidar de placeholders que terminarem cedo
            status_win.win.after(500, status_win._auto_close_check)

        
        result = _run_branch(
            blocks=blocks,
            next_map=next_map,
            json_path=json_path,
            start_block=start_block,
            progress_callback=progress_callback,
            label_callback=label_callback,
            stop_event=stop_event,
            thread_name=thread_name,
            status_win=status_win
        )
        
        logger.info(f"Macro execution completed with result: {result}")
        return result
    except Exception as e:
        logger.error(f"Error executing macro: {e}")
        logger.error(traceback.format_exc())
        
        # Schedule error message on main thread if callback provided
        if label_callback and callable(label_callback):
            schedule_on_main_thread(
                label_callback, 
                "Error", 
                f"Error executing macro: {type(e).__name__}: {e}"
            )
        
        return False


def _run_branch(blocks, next_map, json_path, start_block, progress_callback, label_callback, stop_event, thread_name, status_win):
    """
    Run a branch of the macro execution.
    
    Args:
        blocks: Dictionary of blocks by ID
        next_map: Dictionary of next blocks by ID and branch
        json_path: Path to the JSON file
        start_block: ID of the starting block
        progress_callback: Callback for progress updates
        label_callback: Callback for label updates
        stop_event: Event to signal stopping
        thread_name: Name of the thread
        status_win: Status window object
        
    Returns:
        True if execution completed successfully, False otherwise
    """
    global _active_threads
    
    # Increment active thread count
    with _active_lock:
        _active_threads += 1
    
    logger.info(f"Starting branch execution: {thread_name} from block {start_block}")
    
    try:
        # Make callbacks thread-safe
        def safe_callback(callback):
            if callback is None:
                return lambda *a, **kw: None
            
            def wrapper(*args, **kwargs):
                if not is_main_thread():
                    schedule_on_main_thread(callback, *args, **kwargs)
                else:
                    callback(*args, **kwargs)
            
            return wrapper
        
        safe_progress = safe_callback(progress_callback)
        safe_label = safe_callback(label_callback)

        # ─── Detecta se existe ao menos um Start Thread em todo o macro ─────────────
        has_startthread = any(
            ((blk.get("params", {}).get("type", "")).strip().lower() == "startthread")
            for blk in blocks.values()
        )

        # ─── Inicializa contadores para a barra de progresso ───────────
        total = len(blocks)
        step  = 0
        
        # Initialize execution context
        base_ctx = {
            "blocks":      blocks,
            "next_map":    next_map,
            "json_path":   json_path,
            "stop_event":  stop_event,
            "thread_name": thread_name,
            "status_win":  status_win,
            "set_current": lambda bid: setattr(context, "current_id", bid)
        }
        
        context = ExecContext(base_ctx)
        current_id = start_block
        context["current_id"] = current_id
        
        # Notify start (só se não for root-silenciado)
        if not (thread_name == "Thread Principal" and has_startthread) and safe_label:
            safe_label(thread_name, f"Starting {thread_name} at block {start_block}")
        
        # Main execution loop
        while current_id is not None:
            # (Re-lê o nome atual da thread para saber se continua "Thread Principal" ou já mudou)
            current_label = context["thread_name"]
            root_silenced = (current_label == "Thread Principal" and has_startthread)
    
            # Check for stop request
            if stop_event.is_set() or _macro_parar:
                logger.info(f"Execution stopped: {current_label}")
                break
            
            # Check for pause
            while _macro_pausar and not stop_event.is_set() and not _macro_parar:
                time.sleep(0.1)
    
            # Get the current block
            bloco = blocks.get(current_id)
            if bloco is None:
                logger.error(f"Block not found: {current_id}")
                break
            
            # 1) Lê params para passar ao handler:
            params = bloco.get("params", {})
            # 2) PRIORITÁRIO: use params["type"] (interno/inglês), senão caia em bloco["type"] (rótulo em PT)
            action_type = ""
            if isinstance(params.get("type"), str) and params["type"].strip():
                action_type = params["type"].strip().lower()
            else:
                action_type = bloco.get("type", "").strip().lower()
    
            # Log execution
            logger.debug(f"Executing block {current_id} ({action_type}) under thread {current_label}")
    
            # Update label & progress se não estivermos no “Thread Principal” silenciado
            if not root_silenced and safe_label:
                # Para rótulo, procura um nome customizado em params["name"], ou cai para action_type
                block_name = params.get("name", action_type)
                safe_label(current_label, f"{block_name} ({action_type})")
                # ─── Atualiza a barra de progresso ─────────────────────────
                step += 1
                if safe_progress:
                    safe_progress(current_label, step, total)
            
            try:
                # Prepara um “set_current” local para que as ações possam redirecionar o fluxo
                nonlocal_set = [None]
                context["current_id"] = current_id
                context["set_current"] = lambda bid: nonlocal_set.__setitem__(0, bid)
                
                # ─── Injeção de callbacks e status_win para handlers (ex.: startthread) ─────────
                context["progress_callback"] = progress_callback
                context["label_callback"]    = label_callback
                context["status_win"]         = status_win

                # Encontra o handler registrado em core/actions
                handler = REGISTRY.get(action_type)
                if handler:
                    handler(params, context)
                    # Se alguém chamou ctx.set_current(...), usa esse ID para pular
                    if nonlocal_set[0] is not None:
                        current_id = nonlocal_set[0]
                        continue

                # ─── Fluxo padrão caso não haja redirecionamento ──────────────────
                nxts = next_map[current_id].get("default", [])
                current_id = nxts[0] if nxts else None
            except Exception as e:
                # Se der exceção, logamos e tentamos seguir a “default” de qualquer forma
                logger.error(f"Error handling action {action_type}: {e}")
                logger.error(traceback.format_exc())
                nxts = next_map[current_id].get("default", [])
                current_id = nxts[0] if nxts else None
        
        logger.info(f"Branch execution completed: {thread_name}")
        return True
    except Exception as e:
        logger.error(f"Error in branch execution: {e}")
        logger.error(traceback.format_exc())
        return False
    finally:
        # Sinaliza que esta thread terminou (para que o StatusWindow saiba que pode fechar)
        try:
            stop_event.set()
        except Exception:
            pass

        # Decrementa contador de threads ativas
        with _active_lock:
            _active_threads -= 1


def start_keyboard_monitor():
    """
    Start a thread to monitor keyboard for Ctrl+Q (stop) and Ctrl+P (pause).

    Returns:
        The monitor thread, ou None se não for possível importar 'keyboard'.
    """
    global _macro_parar, _macro_pausar

    try:
        import keyboard
    except ImportError:
        logger.error("Módulo 'keyboard' não está instalado; não será possível monitorar teclas.")
        return None

    def on_stop():
        # Callback para Ctrl+Q: sinaliza encerramento das macros
        global _macro_parar
        _macro_parar = True
        logger.info("Hotkey Ctrl+Q: sinalizando encerramento da macro (_macro_parar = True)")

    def on_pause_toggle():
        # Callback para Ctrl+P: alterna pause/continue
        global _macro_pausar
        _macro_pausar = not _macro_pausar
        estado = "PAUSA" if _macro_pausar else "CONTINUAR"
        logger.info(f"Hotkey Ctrl+P: toggle_pause → {estado}")

    # Registra as hotkeys apenas uma vez
    try:
        keyboard.add_hotkey("ctrl+q", on_stop)
        keyboard.add_hotkey("ctrl+p", on_pause_toggle)
    except Exception as e:
        logger.error(f"Não foi possível registrar hotkeys de teclado: {e}")
        return None

    # Para manter o thread vivo (não precisamos de loop polling), 
    # criamos um thread “fantasma” que só existe para manter o hotkey ativo.
    def dummy():
        # Esse thread não faz nada além de manter o programa rodando
        keyboard.wait()  # Bloqueia até o programa terminar

    try:
        monitor_thread = threading.Thread(target=dummy, daemon=True)
        monitor_thread.start()
        logger.info("Keyboard hotkeys registradas: Ctrl+Q e Ctrl+P ativas.")
        return monitor_thread
    except Exception as e:
        logger.error(f"Não foi possível iniciar o monitor de teclado: {e}")
        return None


def get_active_thread_count():
    """
    Get the number of active macro execution threads.
    
    Returns:
        Number of active threads
    """
    global _active_threads
    
    with _active_lock:
        return _active_threads


def is_macro_running():
    """
    Check if any macro is currently running.
    
    Returns:
        True if a macro is running, False otherwise
    """
    return get_active_thread_count() > 0


def stop_all_macros():
    """
    Stop all running macros.
    
    Returns:
        True if stop was requested, False if no macros were running
    """
    global _macro_parar
    
    if is_macro_running():
        _macro_parar = True
        return True
    
    return False


def toggle_pause():
    """
    Toggle pause state for all running macros.
    
    Returns:
        New pause state (True for paused, False for running)
    """
    global _macro_pausar
    
    _macro_pausar = not _macro_pausar
    return _macro_pausar
