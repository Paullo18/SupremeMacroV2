from . import register

@register("label")
def run(params, ctx):
    """Labels não executam nada – servem de âncora"""
    pass
