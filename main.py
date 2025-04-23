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
import json, os
import threading

class FlowchartApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Flowchart Macro Editor")
        # Define o tamanho da janela
        largura_janela = 1400
        altura_janela = 700

        # Pega o tamanho da tela
        largura_tela = root.winfo_screenwidth()
        altura_tela = root.winfo_screenheight()

        # Calcula a posição x e y para centralizar
        pos_x = (largura_tela // 2) - (largura_janela // 2)
        pos_y = (altura_tela // 2) - (altura_janela // 2)

        # Define a geometria com posição calculada
        root.geometry(f"{largura_janela}x{altura_janela}+{pos_x}+{pos_y}")

        # Frame de topo
        self.top_frame = tk.Frame(root, height=50, bg="#e0e0e0", )
        self.top_frame.pack(side="top", fill="x")

        # Frame de menu lateral
        self.menu_frame = tk.Frame(root, width=80, bg="#f0f0f0")
        self.menu_frame.pack(side="left", fill="y")

        # Canvas
        self.canvas = tk.Canvas(root, bg="#c3cfe2", bd=0, highlightthickness=0)  # azul acinzentado suave
        self.canvas.pack(side="right", fill="both", expand=True, padx=6, pady=6)


        # Gerenciadores
        self.blocos = BlocoManager(self.canvas, self)
        self.setas = SetaManager(self.canvas, self.blocos)

        # Cache para imagens
        self.icones = {}
        self.icones_menu = {}
        self.icones_topo = {}
        
        self.itens_selecionados = []


        # Botões do topo
        botoes_topo = [
            ("Novo", "new_icon.png"),
            ("Salvar", "save_icon.png"),
            ("Carregar", "load_icon.png"),
            ("Remover", "remove_icon.png"),
            ("Executar", "execute_icon.png"),
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

        # Botões laterais (blocos)
        botoes_icone = [
            ("Clique", "click_icon.png"),
            ("Texto", "text_icon.png"),
            ("Delay", "delay_icon.png"),
            ("Label", "label_icon.png"),
            ("GoTo", "goto_icon.png"),
            ("Se Imagem", "ifimage_icon.png"),
            ("OCR", "ocr_icon.png"),
            ("OCR duplo", "doubleocr_icon.png"),
            ("Loop", "loop_icon.png"),
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

        # Botão de conectar
        btn_conectar = tk.Label(self.menu_frame, text="➕", bg="#ddd", width=5, relief="raised", bd=2, cursor="hand2")
        btn_conectar.pack(pady=10)
        btn_conectar.bind("<Button-1>", lambda e: self.setas.ativar_conexao())

        # Vincula eventos
        bind_eventos(self.canvas, self.blocos, self.setas, self.root)

    def executar_acao_topo(self, nome):
        if nome == "Novo":
            # limpa tudo e cria novos managers
            self.canvas.delete("all")
            self.blocos = BlocoManager(self.canvas, self)
            self.setas  = SetaManager(self.canvas, self.blocos)
            bind_eventos(self.canvas, self.blocos, self.setas, self.root)
            return

        if nome == "Salvar":
            # exporta para tmp e chama GUI de salvamento
            export_macro_to_tmp(self.blocos.blocks, self.setas.setas)
            salvar_macro_gui()
            return

        elif nome == "Carregar":
            path = filedialog.askopenfilename(filetypes=[("JSON","*.json")], title="Abrir macro")
            if not path:
                return
            try:
                with open(path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                # limpa canvas e gerenciadores
                self.canvas.delete("all")
                self.blocos = BlocoManager(self.canvas, self)
                self.setas  = SetaManager(self.canvas, self.blocos)
                bind_eventos(self.canvas, self.blocos, self.setas, self.root)

                # recria blocos com IDs e actions
                id_map = {}
                for blk in data.get("blocks", []):
                    btype = blk.get("type", "")
                    bloco = self.blocos.adicionar_bloco(btype, "white")
                    x, y = blk.get("x", bloco["x"]), blk.get("y", bloco["y"])
                    bx2, by2 = x + bloco["width"], y + bloco["height"]
                    self.canvas.coords(bloco["rect"], x, y, bx2, by2)
                    if bloco.get("icon"):
                        self.canvas.coords(bloco["icon"], x, y)
                    bloco["x"], bloco["y"] = x, y
                    bloco["id"] = blk.get("id")
                    id_map[bloco["id"]] = bloco

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
                            if params.get('mode') == 'quantidade':
                                txt = f"INÍCIO LOOP {params.get('count')}x"
                            else:
                                txt = "INÍCIO LOOP INFINITO"
                        elif tipo == "ocr":
                            txt = f"OCR: '{params.get('text')}'"
                        elif tipo == "ocr_duplo":
                            cond = params.get('condicao', 'and').upper()
                            txt = f"OCR Duplo: '{params.get('text1')}' {cond} '{params.get('text2')}'"
                        else:
                            txt = tipo.upper()
                        bloco["label_id"] = self.canvas.create_text(
                            x + bloco["width"]/2,
                            y + bloco["height"] + 8,
                            text=txt, font=("Arial", 9), fill="black"
                        )
                # recria conexões
                for conn in data.get("connections", []):
                    origem = id_map.get(conn.get("from"))
                    destino = id_map.get(conn.get("to"))
                    if origem and destino:
                        self.setas.desenhar_linha(origem, destino)

                messagebox.showinfo("Carregado", f"Macro carregada de:\n{path}")
                return
            except Exception as e:
                messagebox.showerror("Erro ao carregar", str(e))
                return

        elif nome == "Remover":
            print("🗑 Remover item(s) selecionado(s)")
            # usa a mesma rotina já ligada à tecla Delete
            self.blocos.deletar_selecionados()

        elif nome == "Executar":
            # só exporta para tmp (sem salvar em Macros/)
            tmp_path = export_macro_to_tmp(self.blocos.blocks, self.setas.setas)
        
            # dispara execução direto do JSON temporário
            import threading
            threading.Thread(
                target=lambda: executar_macro_flow(tmp_path),
                daemon=True
            ).start()
            return


        if nome == "Remover":
            self.blocos.deletar_selecionados()
            return
            # TODO: iniciar execução dos blocos

        # Gerenciadores de canvas
        #self.blocos = BlocoManager(self.canvas, self)
        #self.setas  = SetaManager(self.canvas, self.blocos)

        #bind_eventos(self.canvas, self.blocos, self.setas, self.root)


# Inicialização
if __name__ == "__main__":
    root = tk.Tk()
    app = FlowchartApp(root)
    root.mainloop()
