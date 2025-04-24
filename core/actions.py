import tkinter as tk
from tkinter import Toplevel, StringVar, IntVar, Label, Entry, Button, simpledialog, Radiobutton, messagebox, Checkbutton
import threading
import pyautogui
import time
import keyboard
from PIL import ImageGrab, ImageTk, Image
import pytesseract
import os
import cv2
import numpy as np
from datetime import datetime

def editar_acao(event, listbox, actions, update_list, tela):
    selecionado = listbox.selection()
    if not selecionado:
        return
    index = listbox.index(selecionado[0])
    acao = actions[index]
    tipo = acao.get('type')
    print("Tipo da ação selecionada:", tipo)

    if tipo in ('endif', 'else', 'loopend', 'loopcancel'):
        return

    elif acao['type'] == 'click':
        janela = Toplevel(tela)
        janela.title("Editar Clique")
        janela.geometry("300x200")
        janela.grab_set()

        var_x = IntVar(value=acao.get("x", 0))
        var_y = IntVar(value=acao.get("y", 0))

        Label(janela, text="X:").pack()
        entry_x = Entry(janela, textvariable=var_x)
        entry_x.pack()
        Label(janela, text="Y:").pack()
        entry_y = Entry(janela, textvariable=var_y)
        entry_y.pack()

        def monitorar_mouse():
            while True:
                try:
                    x, y = pyautogui.position()
                    if not entry_x.winfo_exists() or not entry_y.winfo_exists():
                        break
                    entry_x.delete(0, tk.END)
                    entry_x.insert(0, str(x))
                    entry_y.delete(0, tk.END)
                    entry_y.insert(0, str(y))
                    if keyboard.is_pressed('F2'):
                        acao["x"] = x
                        acao["y"] = y
                        update_list(listbox, actions)
                        messagebox.showinfo("Atualizado", f"Nova posição salva: ({x}, {y})")
                        janela.destroy()
                        break
                    time.sleep(0.01)
                except tk.TclError:
                    break

        threading.Thread(target=monitorar_mouse, daemon=True).start()



    elif tipo == 'type':
        janela = Toplevel(tela)
        janela.title("Editar Texto")
        janela.geometry("300x150")

        texto_var = StringVar(value=acao.get("text", ""))

        Label(janela, text="Texto a digitar:").pack()
        Entry(janela, textvariable=texto_var).pack()

        def confirmar():
            acao["text"] = texto_var.get()
            update_list(listbox, actions)
            janela.destroy()

        Button(janela, text="Salvar", command=confirmar).pack(pady=10)

    elif tipo == 'delay':
        janela = Toplevel(tela)
        janela.title("Editar Delay")
        janela.geometry("300x300")
        janela.grab_set()

        h = IntVar()
        m = IntVar()
        s = IntVar()
        ms = IntVar()

        total_ms = acao.get("time", 0)
        h.set(total_ms // 3600000)
        m.set((total_ms % 3600000) // 60000)
        s.set((total_ms % 60000) // 1000)
        ms.set(total_ms % 1000)

        Label(janela, text="Delay suspende a execução por um tempo em milissegundos.").pack(pady=5)
        Label(janela, text="Milissegundos:").pack()
        Entry(janela, textvariable=ms).pack()

        Label(janela, text="Ou como:").pack()
        Label(janela, text="Horas:").pack(); Entry(janela, textvariable=h).pack()
        Label(janela, text="Minutos:").pack(); Entry(janela, textvariable=m).pack()
        Label(janela, text="Segundos:").pack(); Entry(janela, textvariable=s).pack()
        Label(janela, text="Milissegundos:").pack(); Entry(janela, textvariable=ms).pack()

        def confirmar():
            total = ((h.get() * 3600 + m.get() * 60 + s.get()) * 1000) + ms.get()
            acao["time"] = total
            update_list(listbox, actions)
            janela.destroy()

        Button(janela, text="Confirmar", command=confirmar).pack(pady=10)



    elif tipo == 'label':
        janela = Toplevel(tela)
        janela.title("Editar Label")
        janela.geometry("300x150")

        nome_var = StringVar(value=acao.get("name", ""))

        Label(janela, text="Nome da Label:").pack()
        Entry(janela, textvariable=nome_var).pack()

        def confirmar():
            acao["name"] = nome_var.get()
            update_list(listbox, actions)
            janela.destroy()

        Button(janela, text="Salvar", command=confirmar).pack(pady=10)

    elif tipo == 'goto':
        janela = Toplevel(tela)
        janela.title("Editar GOTO")
        janela.geometry("300x150")

        label_var = StringVar(value=acao.get("label", ""))

        Label(janela, text="Nome da Label de destino:").pack()
        Entry(janela, textvariable=label_var).pack()

        def confirmar():
            acao["label"] = label_var.get()
            update_list(listbox, actions)
            janela.destroy()

        Button(janela, text="Salvar", command=confirmar).pack(pady=10)

    def testar_ocr_area(x, y, w, h, texto_esperado="", verificar_vazio=False):
        try:
            bbox = (x, y, x + w, y + h)
            img = ImageGrab.grab(bbox=bbox)
            texto_detectado = pytesseract.image_to_string(img).strip()
            if verificar_vazio:
                if texto_detectado == "":
                    messagebox.showinfo("OCR Detectado", "A área está vazia (como esperado).")
                else:
                    messagebox.showinfo("OCR Detectado", f"A área deveria estar vazia, mas detectou:\n{texto_detectado}")
            else:
                messagebox.showinfo("OCR Detectado", f"Texto detectado:\n{texto_detectado}")
        except Exception as e:
            messagebox.showerror("Erro OCR", str(e))

    def testar_ocr_duplo_areas(coords1, coords2, texto1="", texto2="", vazio1=False, vazio2=False):
        try:
            bbox1 = (coords1['x'], coords1['y'], coords1['x'] + coords1['w'], coords1['y'] + coords1['h'])
            bbox2 = (coords2['x'], coords2['y'], coords2['x'] + coords2['w'], coords2['y'] + coords2['h'])
            img1 = ImageGrab.grab(bbox=bbox1)
            img2 = ImageGrab.grab(bbox=bbox2)
            texto_detectado1 = pytesseract.image_to_string(img1).strip()
            texto_detectado2 = pytesseract.image_to_string(img2).strip()

            resultado1 = "✔️" if (vazio1 and texto_detectado1 == "") or (texto1.lower() in texto_detectado1.lower()) else "❌"
            resultado2 = "✔️" if (vazio2 and texto_detectado2 == "") or (texto2.lower() in texto_detectado2.lower()) else "❌"

            messagebox.showinfo("OCR Duplo Detectado",
                f"Área 1 ({resultado1}):\nEsperado: '{texto1}'\nDetectado: '{texto_detectado1}'\n\n"
                f"Área 2 ({resultado2}):\nEsperado: '{texto2}'\nDetectado: '{texto_detectado2}'")
        except Exception as e:
            messagebox.showerror("Erro OCR Duplo", str(e))

    if acao['type'] == 'ocr':
        janela = Toplevel(tela)
        janela.title("Editar OCR")
        janela.geometry("300x280")
        texto_var = StringVar(value=acao.get('text', ''))
        verificar_vazio = IntVar(value=1 if acao.get('verificar_vazio') else 0)
        coords = {'x': acao['x'], 'y': acao['y'], 'w': acao['w'], 'h': acao['h']}

        Label(janela, text="Texto esperado:").pack(pady=5)
        Entry(janela, textvariable=texto_var).pack(pady=5)

        Checkbutton(janela, text="Verificar se está vazio", variable=verificar_vazio).pack(pady=5)

        janela.coords_label = Label(janela, text=f"Área: x={coords['x']} y={coords['y']} w={coords['w']} h={coords['h']}")
        janela.coords_label.pack(pady=5)

        def selecionar_area():
            janela.withdraw()
            overlay = Toplevel()
            overlay.attributes("-fullscreen", True)
            overlay.attributes("-alpha", 0.3)
            canvas = tk.Canvas(overlay, cursor="cross", bg="black")
            canvas.pack(fill="both", expand=True)

            rect = None
            start_x = start_y = 0

            def cancelar(event):
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
                janela.coords_label.config(text=f"Área: x={coords['x']} y={coords['y']} w={coords['w']} h={coords['h']}")

            canvas.bind("<Button-1>", on_mouse_down)
            canvas.bind("<B1-Motion>", on_mouse_drag)
            canvas.bind("<ButtonRelease-1>", on_mouse_up)
            canvas.bind("<Escape>", cancelar)

            overlay.mainloop()

        Button(janela, text="Selecionar nova área", command=selecionar_area).pack(pady=5)
        Button(janela, text="Testar OCR", command=lambda: testar_ocr_area(coords['x'], coords['y'], coords['w'], coords['h'], texto_var.get(), verificar_vazio.get())).pack(pady=5)

        def confirmar():
            if coords['w'] == 0 or coords['h'] == 0:
                messagebox.showerror("Erro", "A área precisa estar definida.")
                return
            acao['text'] = texto_var.get()
            acao['verificar_vazio'] = bool(verificar_vazio.get())
            acao['x'] = coords['x']
            acao['y'] = coords['y']
            acao['w'] = coords['w']
            acao['h'] = coords['h']
            update_list(listbox, actions)
            janela.destroy()

        Button(janela, text="OK", command=confirmar).pack(pady=10)

    elif acao['type'] == 'ocr_duplo':
        janela = Toplevel(tela)
        janela.title("Editar OCR Duplo")
        janela.geometry("400x530")

        texto1 = StringVar(value=acao.get('text1', ''))
        texto2 = StringVar(value=acao.get('text2', ''))
        vazio1 = IntVar(value=1 if acao.get("vazio1") else 0)
        vazio2 = IntVar(value=1 if acao.get("vazio2") else 0)
        condicao = StringVar(value=acao.get('condicao', 'and'))

        coords1 = {'x': acao.get('x1', 0), 'y': acao.get('y1', 0), 'w': acao.get('w1', 0), 'h': acao.get('h1', 0)}
        coords2 = {'x': acao.get('x2', 0), 'y': acao.get('y2', 0), 'w': acao.get('w2', 0), 'h': acao.get('h2', 0)}

        Label(janela, text="Texto 1:").pack()
        Entry(janela, textvariable=texto1).pack()
        Checkbutton(janela, text="Verificar se está vazio", variable=vazio1).pack()

        label1 = Label(janela, text=f"Área 1: x={coords1['x']} y={coords1['y']} w={coords1['w']} h={coords1['h']}")
        label1.pack()
        Button(janela, text="Selecionar área 1", command=lambda: capturar_area(coords1, label1)).pack(pady=5)

        Label(janela, text="Texto 2:").pack()
        Entry(janela, textvariable=texto2).pack()
        Checkbutton(janela, text="Verificar se está vazio", variable=vazio2).pack()

        label2 = Label(janela, text=f"Área 2: x={coords2['x']} y={coords2['y']} w={coords2['w']} h={coords2['h']}")
        label2.pack()
        Button(janela, text="Selecionar área 2", command=lambda: capturar_area(coords2, label2)).pack(pady=5)

        Label(janela, text="Condição:").pack()
        Radiobutton(janela, text="Ambos (AND)", variable=condicao, value="and").pack(anchor="w")
        Radiobutton(janela, text="Um ou outro (OR)", variable=condicao, value="or").pack(anchor="w")

        Button(janela, text="Testar OCR", command=lambda: testar_ocr_duplo_areas(coords1, coords2, texto1.get(), texto2.get(), vazio1.get(), vazio2.get())).pack(pady=5)

        def capturar_area(coords, label):
            janela.withdraw()
            overlay = Toplevel()
            overlay.attributes("-fullscreen", True)
            overlay.attributes("-alpha", 0.3)
            canvas = tk.Canvas(overlay, cursor="cross", bg="black")
            canvas.pack(fill="both", expand=True)

            rect = None
            start_x = start_y = 0

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
                coords['x'] = int(min(x1, x2))
                coords['y'] = int(min(y1, y2))
                coords['w'] = int(abs(x2 - x1))
                coords['h'] = int(abs(y2 - y1))
                overlay.destroy()
                janela.deiconify()
                label.config(text=f"x={coords['x']} y={coords['y']} w={coords['w']} h={coords['h']}")

            canvas.bind("<Button-1>", on_mouse_down)
            canvas.bind("<B1-Motion>", on_mouse_drag)
            canvas.bind("<ButtonRelease-1>", on_mouse_up)

            overlay.mainloop()

        def confirmar():
            acao['text1'] = texto1.get()
            acao['text2'] = texto2.get()
            acao['vazio1'] = bool(vazio1.get())
            acao['vazio2'] = bool(vazio2.get())
            acao['condicao'] = condicao.get()
            acao['x1'], acao['y1'], acao['w1'], acao['h1'] = coords1['x'], coords1['y'], coords1['w'], coords1['h']
            acao['x2'], acao['y2'], acao['w2'], acao['h2'] = coords2['x'], coords2['y'], coords2['w'], coords2['h']
            update_list(listbox, actions)
            janela.destroy()

        Button(janela, text="Salvar", command=confirmar).pack(pady=10)
    
    elif tipo == 'imagem':
        from core.storage import caminho_arquivo_tmp

        janela = Toplevel(tela)
        janela.title("Editar Reconhecimento de Imagem")
        janela.geometry("300x400")
        janela.grab_set()

        imagem_ref = {'img': None}
        area_busca = {'x': acao['x'], 'y': acao['y'], 'w': acao['w'], 'h': acao['h']}

        label_preview = None
        label_coords = None

        def restaurar_imagem():
            # Tenta primeiro na pasta tmp
            nome_arquivo = acao.get("imagem", "")
            caminho = os.path.join("tmp", nome_arquivo)
            if not os.path.exists(caminho) and caminho_arquivo_tmp:
                # Tenta resolver a partir da pasta da macro
                macro_dir = os.path.dirname(caminho_arquivo_tmp)
                caminho = os.path.join(macro_dir, nome_arquivo)

            if os.path.exists(caminho):
                try:
                    with Image.open(caminho) as img:
                        imagem_ref['img'] = img.copy()
                except Exception as e:
                    messagebox.showerror("Erro", f"Erro ao carregar imagem: {e}")

        restaurar_imagem()

        def atualizar_preview():
            nonlocal label_preview
            if imagem_ref['img'] and area_busca['w'] > 0 and area_busca['h'] > 0:
                try:
                    preview = imagem_ref['img'].resize((200, int(200 * area_busca['h'] / area_busca['w'])))
                    photo = ImageTk.PhotoImage(preview)
                    if label_preview:
                        label_preview.config(image=photo)
                        label_preview.image = photo
                    else:
                        label_preview = Label(janela, image=photo)
                        label_preview.image = photo
                        label_preview.pack(pady=5)
                except Exception as e:
                    messagebox.showerror("Erro", f"Erro ao criar preview: {e}")

        atualizar_preview()

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
                bbox = (area_busca['x'], area_busca['y'], area_busca['x'] + area_busca['w'], area_busca['y'] + area_busca['h'])
                img_area = ImageGrab.grab(bbox)
                img_area_cv = cv2.cvtColor(np.array(img_area), cv2.COLOR_RGB2BGR)
                img_ref_cv = cv2.cvtColor(np.array(imagem_ref['img']), cv2.COLOR_RGB2BGR)

                result = cv2.matchTemplate(img_area_cv, img_ref_cv, cv2.TM_CCOEFF_NORMED)
                _, max_val, _, _ = cv2.minMaxLoc(result)

                if max_val > 0.8:
                    messagebox.showinfo("Resultado", "Imagem encontrada na área selecionada.")
                else:
                    messagebox.showinfo("Resultado", "Imagem NÃO encontrada.")
            except Exception as e:
                messagebox.showerror("Erro", f"Ocorreu um erro ao testar: {e}")

        def confirmar():
            if not imagem_ref['img']:
                messagebox.showerror("Erro", "Imagem não definida.")
                return

            if area_busca['w'] <= 0 or area_busca['h'] <= 0:
                messagebox.showerror("Erro", "Área de busca não definida.")
                return

            pasta_tmp = "tmp"
            os.makedirs(pasta_tmp, exist_ok=True)

            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
            nome_arquivo = f"imagem_{timestamp}.png"
            caminho_arquivo = os.path.join(pasta_tmp, nome_arquivo)

            try:
                imagem_ref['img'].save(caminho_arquivo)
            except Exception as e:
                messagebox.showerror("Erro", f"Erro ao salvar imagem: {e}")
                return

            acao['x'] = area_busca['x']
            acao['y'] = area_busca['y']
            acao['w'] = area_busca['w']
            acao['h'] = area_busca['h']
            acao['imagem'] = nome_arquivo

            update_list(listbox, actions)
            janela.destroy()

        Button(janela, text="Selecionar imagem", command=selecionar_imagem).pack(pady=5)
        Button(janela, text="Selecionar área de busca", command=selecionar_area_busca).pack(pady=5)
        Button(janela, text="Testar se imagem está presente", command=testar_presenca_imagem).pack(pady=5)

        frame_botoes = tk.Frame(janela)
        frame_botoes.pack(pady=10)
        Button(frame_botoes, text="Salvar", command=confirmar).pack(side=tk.LEFT, padx=5)
        Button(frame_botoes, text="Cancelar", command=janela.destroy).pack(side=tk.LEFT, padx=5)


    elif tipo == 'loopstart':
        janela = Toplevel(tela)
        janela.title("Editar Loop")
        janela.geometry("300x200")
        janela.grab_set()

        tipo_loop = StringVar(value=acao.get("mode", "quantidade"))
        quantidade = IntVar(value=acao.get("count", 1))

        Radiobutton(janela, text="Loop com quantidade fixa", variable=tipo_loop, value="quantidade").pack(anchor="w")
        Entry(janela, textvariable=quantidade).pack()
        Radiobutton(janela, text="Loop infinito", variable=tipo_loop, value="infinito").pack(anchor="w")

        def confirmar():
            if tipo_loop.get() == "quantidade":
                acao["mode"] = "quantidade"
                acao["count"] = quantidade.get()
            else:
                acao["mode"] = "infinito"
                acao.pop("count", None)
            update_list(listbox, actions)
            janela.destroy()

        Button(janela, text="Confirmar", command=confirmar).pack(pady=10)