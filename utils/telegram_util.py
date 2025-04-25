import requests
from typing import Optional

# --------------------- CONFIGURAÇÃO ---------------------
# Você pode manter BOT_TOKEN e CHAT_ID aqui ou passar direto como parâmetro.
# BOT_TOKEN = "<seu_bot_token>"
# CHAT_ID   = "<seu_chat_id>"


def send_message(bot_token: str, chat_id: str, text: str, parse_mode: str = "Markdown") -> None:
    """
    Envia uma mensagem de texto para o Telegram.
    """
    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    payload = {"chat_id": chat_id, "text": text, "parse_mode": parse_mode}
    resp = requests.post(url, json=payload)
    resp.raise_for_status()


def send_photo(
    bot_token: str,
    chat_id: str,
    photo_path: str,
    caption: Optional[str] = None
) -> None:
    """
    Envia uma imagem (photo) para o Telegram.

    :param bot_token: token do bot (ex: "1234:ABC...")
    :param chat_id:  id do chat ou canal
    :param photo_path: caminho local do arquivo de imagem (.png, .jpg)
    :param caption: legenda opcional para a foto
    """
    url = f"https://api.telegram.org/bot{bot_token}/sendPhoto"
    with open(photo_path, "rb") as f:
        files = {"photo": f}
        data = {"chat_id": chat_id}
        if caption:
            data["caption"] = caption
        resp = requests.post(url, data=data, files=files)
        resp.raise_for_status()  
