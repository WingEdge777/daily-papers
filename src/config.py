import yaml
from pathlib import Path
from .models import Config


class ConfigManager:
    def __init__(self, config_path: str = "config.yaml"):
        self.config_path = Path(config_path)

    def load(self) -> Config:
        if not self.config_path.exists():
            raise FileNotFoundError(f"Config file not found: {self.config_path}")
        
        with open(self.config_path, 'r', encoding='utf-8') as f:
            config_dict = yaml.safe_load(f)
        
        return Config(**config_dict)
