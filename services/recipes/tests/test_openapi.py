"""The committed openapi.yaml must describe exactly the endpoints this service has.

If someone adds or removes a route without updating the document (or the reverse), this fails.
"""
import os
import re

import yaml

from app import create_app

OPENAPI = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "openapi.yaml")


def documented_endpoints():
    with open(OPENAPI, encoding="utf-8") as f:
        paths = yaml.safe_load(f)["paths"]
    return {(method.upper(), path) for path, item in paths.items()
            for method in item if method != "parameters"}


def flask_endpoints(app):
    endpoints = set()
    for rule in app.url_map.iter_rules():
        if rule.endpoint == "static":
            continue
        path = re.sub(r"<(?:\w+:)?(\w+)>", r"{\1}", rule.rule)  # <int:plan_id> -> {plan_id}
        endpoints |= {(method, path) for method in rule.methods - {"HEAD", "OPTIONS"}}
    return endpoints


def test_openapi_matches_the_routes(database_url):
    assert flask_endpoints(create_app(database_url)) == documented_endpoints()
