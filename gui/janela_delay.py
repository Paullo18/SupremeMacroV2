import tkinter as tk
from tkinter import Toplevel, IntVar, StringVar, Label, Entry, Button, Frame

def add_delay(actions, update_list, tela, *, initial=None):
    # Cria janela modal centrada e em foco
    janela = Toplevel(tela)
    janela.title("Adicionar Delay")
    janela.transient(tela)
    janela.resizable(False, False)
    janela.grab_set()
    janela.focus_force()

    # Atalhos: ESC cancela, ENTER confirma
    def on_escape(e): janela.destroy()
    def on_enter(e): confirmar()
    janela.bind('<Escape>', on_escape)
    janela.bind('<Return>', on_enter)

    # Container principal
    container = Frame(janela)
    container.pack(padx=10, pady=10, fill='x')

    # --- Nome customizado do bloco ---
    Label(container, text="Nome do bloco:").pack(anchor='w')
    label_var = StringVar(value=initial.get('name','') if initial else '')
    Entry(container, textvariable=label_var).pack(anchor='w', fill='x', pady=(0,10))

    # --- Decomposição básica de time (h/m/s) ---
    if initial and 'time' in initial:
        total_time = initial['time']
        h0 = total_time // 3600000
        rem = total_time % 3600000
        m0 = rem // 60000
        rem2 = rem % 60000
        s0 = rem2 // 1000
        struct_ms = rem2 % 1000
    else:
        h0 = m0 = s0 = struct_ms = 0

    # --- Pré-popula explicitamente ms e ms2, se vierem em initial ---
    if initial:
        ms0  = initial.get('ms',  0)    # <-- aqui: pega valor do campo único
        ms20 = initial.get('ms2', 0)    # <-- aqui: pega valor do campo estruturado
    else:
        ms0 = ms20 = 0

    # --- Fallback: se ambos forem zero, decide pelo 'time' bruto ---
    if ms0==0 and ms20==0 and initial and 'time' in initial:
        if h0==0 and m0==0 and s0==0:
            ms0  = total_time
            ms20 = 0
        else:
            ms0  = 0
            ms20 = struct_ms

    # --- Delay em milissegundos direto ---
    Label(container, text="Delay em milissegundos:").pack(anchor='w', pady=(0,5))
    ms_var = IntVar(value=ms0)  # <-- pré-preenche só o campo usado
    entry_ms = Entry(container, textvariable=ms_var)
    entry_ms.pack(anchor='w', fill='x', pady=(0,10))
    entry_ms.bind('<FocusOut>',
        lambda e,var=ms_var: var.set(0) if not e.widget.get().strip() else None
    )

    # --- Delay estruturado ---
    Label(container, text="Ou como:").pack(anchor='w')
    time_frame = Frame(container)
    time_frame.pack(anchor='w', fill='x', pady=(5,0))

    h_var   = IntVar(value=h0)
    m_var   = IntVar(value=m0)
    s_var   = IntVar(value=s0)
    ms2_var = IntVar(value=ms20)  # <-- pré-preenche só o campo usado

    Label(time_frame, text="Horas:").grid(row=0, column=0, sticky='w')
    Entry(time_frame, textvariable=h_var, width=5).grid(row=0, column=1, padx=(5,15))
    Label(time_frame, text="Minutos:").grid(row=0, column=2, sticky='w')
    Entry(time_frame, textvariable=m_var, width=5).grid(row=0, column=3)

    Label(time_frame, text="Segundos:").grid(row=1, column=0, sticky='w', pady=(5,0))
    Entry(time_frame, textvariable=s_var, width=5).grid(row=1, column=1, padx=(5,15), pady=(5,0))
    Label(time_frame, text="Milissegundos:").grid(row=1, column=2, sticky='w', pady=(5,0))
    entry_ms2 = Entry(time_frame, textvariable=ms2_var, width=5)
    entry_ms2.grid(row=1, column=3, pady=(5,0))
    entry_ms2.bind('<FocusOut>',
        lambda e,var=ms2_var: var.set(0) if not e.widget.get().strip() else None
    )

    # Mutual exclusion: zera o campo oposto assim que um puder > 0
    def on_ms_change(*_):
        try:
            if ms_var.get() > 0:
                ms2_var.set(0)
        except tk.TclError:
            pass

    def on_ms2_change(*_):
        try:
            if ms2_var.get() > 0:
                ms_var.set(0)
        except tk.TclError:
            pass

    ms_var.trace_add('write',  on_ms_change)
    ms2_var.trace_add('write', on_ms2_change)

    # --- Confirmação com try/except e gravação de ms/ms2 ---
    def confirmar():
        container.focus_set()      # força FocusOut em todos os entries
        janela.update_idletasks()
        try:
            h   = h_var.get()   or 0
            m   = m_var.get()   or 0
            s   = s_var.get()   or 0
            ms2 = ms2_var.get() or 0
            ms  = ms_var.get()  or 0
        except tk.TclError:
            h = m = s = ms2 = ms = 0
            h_var.set(m_var.set(s_var.set(ms2_var.set(ms_var.set(0)))))

        struct_total = (h*3600 + m*60 + s)*1000 + ms2
        total = struct_total if struct_total > 0 else ms

        ac = {
            "type":  "delay",
            "time":  total,
            "ms":    ms,     # <-- aqui: salva explicitamente o valor puro
            "ms2":   ms2     # <-- aqui: salva explicitamente o valor estruturado
        }
        name = label_var.get().strip()
        if name:
            ac["name"] = name

        actions.append(ac)
        update_list()
        janela.destroy()

    # Botões OK / Cancelar
    btn_frame = Frame(janela)
    btn_frame.pack(fill='x', padx=10, pady=(10,10))
    Button(btn_frame, text="Cancelar", width=10, command=janela.destroy).pack(side='right', padx=(5,0))
    Button(btn_frame, text="OK",       width=10, command=confirmar).pack(side='right')

    # Centraliza a janela na tela
    janela.update_idletasks()
    w = janela.winfo_width();  h = janela.winfo_height()
    sw = janela.winfo_screenwidth(); sh = janela.winfo_screenheight()
    x = (sw//2) - (w//2);      y = (sh//2) - (h//2)
    janela.geometry(f"{w}x{h}+{x}+{y}")
