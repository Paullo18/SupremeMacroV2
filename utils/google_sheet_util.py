import gspread
from google.oauth2.service_account import Credentials

# 1. Defina o escopo
SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]

# 2. Carregue as credenciais do JSON
creds = Credentials.from_service_account_file("traderautosuite-a3d582ad9769.json", scopes=SCOPES)

# 3. Autorize e abra a planilha
client = gspread.authorize(creds)
_sh     = client.open_by_key("16xB0QcrS0gQLIkfGAvoc9iwFEbo97ZyCQHMYpn-cV8I")
_ws     = _sh.sheet1   # ou sh.worksheet("NomeDaAba")

# 4. Escreva algo, por exemplo:
def append_next_row(valor: str, col: int = 2):
    # Descobre próxima linha livre na coluna col
    col_vals = _ws.col_values(col)
    next_row = len(col_vals) + 1
    print(f"[Sheets] Próxima linha na coluna {col}: {next_row!r}")
    print(f"[Sheets] Valor a ser escrito: {repr(valor)}")
    if not valor:
        print("[Sheets] Atenção: texto extraído vazio, nada será escrito.")
        return
    _ws.update_cell(next_row, col, valor)
    print("[Sheets] update_cell concluído.")