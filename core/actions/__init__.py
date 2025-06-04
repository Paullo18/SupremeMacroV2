"""
Registry central de handlers dos blocos.

Todo módulo dentro de core/actions deve:

    from . import register

    @register("click")
    def run(params, ctx): ...
"""

import importlib
import pkgutil

REGISTRY = {}


def register(name: str):
    """Decorator que registra a função `run` de um bloco."""
    def _decorator(fn):
        REGISTRY[name.lower()] = fn
        return fn
    return _decorator


# ────────────────────────────────────────────────────────────────
# Auto-discover: importa todos os *.py dentro de core/actions
# (exceto este __init__) para preencher REGISTRY automaticamente.
# ────────────────────────────────────────────────────────────────
for _finder, modname, _ispkg in pkgutil.iter_modules(__path__):
    importlib.import_module(f"{__name__}.{modname}")
