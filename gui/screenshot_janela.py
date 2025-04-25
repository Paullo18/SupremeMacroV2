import tkinter as tk
from tkinter import Toplevel, Frame, LabelFrame, Label, Button, Radiobutton, Checkbutton, BooleanVar, StringVar, Entry, filedialog, Canvas, messagebox
from PIL import ImageGrab, Image, ImageTk
from datetime import datetime

# ========================================================================
# Janela "Screenshot" – organizado com funções e widgets em ordem
# ========================================================================

def add_screenshot(actions, update_list, tela, *, initial=None):
    win = Toplevel(tela)
    win.title("Adicionar Screenshot")
    win.geometry("800x600")
    win.grab_set()

    # variáveis iniciais
    region      = initial.get('region', {'x':0,'y':0,'w':0,'h':0}) if initial else {'x':0,'y':0,'w':0,'h':0}
    mode_var    = StringVar(value=initial.get('mode','whole') if initial else 'whole')
    save_disk   = BooleanVar(value=(initial.get('save_to')=='disk'))
    copy_clip   = BooleanVar(value=(initial.get('save_to')=='clipboard'))
    send_tel    = BooleanVar(value=(initial.get('save_to')=='telegram'))
    custom_msg  = BooleanVar(value=initial.get('custom_message_enabled', False) if initial else False)
    path_mode   = StringVar(value=initial.get('path_mode','default') if initial else 'default')
    custom_path = StringVar(value=initial.get('custom_path','') if initial else '')
    token_var   = StringVar(value=initial.get('token','') if initial else '')
    chat_var    = StringVar(value=initial.get('chat_id','') if initial else '')
    message_var = StringVar(value=initial.get('custom_message','') if initial else '')
    job_preview = {'id': None}

    # thumb e preview
    thumbs = {}
    def thumb(img, cvs):
        w,h = int(cvs['width']), int(cvs['height'])
        im = img.copy(); im.thumbnail((w,h))
        ph = ImageTk.PhotoImage(im)
        cvs.delete('all'); cvs.create_image(w//2, h//2, image=ph, anchor='center')
        thumbs['main'] = ph

    def refresh_preview():
        snap = ImageGrab.grab() if mode_var.get()=='whole' else ImageGrab.grab(bbox=(region['x'],region['y'],region['x']+region['w'],region['y']+region['h']))
        thumb(snap, canvas_main)
        job_preview['id'] = win.after(500, refresh_preview)

    def start_preview():
        if job_preview['id'] is None:
            refresh_preview()

    def stop_preview():
        if job_preview['id'] is not None:
            win.after_cancel(job_preview['id']); job_preview['id'] = None

    # layout
    left = Frame(win); right = Frame(win)
    left.pack(side='left', fill='both', expand=True, padx=10, pady=10)
    right.pack(side='right', fill='y', padx=10, pady=10)

    # canvas
    canvas_main = Canvas(left, width=400, height=400, bg='#eee', highlightthickness=1, highlightbackground='black')
    canvas_main.pack()
    Label(left, text="Região Selecionada").pack(pady=(5,0))
    lbl_coords = Label(left, text=f"x={region['x']} y={region['y']} w={region['w']} h={region['h']}")
    lbl_coords.pack()

    # Modos
    mf = LabelFrame(right, text="Modos"); mf.pack(fill='x', pady=(0,10))
    Radio1 = Radiobutton(mf, text="Tela toda", variable=mode_var, value='whole')
    Radio2 = Radiobutton(mf, text="Região na tela", variable=mode_var, value='region')
    Radio1.pack(anchor='w'); Radio2.pack(anchor='w')
    btn_select = Button(mf, text="Selecionar Região")
    btn_select.pack(fill='x', pady=5)

    # Comportamento
    cf = LabelFrame(right, text="Comportamento*"); cf.pack(fill='x', pady=(0,10))
    chk_disk = Checkbutton(cf, text="Salvar no disco", variable=save_disk)
    chk_disk.pack(anchor='w')
    df = Frame(cf); df.pack(fill='x', padx=20)
    rb_def = Radiobutton(df, text="Padrão", variable=path_mode, value='default')
    rb_cus = Radiobutton(df, text="Customizado", variable=path_mode, value='custom')
    rb_def.pack(anchor='w'); rb_cus.pack(anchor='w')
    df_dest = Frame(cf); df_dest.pack(fill='x', padx=20, pady=(5,0))
    btn_dest = Button(df_dest, text="Selecionar Destino")
    ent_dest = Entry(df_dest, textvariable=custom_path)
    btn_dest.pack(side='left'); ent_dest.pack(side='left', padx=5)
    chk_clip = Checkbutton(cf, text="Copiar para área de transferência", variable=copy_clip)
    chk_clip.pack(anchor='w', pady=5)

    chk_tel = Checkbutton(cf, text="Enviar para Telegram", variable=send_tel)
    chk_tel.pack(anchor='w')
    tf = Frame(cf); tf.pack(fill='x', padx=20, pady=(0,5))
    Label(tf, text="Token:*").grid(row=0,column=0); Entry(tf, textvariable=token_var).grid(row=0,column=1)
    Label(tf, text="Chat ID:*").grid(row=1,column=0); Entry(tf, textvariable=chat_var).grid(row=1,column=1)

    chk_msg = Checkbutton(cf, text="Mensagem Customizada", variable=custom_msg)
    chk_msg.pack(anchor='w', pady=(5,0))
    mf_msg = Frame(cf); mf_msg.pack(fill='x', padx=20, pady=(0,5))
    Label(mf_msg, text="Mensagem:").pack(side='left')
    entry_msg = Entry(mf_msg, textvariable=message_var, width=30)
    entry_msg.pack(side='left')

    # vinculando comandos
    Radio1.config(command=lambda: [update_mode(), stop_preview()])
    Radio2.config(command=lambda: [update_mode(), stop_preview()])
    btn_select.config(command=lambda: select_region())
    chk_disk.config(command=lambda: update_behavior())
    rb_def.config(command=lambda: update_behavior())
    rb_cus.config(command=lambda: update_behavior())
    btn_dest.config(command=lambda: choose_path())
    chk_tel.config(command=lambda: update_behavior())
    chk_msg.config(command=lambda: update_behavior())

    # Update functions
    def update_mode():
        if mode_var.get()=='region':
            btn_select.config(state='normal')
        else:
            btn_select.config(state='disabled')

    def update_behavior():
        # disco options
        st_disk = 'normal' if save_disk.get() else 'disabled'
        for w in df.winfo_children(): w.config(state=st_disk)
        # destino customizado
        st_dest = 'normal' if save_disk.get() and path_mode.get()=='custom' else 'disabled'
        btn_dest.config(state=st_dest); ent_dest.config(state=st_dest)
        # telegram
        st_tel = 'normal' if send_tel.get() else 'disabled'
        for w in tf.winfo_children(): w.config(state=st_tel)
        # mensagem
        st_msg = 'normal' if (send_tel.get() and custom_msg.get()) else 'disabled'
        entry_msg.config(state=st_msg)

    def select_region():
        win.withdraw(); ov=Toplevel(win);
        ov.attributes('-fullscreen',True); ov.attributes('-alpha',0.3)
        cvs=Canvas(ov,cursor='cross'); cvs.pack(fill='both',expand=True)
        rect=[None]; sx=sy=0
        def dn(e): nonlocal sx,sy; sx,sy=cvs.canvasx(e.x),cvs.canvasy(e.y); rect[0]=cvs.create_rectangle(sx,sy,sx,sy,outline='red',width=2)
        def dr(e): cvs.coords(rect[0],sx,sy,cvs.canvasx(e.x),cvs.canvasy(e.y))
        def up(e): x1,y1,x2,y2=cvs.coords(rect[0]); ov.destroy(); win.deiconify(); x,y=int(min(x1,x2)),int(min(y1,y2)); w,h=int(abs(x2-x1)),int(abs(y2-y1)); region.update({'x':x,'y':y,'w':w,'h':h}); lbl_coords.config(text=f"x={x} y={y} w={w} h={h}"); start_preview()
        cvs.bind('<Button-1>',dn); cvs.bind('<B1-Motion>',dr); cvs.bind('<ButtonRelease-1>',up)
        ov.bind('<Escape>',lambda e:ov.destroy() or win.deiconify())

    def choose_path():
        folder=filedialog.askdirectory()
        if folder: custom_path.set(folder)

    def close_window(save):
        stop_preview()
        if not save: win.destroy(); return
        # validar comportamento
        if not (save_disk.get() or copy_clip.get() or send_tel.get()):
            messagebox.showwarning("Configuração","Selecione ao menos um comportamento."); return
        # validar telegram
        if send_tel.get() and not token_var.get(): messagebox.showwarning("Token","Preencha o Token."); return
        if send_tel.get() and not chat_var.get(): messagebox.showwarning("Chat ID","Preencha o Chat ID."); return
        # validar destino
        if save_disk.get() and path_mode.get()=='custom' and not custom_path.get(): messagebox.showwarning("Destino","Selecione pasta."); return
        cfg={'type':'screenshot','mode':mode_var.get(),'region':region,'save_to':('telegram' if send_tel.get() else 'disk' if save_disk.get() else 'clipboard'),'path_mode':path_mode.get(),'custom_path':custom_path.get(),'token':token_var.get(),'chat_id':chat_var.get(),'custom_message_enabled':custom_msg.get(),'custom_message':message_var.get()}
        actions.append(cfg); update_list(); win.destroy()

    # botões finais
    bf=Frame(win); bf.place(relx=1.0,rely=1.0,anchor='se',x=-20,y=-20)
    Button(bf,text="Ok",width=10,command=lambda:close_window(True)).pack(side='right',padx=(0,5))
    Button(bf,text="Cancelar",width=10,command=lambda:close_window(False)).pack(side='right')

    # inicialização
    update_mode(); update_behavior(); start_preview()
