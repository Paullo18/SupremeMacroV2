from . import register
from pathlib import Path
from datetime import datetime
import pyautogui      # usado para tela inteira
from PIL import ImageGrab
from utils.telegram_util import send_photo
from utils.clipboard_util import copy_image

@register("screenshot")
def run(params, ctx):
    """
    Compatível com formato antigo e com o formato novo do editor.

      • Formato antigo:
            {x,y,w,h, "save_path": "..."}
      • Formato novo:
            {
              "mode": "whole" | "region",
              "region": {x,y,w,h},
              "path_mode": "default" | "custom",
              "custom_path": ".../arquivo.png"
            }
    """

    # -------- 1. capturar imagem ----------------------------------
    mode = params.get("mode", "region").lower()

    if mode == "whole":
        img = pyautogui.screenshot()                 # tela inteira
    else:
        region = params.get("region", params)        # fallback p/ legado
        if all(k in region for k in ("x", "y", "w", "h")) and \
           (region["w"] > 0 or region["h"] > 0):
            bbox = (
                region["x"],
                region["y"],
                region["x"] + region["w"],
                region["y"] + region["h"],
            )
            img = ImageGrab.grab(bbox=bbox)
        else:                                        # nada selecionado → tela toda
            img = pyautogui.screenshot()

    # -------- 2. onde salvar --------------------------------------
    save_path = params.get("save_path")                    # legado

    if not save_path:                                      # formato novo
        if params.get("path_mode") == "custom" and params.get("custom_path"):
            save_path = params["custom_path"]
        else:
            # pasta padrão agora é <macro>/Screenshots
            macro_dir = Path(ctx["json_path"]).parent

            # se o JSON vier de tmp/, redireciona para
            # macros/<NOME_MACRO>/Screenshots
            if macro_dir.name.lower() == "tmp":
                macro_name = ctx.get("disp_name") or Path(ctx["json_path"]).stem
                alt = Path("macros") / macro_name.strip()
                alt.mkdir(parents=True, exist_ok=True)        # garante existe
                macro_dir = alt

            save_path = macro_dir / "Screenshots"

    # --- garante nome + extensão --------------------------
    save_path = Path(save_path).expanduser()

    if save_path.is_dir() or save_path.suffix == "":       # é só pasta
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        save_path = save_path / f"screenshot_{timestamp}.png"

    if save_path.suffix.lower() not in (".png", ".jpg", ".jpeg", ".bmp"):
        # se o usuário pôs caminho sem ext, acrescenta .png
        save_path = save_path.with_suffix(".png")

    save_path = Path(save_path).expanduser()
    save_path.parent.mkdir(parents=True, exist_ok=True)
    img.save(save_path)

    # -------- 3. envio opcional: Telegram -------------------------
    if params.get("save_to", "").lower() == "telegram":
        try:
            caption = params.get("custom_message", "") \
                      if params.get("custom_message_enabled") else None
            send_photo(
                bot_token = params["token"],
                chat_id   = params["chat_id"],
                photo_path= str(save_path),
                caption   = caption
            )
        except Exception as exc:
            print(f"[WARN] Falha ao enviar para Telegram: {exc}")

     # -------- 4. copiar p/ clipboard ------------------------------
    if params.get("save_to", "").lower() == "clipboard" or params.get("copy_to_clipboard"):
        try:
            copy_image(img)                       # PIL.Image ainda está em memória
        except Exception as exc:
            print(f"[WARN] Não foi possível copiar imagem para clipboard: {exc}")
