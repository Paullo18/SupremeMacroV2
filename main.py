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

        self.canvas = tk.Canvas(root, bg="white")
        self.canvas.pack(side="right", fill="both", expand=True)

        self.menu_frame = tk.Frame(root, width=80, bg="#f0f0f0")
        self.menu_frame.pack(side="left", fill="y")

        # Gerenciadores
        self.blocos = BlocoManager(self.canvas, self)
        self.setas = SetaManager(self.canvas, self.blocos)

        # Cache para ícones
        self.icones = {}

        # Lista dos blocos com seus arquivos
        blocos_icone = [
            ("Clique", "click_icon.png"),
            ("Texto", "text_icon.png"),
            ("Delay", "delay_icon.png"),
            ("Label", "label_icon.png"),
            ("GoTo", "goto_icon.png"),
        ]
        
        for nome, arquivo in blocos_icone:
            caminho = os.path.join("icons", arquivo)
            if os.path.exists(caminho):
                img = Image.open(caminho).resize((112, 40), Image.Resampling.LANCZOS)
                tk_img = ImageTk.PhotoImage(img)
                self.icones[nome] = tk_img  # ← evita coleta pelo garbage collector

                btn = tk.Label(self.menu_frame, image=tk_img, cursor="hand2", bg="#f0f0f0")
                btn.pack(pady=5, padx=5)
                btn.bind("<Button-1>", lambda e, n=nome: self.blocos.adicionar_bloco(n, "white"))
            else:
                print(f"[Aviso] Ícone '{arquivo}' não encontrado.")

        # Botão de conexão (ainda em texto)
        btn_conectar = tk.Label(self.menu_frame, text="➕", bg="#ddd", width=5, relief="raised", bd=2, cursor="hand2")
        btn_conectar.pack(pady=10)
        btn_conectar.bind("<Button-1>", lambda e: self.setas.ativar_conexao())

        # Vincula eventos
        bind_eventos(self.canvas, self.blocos, self.setas, self.root)


# Inicialização
if __name__ == "__main__":
    root = tk.Tk()
    app = FlowchartApp(root)
    root.mainloop()
