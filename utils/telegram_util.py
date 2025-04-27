import requests
from typing import  Union, List, Optional

# --------------------- CONFIGURAÇÃO ---------------------
# Você pode manter BOT_TOKEN e CHAT_ID aqui ou passar direto como parâmetro.
# BOT_TOKEN = "<seu_bot_token>"
# CHAT_ID   = "<seu_chat_id>"


def send_message(
    bot_token: str,
    chat_id: Union[str, List[str]],
    text: str,
    parse_mode: str = "Markdown"
) -> None:
    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    # Normaliza para lista
    if isinstance(chat_id, str):
        # aceita tanto "id1,id2" quanto um único "id"
        chat_ids = [c.strip() for c in chat_id.split(",") if c.strip()]
    else:
        chat_ids = chat_id

    for cid in chat_ids:
        payload = {"chat_id": cid, "text": text, "parse_mode": parse_mode}
        resp = requests.post(url, json=payload)
        resp.raise_for_status()


def send_photo(
    bot_token: str,
    chat_id: Union[str, List[str]],
    photo_path: str,
    caption: Optional[str] = None
) -> None:
    """
    Envia uma imagem (photo) para o Telegram em múltiplos chat_ids.

    :param bot_token: token do bot (ex: "1234:ABC...")
    :param chat_id:  id do chat, lista de ids, ou string "id1,id2"
    :param photo_path: caminho local do arquivo de imagem (.png, .jpg)
    :param caption: legenda opcional para a foto
    """
    url = f"https://api.telegram.org/bot{bot_token}/sendPhoto"

    # Normaliza chat_id para lista
    if isinstance(chat_id, str):
        chat_ids = [c.strip() for c in chat_id.split(",") if c.strip()]
    else:
        chat_ids = chat_id

    for cid in chat_ids:
        with open(photo_path, "rb") as f:
            files = {"photo": f}
            data = {"chat_id": cid}
            if caption:
                data["caption"] = caption
            resp = requests.post(url, data=data, files=files)
            resp.raise_for_status()
