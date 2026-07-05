import pytest
import yaml

from builder.config import settings
from builder.aggregator import aggregate_in_ir
from builder.serializator import (
    _slot_mapping,
    serialize_nlu,
    serialize_domain,
    serialize_rules,
    serialize_stories,
)
from builder.utils import BuildError


EMPTY_SHARED = {
    "entities": {}, 
    "rules": [], 
    "stories": [], 
    "responses": {}
}


# ------------ _slot_mapping ------------
def test_slot_mapping_from_entity_default_name():
    assert _slot_mapping("city", {"from": "entity"}) == {
        "type": "from_entity",
        "entity": "city",
    }


def test_slot_mapping_from_entity_override():
    assert _slot_mapping("place", {
        "from": "entity", 
        "entity": "city"
    }) == {
        "type": "from_entity",
        "entity": "city",
    }


def test_slot_mapping_from_text():
    assert _slot_mapping("q", {"from": "text"}) == {"type": "from_text"}


def test_slot_mapping_from_intent_default_value():
    assert _slot_mapping("f", {"from": "intent"}) == {
        "type": "from_intent",
        "value": True,
    }


def test_slot_mapping_default_source_is_entity():
    assert _slot_mapping("city", {})["type"] == "from_entity"


def test_slot_mapping_unknown_source_raises():
    with pytest.raises(BuildError, match="unknown source"):
        _slot_mapping("x", {"from": "space"})


# ------------ nlu.yml ------------
def test_serialize_nlu_valid_yaml(project):
    module = {
        "module": "weather",
        "intent": "ask",
        "examples": ["погода в [москве](city)"],
        "entities": {
            "city": {
                "lookup": ["москва"], 
                "synonyms": {
                    "москва": ["мск"]
                }
            }
        },
        "response": ["ok"],
    }

    ir = aggregate_in_ir([module], EMPTY_SHARED)
    serialize_nlu(ir)

    text = (project.rasa_data_dir / "nlu.yml").read_text(encoding="utf-8")
    assert settings.GEN_HEADER.strip() in text
    data = yaml.safe_load(text)
    assert data["version"] == settings.RASA_VERSION
    names = [item.get("intent") for item in data["nlu"] if "intent" in item]
    assert "weather_ask" in names


# ------------ domain.yml ------------
def test_serialize_domain_structure(project):
    module = {
        "module": "taxi",
        "intent": "order",
        "examples": ["такси из [москвы](city)"],
        "entities": {
            "city": {
                "lookup": ["москва"]
            }
        },
        "slots": {
            "from_city": {
                "from": "entity", 
                "entity": "city", 
                "type": "text"
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
    }

    ir = aggregate_in_ir([module], EMPTY_SHARED)
    serialize_domain(ir)

    text = (project.rasa_dir / "domain.yml").read_text(encoding="utf-8")
    data = yaml.safe_load(text)
    assert data["version"] == settings.RASA_VERSION
    assert "taxi_order" in data["intents"]
    assert "city" in data["entities"]
    assert data["slots"]["from_city"]["type"] == "text"
    assert data["slots"]["from_city"]["mappings"] == [{
        "type": "from_entity", 
        "entity": "city"
    }]

    assert "taxi_order_form" in data["forms"]
    assert data["actions"] == ["action_dispatch"]
    assert "session_config" in data


def test_serialize_domain_no_forms_key_when_none(project):
    module = {
        "module": "m", 
        "intent": "i", 
        "examples": ["e"], 
        "response": ["ok"]
    }
    ir = aggregate_in_ir([module], EMPTY_SHARED)
    serialize_domain(ir)
    data = yaml.safe_load((project.rasa_dir / "domain.yml").read_text(encoding="utf-8"))
    assert "forms" not in data


# ------------ rules.yml ------------
def test_serialize_rules_valid_yaml(project):
    module = {
        "module": "m",
        "intent": "i",
        "examples": ["e"],
        "handler": {
            "type": "function", 
            "name": "run"
        }
    }

    ir = aggregate_in_ir([module], EMPTY_SHARED)
    serialize_rules(ir)
    data = yaml.safe_load((project.rasa_data_dir / "rules.yml").read_text(encoding="utf-8"))
    assert data["version"] == settings.RASA_VERSION
    assert any(r["rule"] == "m_i" for r in data["rules"])


# ------------ stories.yml ------------
def test_stories_file_written_when_present(project):
    module = {
        "module": "m",
        "intent": "i",
        "examples": ["e"],
        "response": ["ok"],
        "stories": [{
            "story": "s", 
            "steps": [{"intent": "m_i"}]
        }],
    }
    ir = aggregate_in_ir([module], EMPTY_SHARED)
    serialize_stories(ir)
    stories_file = project.rasa_data_dir / "stories.yml"
    assert stories_file.exists()
    data = yaml.safe_load(stories_file.read_text(encoding="utf-8"))
    assert data["stories"][0]["story"] == "s"


def test_stories_file_removed_when_empty(project):
    stories_file = project.rasa_data_dir / "stories.yml"
    stories_file.write_text("old", encoding="utf-8")

    module = {
        "module": "m", 
        "intent": "i", 
        "examples": ["e"], 
        "response": ["ok"]
    }
    ir = aggregate_in_ir([module], EMPTY_SHARED)
    serialize_stories(ir)
    assert not stories_file.exists()
