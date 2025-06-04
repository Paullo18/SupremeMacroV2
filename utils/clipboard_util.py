"""
Funções para copiar texto ou imagem para o clipboard no Windows.

Requer:  pip install pywin32  (pacote pypi: pywin32)
"""

import io
from typing import Union
from PIL import Image
import win32clipboard
import win32con


def _image_to_dib_bytes(im: Image.Image) -> bytes:
    """
    Converte PIL.Image (RGB ou RGBA) para bytes no formato DIB
    exigido pelo Windows clipboard.
    """
    # garante formato BMP 24-bit (o CF_DIB não suporta PNG)
    with io.BytesIO() as bmp:
        im.convert("RGB").save(bmp, "BMP")
        dib = bmp.getvalue()[14:]      # salta cabeçalho BMP de 14 bytes
    return dib


def copy_image(im: Union[Image.Image, str]) -> None:
    """
    Copia uma PIL.Image (ou caminho de arquivo) para a área de transferência.
    """
    if isinstance(im, str):
        im = Image.open(im)

    dib = _image_to_dib_bytes(im)

    win32clipboard.OpenClipboard()
    try:
        win32clipboard.EmptyClipboard()
        win32clipboard.SetClipboardData(win32con.CF_DIB, dib)
    finally:
        win32clipboard.CloseClipboard()
