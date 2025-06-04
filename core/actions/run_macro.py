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

    execute_macro(filho_abs, ctx)      # executa dentro da mesma thread
