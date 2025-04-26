import tkinter as tk
from tkinter import ttk
import json
import os

# Path padrão para o arquivo de configurações (na raiz do projeto)
CONFIG_PATH = os.path.abspath(
    os.path.join(os.path.dirname(__file__), os.pardir, "settings.json")
)

class SettingsDialog(tk.Toplevel):
    def __init__(self, parent):
        super().__init__(parent)
        self.title("Opções")
        self.geometry("600x400")
        self.transient(parent)
        self.grab_set()

        # Carrega configurações existentes ou cria vazio
        self.settings = self.load_settings()

        # ───────── Centralizar na janela pai ─────────
        self.update_idletasks()
        pw = parent.winfo_width(); ph = parent.winfo_height()
        px = parent.winfo_rootx();   py = parent.winfo_rooty()
        w = self.winfo_width();      h = self.winfo_height()
        x = px + (pw - w) // 2;       y = py + (ph - h) // 2
        self.geometry(f"{w}x{h}+{x}+{y}")

        # ───────── Layout em 2 colunas ─────────
        self.columnconfigure(0, weight=0)
        self.columnconfigure(1, weight=1)
        self.rowconfigure(0, weight=1)

        # ───────── Menu Expansível (Treeview) ─────────
        self.tree = ttk.Treeview(self, show="tree")
        self.tree.grid(row=0, column=0, sticky="ns")
        scroll = ttk.Scrollbar(self, command=self.tree.yview, orient="vertical")
        self.tree.configure(yscrollcommand=scroll.set)
        scroll.grid(row=0, column=0, sticky="nse")

        conexoes = self.tree.insert("", "end", text="Conexões", open=True)
        self.tree.insert(conexoes, "end", text="Telegram")
        self.tree.insert("", "end", text="Arquivos", open=False)
        self.tree.insert("", "end", text="Auto Save")
        self.tree.insert("", "end", text="Backup")
        workbench = self.tree.insert("", "end", text="Workbench", open=False)
        self.tree.insert(workbench, "end", text="Layout")
        self.tree.insert(workbench, "end", text="Appearance")
        self.tree.insert("", "end", text="Ajuda")

        # ───────── Painel de Conteúdo ─────────
        self.content = ttk.Frame(self, padding=10)
        self.content.grid(row=0, column=1, sticky="nsew")
        self.content.columnconfigure(0, weight=1)

        # bind de seleção
        self.tree.bind("<<TreeviewSelect>>", self.on_select)

        # inicializa com Telegram selecionado
        first_leaf = self.tree.get_children(conexoes)[0]
        self.tree.selection_set(first_leaf)
        self.show_content("Telegram")

        # ───────── Botões Salvar/Cancelar ─────────
        btn_frame = ttk.Frame(self)
        btn_frame.grid(row=1, column=0, columnspan=2, pady=10, sticky="e")
        ttk.Button(btn_frame, text="Salvar", command=self.on_save).pack(side="right", padx=5)
        ttk.Button(btn_frame, text="Cancelar", command=self.on_cancel).pack(side="right")

    def load_settings(self):
        try:
            with open(CONFIG_PATH, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}

    def save_settings(self):
        try:
            with open(CONFIG_PATH, "w", encoding="utf-8") as f:
                json.dump(self.settings, f, indent=4)
        except Exception as e:
            print(f"Erro ao salvar configurações: {e}")

    def on_select(self, event):
        sel = self.tree.selection()
        if not sel: return
        item = sel[0]
        key = self.tree.item(item, "text")
        if not self.tree.get_children(item):
            self.show_content(key)

    def clear_content(self):
        for w in self.content.winfo_children():
            w.destroy()

    def show_content(self, key):
        self.clear_content()
        if key == "Telegram":
            # Bot Token
            ttk.Label(self.content, text="Bot Token:").grid(row=0, column=0, sticky="w")
            self.token_var = tk.StringVar(value=self.settings.get("telegram_token", ""))
            ttk.Entry(self.content, textvariable=self.token_var).grid(row=1, column=0, sticky="ew", pady=5)

            # Chat ID
            ttk.Label(self.content, text="Chat ID:").grid(row=2, column=0, sticky="w", pady=(10,0))
            self.chat_id_var = tk.StringVar(value=self.settings.get("telegram_chat_id", ""))
            ttk.Entry(self.content, textvariable=self.chat_id_var).grid(row=3, column=0, sticky="ew", pady=5)
        else:
            ttk.Label(self.content, text=f"Configurações de '{key}' ainda não implementadas.")\
               .grid(row=0, column=0, sticky="w")

    def on_save(self):
        # Atualiza dicionário e persiste em arquivo
        self.settings["telegram_token"] = self.token_var.get()
        self.settings["telegram_chat_id"] = self.chat_id_var.get()
        self.save_settings()
        self.destroy()

    def on_cancel(self):
        self.destroy()
