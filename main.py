import tkinter as tk
from blocos import BlocoManager
from setas import SetaManager
from eventos import bind_eventos
from util import clicou_em_linha
from PIL import Image, ImageTk
import os

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
            print("🔄 Novo projeto")
            # TODO: limpar canvas, resetar estados
        elif nome == "Salvar":
            print("💾 Salvar macro")
            # TODO: abrir diálogo e salvar .json
        elif nome == "Carregar":
            print("📂 Carregar macro")
            # TODO: abrir .json e reconstruir blocos
        elif nome == "Remover":
            print("🗑 Remover item selecionado")
            self.setas.deletar_item(None)
        elif nome == "Executar":
            print("▶ Executar macro")
            # TODO: iniciar execução dos blocos


# Inicialização
if __name__ == "__main__":
    root = tk.Tk()
    app = FlowchartApp(root)
    root.mainloop()
