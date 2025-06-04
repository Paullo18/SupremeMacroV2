import tkinter as tk
from tkinter import ttk
from core import show_warning
import tkinter.font as tkfont
import keyboard  # pip install keyboard
import threading

# Texto de placeholder
PLACEHOLDER = "Exemplo: <CTRL+S>"

def add_texto(actions, update_list, tela, listbox=None, *, initial=None):
    # cria janela modal
    top = tk.Toplevel(tela)
    top.withdraw()
    top.transient(tela)
    top.title("Adicionar Texto/Atalho")
    top.resizable(False, False)

    # --- Nome do bloco --------------------------------------------
    ttk.Label(top, text="Nome do bloco:")\
        .pack(anchor="w", padx=10, pady=(10, 0))
    name_var = tk.StringVar(value=initial.get('name', '') if initial else '')
    ttk.Entry(top, textvariable=name_var, width=48)\
        .pack(fill="x", padx=10, pady=(0, 10))

    # --- Seleção de modo: Texto ou Comando de Teclado -------------
    mode_frame = ttk.Frame(top)
    mode_frame.pack(anchor="w", padx=10, pady=(0, 10))
    mode_var = tk.StringVar(
        value=('hotkey' if initial and initial.get('type') == 'hotkey' else 'text')
    )
    ttk.Label(mode_frame, text="Modo:")\
        .grid(row=0, column=0, sticky="w")
    ttk.Radiobutton(mode_frame, text="Digitar Texto", variable=mode_var,
                    value='text', command=lambda: switch_mode())\
        .grid(row=0, column=1, padx=5)
    ttk.Radiobutton(mode_frame, text="Comandos de Teclado", variable=mode_var,
                    value='hotkey', command=lambda: switch_mode())\
        .grid(row=0, column=2, padx=5)

    # --- Frame para digitar texto ---------------------------------
    text_frame = ttk.Frame(top)
    ttk.Label(text_frame, text="Texto a digitar:")\
        .pack(anchor="w", padx=10, pady=(0, 2))
    texto_var = tk.StringVar(
        value=initial.get('content', '') if initial and initial.get('type') == 'text' else ''
    )
    entry_text = ttk.Entry(text_frame, textvariable=texto_var, width=48)
    entry_text.pack(fill="x", padx=10, pady=(0, 10))

    # --- Frame para capturar atalho de teclado ---------------------
    hotkey_frame = ttk.Frame(top)
    ttk.Label(hotkey_frame, text="Pressione o atalho desejado:")\
        .grid(row=0, column=0, columnspan=2, sticky='w', pady=(0, 2))

    hotkey_var = tk.StringVar()
    if initial and initial.get('type') == 'hotkey' and initial.get('command'):
        hotkey_var.set(initial['command'])
        has_initial = True
    else:
        hotkey_var.set(PLACEHOLDER)
        has_initial = False

    entry_hotkey = ttk.Entry(hotkey_frame, textvariable=hotkey_var, state='readonly')
    entry_hotkey.grid(row=1, column=0, sticky='we', padx=(0, 5))
    entry_hotkey.bind('<Control-v>', lambda e: 'break')
    hotkey_frame.columnconfigure(0, weight=1)

    # botão Limpar ao lado
    ttk.Button(hotkey_frame, text="Limpar Atalho", command=lambda: show_placeholder())\
        .grid(row=1, column=1, sticky='e')

    # configura fontes para placeholder
    default_font = tkfont.Font(entry_hotkey, entry_hotkey.cget("font"))
    placeholder_font = default_font.copy()
    placeholder_font.configure(slant="italic")

    def show_placeholder():
        entry_hotkey.configure(font=placeholder_font, foreground='gray50')
        hotkey_var.set(PLACEHOLDER)

    def clear_placeholder():
        entry_hotkey.configure(font=default_font, foreground='black')
        hotkey_var.set('')

    # --- Funções de captura de teclado -----------------------------
    def compute_combo(keys_set):
        mods = []
        if any(k in keys_set for k in ('ctrl', 'control')):
            mods.append('Ctrl')
        if 'shift' in keys_set:
            mods.append('Shift')
        if 'alt' in keys_set:
            mods.append('Alt')
        others = sorted(k.upper() for k in keys_set
                        if k.lower() not in ('ctrl', 'control', 'shift', 'alt'))
        return '+'.join(mods + others)

    def finish_capture(combo):
        entry_hotkey.configure(font=default_font, foreground='black')
        hotkey_var.set(combo)
        keyboard.unhook_all()
        top.grab_release()
        top.focus_force()

    def capture_thread():
        recorded = set()
        pressed  = set()

        def handler(event):
            name = event.name.lower()
            # primeira tecla deve ser modificador
            if event.event_type == keyboard.KEY_DOWN and not recorded:
                if name not in ('ctrl', 'control', 'alt', 'shift', 'windows', 'win'):
                    keyboard.unhook_all()
                    top.after(0, top.grab_release)
                    return

            if event.event_type == keyboard.KEY_DOWN:
                pressed.add(name)
                recorded.add(name)
                top.after(0, hotkey_var.set, compute_combo(recorded))

            elif event.event_type == keyboard.KEY_UP:
                pressed.discard(name)
                if not pressed and recorded:
                    combo = compute_combo(recorded)
                    keyboard.unhook_all()
                    top.after(0, finish_capture, combo)

        keyboard.hook(handler, suppress=True)

    def start_capture(event=None):
        clear_placeholder()
        top.grab_set()
        threading.Thread(target=capture_thread, daemon=True).start()

    entry_hotkey.bind('<Button-1>', start_capture)

    # switch_mode precisa existir antes de ser chamado
    def switch_mode():
        if mode_var.get() == 'text':
            show_placeholder()
            hotkey_frame.pack_forget()
            text_frame.pack(fill='x', padx=10, pady=(0, 10))
            entry_text.focus_set()
        else:
            text_frame.pack_forget()
            hotkey_frame.pack(fill='x', padx=10, pady=(0, 10))
            entry_hotkey.config(state='readonly')
            if not has_initial and not hotkey_var.get():
                show_placeholder()

    # aplica modo inicial
    switch_mode()

    # --- Botões OK / Cancelar sempre na parte inferior ------------
    frame_btn = ttk.Frame(top)
    ttk.Button(frame_btn, text="Cancelar", command=lambda: (keyboard.unhook_all(), top.grab_release(), top.destroy()))\
        .pack(side='left', padx=5)
    ttk.Button(frame_btn, text="OK", command=lambda e=None: confirmar())\
        .pack(side='left')
    frame_btn.pack(side='bottom', fill='x', padx=10, pady=(10, 10))

    # binds gerais
    top.bind("<Return>", lambda e: confirmar())
    top.bind("<Escape>", lambda e: (keyboard.unhook_all(), top.grab_release(), top.destroy()))

    # --- Centralizar e bloquear resize ----------------------------
    top.update_idletasks()
    px, py = tela.winfo_rootx(), tela.winfo_rooty()
    pw, ph = tela.winfo_width(), tela.winfo_height()
    w, h   = top.winfo_width(), top.winfo_height()
    x = px + (pw - w)//2
    y = py + (ph - h)//2
    top.geometry(f"{w}x{h}+{x}+{y}")
    top.deiconify()
    top.minsize(w, h)
    top.maxsize(w, h)
    top.focus_force()

    def confirmar(event=None):
        nome = name_var.get().strip()
        modo = mode_var.get()
        if modo == 'text':
            conteudo = texto_var.get().strip()
            if not conteudo:
                show_warning("Campo vazio", "Digite algum texto antes de confirmar.")
                return
            ac = {"type": "text", "content": conteudo}
        else:
            comando = hotkey_var.get().strip()
            if not comando or comando == PLACEHOLDER:
                show_warning("Campo vazio", "Defina um atalho antes de confirmar.")
                return
            ac = {"type": "hotkey", "command": comando, "content": comando}

        if nome:
            ac["name"] = nome
        if initial is not None:
            initial.clear()
            initial.update(ac)
        actions.append(ac)

        if callable(update_list):
            update_list()

        if listbox is not None:
            preview = (
                f"TXT: \"{conteudo[:18]}…\"" if modo == 'text' and len(conteudo) > 20 else
                f"CMD: {comando}"
            )
            sel = listbox.curselection() if initial is not None else None
            if sel:
                idx = sel[0]
                listbox.delete(idx)
                listbox.insert(idx, preview)
            else:
                listbox.insert(tk.END, preview)

        top.destroy()
