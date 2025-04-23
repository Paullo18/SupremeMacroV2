def bind_eventos(canvas, blocos, setas, root):
    canvas.bind("<Button-1>",           blocos.canvas_clique)
    canvas.bind("<B1-Motion>",          blocos.mover_bloco)
    canvas.bind("<ButtonRelease-1>",    blocos.finalizar_arrasto)
    canvas.bind("<Motion>",             setas.atualizar_linha_temporaria, add="+")
    canvas.bind("<Button-1>",           setas.selecionar_item,       add="+")
    root.bind("<Delete>",               setas.deletar_item)
