import tkinter as tk
from tkinter import messagebox


def abrir_fork_dialog(parent, bloco, conectar_ids, salvar_callback):
    """
    parent         → janela principal
    bloco          → dicionário do bloco Start Thread
    conectar_blocos→ lista de blocos conectados à saída (dicionários)
    salvar_callback→ função(block_id, thread_name, config) para gravar escolha
    """
    dlg = tk.Toplevel(parent)
    dlg.title("Configurar Forks")
    dlg.transient(parent)
    dlg.geometry("500x400")        # Tamanho inicial fixo
    dlg.resizable(False, False)    # Não redimensionável
    dlg.grab_set()                 # Foco modal na janela
    dlg.focus_force()              # Traz a janela para frente

    # --- Nome da Thread ---------------------------------------------
    tk.Label(dlg, text="Nome da Thread:").grid(
        row=0, column=0, sticky="w", padx=5, pady=5
    )
    thread_name_var = tk.StringVar(
        value=bloco.get("acao", {}).get("thread_name", "")
    )
    dlg.columnconfigure(1, weight=1)
    tk.Entry(dlg, textvariable=thread_name_var).grid(
        row=0, column=1, padx=5, pady=5, sticky="we"
    )

    # --- Recupera seleção anterior de forks -------------------------
    previous = bloco.get("acao", {}).get("forks", {})
    try:
        initial = next(k for k, v in previous.items() if v == "Continuar Fluxo")
    except StopIteration:
        initial = -1

    # --- Variável de controle (escolha principal) --------------------
    principal_var = tk.IntVar(value=initial)

    # --- Instrução ao usuário ----------------------------------------
    tk.Label(
        dlg,
        text="Selecione abaixo qual bloco será o fluxo principal."
    ).grid(
        row=1, column=0, columnspan=2,
        sticky="w", padx=5, pady=(5, 2)
    )

    # --- Frame para o fluxo principal -------------------------------
    principal_frame = tk.LabelFrame(dlg, text="Fluxo Principal")
    principal_frame.grid(
        row=2, column=0, columnspan=2,
        sticky="we", padx=5, pady=5
    )

    # --- Frame para os outros fluxos --------------------------------
    others_frame = tk.LabelFrame(dlg, text="Nova(s) Thread(s)")
    others_frame.grid(
        row=3, column=0, columnspan=2,
        sticky="we", padx=5, pady=5
    )

    # --- Cria Radiobuttons para cada destino ------------------------
    rb_widgets = {}
    for dest in conectar_ids:
        acao = dest.get("acao", {})
        # se tiver label customizada, exibe apenas ela
        if acao.get("name"):
            txt = acao["name"]
        else:
            tipo = acao.get("type", "").lower()
            if tipo == "click":
                txt = f"Click @({acao['x']},{acao['y']})"
            elif tipo == "delay":
                txt = f"Delay: {acao['time']}ms"
            elif tipo == "goto":
                txt = f"GOTO → {acao['label']}"
            elif tipo == "imagem":
                x, y, w, h = acao['x'], acao['y'], acao['w'], acao['h']
                txt = f"Img:{acao['imagem']} @({x},{y},{w},{h})"
            elif tipo == "loopstart":
                if acao.get("mode") == "quantidade":
                    txt = f"INÍCIO LOOP {acao['count']}x"
                else:
                    txt = "INÍCIO LOOP INFINITO"
            elif tipo == "ocr":
                if acao.get("verificar_vazio"):
                    txt = "OCR: [vazio]"
                else:
                    txt = f"OCR: '{acao.get('text','')}'"
            elif tipo == "ocr_duplo":
                cond = acao.get("condicao","and").upper()
                txt = (f"OCR Duplo: '{acao.get('text1','')}' "
                       f"{cond} '{acao.get('text2','')}'")
            elif tipo == "text":
                cont = acao.get("content", "")
                preview = (cont[:18] + "…") if len(cont) > 18 else cont
                txt = f'TXT: "{preview}"'
            elif tipo == "screenshot":
                if acao.get("mode") == "whole":
                    txt = "Screenshot: tela inteira"
                else:
                    x, y, w, h = acao['region'].values()
                    txt = f"Screenshot: reg ({x},{y},{w}×{h})"
            else:
                txt = dest.get("text", f"Block {dest.get('id')}")

        rb = tk.Radiobutton(
            dlg,
            text=txt,
            variable=principal_var,
            value=dest["id"],
            anchor="w",
            justify="left"
        )
        rb_widgets[dest["id"]] = rb

    # --- Função para rearranjar radiobuttons ------------------------
    def layout_rbs(*args):
        for rb in rb_widgets.values():
            rb.grid_forget()
        sel = principal_var.get()
        if sel in rb_widgets:
            rb_widgets[sel].grid(
                in_=principal_frame,
                row=0, column=0,
                sticky="w", padx=5, pady=2
            )
        row = 0
        for dest in conectar_ids:
            did = dest["id"]
            if did != sel:
                rb_widgets[did].grid(
                    in_=others_frame,
                    row=row, column=0,
                    sticky="w", padx=5, pady=2
                )
                row += 1

    principal_var.trace_add('write', layout_rbs)
    layout_rbs()

    # --- Botões OK / Cancelar ----------------------------------------
    def on_ok():
        sel = principal_var.get()
        if sel == -1:
            messagebox.showwarning(
                "Erro",
                "Selecione um destino para Nova Thread."
            )
            return
        config = {
            dest["id"]: (
                "Continuar Fluxo" if dest["id"] == sel
                else "Nova Thread"
            )
            for dest in conectar_ids
        }
        print(f"[DEBUG][FORKS CONFIG] thread_name={thread_name_var.get()}, config={config}")
        salvar_callback(
            bloco_id=bloco["id"],
            thread_name=thread_name_var.get(),
            config=config
        )
        dlg.destroy()

    btns = tk.Frame(dlg)
    btns.grid(row=4, column=0, columnspan=2, pady=10, sticky="e", padx=10)
    tk.Button(btns, text="OK", width=10, command=on_ok).pack(side="left", padx=5)
    tk.Button(btns, text="Cancelar", width=10, command=dlg.destroy).pack(side="left")

    # --- Centraliza na janela principal -----------------------------
    dlg.update_idletasks()
    px, py = parent.winfo_rootx(), parent.winfo_rooty()
    pw, ph = parent.winfo_width(), parent.winfo_height()
    ww, wh = dlg.winfo_width(), dlg.winfo_height()
    x = px + (pw - ww)//2
    y = py + (ph - wh)//2
    dlg.geometry(f"+{x}+{y}")