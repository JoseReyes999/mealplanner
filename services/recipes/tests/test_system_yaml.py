"""system.yaml (repository root) must list exactly the environment variables this service reads,
with the same defaults, so the description can't drift away from the code."""
import os
import re

import yaml

import config

SERVICE = os.path.basename(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "..")


def read_by_config():
    """{NAME: default} for every os.environ.get("NAME", "default") in config.py."""
    with open(config.__file__, encoding="utf-8") as f:
        return dict(re.findall(r'os\.environ\.get\("([A-Z0-9_]+)",\s*"([^"]*)"\)', f.read()))


def test_env_in_system_yaml_matches_config():
    with open(os.path.join(ROOT, "system.yaml"), encoding="utf-8") as f:
        described = yaml.safe_load(f)["services"][SERVICE]["env"]
    in_code = read_by_config()
    assert set(described) == set(in_code)
    for name, var in described.items():
        if var.get("secret"):
            assert in_code[name] == "", f"{name} is a secret, so the code must not have a default"
        else:
            assert str(var["default"]) == in_code[name], f"{name}: default differs from config.py"