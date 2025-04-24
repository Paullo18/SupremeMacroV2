import tkinter as tk
from tkinter import Toplevel, IntVar, Label, Entry, messagebox
import pyautogui
import threading
import time
import keyboard

def add_click(actions, update_list, tela):
    janela = Toplevel(tela)
    janela.grab_set()
    janela.title("Adicionar Clique")
    janela.geometry("300x200")

    var_x = IntVar()
    var_y = IntVar()
    Label(janela, text="X:").pack()
    entry_x = Entry(janela, textvariable=var_x)
    entry_x.pack()
    Label(janela, text="Y:").pack()
    entry_y = Entry(janela, textvariable=var_y)
    entry_y.pack()

    def monitorar_mouse():
        while True:
            try:
                x, y = pyautogui.position()
                if not entry_x.winfo_exists() or not entry_y.winfo_exists():
                    break
                entry_x.delete(0, tk.END)
                entry_x.insert(0, str(x))
                entry_y.delete(0, tk.END)
                entry_y.insert(0, str(y))
                if keyboard.is_pressed('F2'):
                    nova_acao = {"type": "click", "x": x, "y": y}
                    # Em vez de inserir via inserir_acao, fazemos direto:
                    actions.append(nova_acao)
                    update_list()
                    messagebox.showinfo("Capturado", f"Clique registrado em ({x}, {y})")
                    janela.destroy()
                    break
                time.sleep(0.01)
            except tk.TclError:
                break  # Encerra a thread se os widgets forem destruídos

    threading.Thread(target=monitorar_mouse, daemon=True).start()
