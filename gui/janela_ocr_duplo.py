import tkinter as tk
from tkinter import Toplevel, StringVar, Label, Entry, Button, messagebox, Radiobutton, BooleanVar
from PIL import ImageGrab, ImageTk
from core.inserir import inserir_acao
import pytesseract

def add_ocr_duplo(actions, atualizar, tela, listbox):
    janela = Toplevel(tela)
    janela.grab_set()

    janela.title("Adicionar OCR Duplo")
    janela.geometry("350x500")

    texto1 = StringVar()
    texto2 = StringVar()
    condicao = StringVar(value="and")
    vazio1 = BooleanVar(value=False)
    vazio2 = BooleanVar(value=False)

    coords1 = {'x': 0, 'y': 0, 'w': 0, 'h': 0}
    coords2 = {'x': 0, 'y': 0, 'w': 0, 'h': 0}

    def selecionar_area(coords, label):
        janela.withdraw()
        overlay = tk.Toplevel()
        overlay.attributes("-fullscreen", True)
        overlay.attributes("-alpha", 0.3)
        overlay.grab_set()  # bloqueia outras janelas enquanto seleciona
        canvas = tk.Canvas(overlay, cursor="cross", bg="black")
        canvas.pack(fill="both", expand=True)

        rect = None
        start_x = start_y = 0

        def cancelar(event):
            overlay.destroy()
            janela.deiconify()
            janela.grab_set()

        def on_mouse_down(event):
            nonlocal start_x, start_y, rect
            start_x = canvas.canvasx(event.x)
            start_y = canvas.canvasy(event.y)
            rect = canvas.create_rectangle(start_x, start_y, start_x, start_y, outline="red", width=2)

        def on_mouse_drag(event):
            if rect:
                canvas.coords(rect, start_x, start_y, canvas.canvasx(event.x), canvas.canvasy(event.y))

        def on_mouse_up(event):
            x1, y1, x2, y2 = canvas.coords(rect)
            coords['x'], coords['y'] = int(min(x1, x2)), int(min(y1, y2))
            coords['w'], coords['h'] = int(abs(x2 - x1)), int(abs(y2 - y1))
            overlay.destroy()
            janela.deiconify()
            janela.grab_set()
            label.config(text=f"x={coords['x']} y={coords['y']} w={coords['w']} h={coords['h']}")

            try:
                snapshot = ImageGrab.grab(bbox=(coords['x'], coords['y'], coords['x']+coords['w'], coords['y']+coords['h']))
                snapshot = snapshot.resize((200, int(200 * coords['h'] / coords['w'])))
                photo = ImageTk.PhotoImage(snapshot)
                img = Label(janela, image=photo)
                img.image = photo
                img.pack()
            except:
                pass

        canvas.bind("<Button-1>", on_mouse_down)
        canvas.bind("<B1-Motion>", on_mouse_drag)
        canvas.bind("<ButtonRelease-1>", on_mouse_up)
        
        overlay.bind_all("<Escape>", lambda e: cancelar(e))
        canvas.focus_set()


    def testar_ocr_duplo():
        if coords1['w'] > 0 and coords2['w'] > 0:
            bbox1 = (coords1['x'], coords1['y'], coords1['x'] + coords1['w'], coords1['y'] + coords1['h'])
            bbox2 = (coords2['x'], coords2['y'], coords2['x'] + coords2['w'], coords2['y'] + coords2['h'])
            img1 = ImageGrab.grab(bbox=bbox1)
            img2 = ImageGrab.grab(bbox=bbox2)
            texto1_detectado = pytesseract.image_to_string(img1).strip()
            texto2_detectado = pytesseract.image_to_string(img2).strip()
            messagebox.showinfo("OCR Duplo Detectado",
                f"Área 1:\n{texto1_detectado or '[vazio]'}\n\nÁrea 2:\n{texto2_detectado or '[vazio]'}")
        else:
            messagebox.showwarning("Áreas não definidas", "Por favor, defina ambas as áreas.")
    
    Button(janela, text="Testar OCR", command=testar_ocr_duplo).pack(pady=5)


    Label(janela, text="Texto 1:").pack()
    Entry(janela, textvariable=texto1).pack()
    tk.Checkbutton(janela, text="Verificar se está vazio", variable=vazio1).pack()

    label_area1 = Label(janela, text="Área 1: não definida")
    label_area1.pack()
    Button(janela, text="Selecionar Área 1", command=lambda: selecionar_area(coords1, label_area1)).pack()

    Label(janela, text="Texto 2:").pack()
    Entry(janela, textvariable=texto2).pack()
    tk.Checkbutton(janela, text="Verificar se está vazio", variable=vazio2).pack()

    label_area2 = Label(janela, text="Área 2: não definida")
    label_area2.pack()
    Button(janela, text="Selecionar Área 2", command=lambda: selecionar_area(coords2, label_area2)).pack()

    Label(janela, text="Condição:").pack()
    Radiobutton(janela, text="Ambos (AND)", variable=condicao, value="and").pack(anchor="w")
    Radiobutton(janela, text="Um ou outro (OR)", variable=condicao, value="or").pack(anchor="w")

    def confirmar():
        if coords1['w'] == 0 or coords2['w'] == 0:
            messagebox.showerror("Erro", "Ambas as áreas devem estar definidas.")
            return
        inserir_acao(actions, {
            "type": "ocr_duplo",
            "x1": coords1['x'], "y1": coords1['y'], "w1": coords1['w'], "h1": coords1['h'],
            "x2": coords2['x'], "y2": coords2['y'], "w2": coords2['w'], "h2": coords2['h'],
            "text1": texto1.get(), "text2": texto2.get(),
            "condicao": condicao.get(),
            "vazio1": vazio1.get(),
            "vazio2": vazio2.get()
        }, listbox, atualizar)
        janela.destroy()

    Button(janela, text="Adicionar", command=confirmar).pack(pady=10)
