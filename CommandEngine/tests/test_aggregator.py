import pytest

from builder.aggregator import aggregate_in_ir


def _ir(manifests, shared=None):
    shared = shared or {
        "entities": {}, 
        "rules": [], 
        "stories": [], 
        "responses": {}
    }
    
    return aggregate_in_ir(manifests, shared)


# ------------ static ------------
def test_static_produces_response_and_rule():
    module = {
        "module": "greeting",
        "intent": "hi",
        "examples": ["привет"],
        "response": ["Привет!", "Здравствуйте!"],
    }

    ir = _ir([module])
    assert "greeting_hi" in ir["intents"]
    assert ir["responses"]["utter_greeting_hi"] == [
        {"text": "Привет!"},
        {"text": "Здравствуйте!"},
    ]

    assert {
        "rule": "greeting_hi",
        "steps": [{"intent": "greeting_hi"}, {"action": "utter_greeting_hi"}],
    } in ir["rules"]


def test_static_response_as_string_wrapped():
    module = {
        "module": "m", 
        "intent": "i", 
        "examples": ["e"], 
        "response": "один"
    }
    ir = _ir([module])
    assert ir["responses"]["utter_m_i"] == [{"text": "один"}]


# ------------ dynamic ------------
def test_dynamic_produces_dispatch_rule():
    module = {
        "module": "music",
        "intent": "play",
        "examples": ["включи"],
        "handler": {
            "type": "function", 
            "name": "run_play"
        },
    }

    ir = _ir([module])
    assert {
        "rule": "music_play",
        "steps": [
            {"intent": "music_play"}, 
            {"action": "action_dispatch"}
        ],
    } in ir["rules"]

    assert "action_dispatch" in ir["actions"]


# ------------ form ------------
def test_form_produces_form_asks_and_two_rules():
    module = {
        "module": "taxi",
        "intent": "order",
        "examples": ["вызови такси"],
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
    }

    ir = _ir([module])
    form_name = "taxi_order_form"
    assert ir["forms"][form_name] == {"required_slots": ["from_city"]}
    assert ir["responses"]["utter_ask_from_city"] == [{"text": "Откуда?"}]

    rule_names = {r["rule"] for r in ir["rules"]}
    assert f"activate {form_name}" in rule_names
    assert f"submit {form_name}" in rule_names

    submit = next(r for r in ir["rules"] if r["rule"] == f"submit {form_name}")
    assert submit["condition"] == [{"active_loop": form_name}]
    assert {"action": "action_dispatch"} in submit["steps"]


# ------------ entity_names ------------
def test_entity_names_collected_from_examples_and_slots():
    module = {
        "module": "weather",
        "intent": "ask",
        "examples": ["погода в [москве](city)"],
        "entities": {
            "city": {
                "lookup": ["москва"]
            }
        },
        "slots": {
            "place": {
                "from": "entity", 
                "entity": "region"
            }
        },
        "response": ["ok"],
    }
    
    ir = _ir([module])
    assert set(ir["entity_names"]) == {"city", "region"}
    assert ir["entity_names"] == sorted(ir["entity_names"])


def test_slot_from_entity_without_override_uses_slot_name():
    module = {
        "module": "m",
        "intent": "i",
        "examples": ["e"],
        "slots": {
            "city": {
                "from": "entity"
            }
        },
        "response": ["ok"],
    }
    ir = _ir([module])
    assert "city" in ir["entity_names"]


def test_slot_from_text_not_added_to_entity_names():
    module = {
        "module": "m",
        "intent": "i",
        "examples": ["e"],
        "slots": {
            "query": {
                "from": "text"
            }
        },
        "response": ["ok"],
    }

    ir = _ir([module])
    assert "query" not in ir["entity_names"]


# ------------ entities NLU: lookup / synonyms ------------
def test_lookup_and_synonyms_emitted_to_nlu():
    module = {
        "module": "weather",
        "intent": "ask",
        "examples": ["погода в [москве](city)"],
        "entities": {
            "city": {
                "lookup": ["москва", "казань"],
                "synonyms": {
                    "санкт-петербург": [
                        "питер", "спб"
                    ]
                }
            }
        },
        "response": ["ok"],
    }

    ir = _ir([module])
    kinds = {kind: payload for kind, payload in ir["nlu"]}
    lookups = [p for k, p in ir["nlu"] if k == "lookup"]
    synonyms = [p for k, p in ir["nlu"] if k == "synonym"]

    assert {"name": "city", "examples": ["москва", "казань"]} in lookups
    assert {"name": "санкт-петербург", "examples": ["питер", "спб"]} in synonyms


# ------------ shared ------------
def test_shared_data_merged_into_ir():
    shared = {
        "entities": {
            "city": {
                "lookup": ["москва"]
            }
        },
        "rules": [{
            "rule": "fallback", 
            "steps": []
        }],
        "stories": [{
            "story": "s", 
            "steps": []
        }],
        "responses": {
            "utter_default": [
                {"text": "Не понял"}
            ]
        },
    }

    module = {
        "module": "m", 
        "intent": "i", 
        "examples": ["e"], 
        "response": ["ok"]
    }

    ir = _ir([module], shared)
    assert ir["responses"]["utter_default"] == [{"text": "Не понял"}]
    assert {"rule": "fallback", "steps": []} in ir["rules"]
    assert {"story": "s", "steps": []} in ir["stories"]
    
    assert "city" in ir["entities"]
    assert ("lookup", {"name": "city", "examples": ["москва"]}) in ir["nlu"]


def test_local_stories_appended():
    module = {
        "module": "m",
        "intent": "i",
        "examples": ["e"],
        "response": ["ok"],
        "stories": [{
            "story": "local", 
            "steps": []
        }],
    }

    ir = _ir([module])
    assert {"story": "local", "steps": []} in ir["stories"]


def test_multi_command_manifest_all_intents_present():
    from builder.utils import manifest_to_commands

    module = {
        "module": "music",
        "__dir": None,
        "entities": {"artist": {"lookup": ["queen"]}},
        "commands": [
            {
                "intent": "play",
                "examples": ["включи [queen](artist)"],
                "handler": {
                    "type": "function", 
                    "name": "run_play"
                },
            },
            {
                "intent": "next", 
                "examples": ["дальше"], 
                "response": ["Дальше"]
            },
        ],
    }
    
    ir = _ir([module])
    assert "music_play" in ir["intents"]
    assert "music_next" in ir["intents"]
    assert "utter_music_next" in ir["responses"]
