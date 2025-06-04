# core/actions/startthread.py

from . import register
import threading
import core.executor.macro_executor as _executor


@register("startthread")
def run(params, ctx):
    """
    - Se apenas 1 sub-thread for criada (len(novas_threads) == 1), essa sub-thread herda
      diretamente disp_name_param (thread_name do Start Thread), caso não tenha 
      thread_name/name. Sem “– ramo”.
    - Se 2 ou mais sub-threads forem criadas, usamos “parent_label – ramo {dest}”
      para tornar cada rótulo único.
    - Mantém a ordem: primeiro redireciona o fluxo-principal (ctx.set_current(main_dest)),
      renomeando o pai apenas se ele ainda se chamar “Thread Principal”; depois cria 
      as sub-threads.
    - Além disso, tenta usar `status_win._placeholder_events[display_name]` para obter
      um Event pré-cadastrado. Se não encontrar, só então cria um novo.
    """
    from core.executor.macro_executor import _run_branch

    # 1) Recupera dados do contexto
    current_id      = ctx.get("current_id")
    blocks          = ctx.get("blocks")
    next_map        = ctx.get("next_map")
    json_path       = ctx.get("json_path")
    stop_event      = ctx.get("stop_event")
    disp_name_param = params.get("thread_name")   # Ex: "Fecha Trade", "Entrada Detectada Short"
    status_win      = ctx.get("status_win")

    # 2) Constrói o dicionário { dest_id:int : "Nova Thread" | "Continuar Fluxo" }
    raw_forks = params.get("forks", {}) or {}
    forks = {int(k): v for k, v in raw_forks.items()}

    # 3) Reúne destinos em next_map[current_id] para keys ["default","true","false"]
    branches = ["default", "true", "false"]
    main_dest = None
    novas_threads = []
    for br in branches:
        for dest in next_map.get(current_id, {}).get(br, []):
            escolha = forks.get(dest, "Continuar Fluxo")
            if escolha == "Nova Thread":
                novas_threads.append(dest)
            elif main_dest is None:
                main_dest = dest

    # 4) ► FLUXO PRINCIPAL: primeiro, renomeia e redireciona o pai para main_dest
    if main_dest is not None:
        current_name = ctx.get("thread_name") or "Thread Principal"

        # Só renomeia o pai se ainda se chamar "Thread Principal"
        if current_name == "Thread Principal" and disp_name_param:
            ctx["thread_name"] = disp_name_param
            if status_win:
                status_win.register_stop_event(disp_name_param, stop_event)

                def restart_parent(name, new_evt, _bid=current_id, _disp=disp_name_param):
                    t2 = threading.Thread(
                        target=_executor._run_branch,
                        name=_disp,
                        args=(
                            blocks,
                            next_map,
                            json_path,
                            _bid,
                            ctx.get("progress_callback"),
                            ctx.get("label_callback"),
                            new_evt,
                            _disp,
                            status_win
                        ),
                        daemon=True
                    )
                    t2.start()
                    status_win.register_stop_event(_disp, new_evt)
                    status_win.register_restart_callback(_disp, restart_parent)

                status_win.register_restart_callback(disp_name_param, restart_parent)

        # Em seguida, faz a própria thread-pai pular para main_dest
        ctx["set_current"](main_dest)
    else:
        # Se não houver main_dest, encerra imediatamente a thread-pai
        ctx["set_current"](None)
        return None

    # 5) ► THREAD-FILHO: define parent_label e conta quantas forks existem
    parent_label = disp_name_param or "Thread Principal"
    count_forks = len(novas_threads)

    # Recupera o dicionário de placeholders (display_name -> Event) pre‐registrado
    placeholder_dict = getattr(status_win, "_placeholder_events", {})

    for dest in novas_threads:
        # 5.1) Pega params do bloco-filho e decide o base_name (label) de acordo com quantas forks
        child_block  = blocks.get(dest, {})
        child_params = child_block.get("params", {})

        if child_params.get("thread_name"):
            base_name = child_params["thread_name"]
        elif child_params.get("name"):
            base_name = child_params["name"]
        else:
            if count_forks == 1:
                # Única sub-thread → herda disp_name_param
                base_name = parent_label
            else:
                # Várias sub-threads → “parent_label – ramo {dest}”
                base_name = f"{parent_label} – ramo {dest}"

        display_name  = base_name
        internal_name = f"{base_name}-{dest}"

        # 5.2) Tenta reutilizar o placeholder antigo (Event) se existir
        if display_name in placeholder_dict:
            child_evt = placeholder_dict[display_name]
        else:
            # Caso não exista (ex.: fork gerado dinamicamente), criamos e registramos novo
            child_evt = threading.Event()
            status_win.register_stop_event(display_name, child_evt)

            def restart_child(name, new_evt, _dest=dest, _disp=display_name, _iname=internal_name):
                t2 = threading.Thread(
                    target=_run_branch,
                    name=_iname,
                    args=(
                        blocks,
                        next_map,
                        json_path,
                        _dest,
                        ctx.get("progress_callback"),
                        ctx.get("label_callback"),
                        new_evt,
                        _disp,
                        status_win
                    ),
                    daemon=True
                )
                t2.start()
                status_win.register_stop_event(_disp, new_evt)
                status_win.register_restart_callback(_disp, restart_child)

            status_win.register_restart_callback(display_name, restart_child)
            placeholder_dict[display_name] = child_evt

        # 5.3) Cria e inicia a sub-thread com o Event (placeholder ou novo)
        th = threading.Thread(
            target=_run_branch,
            name=internal_name,
            args=(
                blocks,
                next_map,
                json_path,
                dest,
                ctx.get("progress_callback"),
                ctx.get("label_callback"),
                child_evt,
                display_name,
                status_win
            ),
            daemon=True
        )
        th.start()

    # 6) Retorna None para sinalizar que já redirecionamos o fluxo-principal
    return None
