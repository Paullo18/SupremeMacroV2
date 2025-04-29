import tkinter as tk
from tkinter import Toplevel, IntVar, StringVar, Label, Entry, Button, Frame
import pyautogui, threading, time, keyboard

def add_click(actions, update_list, tela, *, initial=None):  # <— aqui! recebe initial
    # --- Cria janela centrada e modal ---
    janela = Toplevel(tela)
    janela.title("Adicionar Clique")
    janela.transient(tela)
    janela.grab_set()
    janela.resizable(False, False)

    # Container de widgets
    container = Frame(janela)
    container.pack(padx=10, pady=10, fill='x')

    # --- Nome do bloco ---
    Label(container, text="Nome do bloco:").pack(anchor='w')
    label_var = StringVar(value=initial.get('name','') if initial else '')  # <— aqui! pré-carrega nome
    Entry(container, textvariable=label_var).pack(anchor='w', fill='x', pady=(0,10))

    # --- Coordenadas X/Y ---
    Label(container, text="X:").pack(anchor='w')
    var_x = IntVar(value=initial.get('x',0) if initial else 0)  # <— aqui! pré-carrega X
    entry_x = Entry(container, textvariable=var_x)
    entry_x.pack(anchor='w', fill='x')

    Label(container, text="Y:").pack(anchor='w', pady=(5,0))
    var_y = IntVar(value=initial.get('y',0) if initial else 0)  # <— aqui! pré-carrega Y
    entry_y = Entry(container, textvariable=var_y)
    entry_y.pack(anchor='w', fill='x', pady=(0,10))

    # --- Label de status (invisível até iniciar captura) ---
    status_lbl = Label(container, text="", font=("Arial",9))

    # --- Função de confirmação (OK / Enter) ---
    def confirm_manual(event=None):  # <— aqui! aceita evento do Enter
        x, y = var_x.get(), var_y.get()
        nova_acao = {"type":"click","x":x,"y":y}
        name = label_var.get().strip()
        if name:
            nova_acao["name"] = name

        if initial is not None:
            initial.update(nova_acao)      # <— aqui! atualiza em edição
        else:
            actions.append(nova_acao)
        try:
            update_list()
        except Exception as e:
            print("Erro em update_list:", e)
        janela.destroy()

    # --- Monitor F2 para captura automática ---
    def monitor_mouse():
        while True:
            try:
                x, y = pyautogui.position()
                if not entry_x.winfo_exists():
                    break
                var_x.set(x)
                var_y.set(y)
                time.sleep(0.02)
                if keyboard.is_pressed('F2'):
                    status_lbl.config(text=f"Capturado: ({x}, {y})", fg="green")  # <— aqui! verde após captura
                    janela.update_idletasks()                                     # <— aqui!
                    _recentralizar()                                              # <— aqui!
                    break
            except tk.TclError:
                break

    # --- Inicia captura (botão) ---
    def start_capture():
        start_btn.config(state='disabled')
        status_lbl.config(text="Aguardando F2...", fg="red")  # <— aqui! vermelho ao aguardar
        status_lbl.pack(anchor='w', pady=(0,10))               # <— aqui! agora visível
        janela.focus_force()
        threading.Thread(target=monitor_mouse, daemon=True).start()

    start_btn = Button(container, text="Iniciar Captura", command=start_capture)
    start_btn.pack(anchor='w', pady=(0,10))

    # --- Botões OK e Cancelar ---
    btn_frame = Frame(janela)
    btn_frame.pack(fill='x', padx=10, pady=(0,10))
    Button(btn_frame, text="Cancelar", width=10, command=janela.destroy).pack(side='right', padx=(5,0))
    Button(btn_frame, text="OK",       width=10, command=confirm_manual).pack(side='right')

    # --- Atalhos de teclado globalmente ---
    janela.bind_all("<Return>", confirm_manual)               # <— aqui! Enter confirma
    janela.bind_all("<Escape>", lambda e: janela.destroy())   # <— aqui! Esc cancela

    # --- Função para centralizar a janela ---
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
        janela.geometry(f"+{x}+{y}")                          # <— aqui!

    _recentralizar()      # centraliza inicialmente
    janela.focus_force()  # força foco na janela
