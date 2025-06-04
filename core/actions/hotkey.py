from . import register
import keyboard
import time

@register("hotkey")
def run(params, ctx):
    """
    params esperados:
      command: string com o atalho, por ex. "<CTRL+S>"
      content: mesma string (usada para preview)
    """
    cmd = params.get("command", "").strip()
    if not cmd:
        return

    # remove os <> se estiverem lá
    if cmd.startswith("<") and cmd.endswith(">"):
        cmd = cmd[1:-1]

    # converte para minúsculas e dispara o atalho
    # ex: "CTRL+S" -> "ctrl+s"
    sequence = cmd.lower().replace("+", "+")
    keyboard.send(sequence)

    # um breve pause para garantir a execução do atalho
    time.sleep(0.1)
