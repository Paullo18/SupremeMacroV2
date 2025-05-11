import tkinter as tk
from tkinter import (
    Toplevel,
    Frame,
    LabelFrame,
    Label,
    Button,
    Radiobutton,
    Checkbutton,
    BooleanVar,
    StringVar,
    Entry,
    filedialog,
    Canvas,
    messagebox
    )

from PIL import ImageGrab, Image, ImageTk
from datetime import datetime
import json, os
from pathlib import Path
from tkinter import ttk
# Path para configurações gerais
CONFIG_PATH = Path(__file__).parent.parent / "settings.json"

def load_settings():
    try:
        with open(CONFIG_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except:
        return {}
# -------------------------------------------------------------------
#  🔄 Função utilitária para SEMPRE recarregar as configurações
#      ‣ garante que novos bots salvos em Settings apareçam no bloco
# -------------------------------------------------------------------
def _refresh_telegram():
    global global_settings, default_token, default_chat_id, telegram_bots
    global_settings = load_settings()
    default_token = global_settings.get("telegram_token", "")
    default_chat_id = global_settings.get("telegram_chat_id", "")
    # compatível com chaves antigas **telegram_bots** e atuais **telegram**
    telegram_bots = (
        global_settings.get("telegram_bots")
        or global_settings.get("telegram")
        or []
    )

# Carrega uma primeira vez (evita NameError caso outro módulo use já‑importado)
_refresh_telegram()

# --------------------------------------------------------------------
# Lista de bots configurados
#   • Suporta tanto a chave antiga **"telegram_bots"**
#   • Quanto a chave atual     **"telegram"**
# --------------------------------------------------------------------
# Exemplo em settings.json:
# "telegram": [
#   {"name": "Alert Bot", "token": "123:ABC", "chat_id": "-100"},
#   {"name": "Logs",      "token": "456:DEF", "chat_id": "-200"}
# ]

# ========================================================================
# Janela "Screenshot"
# ========================================================================

# -------------------------------------------------------
#  Janela principal
#     • antes de criar UI chamamos _refresh_telegram()
# -------------------------------------------------------
def add_screenshot(actions, update_list, tela, *, initial=None):
    # garante lista de bots atualizada se o usuário salvou novas configs
    _refresh_telegram()
    # -------------------------------------------------------
    # Configuração inicial da janela
    # -------------------------------------------------------
    win = Toplevel(tela)
    win.withdraw()
    win.transient(tela)

    header_frame = Frame(win)
    header_frame.pack(fill="x", padx=5, pady=5)
    Label(header_frame, text="Nome do bloco:").pack(side="left")
    name_var = StringVar(value=initial.get("name", "") if initial else "")
    Entry(header_frame, textvariable=name_var, width=30).pack(side="left", padx=(5, 0))

    win.attributes("-alpha", 0)
    win.title("Adicionar Screenshot")
    win.geometry("800x600")

    win.update_idletasks()
    px, py = tela.winfo_rootx(), tela.winfo_rooty()
    pw, ph = tela.winfo_width(), tela.winfo_height()
    w, h = win.winfo_width(), win.winfo_height()
    win.geometry(f"{w}x{h}+{px + (pw - w) // 2}+{py + (ph - h) // 2}")

    # -------------------------------------------------------
    # Variáveis de estado
    # -------------------------------------------------------
    region = (
        initial.get("region", {"x": 0, "y": 0, "w": 0, "h": 0})
        if initial
        else {"x": 0, "y": 0, "w": 0, "h": 0}
    )
    mode_var = StringVar(value=initial.get("mode", "whole") if initial else "whole")
    save_disk = BooleanVar(value=(initial.get("save_to") == "disk"))
    copy_clip = BooleanVar(value=(initial.get("save_to") == "clipboard"))
    send_tel = BooleanVar(value=(initial.get("save_to") == "telegram"))
    custom_msg = BooleanVar(value=initial.get("custom_message_enabled", False) if initial else False)

    path_mode = StringVar(value=initial.get("path_mode", "default") if initial else "default")
    custom_path = StringVar(value=initial.get("custom_path", "") if initial else "")

    # ------------------------
    # Bot Telegram
    # ------------------------
    # Lista de bots ordenada alfabeticamente
    bot_names = sorted(
        [b.get("name", f"Bot {i}") for i, b in enumerate(telegram_bots)] or ["Padrão"],
        key=str.lower,
    )
    bot_var = StringVar(
        value=initial.get("bot_name", bot_names[0] if bot_names else "Padrão")
    )

    # Mensagem customizada
    message_var = StringVar(value=initial.get("custom_message", "") if initial else "")

    job_preview = {"id": None}
    thumbs = {}

    # -------------------------------------------------------
    # Funções auxiliares
    # -------------------------------------------------------
    def _thumb(img, cvs):
        w, h = int(cvs["width"]), int(cvs["height"])
        im = img.copy()
        im.thumbnail((w, h))
        ph = ImageTk.PhotoImage(im)
        cvs.delete("all")
        cvs.create_image(w // 2, h // 2, image=ph, anchor="center")
        thumbs["main"] = ph

    def _refresh_preview():
        snap = (
            ImageGrab.grab()
            if mode_var.get() == "whole"
            else ImageGrab.grab(
                bbox=(
                    region["x"],
                    region["y"],
                    region["x"] + region["w"],
                    region["y"] + region["h"],
                )
            )
        )
        _thumb(snap, canvas_main)
        job_preview["id"] = win.after(500, _refresh_preview)

    def _start_preview():
        if job_preview["id"] is None:
            _refresh_preview()

    def _stop_preview():
        if job_preview["id"] is not None:
            win.after_cancel(job_preview["id"])
            job_preview["id"] = None

    # -------------------------------------------------------
    # Callbacks UI
    # -------------------------------------------------------
    def update_mode():
        _stop_preview()
        canvas_main.delete("all")
        if mode_var.get() == "region":
            btn_select.config(state="normal")
            lbl_title.config(text="Região Selecionada")
            if region.get("w") and region.get("h"):
                _start_preview()
                lbl_coords.config(
                    text=f"x={region['x']} y={region['y']} w={region['w']} h={region['h']}"
                )
            else:
                canvas_main.create_text(
                    int(canvas_main["width"]) // 2,
                    int(canvas_main["height"]) // 2,
                    text="Selecione uma região!",
                    anchor="center",
                )
                lbl_coords.config(text="Selecione uma região!")
        else:
            btn_select.config(state="disabled")
            lbl_title.config(text="Tela Toda")
            lbl_coords.config(text="")
            _start_preview()

    def update_behavior():
        # Salvar em disco
        st_disk = "normal" if save_disk.get() else "disabled"
        for wdg in disk_frame.winfo_children():
            wdg.config(state=st_disk)

        st_dest = "normal" if save_disk.get() and path_mode.get() == "custom" else "disabled"
        btn_dest.config(state=st_dest)
        ent_dest.config(state=st_dest)

        # Telegram
        st_tel = "normal" if send_tel.get() else "disabled"
        om_bot.config(state=st_tel)
        chk_msg.config(state=st_tel)

        # Mensagem
        st_msg = "normal" if send_tel.get() and custom_msg.get() else "disabled"
        entry_msg.config(state=st_msg)

    def select_region():
        win.withdraw()
        ov = Toplevel(win)
        ov.attributes("-fullscreen", True)
        ov.attributes("-alpha", 0.3)
        ov.grab_set()
        ov.focus_force()

        cvs = Canvas(ov, cursor="cross")
        cvs.pack(fill="both", expand=True)

        rect = [None]
        sx = sy = 0

        def dn(e):
            nonlocal sx, sy
            sx, sy = cvs.canvasx(e.x), cvs.canvasy(e.y)
            rect[0] = cvs.create_rectangle(sx, sy, sx, sy, outline="red", width=2)

        def dr(e):
            cvs.coords(rect[0], sx, sy, cvs.canvasx(e.x), cvs.canvasy(e.y))

        def up(e):
            x1, y1, x2, y2 = cvs.coords(rect[0])
            ov.destroy()
            win.deiconify()
            win.lift()
            win.focus_force()
            win.after(10, win.focus_set)

            sx2, sy2 = int(min(x1, x2)), int(min(y1, y2))
            w2, h2 = int(abs(x2 - x1)), int(abs(y2 - y1))
            region.update({"x": sx2, "y": sy2, "w": w2, "h": h2})
            lbl_coords.config(text=f"x={sx2} y={sy2} w={w2} h={h2}")
            _start_preview()

        cvs.bind("<Button-1>", dn)
        cvs.bind("<B1-Motion>", dr)
        cvs.bind("<ButtonRelease-1>", up)

        def _on_overlay_escape(event):
            ov.destroy()
            win.deiconify()
            win.lift()
            win.focus_force()
            win.after(10, win.focus_set)
            return "break"

        ov.bind("<Escape>", _on_overlay_escape)

    def choose_path():
        folder = filedialog.askdirectory()
        if folder:
            custom_path.set(folder)

    def close_window(save):
        _stop_preview()
        if not save:
            win.destroy()
            return

        if not (save_disk.get() or copy_clip.get() or send_tel.get()):
            messagebox.showwarning("Configuração", "Selecione ao menos um comportamento.")
            return

        # Determina token/chat
        bot_name_selected = None
        token_used, chat_used = default_token, default_chat_id

        if send_tel.get():
            if not telegram_bots and not default_token:
                messagebox.showwarning(
                    "Telegram", "Nenhum bot configurado nas Settings.")
                return
            bot_name_selected = bot_var.get()
            sel_bot = next(
                (b for b in telegram_bots if b.get("name") == bot_name_selected),
                None,
            )
            if sel_bot:
                token_used = sel_bot.get("token", default_token)
                chat_used = sel_bot.get("chat_id", default_chat_id)

        cfg = {
            "type": "screenshot",
            "mode": mode_var.get(),
            "region": region,
            "save_to": (
                "telegram"
                if send_tel.get()
                else "disk" if save_disk.get() else "clipboard"
            ),
            "path_mode": path_mode.get(),
            "custom_path": custom_path.get(),
            "token": token_used,
            "chat_id": chat_used,
            "bot_name": bot_name_selected,
            "custom_message_enabled": custom_msg.get(),
            "custom_message": message_var.get(),
        }

        bloco_nome = name_var.get().strip()
        if bloco_nome:
            cfg["name"] = bloco_nome

        actions.clear()
        actions.append(cfg)
        update_list()
        win.destroy()

    # -------------------------------------------------------
    # Layout
    # -------------------------------------------------------
    left = Frame(win)
    right = Frame(win)
    left.pack(side="left", fill="both", expand=True, padx=10, pady=10)
    right.pack(side="right", fill="y", padx=10, pady=10)

    canvas_main = Canvas(
        left,
        width=400,
        height=400,
        bg="#eee",
        highlightthickness=1,
        highlightbackground="black",
    )
    canvas_main.pack()
    lbl_title = Label(left, text="")
    lbl_title.pack(pady=(5, 0))
    lbl_coords = Label(left, text="")
    lbl_coords.pack()

    # ------------------------
    # Seção de modos
    # ------------------------
    mf = LabelFrame(right, text="Modos")
    mf.pack(fill="x", pady=(0, 10))
    rb_whole = Radiobutton(
        mf, text="Tela toda", variable=mode_var, value="whole", command=update_mode
    )
    rb_region = Radiobutton(
        mf, text="Região na tela", variable=mode_var, value="region", command=update_mode
    )
    rb_whole.pack(anchor="w")
    rb_region.pack(anchor="w")
    btn_select = Button(mf, text="Selecionar Região", command=select_region)
    btn_select.pack(fill="x", pady=5)

    # ------------------------
    # Comportamento (Salvar/Clipboard)
    # ------------------------
    cf = LabelFrame(right, text="Comportamento*")
    cf.pack(fill="x", pady=(0, 10))

    chk_disk = Checkbutton(cf, text="Salvar no disco", variable=save_disk, command=update_behavior)
    chk_disk.pack(anchor="w")

    disk_frame = Frame(cf)
    disk_frame.pack(fill="x", padx=20)
    rb_def = Radiobutton(
        disk_frame, text="Padrão", variable=path_mode, value="default", command=update_behavior
    )
    rb_cus = Radiobutton(
        disk_frame, text="Customizado", variable=path_mode, value="custom", command=update_behavior
    )
    rb_def.pack(side="left")
    rb_cus.pack(side="left", padx=10)

    df_dest = Frame(cf)
    df_dest.pack(fill="x", padx=20, pady=(5, 0))
    btn_dest = Button(df_dest, text="Selecionar Destino", command=choose_path)
    ent_dest = Entry(df_dest, textvariable=custom_path)
    btn_dest.pack(side="left")
    ent_dest.pack(side="left", padx=5)

    chk_clip = Checkbutton(cf, text="Copiar para área de transferência", variable=copy_clip, command=update_behavior)
    chk_clip.pack(anchor="w", pady=5)

    # ------------------------
    # Enviar para Telegram
    # ------------------------
    chk_tel = Checkbutton(cf, text="Enviar para Telegram", variable=send_tel, command=update_behavior)
    chk_tel.pack(anchor="w")

    tf = Frame(cf)
    tf.pack(fill="x", padx=20, pady=(0, 5))
    Label(tf, text="Bot:").grid(row=0, column=0, sticky="e")
    
    tf.columnconfigure(1, weight=1)

    chk_msg = Checkbutton(cf, text="Mensagem Customizada", variable=custom_msg, command=update_behavior)
    chk_msg.pack(anchor="w", pady=(5, 0))
    # Combobox comum (somente seleção) em ordem alfabética
    om_bot = ttk.Combobox(
        tf,
        textvariable=bot_var,
        values=bot_names,
        state="readonly",
    )

    om_bot.grid(row=0, column=1, sticky="ew")
    mf_msg = Frame(cf)
    mf_msg.pack(fill="x", padx=20, pady=(0, 5))
    Label(mf_msg, text="Mensagem:").pack(side="left")
    entry_msg = Entry(mf_msg, textvariable=message_var, width=30)
    entry_msg.pack(side="left")

    # ------------------------
    # Botões finais
    # ------------------------
    bf = Frame(win)
    bf.place(relx=1.0, rely=1.0, anchor="se", x=-20, y=-20)
    Button(bf, text="Ok", width=10, command=lambda: close_window(True)).pack(side="right", padx=(0, 5))
    Button(bf, text="Cancelar", width=10, command=lambda: close_window(False)).pack(side="right")

    # -------------------------------------------------------
    # Inicialização
    # -------------------------------------------------------
    update_mode()
    update_behavior()

    win.bind("<Escape>", lambda e: close_window(False))
    win.deiconify()
    win.attributes("-alpha", 1)
    win.resizable(False, False)
    win.grab_set()
    win.focus_force()
