import time
import tkinter as tk
from tkinter import filedialog
from blocos import BlocoManager
from setas import SetaManager
from eventos import bind_eventos
from PIL import Image, ImageTk

#import thread_safe_patch
#thread_safe_patch.apply_thread_safety_patches()

from core.storage import export_macro_to_tmp, salvar_macro_gui
from core.executor import execute_macro as executar_macro_flow
from gui.macro_status import MacroStatusWindow
from gui.settings_window import SettingsDialog
from gui.ocr_to_sheet import add_ocr_to_sheet
import json, os, shutil, threading
import core.storage as storage
from core.telegram_listener import start_telegram_bot
#from tkinter import messagebox
#from core.executar import process_ui_queue
import core
from core import process_main_thread_queue as process_ui_queue
from core import show_info, show_error, ask_yes_no

from gui.helpers.ui_helpers import centralizar_janela, criar_menubar, carregar_icone, adicionar_botao



def macro_em_pasta_macros(path_):
    """Retorna True se *path_* for .../Macros/<nome>/macro.json."""
    abs_path   = os.path.abspath(path_)
    macros_abs = os.path.abspath(storage.MACROS_DIR)
    return abs_path.endswith(os.sep + "macro.json") and abs_path.startswith(macros_abs + os.sep)

class FlowchartApp:
    def __init__(self, root):
        self.root = root
        self.root.title("TraderAutoSuite v0.9.5")

        # flag para alterações não salvas
        self._dirty = False
        # intercepta o “X” da janela
        self.root.protocol("WM_DELETE_WINDOW", self._on_closing)

        # ---------------- layout da janela -----------------
        centralizar_janela(self.root, 1400, 890)

        self.root.bind_all("<Control-r>", lambda evt: self.executar_macro())
        storage.app = self

        # ————— Barra de Menu (refatorado via helper) —————
        menus = {
            "Arquivo": [
                ("Novo", self.novo_arquivo),
                ("Abrir...", self._acao_carregar),
                ("Salvar", self.salvar_arquivo),
                ("Salvar como...", self.salvar_como),
                "separator",
                ("Sair", self.root.quit)
            ],
            "Editar": [
                ("Desfazer", self.desfazer),
                ("Refazer", self.refazer),
                "separator",
                ("Copiar", self.copiar),
                ("Colar", self.colar),
                ("Recortar", self.recortar)
            ],
            "View": [
                ("Mostrar Barra de Ferramentas", self.toggle_toolbar),
                ("Mostrar Painel de Propriedades", self.toggle_properties)
            ],
            "Ações": [
                ("Executar Macro", self.executar_macro),
                ("Parar Macro", self.parar_macro)
            ],
            "Ferramentas": [
                ("Opções...", self.abrir_configuracoes),
                ("Testar OCR", self.testar_ocr)
            ],
            "Ajuda": [
                ("Documentação", self.abrir_documentacao),
                "separator",
                ("Sobre", self.sobre)
            ]
        }
        criar_menubar(self.root, menus)

        #self.root.after(100, process_ui_queue)

        # -------- frames e canvas --------------------------
        self.top_frame   = tk.Frame(root, height=50,  bg="#e0e0e0")
        self.menu_frame  = tk.Frame(root, width=80,   bg="#f0f0f0")
        self.canvas      = tk.Canvas(root, bg="#c3cfe2", bd=0, highlightthickness=0)
        self.top_frame.pack(side="top",   fill="x")
        self.menu_frame.pack(side="left", fill="y")
        self.canvas.pack    (side="right", fill="both", expand=True, padx=6, pady=6)
        #self.canvas.configure(scrollregion=(0, 0, 5000, 5000))

        self.macro_name_label = tk.Label(
            self.top_frame,
            text="Macro: <nenhuma>",
            bg="#e0e0e0",
            font=("Arial", 10, "italic")
        )
        self.macro_name_label.pack(side="right", padx=10)
        
        # controla nome + estrela de dirty
        self._current_macro = None
        self._dirty = False
        self._update_macro_label()

        self.menu_frame.pack(side="left", fill="y")

        # eventos de controle
        self.pause_event = threading.Event()
        self.stop_event  = threading.Event()
        self.macro_thread = None
        self.status_win   = None

        # -------------- NOVO: fila de chamadas UI -----------------
        from queue import Queue, Empty
        self._ui_q   = Queue()                         # fila de tarefas UI
        self.post_ui = self._ui_q.put                  # helper para enfileirar chamadas ao Tk

        def _drain_ui():
            try:
                while True:
                    fn = self._ui_q.get_nowait()
                    fn()                              # executa no main-thread
            except Empty:
                pass
            self.root.after(30, _drain_ui)

        self.root.after(30, _drain_ui)
        

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
    def novo_arquivo(self):
        # limpa tudo e reseta estado da macro (mesma lógica do botão Novo)
        if abs(self._zoom_scale - self._zoom_default) > 1e-3:
            self._reset_zoom()
        self.canvas.delete("all")
        self.blocos = BlocoManager(self.canvas, self)
        self.setas = SetaManager(self.canvas, self.blocos)
        bind_eventos(self.canvas, self.blocos, self.setas, self.root)
        storage.caminho_macro_real = None
        storage.caminho_arquivo_tmp = None
        # reseta nome e limpa o "*"
        self._current_macro = None
        self._dirty = False
        self._update_macro_label()
    
    
    def abrir_arquivo(self):        show_info("Abrir", "Abrir arquivo…")
    def salvar_arquivo(self):
        """Salva a macro no arquivo atual ou, se não existir, abre o diálogo de salvamento."""
        self._salvar_macro(path=storage.caminho_macro_real)
    def salvar_como(self):
        """Sempre pergunta onde salvar o JSON e as imagens."""
        self._dirty = False
        self._update_macro_label()
        self._salvar_macro(path=None, ask_dialog=True)

    def _salvar_macro(self, path=None, ask_dialog=False):
        """Lógica centralizada para exportar e salvar a macro."""
        # 1) exporta o estado atual para um arquivo temporário
        tmp_path = export_macro_to_tmp(
            self.blocos.blocks,
            self._build_arrows_data(),
            macro_name=(os.path.basename(os.path.dirname(path)) if path else None)
        )
        # 2) escolhe entre salvar existente ou 'Salvar como...'
        if ask_dialog or not path or not os.path.isfile(path):
            # deixa o core.storage cuidar do diálogo e do salvamento completo
            salvar_macro_gui()
        else:
            # consolida JSON e imagens no local existente
            dest_dir = os.path.dirname(path)
            storage._sincronizar_imagens(tmp_path, dest_dir)
            shutil.copy(tmp_path, path)
            show_info("Macro salva", f"Macro salva em:\n{path}")
            storage.caminho_macro_real  = path
            storage.caminho_arquivo_tmp = tmp_path
        # marca alterações salvas
        self._dirty = False
        self._update_macro_label()
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
    
    def _update_macro_label(self):
        """Atualiza a label de macro no topo, adicionando '*' se houver alterações não salvas."""
        nome = self._current_macro or "<nenhuma>"
        self.macro_name_label.config(text=f"Macro: {nome}")
        sinal = "*" if self._dirty else ""
        self.macro_name_label.config(text=f"Macro: {nome}{sinal}")
    
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
        # cria a janela de status e registra já aqui
        status_win = MacroStatusWindow(
            master=self.root,
            on_close=self.root.deiconify
        )
        # cria & armazena o evento de stop antes de iniciar a thread
        self.stop_event = threading.Event()
        self.status_win  = status_win
        # —> Não registrar aqui: o root-branch é registrado
        #     dentro de executar_macro_flow() com o nome vindo do JSON
        self.macro_thread = threading.Thread(
            target=self._run_with_ui,
            args=(tmp_path, status_win),
            daemon=True
        )
        self.macro_thread.start()

    def _run_with_ui(self, json_path: str, status_win: MacroStatusWindow):
        # ------------------------------------------------------------------
        # Carrega JSON (threads serão adicionadas dinamicamente pelo core)
        # ------------------------------------------------------------------
        with open(json_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        # 1) cria o evento de parada principal
        stop_evt = threading.Event()
        self.stop_event = stop_evt

        # callbacks ----------------------------------------------------------------
        # Mapeamento de nomes internos → nomes amigáveis (vazio = mostra sempre o nome original)
        internal2friendly = {}

        def progress_cb(name, step, total):
            display = internal2friendly.get(name, name)
            self.post_ui(lambda: status_win.update_progress(display, step, total))

        def label_cb(name, raw_text):
            # exibe exatamente o texto que veio do core
            display = name
            self.post_ui(lambda: status_win.update_block(display, raw_text))

        # 2) Forçar update da janela de status para garantir que o Toplevel exista
        self.post_ui(lambda: status_win.win.update_idletasks())
        # 3) Esconder a janela principal, deixando apenas a de status visível
        self.post_ui(self.root.withdraw)


        # ------------------------------------------------------------------
        # 4) Registrando callback de restart (AGORA que progress_cb e label_cb existem)
        try:
            executar_macro_flow(
                json_path,
                progress_callback=progress_cb,
                label_callback=label_cb,
                stop_event=stop_evt,
                status_win=status_win
            )

        except ValueError as e:
            # captura 'e' em err=e  ↓↓↓
            self.post_ui(lambda err=e: show_error(
                "Erro ao executar macro", str(err)))

        except Exception as e:
            # idem aqui
            self.post_ui(lambda err=e: show_error(
                "Erro inesperado", f"{type(err).__name__}: {err}"))

        # ------------------------------------------------------------------
        # 4) Limpeza final
        # ------------------------------------------------------------------
        # A janela de status se aut o‑fecha quando TODAS as threads sinalizam stop.
        # Portanto, não a destruímos aqui; apenas restauramos a janela principal.
        # Aguarda até a macro terminar completamente antes de restaurar a janela principal
        def wait_and_restore():
            while storage.macro_running:
                time.sleep(0.1)
            self.post_ui(self.root.deiconify)
        threading.Thread(target=wait_and_restore, daemon=True).start()

    def parar_macro(self):
        """Para imediatamente a macro que estiver em execução."""
        import core.storage as storage
        # desarma flag global
        storage.macro_running = False
        # dispara o evento que o executor observa
        if hasattr(self, 'stop_event'):
            self.stop_event.set()
        # fecha a janela de status (se estiver aberta)
        if hasattr(self, 'status_win') and self.status_win:
            self.post_ui(self.status_win.destroy)
            
    def abrir_configuracoes(self):
        dialog = SettingsDialog(self.root)
        dialog.wait_window()
    def testar_ocr(self):
         add_ocr_to_sheet(actions=None, update_list=None, tela=self.root)
    def abrir_documentacao(self):   pass
    def sobre(self):                show_info("Sobre", "TraderAutoSuite v0.6")
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
            ("Fim Loop",  "endloop_icon.png"),
        ]
        for nome, arquivo in botoes_topo:
            caminho = os.path.join("icons", arquivo)
            if os.path.exists(caminho):
                icon = carregar_icone(caminho, (112, 40))
                self.icones_topo[nome] = icon
                adicionar_botao(
                    self.top_frame,
                    icon,
                    lambda e, n=nome: self.executar_acao_topo(n),
                    side="left",
                    padx=5,
                    pady=5
                )
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
            ("Variavel",       "variable_icon.png"),
            ("Se Variavel",       "if_variable_icon.png"),
        ]
        for nome, arquivo in botoes_icone:
            caminho = os.path.join("icons", arquivo)
            if os.path.exists(caminho):
                icon = carregar_icone(caminho, (112, 40))
                self.icones_menu[nome] = icon
                adicionar_botao(
                    self.menu_frame,
                    icon,
                    lambda e, n=nome: self.blocos.adicionar_bloco(n, "white"),
                    padx=5,
                    pady=5
                )
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
        """
        Devolve uma lista [(origem, destino, branch, cor)] exatamente
        como estão guardados pelo SetaManager – sem deduções nem casts.
        """
        arrows = []
        vistos = set()               # evita duplicatas (orig_id, dest_id)

        for cid, origem, destino in self.setas.setas:
            chave = (origem.get("id"), destino.get("id"))
            if chave in vistos:
                continue
            vistos.add(chave)

            info   = self.setas._setas_info.get(cid, {})
            branch = info.get("branch")          # True / False / None
            cor    = info.get("color")           # string ou None

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
            # limpa canvas e reinicia managers
            self.canvas.delete("all")
            self.blocos = BlocoManager(self.canvas, self)
            self.setas  = SetaManager(self.canvas, self.blocos)
            bind_eventos(self.canvas, self.blocos, self.setas, self.root)
            storage.caminho_macro_real  = None
            storage.caminho_arquivo_tmp = None
            # reseta nome da macro e limpa o "*"
            self._current_macro = None
            self._dirty = False
            self._update_macro_label()

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
        
        # ------------------------------------------------------------------
        # BOTÃO FIM LOOP
        # ------------------------------------------------------------------
        if nome == "Fim Loop":
            # insere um bloco de término de loop
            # cor “white” (ou qualquer cor padrão que você queira)
            self.blocos.adicionar_bloco("Fim Loop", "white")
            return
    # -----------------------------------------------------
    # Carregar macro (JSON)
    # -----------------------------------------------------
    def _acao_carregar(self, path=None):
        """Abre um arquivo JSON e reconstrói o canvas via helper centralizado."""
        # ── garante que o canvas volte a 100 % ─────────────────
        if abs(self._zoom_scale - self._zoom_default) > 1e-3:
            self._reset_zoom()
        # 1) se nenhum path foi passado, pergunta ao usuário
        if path is None:
            path = filedialog.askopenfilename(
                filetypes=[("JSON", "*.json")],
                title="Abrir macro"
            )
            if not path:
                return

        try:
            # 2) usa utilitário para limpar e reconstruir tudo
            from core.storage import rebuild_macro_canvas

            rebuild_macro_canvas(
                path,
                canvas=self.canvas,
                bloco_manager=self.blocos,
                seta_manager=self.setas,
                bind_fn=lambda: bind_eventos(self.canvas, self.blocos, self.setas, self.root)
            )

            # limpa hover antigo e reposiciona todos os handlers
            self.blocos._hovered_block = None
            for b in self.blocos.blocks:
                self.blocos._recolocar_handles(b)

            # ── reposiciona handlers (“⊕”) de todos os blocos carregados
            for bloco in self.blocos.blocks:
                self.blocos._recolocar_handles(bloco)

            # marca este JSON como o arquivo ‘real’ da macro,
            # para que o Salvar apenas sobrescreva sem pedir nome
            # marca este arquivo como a macro atual e atualiza a label
            storage.caminho_macro_real   = path
            storage.caminho_arquivo_tmp  = path
            # mostra só o nome sem extensão
            nome = os.path.splitext(os.path.basename(path))[0]
            # atualiza nome e limpa dirty
            nome = os.path.splitext(os.path.basename(path))[0]
            self._current_macro = nome
            self._dirty = False
            self._update_macro_label()
        except Exception as exc:
            show_error("Erro ao carregar macro", str(exc))

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

    def _set_zoom(self, scale):
        """Aplica um fator de zoom absoluto (1.0 = 100 %)."""
        # remove escala atual
        if abs(self._zoom_scale - self._zoom_default) > 1e-6:
            inv = 1 / self._zoom_scale
            self.canvas.scale("all", 0, 0, inv, inv)

        # aplica nova escala
        if abs(scale - 1.0) > 1e-6:
            self.canvas.scale("all", 0, 0, scale, scale)

        self._zoom_scale = scale
        self._rescale_styles()


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

        # ---- D) fonte das LABELS -----------------------------------
        for bloco in self.blocos.blocks:
            lbl_id = bloco.get("label_id")
            if not lbl_id:
                continue

            tags = self.canvas.gettags(lbl_id)
            base = next((t for t in tags if t.startswith("fs:")), None)
            if base is None:
                self.canvas.addtag_withtag("fs:8", lbl_id)  # 8 pt padrão
                base_fs = 8
            else:
                base_fs = int(base[3:])

            new_fs = max(6, int(base_fs * z))
            self.canvas.itemconfig(lbl_id, font=("Arial", new_fs))
    
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
        """Marca que houve edição desde o último save e atualiza o asterisco na label."""
        self._dirty = True
        self._update_macro_label()

    def _on_closing(self):
        """Pergunta antes de fechar se houver alterações não salvas."""
        if not self._dirty:
            self.root.destroy()
            return

        resp = ask_yes_no(
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
    # ──────────────────────────────────────────────────────────────────────
    # Substitui a fila de UI: em vez de chamar thread_safe_patch, use thread_utils
    root.after(30, process_ui_queue)
    # ——— Agora instancie o app e rode o mainloop normalmente ———
    app = FlowchartApp(root)
    root.mainloop()