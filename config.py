# config.py
import yaml
from types import SimpleNamespace
from threading import Lock
from pathlib import Path

def dict_to_namespace(d):
    if isinstance(d, dict):
        return SimpleNamespace(**{k.upper(): dict_to_namespace(v) for k, v in d.items()})
    elif isinstance(d, list):
        return [dict_to_namespace(i) for i in d]
    else:
        return d

class Config:
    _instance = None
    _lock = Lock()  # 保证线程安全

    def __new__(cls, path=None):
        
        if path is None:
            base_dir = Path(__file__).resolve().parent
            path = base_dir / "config.yaml"
        
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super(Config, cls).__new__(cls)
                    cls._instance.__init_once(path)
        return cls._instance

    def __init_once(self, path):
        self._raw = self._load_config(path)
        self.config = dict_to_namespace(self._raw)

    def _load_config(self, path):
        try:
            with open(path, "r", encoding="utf-8") as file:
                return yaml.safe_load(file)
        except Exception as e:
            raise RuntimeError(f"Failed to load config file {path}: {e}")
