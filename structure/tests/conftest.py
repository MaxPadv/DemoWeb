import os
import urllib.parse

import pytest

GATEWAY = os.environ.get("HR_GATEWAY", "http://localhost:8090")
IVAN = "Иван Петров"
MARIA = "Мария Соколова"
ALEXEY = "Алексей Ким"


def hdr(name, roles=""):
    return {"X-User": urllib.parse.quote(name), "X-Roles": roles}


@pytest.fixture
def gateway():
    return GATEWAY


@pytest.fixture
def backend():
    return GATEWAY


@pytest.fixture
def employees():
    return {"ivan": IVAN, "maria": MARIA, "alexey": ALEXEY}
