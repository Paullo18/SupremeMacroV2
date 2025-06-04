# patch_utils.py
# ---------------------------------------------------
# Decorators para aplicar patches a métodos de BlocoManager,
# garantindo que, após operações de undo/snapshot/mover, as setas sejam redesenhadas.

def patch_undo(blocos_class):
    """
    Decora o método 'desfazer' do BlocoManager para, após desfazer uma ação,
    forçar a atualização das setas no canvas.
    """
    original = blocos_class.desfazer

    def novo_desfazer(self, *args, **kwargs):
        result = original(self, *args, **kwargs)
        # redesenha todas as setas após undo
        self.app.setas.atualizar_setas()
        return result

    blocos_class.desfazer = novo_desfazer
    return blocos_class


def patch_snapshot(blocos_class):
    """
    Decora o método '_snapshot' do BlocoManager (que faz checkpoint do estado)
    para preservar o estado das setas entre snapshots.
    """
    original = blocos_class._snapshot

    def novo_snapshot(self, *args, **kwargs):
        # salva o estado atual das setas
        setas_anteriores = list(self.app.setas.setas)
        result = original(self, *args, **kwargs)
        # restaura o estado das setas, mantendo-as no canvas
        self.app.setas.setas = setas_anteriores
        return result

    blocos_class._snapshot = novo_snapshot
    return blocos_class


def patch_mover_bloco(blocos_class):
    """
    Decora o método 'mover_bloco' do BlocoManager para,
    após mover um bloco, redesenhar todas as setas para manter conexões visuais.
    """
    original = blocos_class.mover_bloco

    def novo_mover(self, *args, **kwargs):
        result = original(self, *args, **kwargs)
        # redesenha todas as setas após mover o bloco
        self.app.setas.atualizar_setas()
        return result

    blocos_class.mover_bloco = novo_mover
    return blocos_class
