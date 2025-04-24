def bind_eventos(canvas, blocos, setas, root):
    # …já existentes…
    canvas.bind("<Button-1>",           blocos.canvas_clique)
    canvas.bind("<B1-Motion>",          blocos.mover_bloco)
    canvas.bind("<ButtonRelease-1>",    blocos.finalizar_arrasto)
    canvas.bind("<Motion>",             setas.atualizar_linha_temporaria, add="+")
    canvas.bind("<Button-1>",           setas.selecionar_item,       add="+")
    # ▼ NOVOS
    root.bind("<Delete>",               blocos.deletar_selecionados)
    root.bind("<Control-a>",            blocos.selecionar_todos)
    root.bind("<Control-A>",            blocos.selecionar_todos)     # Linux ≠ Windows
    root.bind("<Control-x>",            blocos.recortar_selecionados)
    root.bind("<Control-X>",            blocos.recortar_selecionados)
    root.bind("<Control-z>",            blocos.desfazer)
    root.bind("<Control-Z>",            blocos.desfazer)
    root.bind("<Control-y>",            blocos.refazer)
    root.bind("<Control-Y>",            blocos.refazer)
    root.bind("<Control-c>",            blocos.copiar_selecionados)
    root.bind("<Control-C>",            blocos.copiar_selecionados)
    root.bind("<Control-v>",            blocos.colar_selecionados)
    root.bind("<Control-V>",            blocos.colar_selecionados)