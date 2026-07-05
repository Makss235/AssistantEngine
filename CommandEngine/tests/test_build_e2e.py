import pytest
import yaml

from builder.config import settings
from builder.main import build, main
from conftest import static_cmd


def _full_project(project):
    # static
    project.write_module("greeting", {
        "module": "greeting", 
        **static_cmd("hi")
    })
    # dynamic
    project.write_module("music", {
            "module": "music",
            "intent": "play",
            "examples": ["включи [queen](artist)"],
            "entities": {
                "artist": {
                    "lookup": ["queen"]
                }
            },
            "handler": {
                "type": "function", 
                "name": "run"
            },
        },
        handler="def run(slots, entities):\n    return {'text': 'играю'}\n",
    )
    # form
    project.write_module("taxi", {
            "module": "taxi",
            "intent": "order",
            "examples": ["вызови такси из [москвы](city)"],
            "entities": {
                "city": {
                    "lookup": ["москва"]
                }
            },
            "slots": {
                "from_city": {
                    "from": "entity", 
                    "entity": "city"
                }
            },
            "form": {
                "required": ["from_city"], 
                "ask": {"from_city": "Откуда?"}
            },
            "handler": {
                "type": "function", 
                "name": "run"
            },
        },
        handler="def run(slots, entities):\n    return {'text': 'едем'}\n",
    )


def test_build_generates_all_files(project):
    _full_project(project)
    build()

    nlu = yaml.safe_load((project.rasa_data_dir / "nlu.yml").read_text(encoding="utf-8"))
    domain = yaml.safe_load((project.rasa_dir / "domain.yml").read_text(encoding="utf-8"))
    rules = yaml.safe_load((project.rasa_data_dir / "rules.yml").read_text(encoding="utf-8"))

    # все три интента присутствуют
    for intent in ("greeting_hi", "music_play", "taxi_order"):
        assert intent in domain["intents"]

    # форма и её слот
    assert "taxi_order_form" in domain["forms"]
    assert "from_city" in domain["slots"]

    # правила: static->utter, dynamic->dispatch, form activate/submit
    rule_names = {r["rule"] for r in rules["rules"]}
    assert "greeting_hi" in rule_names
    assert "music_play" in rule_names
    assert "activate taxi_order_form" in rule_names
    assert "submit taxi_order_form" in rule_names

    # nlu содержит интенты
    nlu_intents = [i.get("intent") for i in nlu["nlu"] if "intent" in i]
    assert "music_play" in nlu_intents


def test_build_no_stories_removes_file(project):
    _full_project(project)
    (project.rasa_data_dir / "stories.yml").write_text("stale", encoding="utf-8")
    build()
    # историй в модулях нет, файл должен быть удалён
    assert not (project.rasa_data_dir / "stories.yml").exists()


def test_main_exits_1_on_build_error(project, capsys):
    # имя не совпадает с папкой
    project.write_module("greeting", {
        "module": "wrong", 
        **static_cmd()
    
    })
    with pytest.raises(SystemExit) as exc:
        main()
    
    assert exc.value.code == 1
    assert "BUILDING ERROR" in capsys.readouterr().err


def test_main_success_no_exit(project):
    _full_project(project)
    main()


def test_real_modules_build(tmp_path, monkeypatch):
    real_modules = settings.BUILDER_DIR.parent / "modules"
    if not real_modules.exists():
        pytest.skip("real modules/ not found")

    out = tmp_path / "rasa"
    out_data = out / "data"
    out_data.mkdir(parents=True)
    monkeypatch.setattr(settings, "RASA_DIR", out)
    monkeypatch.setattr(settings, "RASA_DATA_DIR", out_data)

    build()
    # domain.yml должен получиться валидным YAML
    domain = yaml.safe_load((out / "domain.yml").read_text(encoding="utf-8"))
    assert "intents" in domain and domain["intents"]
