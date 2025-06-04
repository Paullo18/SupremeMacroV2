from . import register
import importlib
import os

@register("run_macro")
def run(params, ctx):
    # importa diretamente a função execute_macro
    from core.executor.macro_executor import execute_macro

    macro_path = params.get("path")
    if not macro_path:
        return

    # monta caminho absoluto em relação ao JSON atual
    base = os.path.dirname(os.path.abspath(ctx["json_path"]))
    filho_abs = os.path.abspath(os.path.join(base, macro_path))

    execute_macro(
        filho_abs,
        progress_callback=ctx.get("progress_callback"),
        label_callback=ctx.get("label_callback"),
        stop_event=ctx.get("stop_event"),
        status_win=ctx.get("status_win"),
        thread_name=ctx.get("thread_name", "Thread Principal"),
    )
