import json
from pathlib import Path

# Path padrão para o arquivo de configurações\CONFIG_PATH = Path(__file__).resolve().parents[1] / "settings.json"

CONFIG_PATH = Path(__file__).resolve().parents[1] / "settings.json"

class ConfigManager:
    _listeners = []

    @classmethod
    def load(cls):
        """
        Carrega as configurações do arquivo JSON.
        Retorna um dict vazio se o arquivo não existir.
        """
        try:
            with open(CONFIG_PATH, "r", encoding="utf-8") as f:
                return json.load(f)
        except FileNotFoundError:
            return {}

    @classmethod
    def save(cls, settings: dict):
        """
        Salva o dict de configurações no arquivo JSON e notifica listeners.
        """
        with open(CONFIG_PATH, "w", encoding="utf-8") as f:
            json.dump(settings, f, indent=4, ensure_ascii=False)
        cls._notify_listeners(settings)

    @classmethod
    def add_listener(cls, listener):
        """
        Registra uma função que será chamada com o novo settings quando salvar.
        """
        if listener not in cls._listeners:
            cls._listeners.append(listener)

    @classmethod
    def remove_listener(cls, listener):
        """
        Remove uma função da lista de listeners.
        """
        if listener in cls._listeners:
            cls._listeners.remove(listener)

    @classmethod
    def _notify_listeners(cls, settings: dict):
        for listener in cls._listeners:
            try:
                listener(settings)
            except Exception:
                # Protege contra falhas em listeners
                pass
