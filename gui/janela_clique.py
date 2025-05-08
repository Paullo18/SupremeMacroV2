import tkinter as tk
from tkinter import Toplevel, IntVar, StringVar, Label, Entry, Button, Frame, OptionMenu, Canvas
import pyautogui, threading, time, keyboard, os, sys
from PIL import ImageTk

# Utility to get base_dir for bundled resources
def get_base_dir():
    if getattr(sys, 'frozen', False):
        return sys._MEIPASS
    return os.path.dirname(__file__)


def select_area():
    """
    Abre um overlay fullscreen semi‑transparente.
    Clique e arraste define o retângulo.
    ESC cancela (retorna None).
    No release do botão esquerdo, retorna (x1,y1,x2,y2).
    """
    coords = {}
    result = {}

    def on_button_press(e):
        coords['x1'], coords['y1'] = e.x_root, e.y_root
        # cria o retângulo invisível inicialmente
        result['rect'] = overlay.create_rectangle(
            coords['x1'], coords['y1'], e.x_root, e.y_root,
            outline='red', width=2
        )

    def on_mouse_move(e):
        if 'rect' in result:
            overlay.coords(result['rect'],
                          coords['x1'], coords['y1'],
                          e.x_root,    e.y_root)

    def on_button_release(e):
        coords['x2'], coords['y2'] = e.x_root, e.y_root
        # fecha overlay e retorna
        root.quit()

    def on_escape(e):
        coords.clear()
        root.quit()

    root = tk.Tk()
    root.attributes('-fullscreen', True)
    # leve transparência (50%) no fundo
    root.attributes('-alpha', 0.3)
    root.configure(bg='black')

    overlay = tk.Canvas(root, cursor='cross')
    overlay.pack(fill='both', expand=True)

    overlay.bind('<ButtonPress-1>', on_button_press)
    overlay.bind('<B1-Motion>',    on_mouse_move)
    overlay.bind('<ButtonRelease-1>', on_button_release)
    root.bind('<Escape>', on_escape)

    root.mainloop()
    root.destroy()

    if not coords:
        return None

    x1, y1 = coords['x1'], coords['y1']
    x2, y2 = coords['x2'], coords['y2']
    # normalize
    return (min(x1,x2), min(y1,y2), max(x1,x2), max(y1,y2))


def add_click(actions, update_list, tela, *, initial=None):
    # --- Cria janela centrada e modal ---
    janela = Toplevel(tela)
    janela.title("Adicionar Clique")
    janela.transient(tela)
    janela.grab_set()
    janela.resizable(False, False)

    # Container de widgets
    container = Frame(janela)
    container.pack(padx=10, pady=10, fill='x')

    # --- Nome do bloco (sempre visível) ---
    Label(container, text="Nome do bloco:").pack(anchor='w')
    label_var = StringVar(value=initial.get('name','') if initial else '')
    Entry(container, textvariable=label_var).pack(anchor='w', fill='x', pady=(0,10))

    # --- Dropdown de Modo ---
    Label(container, text="Modo:").pack(anchor='w')
    modo_var = StringVar(value=(initial.get('mode','Simples') if initial else 'Simples'))
    modos = ['Simples', 'Aleatório']
    OptionMenu(container, modo_var, *modos).pack(anchor='w', fill='x', pady=(0,10))

    # --- Frames para cada modo ---
    simple_frame = Frame(container)
    random_frame = Frame(container)
    
    # --- Simple Mode Widgets ---
    # Coordenadas X/Y
    Label(simple_frame, text="X:").pack(anchor='w')
    var_x = IntVar(value=initial.get('x',0) if initial else 0)
    entry_x = Entry(simple_frame, textvariable=var_x)
    entry_x.pack(anchor='w', fill='x')

    Label(simple_frame, text="Y:").pack(anchor='w', pady=(5,0))
    var_y = IntVar(value=initial.get('y',0) if initial else 0)
    entry_y = Entry(simple_frame, textvariable=var_y)
    entry_y.pack(anchor='w', fill='x', pady=(0,10))

    # Captura Manual (F2)
    status_lbl = Label(simple_frame, text="", font=("Arial",9))
    def confirm_manual(event=None):
        stop_live.set()
        x, y = var_x.get(), var_y.get()
        nova_acao = {"type":"click","x":x,"y":y}
        name = label_var.get().strip()
        if name:
            nova_acao["name"] = name
        nova_acao["mode"] = 'Simples'
        if initial is not None:
            initial.update(nova_acao)
        else:
            actions.append(nova_acao)
        update_list()
        janela.destroy()

    def monitor_mouse_manual():
        while True:
            try:
                x, y = pyautogui.position()
                if not entry_x.winfo_exists():
                    break
                var_x.set(x)
                var_y.set(y)
                time.sleep(0.02)
                if keyboard.is_pressed('F2'):
                    status_lbl.config(text=f"Capturado: ({x}, {y})", fg="green")
                    janela.update_idletasks()
                    break
            except tk.TclError:
                break

    def start_capture_manual():
        start_btn.config(state='disabled')
        status_lbl.config(text="Aguardando F2...", fg="red")
        status_lbl.pack(anchor='w', pady=(0,10))
        threading.Thread(target=monitor_mouse_manual, daemon=True).start()

    start_btn = Button(simple_frame, text="Iniciar Captura", command=start_capture_manual)
    start_btn.pack(anchor='w', pady=(0,10))
    simple_frame.pack(fill='x')

    # --- Random Mode Widgets ---
    Label(random_frame, text="Região Selecionada:").pack(anchor='w')
    coords_lbl = Label(random_frame, text="Nenhuma região", font=("Arial",9))
    coords_lbl.pack(anchor='w', pady=(0,5))

    live_canvas = Canvas(random_frame, width=200, height=100, bg='black')
    live_canvas.pack(anchor='w', pady=(0,10))

    region = None
    stop_live = threading.Event()

    def select_region():
        nonlocal region
        stop_live.set()
        time.sleep(0.05)
        # método de seleção com overlay e ESC (estenda conforme seu código)
        #from region_select import select_area  # stub: precisa implementar
        region = select_area()
        if region:
            x1,y1,x2,y2 = region
            coords_lbl.config(text=f"({x1},{y1})-({x2},{y2})")
        start_live_preview()

    def start_live_preview():
        stop_live.clear()
        def live_loop():
            while not stop_live.is_set():
                if region:
                    x1,y1,x2,y2 = region
                    pil_img = pyautogui.screenshot(region=(x1,y1,x2-x1,y2-y1))
                    # converte para PhotoImage via PIL
                    photo = ImageTk.PhotoImage(pil_img)
                    live_canvas.delete('all')  # limpa frame anterior
                    live_canvas.create_image(0, 0, anchor='nw', image=photo)
                    # mantém referência para não ser coletado
                    live_canvas.image = photo
                time.sleep(0.2)
        threading.Thread(target=live_loop, daemon=True).start()

    Button(random_frame, text="Selecionar Região", command=select_region).pack(anchor='w', pady=(0,10))

    # --- Atualiza visibilidade de frames conforme modo ---
    def switch_mode(*args):
        if modo_var.get() == 'Simples':
            random_frame.forget()
            simple_frame.pack(fill='x')
        else:
            simple_frame.forget()
            random_frame.pack(fill='x')
    modo_var.trace_add('write', switch_mode)
    switch_mode()

    # --- Botões OK e Cancelar ---
    def on_cancel():
        stop_live.set()
        janela.destroy()
    btn_frame = Frame(janela)
    btn_frame.pack(fill='x', padx=10, pady=(0,10))
    Button(btn_frame, text="Cancelar", width=10, command=on_cancel).pack(side='right', padx=(5,0))
    Button(btn_frame, text="OK", width=10, command=confirm_manual).pack(side='right')

    # --- Global hotkeys ---
    janela.bind_all("<Return>", confirm_manual)
    janela.bind_all("<Escape>", lambda e: (stop_live.set(), janela.destroy()))

    # --- Centralizar janela ---
    def _recentralizar():
        janela.update_idletasks()
        w = janela.winfo_width()
        h = janela.winfo_height()
        rx = tela.winfo_rootx()
        ry = tela.winfo_rooty()
        rw = tela.winfo_width()
        rh = tela.winfo_height()
        x = rx + (rw - w)//2
        y = ry + (rh - h)//2
        janela.geometry(f"+{x}+{y}")
    _recentralizar()
    janela.focus_force()
