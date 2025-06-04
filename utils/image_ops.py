"""
Funções utilitárias para captura de tela, OCR e template-matching.

Dependências:
    pillow      (PIL)
    pytesseract (OCR)
    opencv-python (cv2)
    numpy
"""

from __future__ import annotations

from pathlib import Path
from typing import Dict, Tuple, Optional

import cv2
import numpy as np
import pytesseract
from PIL import Image, ImageGrab

# ----------------------------------------------------------------------
# helpers internos
# ----------------------------------------------------------------------

def _bbox_from_xywh(d: Dict[str, int]) -> Tuple[int, int, int, int]:
    """Dict {x,y,w,h}  →  (x1,y1,x2,y2)"""
    return d["x"], d["y"], d["x"] + d["w"], d["y"] + d["h"]


def _pil_to_cv(pil: Image.Image) -> np.ndarray:
    """PIL (RGB)  →  cv2 (BGR)."""
    cv = np.array(pil)
    return cv[:, :, ::-1].copy()   # RGB→BGR


# ----------------------------------------------------------------------
# API pública
# ----------------------------------------------------------------------

def grab_region(params: Dict) -> Image.Image:
    """
    Captura tela de acordo com params {'x','y','w','h'}.

    Retorna PIL.Image em RGB.
    """
    x1, y1, x2, y2 = _bbox_from_xywh(params)
    img = ImageGrab.grab(bbox=(x1, y1, x2, y2))
    return img.convert("RGB")


def grab_and_ocr(params: Dict,
                 lang: str = "eng",
                 tess_config: str = "--psm 6") -> str:
    """
    Faz screenshot da área (x,y,w,h) e devolve texto OCR.

    • lang e tess_config seguem sintaxe do Tesseract.
    """
    img = grab_region(params)
    txt = pytesseract.image_to_string(img, lang=lang, config=tess_config)
    return txt.strip()


def match_template(params: Dict,
                   method=cv2.TM_CCOEFF_NORMED) -> bool:
    """
    Procura template em região da tela:

        params = {
            'template_path': str,
            'search_box': {'x':..,'y':..,'w':..,'h':..},
            'threshold': 0.8
        }

    Retorna True se encontrado (score ≥ threshold).
    """
    # --- carrega template
    tpl_path = Path(params["template_path"]).expanduser()
    tpl = cv2.imread(str(tpl_path), cv2.IMREAD_COLOR)
    if tpl is None:
        raise FileNotFoundError(f"Template não encontrado: {tpl_path}")
    tpl_h, tpl_w = tpl.shape[:2]

    # --- captura área de busca
    search_params = params["search_box"]
    img_pil = grab_region(search_params)
    img = _pil_to_cv(img_pil)

    # evita falhar se área menor que template
    if img.shape[0] < tpl_h or img.shape[1] < tpl_w:
        return False

    res = cv2.matchTemplate(img, tpl, method)
    _, max_val, _, _ = cv2.minMaxLoc(res)
    return max_val >= params.get("threshold", 0.8)


# ----------------------------------------------------------------------
# extras opcionais
# ----------------------------------------------------------------------

def resize_keep_ratio(img: Image.Image, max_w: int, max_h: int) -> Image.Image:
    """Encolhe mantendo proporção sem ultrapassar (max_w, max_h)"""
    img = img.copy()
    img.thumbnail((max_w, max_h), Image.LANCZOS)
    return img


def draw_bbox(img: Image.Image,
              bbox: Tuple[int, int, int, int],
              color=(255, 0, 0),
              width=2) -> Image.Image:
    """Desenha retângulo no PIL.Image para debug."""
    from PIL import ImageDraw
    im = img.copy()
    draw = ImageDraw.Draw(im)
    draw.rectangle(bbox, outline=color, width=width)
    return im
