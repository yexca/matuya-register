import pytest

from app.matuya.exceptions import MatuyaFormParseError
from app.matuya.parser import extract_hidden_fields


def test_extract_hidden_fields_from_fixture(fixture_text):
    payload = extract_hidden_fields(fixture_text("matuya_entry.html"))

    assert payload["SMPFORM"] == "liqi-lhkikb"
    assert payload["token"] == "entry-token"


def test_extract_hidden_fields_requires_form_and_hidden_fields():
    with pytest.raises(MatuyaFormParseError):
        extract_hidden_fields("<html><body></body></html>")

    with pytest.raises(MatuyaFormParseError):
        extract_hidden_fields("<form><input name='email'></form>")
