import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from blocos import BlocoManager
from setas import SetaManager
from eventos import bind_eventos
from util import clicou_em_linha
from PIL import Image, ImageTk
from core.update_list import update_list
import json, os

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
            path = filedialog.asksaveasfilename(
                defaultextension=".json",
                filetypes=[("JSON","*.json")],
                title="Salvar macro como…"
            )
            if not path: return
            # monta lista de ações a partir dos blocos no canvas
            dados = []
            for bloco in self.blocos.blocks:
                if "acao" in bloco:
                    ac = bloco["acao"].copy()
                    ac["pos_x"] = bloco["x"]
                    ac["pos_y"] = bloco["y"]
                    dados.append(ac)
            with open(path, "w", encoding="utf-8") as f:
                json.dump(dados, f, indent=2, ensure_ascii=False)
            messagebox.showinfo("Salvo", f"Macro salva em:\n{path}")

        elif nome == "Carregar":
            path = filedialog.askopenfilename(
                filetypes=[("JSON","*.json")],
                title="Abrir macro"
            )
            if not path:
                return

            try:
                # 1) carrega o JSON
                with open(path, "r", encoding="utf-8") as f:
                    acoes = json.load(f)  # espera uma lista de {"type":"click","x":..,"y":..}

                # 2) limpa canvas e blocos antigos
                self.canvas.delete("all")
                self.blocos = BlocoManager(self.canvas, self)
                self.setas  = SetaManager(self.canvas, self.blocos)
                bind_eventos(self.canvas, self.blocos, self.setas, self.root)

                # 3) recria cada bloco e seu label
                for ac in acoes:
                    if ac.get("type") == "click":
                        bloco = self.blocos.adicionar_bloco("Clique", "white")
                        # reposiciona retângulo e ícone
                        px, py = ac.get("pos_x", bloco["x"]), ac.get("pos_y", bloco["y"])
                        bx2, by2 = px + bloco["width"], py + bloco["height"]
                        self.canvas.coords(bloco["rect"], px, py, bx2, by2)
                        if bloco.get("icon"):
                            self.canvas.coords(bloco["icon"], px, py)
                        bloco["x"], bloco["y"] = px, py

                        # guarda a ação e desenha o label
                        bloco["acao"]    = ac
                        txt = f"Click @({ac['x']},{ac['y']})"
                        bloco["label_id"] = self.canvas.create_text(
                            px + bloco["width"]/2,
                            py + bloco["height"] + 8,
                            text=txt, font=("Arial", 9), fill="black"
                        )
                messagebox.showinfo("Carregado", f"Macro carregada de:\n{path}")
                return

            except Exception as e:
                messagebox.showerror("Erro ao carregar", str(e))

        elif nome == "Remover":
            print("🗑 Remover item(s) selecionado(s)")
            # usa a mesma rotina já ligada à tecla Delete
            self.blocos.deletar_selecionados()
        elif nome == "Executar":
            print("▶ Executar macro")
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
