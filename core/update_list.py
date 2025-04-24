ICONS = {
    "click": "🖱",
    "type": "⌨️",
    "delay": "⏱",
    "ocr": "🔍",
    "ocr_duplo": "🔎",
    "endif": "🔚",
    "else": "↪️",
    "loopstart": "🔁",
    "loopend": "🔚",
    "loopcancel": "🚫",
    "label": "🏷",
    "goto": "➡️"
}

def update_list(listbox, actions):
    listbox.delete(*listbox.get_children())
    indent_level = 0
    indent_map = []

    for acao in actions:
        tipo = acao["type"]
        if tipo in ["endif", "else", "loopend"]:
            indent_level = max(0, indent_level - 1)
        indent_map.append(indent_level)
        if tipo in ["ocr", "ocr_duplo", "loopstart"]:
            indent_level += 1

    for i, acao in enumerate(actions):
        tipo = acao["type"]
        icon = ICONS.get(tipo, '❓')
        prefixo = ("    " * indent_map[i] + icon).ljust(6) + " "

        # Descrição detalhada
        if tipo == 'click':
            desc = f"{prefixo}Clique em ({acao['x']}, {acao['y']})"
        elif tipo == 'type':
            desc = f"{prefixo}Texto: '{acao['text']}'"
        elif tipo == 'delay':
            desc = f"{prefixo}Delay: {acao['time']}ms"
        elif tipo == 'ocr':
            desc = f"{prefixo}SE OCR = '{acao['text']}'"
        elif tipo == 'ocr_duplo':
            cond = acao.get("condicao", "and").upper()
            desc = f"{prefixo}SE OCR ({acao['text1']}) {cond} ({acao['text2']})"
        elif tipo == 'else':
            desc = f"{prefixo}SENÃO"
        elif tipo == 'endif':
            desc = f"{prefixo}FIM DO IF"
        elif tipo == 'loopstart':
            if acao.get("mode") == "quantidade":
                desc = f"{prefixo}INÍCIO LOOP {acao.get('count')}x"
            else:
                desc = f"{prefixo}INÍCIO LOOP INFINITO"
        elif tipo == 'loopend':
            desc = f"{prefixo}FIM DO LOOP"
        elif tipo == 'loopcancel':
            desc = f"{prefixo}SAIR DO LOOP"
        elif tipo == 'label':
            desc = f"{prefixo}Label: {acao.get('name', '')}"
        elif tipo == 'goto':
            desc = f"{prefixo}GOTO → {acao.get('label', '')}"
        else:
            desc = f"{prefixo}Comando desconhecido"

        # Define tag de cor
        if tipo in ("ocr", "ocr_duplo", "endif"):
            tag = "azul"
        elif tipo in ("click", "goto"):
            tag = "verde"
        elif tipo == "type":
            tag = "preto"
        elif tipo in ("delay", "label", "loopstart", "else", "loopend", "loopcancel"):
            tag = "vermelho"
        else:
            tag = ""

        # Inserir na tabela
        listbox.insert(
            "", "end",
            values=(tipo.upper(), desc, acao.get("comentario", "")),
            tags=(tag,)
        )
