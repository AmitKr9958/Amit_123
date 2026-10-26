"""Config must be strict: a typo in YAML must fail loudly, not disable a rule."""

import pytest
from pydantic import ValidationError

from src.config import Preferences, load_preferences


def test_shipped_preferences_load():
    prefs = load_preferences()
    assert prefs.roles.primary
    assert prefs.application.auto_submit is False


def test_unknown_key_rejected():
    with pytest.raises(ValidationError):
        Preferences.model_validate({"application": {"auto_submitt": True}})
