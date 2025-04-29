import tkinter as tk
from tkinter import Toplevel, IntVar, StringVar, Label, Entry, Button, Frame


def add_delay(actions, update_list, tela):
    # Cria janela modal de Delay
    janela = Toplevel(tela)
    janela.title("Adicionar Delay")
    janela.resizable(False, False)
    janela.grab_set()
    janela.focus_force()

    # Teclas de atalho: ESC para cancelar, ENTER para confirmar
    def on_escape(event):
        janela.destroy()
    def on_enter(event):
        confirmar()
    janela.bind('<Escape>', on_escape)
    janela.bind('<Return>', on_enter)

    # Container principal para alinhamento à esquerda e dimensionamento automático
    container = Frame(janela)
    container.pack(padx=10, pady=10, fill='x')

    # Nome customizado do bloco
    Label(container, text="Nome do bloco:").pack(anchor='w')
    label_var = StringVar()
    Entry(container, textvariable=label_var).pack(anchor='w', fill='x', pady=(0, 10))

    # Delay em milissegundos direto
    Label(container, text="Delay suspende a execução por um tempo em milissegundos.").pack(anchor='w', pady=(0, 5))
    Label(container, text="Milissegundos:").pack(anchor='w')
    ms_var = IntVar()
    Entry(container, textvariable=ms_var).pack(anchor='w', fill='x', pady=(0, 10))

    # Delay estruturado: horas, minutos, segundos, milissegundos
    Label(container, text="Ou como:").pack(anchor='w')
    time_frame = Frame(container)
    time_frame.pack(anchor='w', fill='x', pady=(5, 0))

    h_var = IntVar()
    m_var = IntVar()
    s_var = IntVar()
    ms2_var = IntVar()

    # Linha 1: horas e minutos
    Label(time_frame, text="Horas:").grid(row=0, column=0, sticky='w')
    Entry(time_frame, textvariable=h_var, width=5).grid(row=0, column=1, padx=(5, 15))
    Label(time_frame, text="Minutos:").grid(row=0, column=2, sticky='w')
    Entry(time_frame, textvariable=m_var, width=5).grid(row=0, column=3, padx=(5, 0))

    # Linha 2: segundos e milissegundos
    Label(time_frame, text="Segundos:").grid(row=1, column=0, sticky='w', pady=(5, 0))
    Entry(time_frame, textvariable=s_var, width=5).grid(row=1, column=1, padx=(5, 15), pady=(5, 0))
    Label(time_frame, text="Milissegundos:").grid(row=1, column=2, sticky='w', pady=(5, 0))
    Entry(time_frame, textvariable=ms2_var, width=5).grid(row=1, column=3, padx=(5, 0), pady=(5, 0))

    # Frame de botões na parte inferior, alinhados à direita
    btn_frame = Frame(janela)
    btn_frame.pack(fill='x', padx=10, pady=(10, 10))
    Button(btn_frame, text="Cancelar", width=10, command=janela.destroy).pack(side='right', padx=(5, 0))
    Button(btn_frame, text="OK", width=10, command=lambda: confirmar()).pack(side='right')

    def confirmar():
        # Calcula tempo total em milissegundos (prioriza valores estruturados)
        total = ((h_var.get() * 3600 + m_var.get() * 60 + s_var.get()) * 1000) + ms2_var.get()
        # Se não houver valores estruturados, usa o campo único
        if total == ms2_var.get():
            total = ms_var.get()
        ac = {"type": "delay", "time": total}
        name = label_var.get().strip()
        if name:
            ac["name"] = name
        actions.append(ac)
        update_list()
        janela.destroy()

    # Centraliza a janela na tela após dimensionar conteúdo
    janela.update_idletasks()
    win_w = janela.winfo_width()
    win_h = janela.winfo_height()
    scr_w = janela.winfo_screenwidth()
    scr_h = janela.winfo_screenheight()
    x = (scr_w // 2) - (win_w // 2)
    y = (scr_h // 2) - (win_h // 2)
    janela.geometry(f"{win_w}x{win_h}+{x}+{y}")
