import tkinter as tk
from tkinter import Toplevel, Label, Button, messagebox
from PIL import ImageGrab, ImageTk
import pyautogui
import cv2
import numpy as np
from core.inserir import inserir_acao
import os
from datetime import datetime

def add_imagem(actions, update_list, tela):
    janela = Toplevel(tela)
    janela.title("Adicionar Reconhecimento de Imagem")
    janela.geometry("300x400")
    janela.grab_set()

    imagem_ref = {'img': None}
    area_busca = {'x': 0, 'y': 0, 'w': 0, 'h': 0}

    label_preview = None
    label_coords = None

    def selecionar_imagem():
        janela.withdraw()
        overlay = tk.Toplevel(janela)
        overlay.attributes("-fullscreen", True)
        overlay.attributes("-alpha", 0.3)
        overlay.configure(bg="black")

        canvas = tk.Canvas(overlay, cursor="cross")
        canvas.pack(fill="both", expand=True)

        rect = None
        start_x = start_y = 0

        def cancelar(event=None):
            overlay.destroy()
            janela.deiconify()

        def on_mouse_down(event):
            nonlocal start_x, start_y, rect
            start_x = canvas.canvasx(event.x)
            start_y = canvas.canvasy(event.y)
            rect = canvas.create_rectangle(start_x, start_y, start_x, start_y, outline="red", width=2)

        def on_mouse_drag(event):
            canvas.coords(rect, start_x, start_y, canvas.canvasx(event.x), canvas.canvasy(event.y))

        def on_mouse_up(event):
            x1, y1, x2, y2 = canvas.coords(rect)
            x, y = int(min(x1, x2)), int(min(y1, y2))
            w, h = int(abs(x2 - x1)), int(abs(y2 - y1))
            overlay.destroy()
            janela.deiconify()

            try:
                snapshot = ImageGrab.grab(bbox=(x, y, x + w, y + h))
                imagem_ref['img'] = snapshot

                preview = snapshot.resize((200, int(200 * h / w)))
                photo = ImageTk.PhotoImage(preview)

                nonlocal label_preview
                if label_preview:
                    label_preview.config(image=photo)
                    label_preview.image = photo
                else:
                    label_preview = Label(janela, image=photo)
                    label_preview.image = photo
                    label_preview.pack(pady=5)

            except Exception as e:
                messagebox.showerror("Erro", f"Erro ao capturar imagem: {e}")

        canvas.bind("<Button-1>", on_mouse_down)
        canvas.bind("<B1-Motion>", on_mouse_drag)
        canvas.bind("<ButtonRelease-1>", on_mouse_up)
        overlay.bind("<Escape>", cancelar)
        canvas.focus_set()

    def selecionar_area_busca():
        janela.withdraw()
        overlay = tk.Toplevel(janela)
        overlay.attributes("-fullscreen", True)
        overlay.attributes("-alpha", 0.3)
        overlay.configure(bg="blue")

        canvas = tk.Canvas(overlay, cursor="cross")
        canvas.pack(fill="both", expand=True)

        rect = None
        start_x = start_y = 0

        def cancelar(event=None):
            overlay.destroy()
            janela.deiconify()

        def on_mouse_down(event):
            nonlocal start_x, start_y, rect
            start_x = canvas.canvasx(event.x)
            start_y = canvas.canvasy(event.y)
            rect = canvas.create_rectangle(start_x, start_y, start_x, start_y, outline="yellow", width=2)

        def on_mouse_drag(event):
            canvas.coords(rect, start_x, start_y, canvas.canvasx(event.x), canvas.canvasy(event.y))

        def on_mouse_up(event):
            x1, y1, x2, y2 = canvas.coords(rect)
            area_busca['x'], area_busca['y'] = int(min(x1, x2)), int(min(y1, y2))
            area_busca['w'], area_busca['h'] = int(abs(x2 - x1)), int(abs(y2 - y1))

            overlay.destroy()
            janela.deiconify()

            nonlocal label_coords
            if label_coords:
                label_coords.config(text=f"Área: x={area_busca['x']} y={area_busca['y']} w={area_busca['w']} h={area_busca['h']}")
            else:
                label_coords = Label(janela, text=f"Área: x={area_busca['x']} y={area_busca['y']} w={area_busca['w']} h={area_busca['h']}")
                label_coords.pack(pady=5)

        canvas.bind("<Button-1>", on_mouse_down)
        canvas.bind("<B1-Motion>", on_mouse_drag)
        canvas.bind("<ButtonRelease-1>", on_mouse_up)
        overlay.bind("<Escape>", cancelar)
        canvas.focus_set()

    def testar_presenca_imagem():
        if not imagem_ref['img']:
            messagebox.showerror("Erro", "Imagem de referência não definida.")
            return

        if area_busca['w'] <= 0 or area_busca['h'] <= 0:
            messagebox.showerror("Erro", "Área de busca não definida.")
            return

        try:
            # Captura da área de busca
            bbox = (area_busca['x'], area_busca['y'], area_busca['x'] + area_busca['w'], area_busca['y'] + area_busca['h'])
            img_area = ImageGrab.grab(bbox)
            img_area_cv = cv2.cvtColor(np.array(img_area), cv2.COLOR_RGB2BGR)
            img_ref_cv = cv2.cvtColor(np.array(imagem_ref['img']), cv2.COLOR_RGB2BGR)

            result = cv2.matchTemplate(img_area_cv, img_ref_cv, cv2.TM_CCOEFF_NORMED)
            min_val, max_val, _, _ = cv2.minMaxLoc(result)

            if max_val > 0.8:
                messagebox.showinfo("Resultado", "Imagem encontrada na área selecionada.")
            else:
                messagebox.showinfo("Resultado", "Imagem NÃO encontrada.")
        except Exception as e:
            messagebox.showerror("Erro", f"Ocorreu um erro: {e}")

    def confirmar():
        if not imagem_ref['img']:
            messagebox.showerror("Erro", "Imagem não definida.")
            return
    
        if area_busca['w'] <= 0 or area_busca['h'] <= 0:
            messagebox.showerror("Erro", "Área de busca não definida.")
            return
    
        # Criar pasta tmp se não existir
        pasta_tmp = "tmp"
        os.makedirs(pasta_tmp, exist_ok=True)
    
        # Nome do arquivo com timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
        nome_arquivo = f"imagem_{timestamp}.png"
        caminho_arquivo = os.path.join(pasta_tmp, nome_arquivo)
    
        # Salvar imagem temporária
        try:
            imagem_ref['img'].save(caminho_arquivo)
        except Exception as e:
            messagebox.showerror("Erro", f"Erro ao salvar imagem: {e}")
            return
    
        # grava diretamente e dispara update_list()
        actions.append({
            "type": "imagem",
            "x": area_busca['x'], "y": area_busca['y'],
            "w": area_busca['w'], "h": area_busca['h'],
            "imagem": nome_arquivo
        })
    
        janela.destroy()


    # Botões
    Button(janela, text="Selecionar imagem", command=selecionar_imagem).pack(pady=5)
    Button(janela, text="Selecionar área de busca", command=selecionar_area_busca).pack(pady=5)
    Button(janela, text="Testar se imagem está presente", command=testar_presenca_imagem).pack(pady=5)

    frame_botoes = tk.Frame(janela)
    frame_botoes.pack(pady=10)
    Button(frame_botoes, text="OK", command=confirmar).pack(side=tk.LEFT, padx=5)
    Button(frame_botoes, text="Cancelar", command=janela.destroy).pack(side=tk.LEFT, padx=5)
