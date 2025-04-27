import tkinter as tk
from tkinter import Toplevel, Frame, LabelFrame, Label, Button, Radiobutton, Checkbutton, BooleanVar, StringVar, Entry, filedialog, Canvas, messagebox
from PIL import ImageGrab, Image, ImageTk
from datetime import datetime
import json, os
from pathlib import Path

# Path para configurações gerais
CONFIG_PATH = Path(__file__).parent.parent / "settings.json"

def load_settings():
    try:
        with open(CONFIG_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except:
        return {}

# Carrega token/chat padrão
global_settings = load_settings()
default_token = global_settings.get("telegram_token", "")
default_chat_id = global_settings.get("telegram_chat_id", "")

# ========================================================================
# Janela "Screenshot"
# ========================================================================

def add_screenshot(actions, update_list, tela, *, initial=None):
    # Cria janela filha e esconde antes de posicionar
    win = Toplevel(tela)
    win.withdraw()
    win.attributes('-alpha', 0)
    win.title("Adicionar Screenshot")
    # Define tamanho fixo
    win.geometry("800x600")
    # Janela filha modal, sem mostrar até posicionar
    win.transient(tela)
    # Calcula posição para centralizar
    win.update_idletasks()
    pw = tela.winfo_width(); ph = tela.winfo_height()
    px = tela.winfo_rootx();   py = tela.winfo_rooty()
    w = win.winfo_width();      h = win.winfo_height()
    x = px + (pw - w) // 2;      y = py + (ph - h) // 2
    win.geometry(f"{w}x{h}+{x}+{y}")

    # variáveis iniciais
    region = initial.get('region', {'x':0,'y':0,'w':0,'h':0}) if initial else {'x':0,'y':0,'w':0,'h':0}
    mode_var = StringVar(value=initial.get('mode','whole') if initial else 'whole')
    save_disk = BooleanVar(value=(initial.get('save_to')=='disk'))
    copy_clip = BooleanVar(value=(initial.get('save_to')=='clipboard'))
    send_tel = BooleanVar(value=(initial.get('save_to')=='telegram'))
    custom_msg = BooleanVar(value=initial.get('custom_message_enabled', False) if initial else False)
    path_mode = StringVar(value=initial.get('path_mode','default') if initial else 'default')
    custom_path = StringVar(value=initial.get('custom_path','') if initial else '')
    telegram_mode = StringVar(value=initial.get('telegram_mode','default') if initial else 'default')
    token_var = StringVar(value=initial.get('token','') if initial else '')
    chat_var = StringVar(value=initial.get('chat_id','') if initial else '')
    message_var = StringVar(value=initial.get('custom_message','') if initial else '')
    job_preview = {'id': None}
    thumbs = {}

    # Funções de preview
    def thumb(img, cvs):
        w,h = int(cvs['width']), int(cvs['height'])
        im = img.copy(); im.thumbnail((w,h))
        ph = ImageTk.PhotoImage(im)
        cvs.delete('all'); cvs.create_image(w//2, h//2, image=ph, anchor='center')
        thumbs['main'] = ph

    def refresh_preview():
        snap = ImageGrab.grab() if mode_var.get()=='whole' else ImageGrab.grab(
            bbox=(region['x'],region['y'],region['x']+region['w'],region['y']+region['h'])
        )
        thumb(snap, canvas_main)
        job_preview['id'] = win.after(500, refresh_preview)

    def start_preview():
        if job_preview['id'] is None:
            refresh_preview()

    def stop_preview():
        if job_preview['id'] is not None:
            win.after_cancel(job_preview['id']); job_preview['id'] = None

    # Interface
    def update_mode():
        stop_preview()
        canvas_main.delete('all')
        if mode_var.get() == 'region':
            btn_select.config(state='normal')
            canvas_main.create_text(
                int(canvas_main['width'])//2,
                int(canvas_main['height'])//2,
                text="Selecione uma região!",
                anchor='center'
            )
            lbl_title.config(text="Região Selecionada")
            lbl_coords.config(text="Selecione uma região!")
        else:
            btn_select.config(state='disabled')
            lbl_title.config(text="Tela Toda")
            lbl_coords.config(text="")
            start_preview()

    def update_behavior():
        # Salvar no disco
        st_disk = 'normal' if save_disk.get() else 'disabled'
        for w in disk_frame.winfo_children(): w.config(state=st_disk)
        # Pasta customizada
        st_dest = 'normal' if save_disk.get() and path_mode.get()=='custom' else 'disabled'
        btn_dest.config(state=st_dest); ent_dest.config(state=st_dest)
        # Telegram
        st_tel = 'normal' if send_tel.get() else 'disabled'
        for w in (rb_tel_def, rb_tel_cus): w.config(state=st_tel)
        chk_msg.config(state=st_tel)
        # Token/chat
        tok_state = 'normal' if send_tel.get() and telegram_mode.get()=='custom' else 'disabled'
        ent_token.config(state=tok_state); ent_chat.config(state=tok_state)
        # Mensagem
        st_msg = 'normal' if (send_tel.get() and custom_msg.get()) else 'disabled'
        entry_msg.config(state=st_msg)

    def select_region():
        # Oculta janela principal e cria overlay para seleção de região
        win.withdraw()
        ov = Toplevel(win)
        ov.attributes('-fullscreen', True)
        ov.attributes('-alpha', 0.3)
        # Foco e captura de eventos para overlay
        ov.grab_set()
        ov.focus_force()
        cvs = Canvas(ov, cursor='cross')
        cvs.pack(fill='both', expand=True)
        rect = [None]
        sx = sy = 0
        def dn(e):
            nonlocal sx, sy
            sx, sy = cvs.canvasx(e.x), cvs.canvasy(e.y)
            rect[0] = cvs.create_rectangle(sx, sy, sx, sy, outline='red', width=2)
        def dr(e):
            cvs.coords(rect[0], sx, sy, cvs.canvasx(e.x), cvs.canvasy(e.y))
        def up(e):
            # Ao soltar, captura área e retorna à janela principal
            x1, y1, x2, y2 = cvs.coords(rect[0])
            ov.destroy()
            win.deiconify()
            # Traz a janela principal para frente e foca nela
            win.lift()
            win.focus_force()
            win.after(10, lambda: win.focus_set())  # garante foco
            sx, sy, w, h = int(min(x1, x2)), int(min(y1, y2)), int(abs(x2 - x1)), int(abs(y2 - y1))
            region.update({'x': sx, 'y': sy, 'w': w, 'h': h})
            lbl_coords.config(text=f"x={sx} y={sy} w={w} h={h}")
            start_preview()
        cvs.bind('<Button-1>', dn)
        cvs.bind('<B1-Motion>', dr)
        cvs.bind('<ButtonRelease-1>', up)
        # ESC na sobreposição: cancela apenas a seleção
        def _on_overlay_escape(event):
            ov.destroy()
            win.deiconify()
            # Retorna foco à janela principal após ESC na seleção
            win.lift()
            win.focus_force()
            win.after(10, lambda: win.focus_set())
            return 'break'
        ov.bind('<Escape>', _on_overlay_escape)

    def choose_path():
        folder = filedialog.askdirectory()
        if folder: custom_path.set(folder)

    def close_window(save):
        stop_preview()
        if not save: win.destroy(); return
        if not (save_disk.get() or copy_clip.get() or send_tel.get()):
            return messagebox.showwarning("Configuração","Selecione ao menos um comportamento.")
        if send_tel.get() and telegram_mode.get()=='custom' and not token_var.get():
            return messagebox.showwarning("Token","Preencha o Token.")
        if send_tel.get() and telegram_mode.get()=='custom' and not chat_var.get():
            return messagebox.showwarning("Chat ID","Preencha o Chat ID.")
        token_used = default_token if telegram_mode.get()=='default' else token_var.get()
        chat_used = default_chat_id if telegram_mode.get()=='default' else chat_var.get()
        cfg = {
            'type':'screenshot','mode':mode_var.get(),'region':region,
            'save_to':('telegram' if send_tel.get() else 'disk' if save_disk.get() else 'clipboard'),
            'path_mode':path_mode.get(),'custom_path':custom_path.get(),
            'token':token_used,'chat_id':chat_used,'telegram_mode':telegram_mode.get(),
            'custom_message_enabled':custom_msg.get(),'custom_message':message_var.get()
        }
        actions.append(cfg); update_list(); win.destroy()

    # Layout
    left = Frame(win); right = Frame(win)
    left.pack(side='left', fill='both', expand=True, padx=10, pady=10)
    right.pack(side='right', fill='y', padx=10, pady=10)

    canvas_main = Canvas(left, width=400, height=400, bg='#eee', highlightthickness=1, highlightbackground='black')
    canvas_main.pack()
    lbl_title = Label(left, text="")
    lbl_title.pack(pady=(5,0))
    lbl_coords = Label(left, text="")
    lbl_coords.pack()

    # Modos
    mf = LabelFrame(right, text="Modos"); mf.pack(fill='x', pady=(0,10))
    rb_whole = Radiobutton(mf, text="Tela toda", variable=mode_var, value='whole', command=update_mode)
    rb_region = Radiobutton(mf, text="Região na tela", variable=mode_var, value='region', command=update_mode)
    rb_whole.pack(anchor='w'); rb_region.pack(anchor='w')
    btn_select = Button(mf, text="Selecionar Região", command=select_region)
    btn_select.pack(fill='x', pady=5)

    # Comportamento Disk
    cf = LabelFrame(right, text="Comportamento*"); cf.pack(fill='x', pady=(0,10))
    chk_disk = Checkbutton(cf, text="Salvar no disco", variable=save_disk, command=update_behavior)
    chk_disk.pack(anchor='w')
    disk_frame = Frame(cf); disk_frame.pack(fill='x', padx=20)
    rb_def = Radiobutton(disk_frame, text="Padrão", variable=path_mode, value='default', command=update_behavior)
    rb_cus = Radiobutton(disk_frame, text="Customizado", variable=path_mode, value='custom', command=update_behavior)
    rb_def.pack(side='left'); rb_cus.pack(side='left', padx=10)
    df_dest = Frame(cf); df_dest.pack(fill='x', padx=20, pady=(5,0))
    btn_dest = Button(df_dest, text="Selecionar Destino", command=choose_path)
    ent_dest = Entry(df_dest, textvariable=custom_path)
    btn_dest.pack(side='left'); ent_dest.pack(side='left', padx=5)
    chk_clip = Checkbutton(cf, text="Copiar para área de transferência", variable=copy_clip, command=update_behavior)
    chk_clip.pack(anchor='w', pady=5)

    # Telegram
    chk_tel = Checkbutton(cf, text="Enviar para Telegram", variable=send_tel, command=update_behavior)
    chk_tel.pack(anchor='w')
    tf = Frame(cf); tf.pack(fill='x', padx=20, pady=(0,5))
    rb_tel_def = Radiobutton(tf, text="Padrão", variable=telegram_mode, value='default', command=update_behavior)
    rb_tel_cus = Radiobutton(tf, text="Customizado", variable=telegram_mode, value='custom', command=update_behavior)
    rb_tel_def.grid(row=0, column=0, sticky='w'); rb_tel_cus.grid(row=0, column=1, sticky='w')
    Label(tf, text="Token:").grid(row=1, column=0, sticky='e')
    ent_token = Entry(tf, textvariable=token_var)
    ent_token.grid(row=1, column=1, sticky='ew')
    Label(tf, text="Chat ID:").grid(row=2, column=0, sticky='e')
    ent_chat = Entry(tf, textvariable=chat_var)
    ent_chat.grid(row=2, column=1, sticky='ew')
    chk_msg = Checkbutton(cf, text="Mensagem Customizada", variable=custom_msg, command=update_behavior)
    chk_msg.pack(anchor='w', pady=(5,0))
    mf_msg = Frame(cf); mf_msg.pack(fill='x', padx=20, pady=(0,5))
    Label(mf_msg, text="Mensagem:").pack(side='left')
    entry_msg = Entry(mf_msg, textvariable=message_var, width=30)
    entry_msg.pack(side='left')

    # Botões finais
    bf = Frame(win); bf.place(relx=1.0, rely=1.0, anchor='se', x=-20, y=-20)
    Button(bf, text="Ok", width=10, command=lambda: close_window(True)).pack(side='right', padx=(0,5))
    Button(bf, text="Cancelar", width=10, command=lambda: close_window(False)).pack(side='right')

    # Inicialização
    update_mode(); update_behavior()
    # ESC fecha janela atual e cancela alterações
    win.bind('<Escape>', lambda e: close_window(False))
    # Exibe janela após tudo pronto
    win.deiconify()
    win.attributes('-alpha', 1)
    win.resizable(False, False)
    win.grab_set()
    win.focus_force()
