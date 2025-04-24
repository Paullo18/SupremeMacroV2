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
        self.root.title("Flowchart Macro Editor")
        # ---------------- layout da janela -----------------
        largura_janela, altura_janela = 1400, 700
        largura_tela  = root.winfo_screenwidth()
        altura_tela   = root.winfo_screenheight()
        pos_x = (largura_tela // 2) - (largura_janela // 2)
        pos_y = (altura_tela // 2) - (altura_janela // 2)
        root.geometry(f"{largura_janela}x{altura_janela}+{pos_x}+{pos_y}")

        # -------- frames e canvas --------------------------
        self.top_frame   = tk.Frame(root, height=50,  bg="#e0e0e0")
        self.menu_frame  = tk.Frame(root, width=80,   bg="#f0f0f0")
        self.canvas      = tk.Canvas(root, bg="#c3cfe2", bd=0, highlightthickness=0)
        self.top_frame.pack(side="top",   fill="x")
        self.menu_frame.pack(side="left", fill="y")
        self.canvas.pack    (side="right", fill="both", expand=True, padx=6, pady=6)

        # -------- gerenciadores ----------------------------
        self.blocos = BlocoManager(self.canvas, self)
        self.setas  = SetaManager(self.canvas, self.blocos)
        self.icones, self.icones_menu, self.icones_topo = {}, {}, {}
        self.itens_selecionados = []

        self._criar_botoes_topo()
        self._criar_botoes_menu()
        bind_eventos(self.canvas, self.blocos, self.setas, self.root)

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


# ============================================================
# Inicialização
# ============================================================
if __name__ == "__main__":
    root = tk.Tk()
    app = FlowchartApp(root)
    root.mainloop()