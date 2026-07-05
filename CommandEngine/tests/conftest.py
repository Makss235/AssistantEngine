import json
from pathlib import Path

import pytest

from builder.config import settings


class ProjectBuilder:
    """
    Вспомогательный класс для сборки временного проекта: пишет модули, _shared и
    предоставляет доступ к каталогам rasa для проверки результата.
    """

    def __init__(self, root: Path):
        self.root = root
        self.modules_dir = root / "modules"
        self.shared_dir = self.modules_dir / "_shared"
        self.rasa_dir = root / "rasa"
        self.rasa_data_dir = self.rasa_dir / "data"
        for dir in (self.shared_dir, self.rasa_data_dir):
            dir.mkdir(parents=True, exist_ok=True)

    def write_module(self, name: str, manifest: dict, handler: str | None = None) -> Path:
        """
        Создаёт папку модуля с manifest.json и handler.py (опционально).
        Args:
            name: имя модуля.
            manifest: словарь для manifest.json.
            handler: текст для handler.py (если None, файл не создаётся).
        Returns:
            Путь к папке модуля.
        """
        module_dir = self.modules_dir / name
        module_dir.mkdir(parents=True, exist_ok=True)
        (module_dir / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False), encoding="utf-8")

        if handler is not None:
            (module_dir / "handler.py").write_text(handler, encoding="utf-8")
        return module_dir

    def write_raw_manifest(self, name: str, text: str) -> Path:
        """
        Пишет manifest.json как есть (для проверки битого JSON).
        Args:
            name: имя модуля.
            text: текст для manifest.json.
        Returns:
            Путь к папке модуля.
        """
        module_dir = self.modules_dir / name
        module_dir.mkdir(parents=True, exist_ok=True)
        (module_dir / "manifest.json").write_text(text, encoding="utf-8")
        return module_dir

    def write_shared(self, name: str, data) -> Path:
        """
        Пишет файл в modules/_shared.
        Args:
            name: имя файла.
            data: данные для записи.
        Returns:
            Путь к файлу.
        """
        path = self.shared_dir / name
        path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
        return path


@pytest.fixture
def project(tmp_path, monkeypatch):
    """
    Временный проект с подменёнными путями в settings.
    Args:
        tmp_path: временная папка pytest.
        monkeypatch: фикстура pytest для подмены атрибутов.
    Returns:
        ProjectBuilder: объект для сборки проекта.
    """
    pb = ProjectBuilder(tmp_path)
    monkeypatch.setattr(settings, "MODULES_DIR", pb.modules_dir)
    monkeypatch.setattr(settings, "SHARED_DIR", pb.shared_dir)
    monkeypatch.setattr(settings, "RASA_DIR", pb.rasa_dir)
    monkeypatch.setattr(settings, "RASA_DATA_DIR", pb.rasa_data_dir)
    return pb


# ------------ utils for commands ------------
def static_cmd(intent="hi", **extra):
    """
    Создаёт словарь статической команды с intent, примерами и ответами.
    Args:
        intent: имя intent.
        extra: дополнительные поля для словаря.
    Returns:
        dict: словарь команды.
    """
    cmd = {
        "intent": intent, 
        "examples": ["привет"], 
        "response": ["Привет!"]
    }
    cmd.update(extra)
    return cmd


def dynamic_cmd(intent="run", **extra):
    """
    Создаёт словарь динамической команды с intent, примерами и обработчиком.
    Args:
        intent: имя intent.
        extra: дополнительные поля для словаря.
    Returns:
        dict: словарь команды.
    """
    cmd = {
        "intent": intent,
        "examples": ["сделай что-нибудь"],
        "handler": {
            "type": "function", 
            "name": "run"
        },
    }
    cmd.update(extra)
    return cmd
