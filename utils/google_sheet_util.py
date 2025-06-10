import gspread
from core.config_manager import ConfigManager
from handlers.credentials_handler import list_google_service_accounts
from gspread.utils import a1_to_rowcol


def _get_service():
    """
    Autentica via Service Account configurada e retorna cliente gspread.
    """
    settings = ConfigManager.load()
    cred_name = settings.get("google_sheets_creds")
    creds_list = list_google_service_accounts()
    entry = next((c for c in creds_list if c.name == cred_name), None)
    if entry is None:
        raise ValueError(f"Credencial '{cred_name}' não encontrada")
    # Se entry for Path
    path = entry.path if hasattr(entry, 'path') else str(entry)
    return gspread.service_account(filename=path)


def get_sheet_tabs(sheet_name: str) -> list[dict]:
    """
    Lista abas de uma planilha configurada pelo nome, retornando dicts com 'title' e 'id'.
    """
    settings = ConfigManager.load()
    sheets_cfg = settings.get("google_sheets", [])
    entry = next((s for s in sheets_cfg if s.get("name") == sheet_name), None)
    if not entry:
        return []
    client = _get_service()
    spreadsheet = client.open_by_key(entry.get("id"))
    return [{"title": ws.title, "id": ws.id} for ws in spreadsheet.worksheets()]


def append_next_row(sheet_name: str, tab_id: int, column: str, values: list):
    """
    Insere `values` na próxima linha disponível da coluna `column` na aba identificada por `tab_id`.
    """
    settings = ConfigManager.load()
    sheets_cfg = settings.get("google_sheets", [])
    entry = next((s for s in sheets_cfg if s.get("name") == sheet_name), None)
    if not entry:
        raise ValueError(f"Planilha '{sheet_name}' não encontrada")
    client = _get_service()
    spreadsheet = client.open_by_key(entry.get("id"))
    # Seleciona worksheet por id
    worksheets = spreadsheet.worksheets()
    worksheet = next((ws for ws in worksheets if ws.id == tab_id), None)
    if worksheet is None:
        raise ValueError(f"Aba com id '{tab_id}' não encontrada em '{sheet_name}'")
    # Converte letra da coluna para índice numérico
    col_index = a1_to_rowcol(f"{column}1")[1]
    col_values = worksheet.col_values(col_index)
    next_row = len(col_values) + 1
    cell_label = f"{column}{next_row}"
    worksheet.update(
        cell_label,
        values,
        value_input_option="RAW",
    )
