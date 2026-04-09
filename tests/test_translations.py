"""Static regression tests for entity translation keys.

These tests protect against the root cause of past stale entity_id bugs: an
entity class declaring a ``translation_key`` that doesn't exist in
``translations/en.json`` / ``strings.json``. When that happens, Home Assistant
falls back to using just the device name for the entity_id, which then collides
across entities and produces numeric suffixes like ``..._2``, ``..._3``.

The tests walk the PetSafe entity classes and switch descriptions, then assert
that every ``translation_key`` resolves to a non-empty name in both translation
files, and that the two files agree on the ``entity`` block.
"""

import inspect
import json
from pathlib import Path
from types import ModuleType

from custom_components.petsafe_smartfeed import binary_sensor as binary_sensor_module
from custom_components.petsafe_smartfeed import sensor as sensor_module
from custom_components.petsafe_smartfeed.entity import PetSafeEntity
from custom_components.petsafe_smartfeed.switch import SWITCH_DESCRIPTIONS

_COMPONENT_DIR = (
    Path(__file__).parent.parent / "custom_components" / "petsafe_smartfeed"
)


def _load_translation_files() -> tuple[dict, dict]:
    """Return (en.json, strings.json) parsed contents."""
    en_data = json.loads((_COMPONENT_DIR / "translations" / "en.json").read_text())
    strings_data = json.loads((_COMPONENT_DIR / "strings.json").read_text())
    return en_data, strings_data


def _iter_entity_translation_keys(module: ModuleType) -> list[tuple[str, str]]:
    """Yield (class_name, translation_key) for PetSafeEntity subclasses in module.

    HA's ``CachedProperties`` metaclass (see
    ``homeassistant.helpers.entity.CachedProperties``) wraps ``_attr_*``
    declarations in a property descriptor at class-creation time and stores the
    raw declared value in an attribute prefixed with ``__attr_``. So the value
    we want lives at ``cls.__dict__["__attr_translation_key"]``. That backing
    name is documented in the ``CachedProperties`` docstring.
    """
    keys: list[tuple[str, str]] = []
    for name, cls in inspect.getmembers(module, inspect.isclass):
        if (
            issubclass(cls, PetSafeEntity)
            and cls is not PetSafeEntity
            and cls.__module__ == module.__name__
        ):
            translation_key = cls.__dict__.get("__attr_translation_key")
            assert isinstance(translation_key, str) and translation_key, (
                f"{name} in {module.__name__} must set "
                f"_attr_translation_key to a non-empty string "
                f"(got {translation_key!r})"
            )
            keys.append((name, translation_key))
    return keys


def _assert_key_present(data: dict, domain: str, key: str, filename: str) -> None:
    """Assert that data['entity'][domain][key]['name'] is a non-empty string."""
    entity_block = data.get("entity", {})
    domain_block = entity_block.get(domain, {})
    key_block = domain_block.get(key)
    assert key_block is not None, (
        f"{filename}: missing entity.{domain}.{key} — add a translation entry"
    )
    name = key_block.get("name")
    assert isinstance(name, str) and name, (
        f"{filename}: entity.{domain}.{key}.name must be a non-empty string"
    )


def test_all_sensor_translation_keys_present():
    en_data, strings_data = _load_translation_files()
    keys = _iter_entity_translation_keys(sensor_module)
    assert keys, "No sensor entity classes discovered — test is broken"
    for _class_name, translation_key in keys:
        _assert_key_present(en_data, "sensor", translation_key, "translations/en.json")
        _assert_key_present(strings_data, "sensor", translation_key, "strings.json")


def test_all_binary_sensor_translation_keys_present():
    en_data, strings_data = _load_translation_files()
    keys = _iter_entity_translation_keys(binary_sensor_module)
    assert keys, "No binary_sensor entity classes discovered — test is broken"
    for _class_name, translation_key in keys:
        _assert_key_present(
            en_data, "binary_sensor", translation_key, "translations/en.json"
        )
        _assert_key_present(
            strings_data, "binary_sensor", translation_key, "strings.json"
        )


def test_all_switch_translation_keys_present():
    en_data, strings_data = _load_translation_files()
    assert SWITCH_DESCRIPTIONS, "SWITCH_DESCRIPTIONS is empty — test is broken"
    for desc in SWITCH_DESCRIPTIONS:
        assert desc.translation_key, (
            f"Switch description {desc.key} has no translation_key"
        )
        _assert_key_present(
            en_data, "switch", desc.translation_key, "translations/en.json"
        )
        _assert_key_present(
            strings_data, "switch", desc.translation_key, "strings.json"
        )


def test_strings_and_en_translations_entity_block_match():
    en_data, strings_data = _load_translation_files()
    assert strings_data.get("entity") == en_data.get("entity"), (
        "strings.json and translations/en.json have drifted in the 'entity' block — "
        "update both files together"
    )
