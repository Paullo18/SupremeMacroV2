# core/inserir.py

def inserir_acao(actions, nova_acao, listbox, atualizar_callback):
    # —————— Se não tiver listbox (canvas-only), só appenda e atualize ——————
    if listbox is None:
        actions.append(nova_acao)
        atualizar_callback()
        return

    # —————— Caso haja listbox, faça o comportamento original ——————
    selecionado = listbox.selection()
    if selecionado:
        index = listbox.index(selecionado[0]) + 1  # Insere logo abaixo do item selecionado
        actions.insert(index, nova_acao)

        def selecionar_novo():
            atualizar_callback()
            itens = listbox.get_children()
            if index < len(itens):
                listbox.selection_set(itens[index])
                listbox.see(itens[index])

        listbox.after(50, selecionar_novo)
    else:
        actions.append(nova_acao)

        def selecionar_final():
            atualizar_callback()
            ultimo = len(listbox.get_children()) - 1
            if ultimo >= 0:
                listbox.selection_set(listbox.get_children()[ultimo])
                listbox.see(listbox.get_children()[ultimo])

        listbox.after(50, selecionar_final)
