from bs4 import BeautifulSoup

from .exceptions import MatuyaFormParseError


def extract_hidden_fields(html):
    soup = BeautifulSoup(html, "html.parser")
    form = soup.find("form")
    if form is None:
        raise MatuyaFormParseError("form not found")
    payload = {}
    for field in form.find_all("input", {"type": "hidden"}):
        name = field.get("name")
        value = field.get("value")
        if name and value is not None:
            payload[name] = value
    if not payload:
        raise MatuyaFormParseError("hidden fields not found")
    return payload
