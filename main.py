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
from gui.settings_window import SettingsDialog
import json, os, shutil, threading
import core.storage as storage

def macro_em_pasta_macros(path_):
    """Retorna True se *path_* for .../Macros/<nome>/macro.json."""
    abs_path   = os.path.abspath(path_)
    macros_abs = os.path.abspath(storage.MACROS_DIR)
    return abs_path.endswith(os.sep + "macro.json") and abs_path.startswith(macros_abs + os.sep)

class FlowchartApp:
    def __init__(self, root):
        self.root = root
        self.root.title("TraderAutoSuite v0.6")
        # ---------------- layout da janela -----------------
        largura_janela, altura_janela = 1400, 700
        largura_tela  = root.winfo_screenwidth()
        altura_tela   = root.winfo_screenheight()
        pos_x = (largura_tela // 2) - (largura_janela // 2)
        pos_y = (altura_tela // 2) - (altura_janela // 2)
        root.geometry(f"{largura_janela}x{altura_janela}+{pos_x}+{pos_y}")

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

        # -------- gerenciadores ----------------------------
        self.blocos = BlocoManager(self.canvas, self)
        self.setas  = SetaManager(self.canvas, self.blocos)
        self.icones, self.icones_menu, self.icones_topo = {}, {}, {}
        self.itens_selecionados = []

        self._criar_botoes_topo()
        self._criar_botoes_menu()
        bind_eventos(self.canvas, self.blocos, self.setas, self.root)
    # Métodos de callback (adicione as implementações que desejar)
    def novo_arquivo(self):          messagebox.showinfo("Novo", "Novo arquivo…")
    def abrir_arquivo(self):        messagebox.showinfo("Abrir", "Abrir arquivo…")
    def salvar_arquivo(self):       messagebox.showinfo("Salvar","Salvar arquivo…")
    def desfazer(self):             pass
    def refazer(self):              pass
    def copiar(self):               pass
    def colar(self):                pass
    def recortar(self):             pass
    def toggle_toolbar(self):       pass
    def toggle_properties(self):    pass
    def executar_macro(self):       pass
    def parar_macro(self):          pass
    def abrir_configuracoes(self):
        dialog = SettingsDialog(self.root)
        dialog.wait_window()
    def testar_ocr(self):           pass
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
            # === CASO 1 – macro já existe (…/Macros/<nome>/macro.json) =====
            if storage.caminho_macro_real and os.path.isfile(storage.caminho_macro_real):
                original_json = storage.caminho_macro_real

                # exporta estado atual → tmp  (altera caminho_arquivo_tmp)
                tmp_json = export_macro_to_tmp(
                    self.blocos.blocks,
                    self._build_arrows_data(),
                    macro_name=os.path.basename(os.path.dirname(original_json)),
                )

                # move qualquer PNG novo para  <macro>/img  e conserta caminhos
                storage._sincronizar_imagens(tmp_json, os.path.dirname(original_json))

                # copia tmp sobre o arquivo definitivo
                shutil.copy(tmp_json, original_json)

                # limpa tmp e restaura ponteiros
                storage.limpar_tmp()
                storage.caminho_arquivo_tmp = tmp_json     # último snapshot
                storage.caminho_macro_real  = original_json

                messagebox.showinfo("Salvo", f"Macro atualizada em:\n{original_json}")
                return

            # === CASO 2 – primeiro salvamento =============================
            # exporta para tmp e chama o fluxo de criação/persistência
            export_macro_to_tmp(self.blocos.blocks, self._build_arrows_data())
            storage.salvar_macro_gui()               # aqui caminho_macro_real é definido
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
            macro_name = None
            if storage.caminho_macro_real:                       # macro já foi salva
                macro_name = os.path.basename(
                    os.path.dirname(storage.caminho_macro_real)
                )
            
            tmp_path = export_macro_to_tmp(self.blocos.blocks,
                               self._build_arrows_data(),
                               macro_name=macro_name)
            threading.Thread(
                target=lambda: executar_macro_flow(tmp_path),
                daemon=True
            ).start()


    # -----------------------------------------------------
    # Carregar macro (JSON)
    # -----------------------------------------------------
    def _acao_carregar(self):
        path = filedialog.askopenfilename(filetypes=[("JSON", "*.json")], title="Abrir macro")
        if not path:
            return
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
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
                    tipo = params.get("type", "").lower()
                    if tipo == "click":
                        txt = f"Click @({params.get('x')},{params.get('y')})"
                    elif tipo == "delay":
                        txt = f"Delay: {params.get('time')}ms"
                    elif tipo == "goto":
                        txt = f"GOTO → {params.get('label')}"
                    elif tipo == "imagem":
                        txt = f"Img:{params.get('imagem')} @({params.get('x')},{params.get('y')},{params.get('w')},{params.get('h')})"
                    elif tipo == "label":
                        txt = f"Label: {params.get('name')}"
                    elif tipo == "loopstart":
                        txt = f"INÍCIO LOOP {params.get('count')}x" if params.get('mode') == 'quantidade' else "INÍCIO LOOP INFINITO"
                    elif tipo == "ocr":
                        txt = f"OCR: '{params.get('text')}'"
                    elif tipo == "ocr_duplo":
                        cond = params.get('condicao', 'and').upper()
                        txt = f"OCR Duplo: '{params.get('text1')}' {cond} '{params.get('text2')}'"
                    elif tipo == "text":
                        conteudo = params.get('content', params.get('text', ''))
                        txt = f"TXT: '{conteudo[:18]}…'" if len(conteudo) > 20 else f"TXT: '{conteudo}'"
                    elif tipo == "screenshot":
                        # Desenha rótulo de screenshot
                        if bloco.get("label_id"): self.canvas.delete(bloco["label_id"])
                        bx, by = params.get("x",0), params.get("y",0)
                        w0, h0 = bloco["width"], bloco["height"]
                        if params.get("mode") == "whole":
                            texto = "Screenshot: tela inteira"
                        else:
                            r = params.get("region", {})
                            texto = f"Screenshot: reg ({r['x']},{r['y']},{r['w']}×{r['h']})"
                        bloco["label_id"] = self.canvas.create_text(
                            bx + w0/2,
                            by + h0 + 8,
                            text=texto,
                            font=("Arial", 9),
                            fill="black"
                        )
                    else:
                        txt = tipo.upper()
                    bloco["label_id"] = self.canvas.create_text(
                        x + bloco["width"] / 2,
                        y + bloco["height"] + 8,
                        text=txt, font=("Arial", 9), fill="black"
                    )

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

# ============================================================
# Inicialização
# ============================================================
if __name__ == "__main__":
    root = tk.Tk()
    app = FlowchartApp(root)
    root.mainloop()