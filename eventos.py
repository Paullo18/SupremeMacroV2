def bind_eventos(canvas, blocos, app, root):
    canvas.bind("<Button-1>", blocos.canvas_clique)
    canvas.bind("<B1-Motion>", blocos.mover_bloco)
    canvas.bind("<ButtonRelease-1>", blocos.finalizar_arrasto)
    canvas.bind("<Button-1>", app.selecionar_item, add="+")  # ← correto
    root.bind("<Delete>", app.deletar_item)  # ← correto
