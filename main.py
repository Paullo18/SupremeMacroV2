import tkinter as tk
from blocos import BlocoManager
from setas import SetaManager
from eventos import bind_eventos
from util import clicou_em_linha

class FlowchartApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Flowchart Macro Editor")

        self.canvas = tk.Canvas(root, bg="white")
        self.canvas.pack(side="right", fill="both", expand=True)

        self.menu_frame = tk.Frame(root, width=150, bg="#f0f0f0")
        self.menu_frame.pack(side="left", fill="y")

        # Gerenciadores
        self.blocos = BlocoManager(self.canvas, self)
        self.setas = SetaManager(self.canvas, self.blocos)

        # Botões de blocos
        blocos_disponiveis = [
            ("Início", "green"),
            ("Se Imagem", "orange"),
            ("Clique", "lightblue"),
            ("Delay", "lightgrey"),
            ("Fim", "red"),
        ]
        for nome, cor in blocos_disponiveis:
            btn = tk.Label(self.menu_frame, text=nome, bg=cor, width=15, relief="raised", bd=2, cursor="hand2")
            btn.pack(pady=5, padx=5)
            btn.bind("<Button-1>", lambda e, n=nome, c=cor: self.blocos.adicionar_bloco(n, c))

        # Botão de conexão
        btn_conectar = tk.Label(self.menu_frame, text="➕ Conectar", bg="#ddd", width=15, relief="raised", bd=2, cursor="hand2")
        btn_conectar.pack(pady=10)
        btn_conectar.bind("<Button-1>", lambda e: self.setas.ativar_conexao())

        # Vincula eventos
        bind_eventos(self.canvas, self.blocos, self.setas, self.root)



# Inicialização
if __name__ == "__main__":
    root = tk.Tk()
    app = FlowchartApp(root)
    root.mainloop()
