import tkinter as tk
from tkinter import Toplevel, IntVar, Label, Entry, Button

def add_delay(actions, update_list, tela):
    janela = Toplevel(tela)
    janela.grab_set()
    janela.title("Adicionar Delay")
    janela.geometry("300x300")

    h = IntVar()
    m = IntVar()
    s = IntVar()
    ms = IntVar()

    Label(janela, text="Delay suspende a execução por um tempo em milissegundos.").pack(pady=5)
    Label(janela, text="Milissegundos:").pack()
    Entry(janela, textvariable=ms).pack()

    Label(janela, text="Ou como:").pack()
    Label(janela, text="Horas:").pack(); Entry(janela, textvariable=h).pack()
    Label(janela, text="Minutos:").pack(); Entry(janela, textvariable=m).pack()
    Label(janela, text="Segundos:").pack(); Entry(janela, textvariable=s).pack()
    Label(janela, text="Milissegundos:").pack(); Entry(janela, textvariable=ms).pack()

    def confirmar():
        total = ((h.get() * 3600 + m.get() * 60 + s.get()) * 1000) + ms.get()
        # insere direto no buffer e dispara callback
        actions.append({"type": "delay", "time": total})
        update_list()
        janela.destroy()

    Button(janela, text="Confirmar", command=confirmar).pack(pady=10)
