import pytest

from builder.scanner import scan, _load_shared
from builder.utils import BuildError
from conftest import static_cmd


def test_scan_finds_modules_and_sets_dir(project):
    project.write_module(
        "greeting", 
        {
            "module": "greeting", 
            **static_cmd("hi")
        }
    )
    manifests, shared = scan()
    assert len(manifests) == 1
    manifest = manifests[0]
    assert manifest["module"] == "greeting"
    assert manifest["__dir"] == project.modules_dir / "greeting"


def test_scan_skips_shared_dir(project):
    # _shared лежит в modules/, но не должен попадать в манифесты
    project.write_module("greeting", {
        "module": "greeting", 
        **static_cmd()
    })

    project.write_shared("responses.json", {
        "utter_x": [{"text": "y"}]
    })

    manifests, _ = scan()
    assert [m["module"] for m in manifests] == ["greeting"]


def test_scan_skips_module_without_manifest(project, capsys):
    project.write_module("good", {
        "module": "good", 
        **static_cmd()
    })

    (project.modules_dir / "no_manifest").mkdir()
    manifests, _ = scan()
    assert [m["module"] for m in manifests] == ["good"]
    assert "no_manifest" in capsys.readouterr().out


def test_scan_sorted_order(project):
    project.write_module("zeta", {
        "module": "zeta", 
        **static_cmd()
    })

    project.write_module("alpha", {
        "module": "alpha", 
        **static_cmd()
    })

    manifests, shared = scan()
    assert [m["module"] for m in manifests] == ["alpha", "zeta"]


def test_scan_loads_shared(project):
    project.write_module("g", {
        "module": "g", 
        **static_cmd()
    })

    project.write_shared("rules.json", [
        {
            "rule": "r", 
            "steps": []
        }
    ])

    project.write_shared("entities.json", {
        "city": {
            "lookup": ["москва"]
        }
    })

    _, shared = scan()
    assert shared["rules"] == [{
        "rule": "r", 
        "steps": []
    }]

    assert shared["entities"] == {
        "city": {
            "lookup": ["москва"]
        }
    }
    
    # отсутствующие файлы == пустые структуры
    assert shared["stories"] == []
    assert shared["responses"] == {}


def test_scan_missing_modules_dir_raises(project):
    # удаляем каталог модулей целиком
    import shutil

    shutil.rmtree(project.modules_dir)
    with pytest.raises(BuildError):
        scan()


def test_scan_broken_manifest_raises(project):
    project.write_raw_manifest("broken", "{ this is not json")
    with pytest.raises(BuildError):
        scan()


def test_load_shared_default_when_missing(project):
    assert _load_shared("nope.json", {"d": 1}) == {"d": 1}
    assert _load_shared("nope.json", []) == []
