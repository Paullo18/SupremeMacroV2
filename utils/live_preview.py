"""
utils.live_preview  –  versão 100 % “thread-safe”
Mostra, em um <Canvas>, capturas periódicas de uma área da tela usando
apenas .after() – nada roda fora do main-loop do Tkinter. Permite opcionalmente passar
uma função `transform(image: PIL.Image) -> PIL.Image` para redimensionar/processar a
imagem antes de exibi‑la.
"""
from typing import Callable, Tuple, Optional
from PIL import ImageGrab, ImageTk, Image
import tkinter as tk

BBox = Optional[Tuple[int, int, int, int]]   # (x1,y1,x2,y2) ou None


class LivePreview:
    def __init__(self,
                 canvas: tk.Canvas,
                 region_getter: Callable[[], BBox],
                 interval: float = 0.25,
                 transform: Callable[[Image.Image], Image.Image] = None):
        """
        :param canvas: Canvas onde a imagem será desenhada.
        :param region_getter: função que retorna (x1,y1,x2,y2) ou None.
        :param interval: intervalo, em segundos, entre capturas.
        :param transform: função opcional que recebe um PIL.Image e devolve outro PIL.Image
                          (por exemplo, para redimensionar antes de exibir).
        """
        self.canvas       = canvas
        self.region       = region_getter           # função que retorna bbox
        self.interval_ms  = max(interval, 0.05) * 1000
        self.transform    = transform               # função opcional de transformação
        self._job_id      = None                    # id do .after()
        self._running     = False
        self._tk_img      = None                    # evita GC

    # ---------------------------------------------------
    def start(self):
        if self._running:
            return
        self._running = True
        self._loop()

    def stop(self):
        self._running = False
        if self._job_id:
            try:
                self.canvas.after_cancel(self._job_id)
            except tk.TclError:
                pass                                # canvas destruído
            self._job_id = None
        if self.canvas.winfo_exists():
            self.canvas.delete('all')
        self._tk_img = None

    # ---------------------------------------------------
    def _loop(self):
        if not self._running or not self.canvas.winfo_exists():
            return                                  # nada a fazer

        bbox = self.region()
        if bbox:
            try:
                pil_img = ImageGrab.grab(bbox=bbox)
                # Se o usuário passou uma função transform, aplica antes de converter:
                if self.transform is not None:
                    pil_img = self.transform(pil_img)
                self._tk_img = ImageTk.PhotoImage(pil_img)
                self.canvas.delete('all')
                self.canvas.create_image(0, 0, anchor='nw',
                                         image=self._tk_img)
            except Exception as exc:
                # Loga no console; evita quebrar o loop
                print("LivePreview error:", exc)

        # Agenda a próxima iteração
        self._job_id = self.canvas.after(
            int(self.interval_ms), self._loop)
