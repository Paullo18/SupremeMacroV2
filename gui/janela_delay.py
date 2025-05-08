import sys
import tkinter as tk
from tkinter import Toplevel, StringVar, IntVar
from tkinter import ttk
from tkcalendar import Calendar  # pip install tkcalendar

def add_delay(actions, update_list, tela, *, initial=None):
    # — Helpers internos —
    def _ensure_int(var, default=0):
        try:
            v = var.get()
            if v == '' or v is None:
                var.set(default)
        except (tk.TclError, TypeError):
            var.set(default)

    def _bind_replace_zero(entry, var):
        def on_key(e):
            ch = e.char
            # só substitui se for dígito e o conteúdo for '0' ou vazio
            if ch.isdigit() and entry.get() in ('0', ''):
                var.set(int(ch))
                return 'break'
            # senão deixa rolar o comportamento normal do Spinbox
        entry.bind('<KeyPress>', on_key)

    def _zero_other(a, b):
        try:
            if a.get() > 0:
                b.set(0)
        except tk.TclError:
            pass

    def _clamp(var, max_val):
        try:
            v = var.get()
            if v > max_val:
                var.set(max_val)
        except (tk.TclError, TypeError):
            var.set(0)

    # — Cria janela modal —
    top = Toplevel(tela)
    top.title("Adicionar Delay / Agendar Hora")
    top.transient(tela)
    top.resizable(False, False)
    top.grab_set()
    top.focus_force()
    top.columnconfigure(0, weight=1)

    # — Variáveis iniciais —
    name_var    = StringVar(value=(initial.get('name') if initial else ''))

    ms_var      = IntVar(value=(initial.get('ms')    if initial and initial.get('ms')    is not None else 0))
    total0      = (initial.get('time')               if initial and initial.get('time')  is not None else 0)
    h0          = total0 // 3600000; rem = total0 % 3600000
    m0          = rem // 60000;      rem2 = rem % 60000
    s0          = rem2 // 1000;      ms2_0 = rem2 % 1000
    h_var       = IntVar(value=h0)
    m_var       = IntVar(value=m0)
    s_var       = IntVar(value=s0)
    ms2_var     = IntVar(value=(initial.get('ms2') if initial and initial.get('ms2') is not None else ms2_0))

    date_init   = initial.get('date')    if initial else None
    hour_var    = IntVar(value=(initial.get('hour')   if initial and initial.get('hour')   is not None else 0))
    minute_var  = IntVar(value=(initial.get('minute') if initial and initial.get('minute') is not None else 0))
    second_var  = IntVar(value=(initial.get('second') if initial and initial.get('second') is not None else 0))

    # — Linha 0: Nome do bloco —
    ttk.Label(top, text="Nome do bloco:")\
        .grid(row=0, column=0, sticky="w", padx=10, pady=(10,0))
    ttk.Entry(top, textvariable=name_var)\
        .grid(row=1, column=0, sticky="ew", padx=10)

    # — Separator —
    ttk.Separator(top, orient="horizontal")\
        .grid(row=2, column=0, sticky="ew", padx=10, pady=5)

    # — Linha 3: Modo —
    mode_var = StringVar(value=(initial.get('type') if initial else 'delay'))
    mode_frame = ttk.Frame(top)
    mode_frame.grid(row=3, column=0, sticky="w", padx=10)
    def switch_mode():
        if mode_var.get() == 'delay':
            schedule_lf.grid_forget()
            delay_lf.grid(row=5, column=0, sticky="ew", padx=10)
        else:
            delay_lf.grid_forget()
            schedule_lf.grid(row=6, column=0, sticky="ew", padx=10)
        top.update_idletasks()
        rw, rh = top.winfo_reqwidth(), top.winfo_reqheight()
        sw, sh = top.winfo_screenwidth(), top.winfo_screenheight()
        x, y = (sw-rw)//2, (sh-rh)//2
        top.geometry(f"{rw}x{rh}+{x}+{y}")

    ttk.Radiobutton(mode_frame, text="Delay",        variable=mode_var, value='delay',   command=switch_mode)\
        .pack(side="left")
    ttk.Radiobutton(mode_frame, text="Agendar Hora", variable=mode_var, value='schedule',command=switch_mode)\
        .pack(side="left", padx=10)

    # — Separator —
    ttk.Separator(top, orient="horizontal")\
        .grid(row=4, column=0, sticky="ew", padx=10, pady=5)

    # — Labelframe Configurar Delay —
    delay_lf = ttk.Labelframe(top, text="Configurar Delay")
    delay_lf.columnconfigure(1, weight=1)

    # Delay em ms (sem limite)
    ttk.Label(delay_lf, text="Delay (ms):")\
        .grid(row=0, column=0, sticky="w", padx=5, pady=5)
    entry_ms = tk.Spinbox(delay_lf, from_=0, to=sys.maxsize,
                          textvariable=ms_var, width=12, increment=1)
    entry_ms.grid(row=0, column=1, sticky="w", padx=5, pady=5)
    entry_ms.bind('<FocusOut>', lambda e: _ensure_int(ms_var, 0))
    _bind_replace_zero(entry_ms, ms_var)
    ms_var.trace_add('write',    lambda *_: _clamp(ms_var,   sys.maxsize))

    # Horas (ilimitado)
    ttk.Label(delay_lf, text="Horas:")\
        .grid(row=1, column=0, sticky="w", padx=5, pady=2)
    entry_h = tk.Spinbox(delay_lf, from_=0, to=sys.maxsize,
                         textvariable=h_var, width=5, increment=1)
    entry_h.grid(row=1, column=1, sticky="w", padx=5, pady=2)
    entry_h.bind('<FocusOut>', lambda e: _ensure_int(h_var, 0))
    _bind_replace_zero(entry_h, h_var)
    h_var.trace_add('write',     lambda *_: _clamp(h_var,    sys.maxsize))

    # Minutos (ilimitado)
    ttk.Label(delay_lf, text="Minutos:")\
        .grid(row=1, column=2, sticky="w", padx=5, pady=2)
    entry_m = tk.Spinbox(delay_lf, from_=0, to=sys.maxsize,
                         textvariable=m_var, width=5, increment=1)
    entry_m.grid(row=1, column=3, sticky="w", padx=5, pady=2)
    entry_m.bind('<FocusOut>', lambda e: _ensure_int(m_var, 0))
    _bind_replace_zero(entry_m, m_var)
    m_var.trace_add('write',     lambda *_: _clamp(m_var,    sys.maxsize))

    # Segundos (ilimitado)
    ttk.Label(delay_lf, text="Segundos:")\
        .grid(row=2, column=0, sticky="w", padx=5, pady=2)
    entry_s = tk.Spinbox(delay_lf, from_=0, to=sys.maxsize,
                         textvariable=s_var, width=5, increment=1)
    entry_s.grid(row=2, column=1, sticky="w", padx=5, pady=2)
    entry_s.bind('<FocusOut>', lambda e: _ensure_int(s_var, 0))
    _bind_replace_zero(entry_s, s_var)
    s_var.trace_add('write',     lambda *_: _clamp(s_var,    sys.maxsize))

    # Milissec. estruturais (0–999)
    ttk.Label(delay_lf, text="Milissec.:")\
        .grid(row=2, column=2, sticky="w", padx=5, pady=2)
    entry_ms2 = tk.Spinbox(delay_lf, from_=0, to=999,
                           textvariable=ms2_var, width=5, increment=1)
    entry_ms2.grid(row=2, column=3, sticky="w", padx=5, pady=2)
    entry_ms2.bind('<FocusOut>', lambda e: _ensure_int(ms2_var, 0))
    _bind_replace_zero(entry_ms2, ms2_var)
    ms2_var.trace_add('write',   lambda *_: _clamp(ms2_var,  999))
    ms_var.trace_add('write',    lambda *_: _zero_other(ms_var,   ms2_var))
    ms2_var.trace_add('write',   lambda *_: _zero_other(ms2_var, ms_var))

    # — Labelframe Agendar Data e Hora — (inalterado)
    schedule_lf = ttk.Labelframe(top, text="Agendar Data e Hora")
    schedule_lf.columnconfigure(0, weight=1)
    ttk.Label(schedule_lf, text="Selecione a data:")\
        .grid(row=0, column=0, sticky="w", padx=5, pady=5)
    cal = Calendar(schedule_lf, date_pattern='yyyy-mm-dd')
    if date_init:
        try: cal.selection_set(date_init)
        except: pass
    cal.grid(row=1, column=0, columnspan=6, padx=5, pady=5)

    ttk.Label(schedule_lf, text="Hora:")\
        .grid(row=2, column=0, sticky="w", padx=5, pady=2)
    entry_h2 = tk.Spinbox(schedule_lf, from_=0, to=23, textvariable=hour_var, width=3)
    entry_h2.grid(row=2, column=1, sticky="w", padx=5, pady=2)
    entry_h2.bind('<FocusOut>', lambda e: _ensure_int(hour_var, 0))
    _bind_replace_zero(entry_h2, hour_var)
    hour_var.trace_add('write',  lambda *_: _clamp(hour_var, 23))

    ttk.Label(schedule_lf, text="Minuto:")\
        .grid(row=2, column=2, sticky="w", padx=5, pady=2)
    entry_m2 = tk.Spinbox(schedule_lf, from_=0, to=59, textvariable=minute_var, width=3)
    entry_m2.grid(row=2, column=3, sticky="w", padx=5, pady=2)
    entry_m2.bind('<FocusOut>', lambda e: _ensure_int(minute_var, 0))
    _bind_replace_zero(entry_m2, minute_var)
    minute_var.trace_add('write',lambda *_: _clamp(minute_var, 59))

    ttk.Label(schedule_lf, text="Segundo:")\
        .grid(row=2, column=4, sticky="w", padx=5, pady=2)
    entry_s2 = tk.Spinbox(schedule_lf, from_=0, to=59, textvariable=second_var, width=3)
    entry_s2.grid(row=2, column=5, sticky="w", padx=5, pady=2)
    entry_s2.bind('<FocusOut>', lambda e: _ensure_int(second_var, 0))
    _bind_replace_zero(entry_s2, second_var)
    second_var.trace_add('write',lambda *_: _clamp(second_var, 59))

    # — Separator inferior & Botões —
    ttk.Separator(top, orient="horizontal")\
        .grid(row=7, column=0, sticky="ew", padx=10, pady=5)
    btn_frame = ttk.Frame(top)
    btn_frame.grid(row=8, column=0, sticky="e", padx=10, pady=(0,10))
    ttk.Button(btn_frame, text="Cancelar", command=lambda: top.destroy())\
        .pack(side="right", padx=(0,5))
    def confirmar():
        nome = name_var.get().strip()
        if mode_var.get() == 'delay':
            total_struct = (h_var.get()*3600 + m_var.get()*60 + s_var.get())*1000 + ms2_var.get()
            total = total_struct if total_struct > 0 else ms_var.get()
            ac = {"type":"delay", "time":total, "ms":ms_var.get(), "ms2":ms2_var.get()}
        else:
            date = cal.get_date()
            ac = {
                "type":"schedule", "date":date,
                "hour":hour_var.get(), "minute":minute_var.get(), "second":second_var.get(),
                "custom_name":f"{date} {hour_var.get():02d}:{minute_var.get():02d}:{second_var.get():02d}"
            }
        if nome:
            ac["name"] = nome
        actions.append(ac)
        update_list()
        top.destroy()
    ttk.Button(btn_frame, text="OK", command=confirmar).pack(side="right")

    # — Inicializa modo e centraliza —
    switch_mode()
    top.wait_window()
