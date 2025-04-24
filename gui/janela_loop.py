import tkinter as tk
from tkinter import Toplevel, IntVar, StringVar, Label, Entry, Radiobutton, Button
from core.inserir import inserir_acao

def add_loop(actions, update_list, tela):
    janela = Toplevel(tela)
    janela.grab_set()
    janela.title("Adicionar Loop")
    janela.geometry("300x200")

    tipo = StringVar(value="quantidade")
    quantidade = IntVar(value=1)

    Radiobutton(janela, text="Loop com quantidade fixa", variable=tipo, value="quantidade").pack(anchor="w")
    Entry(janela, textvariable=quantidade).pack()
    Radiobutton(janela, text="Loop infinito", variable=tipo, value="infinito").pack(anchor="w")

    def confirmar():
        # adiciona ao buffer e dispara callback
        if tipo.get() == "quantidade":
            actions.append({"type": "loopstart", "mode": "quantidade", "count": quantidade.get()})
        else:
            actions.append({"type": "loopstart", "mode": "infinito"})
        update_list()
        janela.destroy()

    Button(janela, text="Confirmar", command=confirmar).pack(pady=10)
