from . import register
from utils.google_sheet_util import append_next_row     # implemente no seu helpers

@register("text_to_sheet")
def run(params, ctx):
    """
    params:
        text
        sheet_id / worksheet
    """
    append_next_row(
        sheet_name = params.get("sheet_name") or params.get("sheet"),
        tab_id     = params["tab_id"],
        column     = params.get("column", "A"),
        # gspread espera uma lista de linhas, cada linha é lista de valores:
        values     = [[params["text"]]],
    )
