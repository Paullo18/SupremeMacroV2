import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from blocos import BlocoManager
from setas import SetaManager
from eventos import bind_eventos
from util import clicou_em_linha
from PIL import Image, ImageTk
from core.update_list import update_list
from core.storage import export_macro_to_tmp, salvar_macro_gui, obter_caminho_macro_atual
from core.executar import executar_macro_flow
from gui.macro_status import MacroStatusWindow
from gui.settings_window import SettingsDialog
from gui.ocr_to_sheet import add_ocr_to_sheet
from gui.telegram_command import add_telegram_command
import json, os, shutil, threading
import core.storage as storage
from core.telegram_listener import start_telegram_bot
from tkinter import messagebox


def macro_em_pasta_macros(path_):
    """Retorna True se *path_* for .../Macros/<nome>/macro.json."""
    abs_path   = os.path.abspath(path_)
    macros_abs = os.path.abspath(storage.MACROS_DIR)
    return abs_path.endswith(os.sep + "macro.json") and abs_path.startswith(macros_abs + os.sep)

def _formatar_rotulo(params: dict) -> str:
        """Devolve o texto a ser exibido abaixo do bloco."""
        # 1) nomes dados pelo usuário têm prioridade absoluta
        if params.get("custom_name"):
            return params["custom_name"]
        if params.get("name"):
            return params["name"]
    
        # 2) fallback para rótulos automáticos
        tipo = params.get("type", "").lower()
        if tipo == "click":
            return f"Click @({params.get('x')},{params.get('y')})"
        elif tipo == "delay":
            return f"Delay: {params.get('time')}ms"
        elif tipo == "goto":
            return f"GOTO → {params.get('label')}"
        elif tipo == "imagem":
            return f"Img:{params.get('imagem')} @({params.get('x')},{params.get('y')},{params.get('w')},{params.get('h')})"
        elif tipo == "label":
            return f"Label: {params.get('name')}"
        elif tipo == "loopstart":
            return "INÍCIO LOOP INFINITO" if params.get("mode") != "quantidade" \
                   else f"INÍCIO LOOP {params.get('count')}x"
        elif tipo == "ocr":
            return f"OCR: '{params.get('text')}'"
        elif tipo == "ocr_duplo":
            cond = params.get("condicao", "and").upper()
            return f"OCR Duplo: '{params.get('text1')}' {cond} '{params.get('text2')}'"
        elif tipo == "text":
            txt = params.get("content", params.get("text", ""))
            return f"TXT: '{txt[:18]}…'" if len(txt) > 20 else f"TXT: '{txt}'"

        # exibe comando de atalho
        elif tipo == "hotkey":
            combo = params.get("command", params.get("content", ""))
            return f"CMD: {combo}"
        
        elif tipo == "startthread":
            return params.get("thread_name", "Thread")
        elif tipo == "screenshot":
            if params.get("mode") == "whole":
                return "Screenshot: tela inteira"
            else:
                r = params.get("region", {})
                return f"Screenshot: reg ({r.get('x')},{r.get('y')},{r.get('w')}×{r.get('h')})"
        else:
            return tipo.upper() or "Bloco"
class FlowchartApp:
    def __init__(self, root):
        self.root = root
        self.root.title("TraderAutoSuite v0.9.5")

        # flag para alterações não salvas
        self._dirty = False
        # intercepta o “X” da janela
        self.root.protocol("WM_DELETE_WINDOW", self._on_closing)

        # ---------------- layout da janela -----------------
        largura_janela, altura_janela = 1400, 890
        largura_tela  = root.winfo_screenwidth()
        altura_tela   = root.winfo_screenheight()
        pos_x = (largura_tela // 2) - (largura_janela // 2)
        pos_y = (altura_tela // 2) - (altura_janela // 2)
        root.geometry(f"{largura_janela}x{altura_janela}+{pos_x}+{pos_y}")

        self.root.bind_all("<Control-r>", lambda evt: self.executar_macro())
        storage.app = self

        # ————— Barra de Menu —————
        menubar = tk.Menu(self.root)

        # Arquivo
        arquivo_menu = tk.Menu(menubar, tearoff=0)
        arquivo_menu.add_command(label="Novo", command=self.novo_arquivo)
        arquivo_menu.add_command(label="Abrir...", command=self._acao_carregar)
        arquivo_menu.add_command(label="Salvar", command=self.salvar_arquivo)
        arquivo_menu.add_separator()
        arquivo_menu.add_command(label="Sair", command=self.root.quit)
        menubar.add_cascade(label="Arquivo", menu=arquivo_menu)

        # Editar
        editar_menu = tk.Menu(menubar, tearoff=0)
        editar_menu.add_command(label="Desfazer", command=self.desfazer)
        editar_menu.add_command(label="Refazer", command=self.refazer)
        editar_menu.add_separator()
        editar_menu.add_command(label="Copiar",   command=self.copiar)
        editar_menu.add_command(label="Colar",    command=self.colar)
        editar_menu.add_command(label="Recortar", command=self.recortar)
        menubar.add_cascade(label="Editar", menu=editar_menu)

        # View (Exibir)
        view_menu = tk.Menu(menubar, tearoff=0)
        view_menu.add_checkbutton(label="Mostrar Barra de Ferramentas",  command=self.toggle_toolbar)
        view_menu.add_checkbutton(label="Mostrar Painel de Propriedades", command=self.toggle_properties)
        menubar.add_cascade(label="View", menu=view_menu)

        # Ações
        acoes_menu = tk.Menu(menubar, tearoff=0)
        acoes_menu.add_command(label="Executar Macro", command=self.executar_macro)
        acoes_menu.add_command(label="Parar Macro",    command=self.parar_macro)
        menubar.add_cascade(label="Ações", menu=acoes_menu)

        # Ferramentas
        tools_menu = tk.Menu(menubar, tearoff=0)
        tools_menu.add_command(label="Opções...", command=self.abrir_configuracoes)
        tools_menu.add_command(label="Testar OCR", command=self.testar_ocr)
        menubar.add_cascade(label="Ferramentas", menu=tools_menu)

        # Ajuda
        help_menu = tk.Menu(menubar, tearoff=0)
        help_menu.add_command(label="Documentação", command=self.abrir_documentacao)
        help_menu.add_separator()
        help_menu.add_command(label="Sobre", command=self.sobre)
        menubar.add_cascade(label="Ajuda", menu=help_menu)

        # Associa a barra de menu à janela
        self.root.config(menu=menubar)

        # -------- frames e canvas --------------------------
        self.top_frame   = tk.Frame(root, height=50,  bg="#e0e0e0")
        self.menu_frame  = tk.Frame(root, width=80,   bg="#f0f0f0")
        self.canvas      = tk.Canvas(root, bg="#c3cfe2", bd=0, highlightthickness=0)
        self.top_frame.pack(side="top",   fill="x")
        self.menu_frame.pack(side="left", fill="y")
        self.canvas.pack    (side="right", fill="both", expand=True, padx=6, pady=6)
        #self.canvas.configure(scrollregion=(0, 0, 5000, 5000))

        # eventos de controle
        self.pause_event = threading.Event()
        self.stop_event  = threading.Event()
        self.macro_thread = None
        self.status_win   = None

        # -----------------------------------------------
        #  ZOOM  +  PAN (arrastar com botão direito)
        # -----------------------------------------------
        self._zoom_default = 1.0          # 100 % – é o “padrão de referência”
        self._zoom_scale   = self._zoom_default

        # roda do mouse  (Windows/Mac)
        self.canvas.bind("<MouseWheel>", self._on_zoom)
        # roda do mouse  (Linux X11)
        self.canvas.bind("<Button-4>",   lambda e: self._on_zoom(e, delta=120))
        self.canvas.bind("<Button-5>",   lambda e: self._on_zoom(e, delta=-120))

        # arrastar com botão direito (ou botão do meio, se preferir)
        self.canvas.bind("<ButtonPress-2>", self._start_pan)
        self.canvas.bind("<B2-Motion>",      self._move_pan)

        # ⇢ atalho Ctrl+0  (Windows / Linux / macOS)
        self.root.bind_all("<Control-Key-0>", self._reset_zoom)

        # label de status no rodapé
        self.status_bar = tk.Frame(self.root, bg="#f0f0f0")
        self.status_bar.pack(side="bottom", fill="x")

        # label de zoom alinhada à ESQUERDA
        self.status = tk.Label(
        self.root,
        text="Zoom: 100 %",
        bg="#f0f0f0",
        anchor="w"
        )

        self.status.place(x=6, rely=1.0, anchor="sw")

        threading.Thread(target=start_telegram_bot, daemon=True).start()

        # -------- gerenciadores ----------------------------
        self.blocos = BlocoManager(self.canvas, self)
        self.setas  = SetaManager(self.canvas, self.blocos)
        self.icones, self.icones_menu, self.icones_topo = {}, {}, {}
        self.itens_selecionados = []

        self._criar_botoes_topo()
        self._criar_botoes_menu()
        bind_eventos(self.canvas, self.blocos, self.setas, self.root)
    # Métodos de callback (adicione as implementações que desejar)
    def novo_arquivo(self):         messagebox.showinfo("Novo", "Novo arquivo…")
    def abrir_arquivo(self):        messagebox.showinfo("Abrir", "Abrir arquivo…")
    def salvar_arquivo(self):       
        # Caso 1: macro já existe → atualiza JSON e imagens em place
        if storage.caminho_macro_real and os.path.isfile(storage.caminho_macro_real):
            original = storage.caminho_macro_real
            # exporta estado atual para tmp
            tmp_path = export_macro_to_tmp(
                self.blocos.blocks,
                self._build_arrows_data(),
                macro_name=os.path.basename(os.path.dirname(original))
            )
            # sincroniza imagens para a pasta da macro
            storage._sincronizar_imagens(tmp_path, os.path.dirname(original))
            # sobrescreve o JSON definitivo
            shutil.copy(tmp_path, original)
            # limpa temporários e atualiza ponteiros
            storage.limpar_tmp()
            storage.caminho_macro_real  = original
            storage.caminho_arquivo_tmp = tmp_path
            messagebox.showinfo("Salvo", f"Macro atualizada em:\n{original}")
        else:
            # Caso 2: primeira vez → gera tmp e abre diálogo de nome
            export_macro_to_tmp(self.blocos.blocks, self._build_arrows_data())
            salvar_macro_gui()
        # marca que não há mais alterações pendentes
        self._dirty = False
    def desfazer(self):             pass
    def refazer(self):              pass
    def copiar(self):               pass
    def colar(self):                pass
    def recortar(self):             pass
    def toggle_toolbar(self):       pass
    def toggle_properties(self):    pass

    def _get_block_label(self, block_id: str) -> str:
        """
        Retorna o texto da label do bloco com o id dado.
        Se não encontrar, retorna o próprio id.
        """
        for bloco in self.blocos.blocks:
            # compara como string para evitar mismatches int vs str
            if str(bloco.get("id")) == str(block_id):
                label_id = bloco.get("label_id")
                if label_id:
                    return self.canvas.itemcget(label_id, "text")
        return block_id
    
    def executar_macro(self):
        # marca execução via UI (permanece True até o fim da execução real
        storage.macro_running = True
        # 1) minimiza a janela principal
        self.root.iconify()

        # 2) exporta para tmp (mesma lógica de antes)
        tmp_path = export_macro_to_tmp(
            self.blocos.blocks,
            self._build_arrows_data(),
            macro_name=(os.path.basename(
                os.path.dirname(storage.caminho_macro_real)
            ) if storage.caminho_macro_real else None)
        )

        # 3) dispara a thread que chama o core com callbacks para UI
        status_win = MacroStatusWindow(
            master=self.root,
            on_close=self.root.deiconify
        )
        self.macro_thread = threading.Thread(
            target=self._run_with_ui,
            args=(tmp_path, status_win),
            daemon=True
        )
        self.macro_thread.start()

    def _run_with_ui(self, json_path: str, status_win: MacroStatusWindow):
        # ------------------------------------------------------------------
        # Carrega JSON e prepara nomes de thread
        # ------------------------------------------------------------------
        with open(json_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        friendly_names      = set()          # para criar os quadros
        internal2friendly   = {}             # p/ converter "Thread-95" → "UpdateTrade"

        for blk in data.get("blocks", []):
            params = blk.get("params", {})
            if params.get("type") == "startthread":
                fname = params.get("thread_name")
                if fname:
                    friendly_names.add(fname)

                # mapeia possíveis nomes internos usados pelo executor
                internal2friendly[f"Thread-{blk['id']}"] = fname          # ex.: Thread-92
                for dest_id, fork_kind in params.get("forks", {}).items():
                    if fork_kind == "Nova Thread":
                        internal2friendly[f"Thread-{dest_id}"] = fname    # ex.: Thread-95

        # Cria os quadros ANTES da execução (sem “Thread Principal”)
        status_win.preload_threads(sorted(friendly_names))

        # ------------------------------------------------------------------
        # 2)  Oculta janela principal e prepara execução
        # ------------------------------------------------------------------
        self.root.withdraw()           # minimiza janela principal
        stop_evt = threading.Event()

        # callbacks ----------------------------------------------------------------
        def progress_cb(name, step, total):
            display = internal2friendly.get(name, name)
            status_win.update_progress(display, step, total)

        def label_cb(name, raw_text):
            # --- converte “Thread-95” → nome amigável --------------------
            display = internal2friendly.get(name, name)

            # id do bloco que acabou de rodar
            block_id = raw_text.rsplit(" ", 1)[-1]

            # ① tenta pegar o rótulo que você escreveu no canvas
            label_text = self._get_block_label(block_id)

            if label_text and label_text != block_id:
                # achou label → usa-o diretamente
                desc = label_text
            else:
                # ② fallback: gera descrição baseada no tipo (lógica antiga)
                bloco = next((b for b in self.blocos.blocks
                              if str(b["id"]) == str(block_id)), None)
                if bloco:
                    acao = bloco.get("acao", {})
                    tipo = acao.get("type", "").lower()
                    if tipo == "click":
                        desc = f"Clique @({acao.get('x')}, {acao.get('y')})"
                    elif tipo == "delay":
                        desc = f"Delay de {acao.get('time', 0) // 1000}s"
                    elif tipo in {"thread", "startthread"}:
                        desc = f"Thread → {acao.get('thread_name', f'ID {block_id}')}"
                    else:
                        desc = tipo.capitalize()
                else:
                    parts = raw_text.split()
                    desc = " ".join(parts[:-1]) if len(parts) > 1 else raw_text

            status_win.update_block(display, desc)


        # ------------------------------------------------------------------
        # 3) Executa a macro
        # ------------------------------------------------------------------
        executar_macro_flow(
            json_path,
            progress_callback=progress_cb,
            label_callback=label_cb,
            stop_event=stop_evt
        )

        # ------------------------------------------------------------------
        # 4) Limpeza final
        # ------------------------------------------------------------------
        status_win.win.after(0, status_win.win.destroy)
        self.root.after(0, self.root.deiconify)
        storage.macro_running = False

    def parar_macro(self):          pass
    def abrir_configuracoes(self):
        dialog = SettingsDialog(self.root)
        dialog.wait_window()
    def testar_ocr(self):
         add_ocr_to_sheet(actions=None, update_list=None, tela=self.root)
    def abrir_documentacao(self):   pass
    def sobre(self):                messagebox.showinfo("Sobre", "TraderAutoSuite v0.6")
    # =====================================================
    # UI helpers
    # =====================================================
    def _criar_botoes_topo(self):
        botoes_topo = [
            ("Novo",      "new_icon.png"),
            ("Salvar",    "save_icon.png"),
            ("Carregar",  "load_icon.png"),
            ("Remover",   "remove_icon.png"),
            ("Executar",  "execute_icon.png"),
        ]
        for nome, arquivo in botoes_topo:
            caminho = os.path.join("icons", arquivo)
            if os.path.exists(caminho):
                img = Image.open(caminho).resize((112, 40), Image.Resampling.LANCZOS)
                tk_img = ImageTk.PhotoImage(img)
                self.icones_topo[nome] = tk_img
                btn = tk.Label(self.top_frame, image=tk_img, cursor="hand2", bg="#e0e0e0")
                btn.pack(side="left", padx=5, pady=5)
                btn.bind("<Button-1>", lambda e, n=nome: self.executar_acao_topo(n))
            else:
                print(f"[Aviso] Ícone '{arquivo}' não encontrado.")

    def _criar_botoes_menu(self):
        botoes_icone = [
            ("Clique",     "click_icon.png"),
            ("Texto",      "text_icon.png"),
            ("Delay",      "delay_icon.png"),
            ("Label",      "label_icon.png"),
            ("GoTo",       "goto_icon.png"),
            ("Se Imagem",  "ifimage_icon.png"),
            ("OCR",        "ocr_icon.png"),
            ("OCR duplo",  "doubleocr_icon.png"),
            ("Loop",       "loop_icon.png"),
            ("Screenshot", "screenshot_icon.png"),
            ("Start Thread","thread_icon.png"),
            ("End Thread",  "threadend_icon.png"),
            ("text_to_sheet","text_to_sheet_icon.png"),
            ("Telegram Command","telegram_command_icon.png"),
            ("Run Macro",       "run_macro_icon.png"),
        ]
        for nome, arquivo in botoes_icone:
            caminho = os.path.join("icons", arquivo)
            if os.path.exists(caminho):
                img = Image.open(caminho).resize((112, 40), Image.Resampling.LANCZOS)
                tk_img = ImageTk.PhotoImage(img)
                self.icones_menu[nome] = tk_img
                btn = tk.Label(self.menu_frame, image=tk_img, cursor="hand2", bg="#f0f0f0")
                btn.pack(pady=5, padx=5)
                btn.bind("<Button-1>", lambda e, n=nome: self.blocos.adicionar_bloco(n, "white"))
            else:
                print(f"[Aviso] Ícone '{arquivo}' não encontrado.")
        # botão de conectar
        btn_conectar = tk.Label(self.menu_frame, text="➕", bg="#ddd", width=5,
                                relief="raised", bd=2, cursor="hand2")
        btn_conectar.pack(pady=10)
        btn_conectar.bind("<Button-1>", lambda e: self.setas.ativar_conexao())

    # =====================================================
    # Utilitário: gera lista completa de setas (origem, destino, branch, cor)
    # =====================================================
    def _build_arrows_data(self):
        arrows = []
        for seta_id, origem, destino in self.setas.setas:
            info = self.setas._setas_info.get(seta_id)
            cor = info[2] if info and len(info) >= 3 else \
                  self.canvas.itemcget(seta_id, "fill").lower()
            if cor in ("green", "#00ff00", "#0f0"):
                branch = "true"
            elif cor in ("red", "#ff0000", "#f00"):
                branch = "false"
            else:
                branch = None
            arrows.append((origem, destino, branch, cor))
        return arrows

    # =====================================================
    # Ações do topo (Novo, Salvar, Carregar, Remover, Executar)
    # =====================================================
    def executar_acao_topo(self, nome):
        # ------------------------------------------------------------------
        # BOTÃO NOVO  → limpa tudo
        # ------------------------------------------------------------------
        if nome == "Novo":
            self.canvas.delete("all")
            self.blocos = BlocoManager(self.canvas, self)
            self.setas  = SetaManager(self.canvas, self.blocos)
            bind_eventos(self.canvas, self.blocos, self.setas, self.root)
            storage.caminho_macro_real  = None     # zera ponteiro fixo
            storage.caminho_arquivo_tmp = None
            return

        # ------------------------------------------------------------------
        # BOTÃO SALVAR
        # ------------------------------------------------------------------
        if nome == "Salvar":
            # delega para o método unificado de salvamento
            self.salvar_arquivo()
            return

        # ------------------------------------------------------------------
        # BOTÃO CARREGAR
        # ------------------------------------------------------------------
        if nome == "Carregar":
            self._acao_carregar()
            return

        # ------------------------------------------------------------------
        # BOTÃO REMOVER
        # ------------------------------------------------------------------
        if nome == "Remover":
            self.blocos.deletar_selecionados()
            return

        # ------------------------------------------------------------------
        # BOTÃO EXECUTAR
        # ------------------------------------------------------------------
        if nome == "Executar":
            self.executar_macro()
            return
    # -----------------------------------------------------
    # Carregar macro (JSON)
    # -----------------------------------------------------
    def _acao_carregar(self, path=None):
        # Se veio um path por argumento, usa-o; senão, pergunta ao usuário
        if path is None:
            path = filedialog.askopenfilename(
                filetypes=[("JSON", "*.json")],
                title="Abrir macro"
            )
            if not path:
                return
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            ids_existentes = [blk["id"] for blk in data.get("blocks", [])]
            BlocoManager._next_id = max(ids_existentes, default=0) + 1

            storage.caminho_arquivo_tmp = path
            storage.caminho_macro_real = path
            # limpa canvas e recria managers
            self.canvas.delete("all")
            self.blocos = BlocoManager(self.canvas, self)
            self.setas  = SetaManager(self.canvas, self.blocos)
            bind_eventos(self.canvas, self.blocos, self.setas, self.root)

            # --- recria blocos ----------------------------------
            id_map = {}
            for blk in data.get("blocks", []):
                btype = blk.get("type", "")
                bloco = self.blocos.adicionar_bloco(btype, "white")
            
                # --- calcula novo retângulo ---
                old_x, old_y = bloco["x"], bloco["y"]          # onde o adicionar_bloco() colocou
                x, y = blk.get("x", old_x), blk.get("y", old_y)
                dx, dy = x - old_x, y - old_y                  # delta de deslocamento
            
                # --- move o retângulo e ícone ---
                bx2, by2 = x + bloco["width"], y + bloco["height"]
                self.canvas.coords(bloco["rect"], x, y, bx2, by2)
                if bloco.get("icon"):
                    self.canvas.coords(bloco["icon"], x, y)
            
                # --- **move também todos os handles** ---
                for hid in bloco.get("handles", []):
                    self.canvas.move(hid, dx, dy)
                if bloco.get("true_handle"):
                    self.canvas.move(bloco["true_handle"], dx, dy)
                if bloco.get("false_handle"):
                    self.canvas.move(bloco["false_handle"], dx, dy)
            
                # actualiza as coordenadas salvas no dicionário do bloco
                bloco["x"], bloco["y"] = x, y
                bloco["id"] = blk.get("id")
                id_map[bloco["id"]] = bloco

                # restaura params → desenha label
                params = blk.get("params", {})
                if params:
                    bloco["acao"] = params
                    txt = _formatar_rotulo(params)      # ← nova função
                    cor_label = "blue" if params.get("type") == "startthread" else "black"
                    bloco["label_id"] = self.canvas.create_text(
                        x + bloco["width"]/2, y + bloco["height"] + 8,
                        text=txt, font=("Arial", 9), fill=cor_label
                    )

                #     cor_label = "blue" if tipo == "startthread" else "black"
                #     bloco["label_id"] = self.canvas.create_text(
                #     x + bloco["width"]/2,
                #     y + bloco["height"] + 8,
                #     text=txt,
                #     font=("Arial", 9),
                #     fill=cor_label
                #     )
                # if blk.get("type","").lower() == "texto":
                #     params["type"] = "text"
                # blk["params"] = params

            # --- recria setas -----------------------------------
            for conn in data.get("connections", []):
                origem   = id_map.get(conn.get("from"))
                destino  = id_map.get(conn.get("to"))
                if not origem or not destino:
                    continue
                branch = conn.get("branch")
                cor    = conn.get("color")
                if not cor and branch:
                    cor = "green" if branch == "true" else "red" if branch == "false" else None
                self.setas.desenhar_linha(origem, destino, cor_override=cor)

            messagebox.showinfo("Carregado", f"Macro carregada de:\n{path}")
        except Exception as exc:
            messagebox.showerror("Erro ao carregar", str(exc))

    # =====================================================
    #  Zoom
    # =====================================================
    # ──  método _on_zoom  (substituir o atual) ─────────────────────────────
    def _on_zoom(self, event, *, delta=None):
        d = event.delta if delta is None else delta
        if d == 0:
            return
        
        # -------- passo fixo de 5 % --------------------------------
        STEP = 0.05                        # 5 %
        factor = 1.0 + STEP if d > 0 else 1.0 - STEP
        # -----------------------------------------------------------

        # aplica limites 10 % – 200 %
        new_scale = self._zoom_scale * factor
        if not (0.10 <= new_scale <= 2.00):
            return

        self._zoom_scale = new_scale

        x = self.canvas.canvasx(event.x)
        y = self.canvas.canvasy(event.y)
        self.canvas.scale("all", x, y, factor, factor)
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))
        self._rescale_styles()
        self._update_status()


    # =====================================================
    #  Pan (arraste)
    # =====================================================
    def _start_pan(self, event):
        """Marca ponto inicial para scan_dragto."""
        self.canvas.scan_mark(event.x, event.y)

    def _move_pan(self, event):
        """Chama scan_dragto conforme o mouse move."""
        self.canvas.scan_dragto(event.x, event.y, gain=1)
    
    # ---------------------------------------------------------
    # Ajusta aparência depois que a geometria já foi escalada
    # ---------------------------------------------------------
    def _rescale_styles(self):
        z = self._zoom_scale                 # fator acumulado de zoom

        # ---- A) espessura das setas -----------------------------------
        for seta_id, _, _ in self.setas.setas:
            for seg in self.setas._obter_segmentos(seta_id):
                # tag “w:2” guarda a espessura original
                tags = self.canvas.gettags(seg)
                base = next((t for t in tags if t.startswith("w:")), None)
                if base is None:
                    self.canvas.addtag_withtag("w:2", seg)
                    base_width = 2
                else:
                    base_width = float(base[2:])
                self.canvas.itemconfig(
                    seg, width=max(1, round(base_width * z))
                )

        # ---- B) fonte dos handles “⊕” ---------------------------------
        for bloco in self.blocos.blocks:
            for h in bloco.get("handles", []):
                tags = self.canvas.gettags(h)
                base = next((t for t in tags if t.startswith("fs:")), None)
                if base is None:
                    self.canvas.addtag_withtag("fs:10", h)
                    base_fs = 10
                else:
                    base_fs = int(base[3:])
                new_fs = max(6, int(base_fs * z))
                self.canvas.itemconfig(h, font=("Arial", new_fs, "bold"))

        # ---- C) ícone dos blocos --------------------------------------
        for bloco in self.blocos.blocks:
            icon_id = bloco.get("icon")
            pil_orig = bloco.get("_pil_orig")
            if not icon_id or pil_orig is None:
                continue

            # quanto o ícone já está escalado?
            old_s = bloco.get("_icon_scale", 1.0)
            new_s = self._zoom_scale

            # se a diferença é menor que 1 %, nem mexe
            if abs(new_s - old_s) < 0.01:
                continue

            # gera uma nova bitmap no tamanho certo
            w = max(8, int(bloco["width"]  * new_s))
            h = max(8, int(bloco["height"] * new_s))
            tk_img = ImageTk.PhotoImage(pil_orig.resize((w, h), Image.LANCZOS))

            # troca a imagem no canvas e guarda referências
            self.canvas.itemconfig(icon_id, image=tk_img)
            bloco["_icon_ref"]   = tk_img     # evita GC
            bloco["_icon_scale"] = new_s      # marca a escala atual
    
    # ──  método _reset_zoom  (novo) ────────────────────────────────────────
    def _reset_zoom(self, event=None):
        if abs(self._zoom_scale - self._zoom_default) < 1e-3:
            return                                          # já está no padrão
        factor = self._zoom_default / self._zoom_scale
        self._zoom_scale = self._zoom_default
        # centro = canto superior-esquerdo para não “saltar”
        self.canvas.scale("all", 0, 0, factor, factor)
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))
        self._rescale_styles()
        self._update_status()

    # ──  método _update_status  (novo) ─────────────────────────────────────
    def _update_status(self):
        pct = int(round(self._zoom_scale * 100))
        self.status.config(text=f"{pct} %")

    def _mark_dirty(self):
        """Marca que houve edição desde o último save."""
        self._dirty = True

    def _on_closing(self):
        """Pergunta antes de fechar se houver alterações não salvas."""
        if not self._dirty:
            self.root.destroy()
            return

        resp = messagebox.askyesnocancel(
            "Salvar alterações",
            "Há alterações não salvas. Deseja salvar antes de sair?"
        )
        if resp is None:
            # Cancelou
            return
        if resp:
           # chama o save unificado (já faz export_tmp + “Salvar como” se preciso)
           self.salvar_arquivo()
        self.root.destroy()

# ============================================================
# Inicialização
# ============================================================
if __name__ == "__main__":
    root = tk.Tk()
    app = FlowchartApp(root)
    root.mainloop()