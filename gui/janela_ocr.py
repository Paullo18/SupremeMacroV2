import tkinter as tk
from tkinter import Toplevel, StringVar, BooleanVar, Label, Entry, Button, messagebox, Checkbutton
from PIL import ImageGrab, ImageTk
from core.inserir import inserir_acao
import pytesseract

pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"

def add_ocr(actions, update_list, tela, listbox=None):
    janela = Toplevel(tela)
    janela.grab_set()
    janela.title("Adicionar OCR")
    janela.geometry("300x250")
    
    texto_var = StringVar()
    verificar_vazio_var = BooleanVar(value=False)
    coords = {'x': 0, 'y': 0, 'w': 0, 'h': 0}

    Label(janela, text="Texto esperado:").pack(pady=5)
    Entry(janela, textvariable=texto_var).pack(pady=5)

    Checkbutton(janela, text="Verificar se está vazio", variable=verificar_vazio_var).pack(pady=5)

    def selecionar_area():
        janela.withdraw()
    
        overlay = tk.Toplevel(janela)
        overlay.attributes("-fullscreen", True)
        overlay.attributes("-alpha", 0.3)
        overlay.configure(bg="black")
        overlay.focus_force()
    
        canvas = tk.Canvas(overlay, cursor="cross", bg="black")
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
            if rect:
                canvas.coords(rect, start_x, start_y, canvas.canvasx(event.x), canvas.canvasy(event.y))
    
        def on_mouse_up(event):
            x1, y1, x2, y2 = canvas.coords(rect)
            coords['x'], coords['y'] = int(min(x1, x2)), int(min(y1, y2))
            coords['w'], coords['h'] = int(abs(x2 - x1)), int(abs(y2 - y1))
            overlay.destroy()
            janela.deiconify()
    
            if hasattr(janela, 'coords_label'):
                janela.coords_label.config(text=f"Área: x={coords['x']} y={coords['y']} w={coords['w']} h={coords['h']}")
            else:
                janela.coords_label = Label(janela, text=f"Área: x={coords['x']} y={coords['y']} w={coords['w']} h={coords['h']}")
                janela.coords_label.pack(pady=5)
    
            try:
                snapshot = ImageGrab.grab(bbox=(coords['x'], coords['y'], coords['x']+coords['w'], coords['y']+coords['h']))
                snapshot = snapshot.resize((200, int(200 * coords['h'] / coords['w'])))
                photo = ImageTk.PhotoImage(snapshot)
                label_img = Label(janela, image=photo)
                label_img.image = photo
                label_img.pack(pady=5)
            except:
                Label(janela, text="(pré-visualização não disponível)").pack(pady=5)
    
        # BINDINGS
        canvas.bind("<Button-1>", on_mouse_down)
        canvas.bind("<B1-Motion>", on_mouse_drag)
        canvas.bind("<ButtonRelease-1>", on_mouse_up)
        
        overlay.bind_all("<Escape>", lambda e: cancelar(e))
        canvas.focus_set()




    Button(janela, text="Selecionar área da tela", command=selecionar_area).pack(pady=10)

    def testar_ocr():
        if coords['w'] > 0 and coords['h'] > 0:
            bbox = (coords['x'], coords['y'], coords['x'] + coords['w'], coords['y'] + coords['h'])
            img = ImageGrab.grab(bbox=bbox)
            texto_detectado = pytesseract.image_to_string(img).strip()
            messagebox.showinfo("OCR Detectado", f"Texto detectado:\n{texto_detectado or '[vazio]'}")
        else:
            messagebox.showwarning("Área não definida", "Por favor, selecione uma área primeiro.")

    Button(janela, text="Testar OCR", command=testar_ocr).pack(pady=5)

    def confirmar():
        texto = texto_var.get()
        if coords['w'] > 0 and coords['h'] > 0:
            inserir_acao(actions, {
                "type": "ocr",
                "x": coords['x'], "y": coords['y'],
                "w": coords['w'], "h": coords['h'],
                "text": texto,
                "verificar_vazio": verificar_vazio_var.get()
            }, listbox, update_list)
            janela.destroy()
        else:
            messagebox.showerror("Erro", "A área deve ser definida.")

    frame_botoes = tk.Frame(janela)
    frame_botoes.pack(pady=10)
    Button(frame_botoes, text="OK", command=confirmar).pack(side=tk.LEFT, padx=5)
    Button(frame_botoes, text="Cancelar", command=janela.destroy).pack(side=tk.LEFT, padx=5)
