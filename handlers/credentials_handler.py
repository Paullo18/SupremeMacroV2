import json
from pathlib import Path

# Diretório padrão de credenciais: pasta 'credentials' na raiz do projeto
DEFAULT_CREDS_DIR = Path(__file__).resolve().parents[1] / "credentials"


def is_google_service_account(file_path: Path) -> bool:
    """
    Verifica se o JSON em file_path parece uma credencial de Service Account do Google.
    Procura chaves obrigatórias: 'type', 'client_email' e 'token_uri'.
    """
    try:
        data = json.loads(file_path.read_text(encoding='utf-8'))
    except Exception:
        return False
    return (
        data.get('type') == 'service_account'
        and 'client_email' in data
        and 'token_uri' in data
    )


def list_google_service_accounts(creds_dir: Path = DEFAULT_CREDS_DIR) -> list[Path]:
    """
    Retorna uma lista de arquivos JSON válidos de Service Account do Google
    no diretório de credenciais especificado.
    """
    if not creds_dir.exists():
        raise FileNotFoundError(f"Diretório de credenciais não encontrado: {creds_dir}")

    creds_files = []
    for json_file in creds_dir.glob('*.json'):
        if is_google_service_account(json_file):
            creds_files.append(json_file)
    return creds_files


def select_google_service_account(
    file_name: str = None,
    creds_dir: Path = DEFAULT_CREDS_DIR
) -> Path:
    """
    Seleciona o arquivo de credenciais a ser usado.

    - Se file_name for passado, busca correspondência exata.
    - Se houver apenas um arquivo válido, retorna-o.
    - Caso contrário, lança ValueError pedindo especificar.

    Retorna o Path do JSON selecionado.
    """
    creds = list_google_service_accounts(creds_dir)
    if not creds:
        raise FileNotFoundError(f"Nenhuma credencial de Service Account encontrada em {creds_dir}")

    if file_name:
        matching = [c for c in creds if c.name == file_name]
        if not matching:
            raise ValueError(
                f"Credencial '{file_name}' não encontrada. Disponíveis: {[c.name for c in creds]}"
            )
        return matching[0]

    if len(creds) == 1:
        return creds[0]

    raise ValueError(
        f"Múltiplas credenciais encontradas: {[c.name for c in creds]}."
        " Especifique qual usar."
    )
