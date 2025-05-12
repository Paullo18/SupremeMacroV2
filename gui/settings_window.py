import tkinter as tk
from tkinter import ttk
from core.config_manager import ConfigManager
from handlers.credentials_handler import list_google_service_accounts
from core import telegram_listener as tl

class SettingsDialog(tk.Toplevel):
    def __init__(self, parent):
        super().__init__(parent)
        self.title("Opções")
        self.transient(parent)
        self.grab_set()

        # Carrega configurações via ConfigManager
        self.settings = ConfigManager.load()
        self.sheet_configs = self.settings.get("google_sheets", [])
        self.telegram_configs = self.settings.get("telegram", [])
        self.saved_energy_level = self.settings.get("energy_saving_level", "Desligado")
        initial = self.settings.get("google_sheets_creds", "")
        self.gs_var = tk.StringVar(value=initial)

        # Telegram Commands (Geral)
        self.telegram_cmd_cfg   = self.settings.get("telegram_commands", {})
        self.telegram_cmd_enab  = self.telegram_cmd_cfg.get("enabled", True)
        default_bot = self.telegram_configs[0]["name"] if self.telegram_configs else ""
        self.telegram_cmd_bot   = self.telegram_cmd_cfg.get("bot", default_bot)

        # Listas de linhas dinâmicas
        self.telegram_vars = []  # tuples: (name_var, token_var, chat_id_var, entry_widgets..., remove_btn)
        self.sheet_vars = []     # tuples: (name_var, id_var, entry_widgets..., remove_btn)

        # Layout
        self._center_window(parent, width=600, height=400)
        self.columnconfigure(0, weight=0)
        self.columnconfigure(1, weight=1)

        # Treeview categorias
        self.tree = ttk.Treeview(self, show="tree")
        self.tree.grid(row=0, column=0, sticky="ns")
        scroll = ttk.Scrollbar(self, orient="vertical", command=self.tree.yview)
        scroll.grid(row=0, column=0, sticky="nse")
        self.tree.configure(yscrollcommand=scroll.set)
        geral = self.tree.insert("", "end", text="Geral", open=True)
        self.tree.insert(geral, "end", text="Economia de Energia")
        conexoes = self.tree.insert("", "end", text="Conexões", open=True)
        self.tree.insert(conexoes, "end", text="Telegram")
        self.tree.insert(conexoes, "end", text="Google Sheets")
        arquivos = self.tree.insert("", "end", text="Arquivos", open=False)
        self.tree.insert(arquivos, "end", text="Auto Save")
        self.tree.insert(arquivos, "end", text="Backup")
        workbench = self.tree.insert("", "end", text="Workbench", open=False)
        self.tree.insert(workbench, "end", text="Layout")
        self.tree.insert(workbench, "end", text="Appearance")
        self.tree.insert("", "end", text="Ajuda")

        # Conteúdo
        self.content = ttk.Frame(self, padding=10)
        self.content.grid(row=0, column=1, sticky="nsew")
        self.content.columnconfigure(0, weight=1)
        self.content.columnconfigure(1, weight=1)

        self.tree.bind("<<TreeviewSelect>>", self._on_select)
        # Seleção inicial
        self.tree.selection_set(self.tree.get_children(geral)[0])
        self._show_content("Economia de Energia")

        # Botões Salvar/Cancelar
        btn_frame = ttk.Frame(self)
        btn_frame.grid(row=1, column=0, columnspan=2, pady=10, sticky="e")
        ttk.Button(btn_frame, text="Salvar",   command=self._on_save  ).pack(side="right", padx=5)

        ttk.Button(btn_frame, text="Cancelar", command=self._on_cancel).pack(side="right")
    def _on_cancel(self):
        """Fecha a janela sem salvar alterações."""
        self.destroy()

    def _center_window(self, parent, width, height):
        self.update_idletasks()
        pw, ph = parent.winfo_width(), parent.winfo_height()
        px, py = parent.winfo_rootx(), parent.winfo_rooty()
        x = px + (pw - width) // 2
        y = py + (ph - height) // 2
        self.geometry(f"{width}x{height}+{x}+{y}")

    def _on_select(self, event):
        sel = self.tree.selection()
        if not sel:
            return
        key = self.tree.item(sel[0], "text")
        if not self.tree.get_children(sel[0]):
            self._show_content(key)

    def _clear_content(self):
        for w in self.content.winfo_children():
            w.destroy()

    def _show_content(self, key):
        self._clear_content()
        if key == "Economia de Energia":
            self._build_general()
        elif key == "Telegram":
            self._build_telegram()
        elif key == "Google Sheets":
            self._build_sheets()
        else:
            ttk.Label(self.content, text=f"Configurações de '{key}' não implementadas.").grid(row=0, column=0, sticky="w")

    # --- Geral ---
    def _build_general(self):
        ttk.Label(self.content, text="Selecione o nível de economia de energia:").grid(row=0, column=0, columnspan=4, sticky="w", pady=(0,10))
        self.energy_saving_var = tk.StringVar(value=self.saved_energy_level)
        # Radio buttons empilhados (cada nível em uma linha)
        for idx, level in enumerate(["Desligado", "Nível 1", "Nível 2", "Nível 3"]):
            ttk.Radiobutton(
                self.content, text=level,
                variable=self.energy_saving_var, value=level
            ).grid(row=1 + idx, column=0, sticky="w", padx=5)

        # ────────────────────────────────────────────
        # Itens afetados (delay em ms por bloco)
        # ────────────────────────────────────────────
        # Título
        self.energy_title_lbl = ttk.Label(self.content, text="Itens afetados:")
        self.energy_title_lbl.grid(row=5, column=0, sticky="w", pady=(10,2))

        # Labels empilhadas, recuadas para hierarquia
        self.img_delay_lbl  = ttk.Label(self.content, text="")
        self.ocr_delay_lbl  = ttk.Label(self.content, text="")
        self.ocr2_delay_lbl = ttk.Label(self.content, text="")
        self.img_delay_lbl .grid(row=6, column=0, sticky="w", pady=(0,2), padx=(20,0))
        self.ocr_delay_lbl .grid(row=7, column=0, sticky="w", pady=(0,2), padx=(20,0))
        self.ocr2_delay_lbl.grid(row=8, column=0, sticky="w", pady=(0,2), padx=(20,0))
        # Função que atualiza os textos de delay
        def _update_energy_labels(*args):
            lvl = self.energy_saving_var.get()
            mapping = {
                "Desligado": {"Imagem": 0,   "OCR": 0,   "OCR Duplo": 0},
                "Nível 1":   {"Imagem": "+50",  "OCR": "+100", "OCR Duplo": "+150"},
                "Nível 2":   {"Imagem": "+100", "OCR": "+200", "OCR Duplo": "+300"},
                "Nível 3":   {"Imagem": "+200", "OCR": "+400", "OCR Duplo": "+600"},
            }
            d = mapping.get(lvl, mapping["Desligado"])
            self.img_delay_lbl.config( text=f"Imagem: {d['Imagem']} ms" )
            self.ocr_delay_lbl.config( text=f"OCR: {d['OCR']} ms" )
            self.ocr2_delay_lbl.config(text=f"OCR Duplo: {d['OCR Duplo']} ms")

        # Atualiza sempre que mudar o nível e uma vez ao abrir
        self.energy_saving_var.trace_add("write", _update_energy_labels)
        _update_energy_labels()

    # --- Telegram ---
    def _build_telegram(self):
        # Checkbox
        self.tg_enabled_var = tk.BooleanVar(value=self.telegram_cmd_enab)
        chk = ttk.Checkbutton(
            self.content,
            text="Ativar Comandos do Telegram",
            variable=self.tg_enabled_var, onvalue=True, offvalue=False
        )
        chk.grid(row=1, column=0, columnspan=2, sticky="w", pady=(2,6))

        # Dropdown bot
        ttk.Label(self.content, text="Bot controlador:").grid(row=2, column=0, sticky="w")
        bot_names = [cfg.get("name", "") for cfg in self.telegram_configs]
        self.tg_bot_var = tk.StringVar(value=self.telegram_cmd_bot)
        self.tg_bot_combo = ttk.Combobox(
            self.content,
            textvariable=self.tg_bot_var,
            values=bot_names,
            state="readonly",
            width=25
        )
        self.tg_bot_combo.grid(row=2, column=1, sticky="w")

        # Enable/disable combobox when checkbox changes
        def _toggle_combo(*_):
            state = "readonly" if self.tg_enabled_var.get() else "disabled"
            self.tg_bot_combo.configure(state=state)
        self.tg_enabled_var.trace_add("write", _toggle_combo)
        _toggle_combo()

        sep = ttk.Separator(self.content, orient="horizontal")
        sep.grid(row=3, column=0, columnspan=4, sticky="ew", pady=(10,10))

        # ------------------------------------------------------------------
        # Resto dos controles Telegram (bots cadastrados)
        # ------------------------------------------------------------------

        ttk.Button(self.content, text="Adicionar Telegram", command=self._add_telegram).grid(row=4, column=2, sticky="e", pady=5)
        for col, text in enumerate(["Nome", "Bot Token", "Chat ID"]):
            ttk.Label(self.content, text=text).grid(row=5, column=col, sticky="w", pady=(10,0))

        self.telegram_frame = ttk.Frame(self.content)
        for i in range(4):
            self.telegram_frame.columnconfigure(i, weight=1 if i<3 else 0)
        self.telegram_frame.grid(row=6, column=0, columnspan=4, sticky="nsew")
        # Reconstrói linhas
        existing = self.telegram_vars or []
        self.telegram_vars.clear()
        for cfg in self.telegram_configs:
            self._add_telegram_row(cfg.get("name", ""), cfg.get("token", ""), cfg.get("chat_id", ""))
        if not self.telegram_vars:
            self._add_telegram_row("", "", "")

    def _add_telegram(self):
        self._add_telegram_row("", "", "")

    def _add_telegram_row(self, name, token, chat_id):
        row = len(self.telegram_vars)
        name_var = tk.StringVar(value=name)
        token_var = tk.StringVar(value=token)
        chat_id_var = tk.StringVar(value=chat_id)
        e1 = ttk.Entry(self.telegram_frame, textvariable=name_var, width=20)
        e1.grid(row=row, column=0, sticky="ew", pady=2)
        e2 = ttk.Entry(self.telegram_frame, textvariable=token_var, width=30)
        e2.grid(row=row, column=1, sticky="ew", pady=2)
        e3 = ttk.Entry(self.telegram_frame, textvariable=chat_id_var, width=20)
        e3.grid(row=row, column=2, sticky="ew", pady=2)
        btn = ttk.Button(self.telegram_frame, text="-", width=2, command=lambda idx=row: self._remove_telegram_row(idx))
        btn.grid(row=row, column=3, padx=5)
        self.telegram_vars.append((name_var, token_var, chat_id_var, e1, e2, e3, btn))

    def _remove_telegram_row(self, index):
        name_var, token_var, chat_id_var, e1, e2, e3, btn = self.telegram_vars.pop(index)
        for widget in (e1, e2, e3, btn):
            widget.destroy()
        # Reposiciona as linhas restantes
        for i, (nv, tv, cv, w1, w2, w3, b) in enumerate(self.telegram_vars):
            w1.grid_configure(row=i)
            w2.grid_configure(row=i)
            w3.grid_configure(row=i)
            b.configure(command=lambda idx=i: self._remove_telegram_row(idx))
            b.grid_configure(row=i)

    # --- Google Sheets ---
    def _build_sheets(self):
        ttk.Label(self.content, text="Credencial (JSON):").grid(row=0, column=0, sticky="w")
        creds = list_google_service_accounts()
        names = [p.name for p in creds]
        ttk.Combobox(self.content, textvariable=self.gs_var, values=names, state="readonly").grid(row=1, column=0, columnspan=2, sticky="ew", pady=5)
        ttk.Button(self.content, text="Adicionar Sheet", command=self._add_sheet).grid(row=2, column=2, sticky="e", pady=5)
        ttk.Label(self.content, text="Nome").grid(row=3, column=0, sticky="w", pady=(10,0))
        ttk.Label(self.content, text="Sheet ID").grid(row=3, column=1, sticky="w", pady=(10,0))
        self.sheets_frame = ttk.Frame(self.content)
        for i in range(3):
            self.sheets_frame.columnconfigure(i, weight=1 if i<2 else 0)
        self.sheets_frame.grid(row=4, column=0, columnspan=3, sticky="nsew")
        existing = self.sheet_vars or []
        self.sheet_vars.clear()
        for cfg in self.sheet_configs:
            self._add_sheet_row(cfg.get("name", ""), cfg.get("id", ""))
        if not self.sheet_vars:
            self._add_sheet_row("", "")

    def _add_sheet(self):
        self._add_sheet_row("", "")

    def _add_sheet_row(self, name, sheet_id):
        row = len(self.sheet_vars)
        name_var = tk.StringVar(value=name)
        id_var = tk.StringVar(value=sheet_id)
        e1 = ttk.Entry(self.sheets_frame, textvariable=name_var, width=20)
        e1.grid(row=row, column=0, sticky="ew", pady=2)
        e2 = ttk.Entry(self.sheets_frame, textvariable=id_var, width=30)
        e2.grid(row=row, column=1, sticky="ew", pady=2)
        btn = ttk.Button(self.sheets_frame, text="-", width=2, command=lambda idx=row: self._remove_sheet_row(idx))
        btn.grid(row=row, column=2, padx=5)
        self.sheet_vars.append((name_var, id_var, e1, e2, btn))

    def _remove_sheet_row(self, index):
        name_var, id_var, e1, e2, btn = self.sheet_vars.pop(index)
        for widget in (e1, e2, btn):
            widget.destroy()
        for i, (nv, iv, w1, w2, b) in enumerate(self.sheet_vars):
            w1.grid_configure(row=i)
            w2.grid_configure(row=i)
            b.configure(command=lambda idx=i: self._remove_sheet_row(idx))
            b.grid_configure(row=i)

    def _on_save(self):
        # Telegram
        configs = []
        for name_var, token_var, chat_id_var, *_ in self.telegram_vars:
            name = name_var.get().strip()
            token = token_var.get().strip()
            chat_id = chat_id_var.get().strip()
            if name and token and chat_id:
                configs.append({"name": name, "token": token, "chat_id": chat_id})
        self.settings["telegram"] = configs or self.telegram_configs
        
        # Sheets
        self.settings["google_sheets_creds"] = self.gs_var.get()
        configs = []
        for name_var, id_var, *_ in self.sheet_vars:
            name = name_var.get().strip()
            sid = id_var.get().strip()
            if name and sid:
                configs.append({"name": name, "id": sid})
        self.settings["google_sheets"] = configs
        
        # Economia de Energia
        self.settings["energy_saving_level"] = getattr(self, 'energy_saving_var', tk.StringVar()).get()

        # Telegram Commands (controle remoto)
        enabled = getattr(self, "tg_enabled_var", tk.BooleanVar(value=True)).get()
        bot_sel = getattr(self, "tg_bot_var", tk.StringVar(value="")).get()
        self.settings["telegram_commands"] = {
            "enabled": enabled,
            "bot":     bot_sel
        }

        # Salva configurações
        ConfigManager.save(self.settings)

        # Liga/desliga listener de acordo com flag
        # Reinicia o listener para aplicar QUALQUER alteração imediatamente
        tl.stop_telegram_bot()      # inofensivo se já estiver parado
        if enabled:                 # religa só se a flag estiver marcada
            tl.start_telegram_bot()

        self.destroy()