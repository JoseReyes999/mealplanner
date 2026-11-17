"""Tests for recipes_client.py. requests.get is replaced by a fake, so no recipes service is needed."""
from unittest.mock import patch

import pytest
import requests

import config
import recipes_client
from recipes_client import RecipesUnavailable


class FakeResponse:
    """Just enough of a requests.Response for the client: a status code and a JSON body."""

    def __init__(self, status_code, body=None):
        self.status_code = status_code
        self._body = body

    def json(self):
        if self._body is None:
            raise ValueError("no JSON body")
        return self._body


def fake_get(response=None, error=None):
    """Patch requests.get inside recipes_client to return `response` or raise `error`."""
    return patch.object(recipes_client.requests, "get", return_value=response, side_effect=error)


SCALED = {
    "recipe_id": 1, "name": "Pancakes", "servings": 6,
    "ingredients": [{"ingredient_id": 1, "name": "flour", "quantity": 300.0, "unit": "g"}],
}


def test_get_scaled_ingredients_calls_the_right_url_with_a_timeout():
    with fake_get(FakeResponse(200, SCALED)) as get:
        lines = recipes_client.get_scaled_ingredients(1, 6)
    assert lines == SCALED["ingredients"]
    get.assert_called_once_with(
        config.RECIPES_URL + "/recipes/1/scaled",
        params={"servings": 6},
        timeout=config.RECIPES_TIMEOUT_S,
    )


def test_get_scaled_ingredients_missing_recipe_returns_none():
    with fake_get(FakeResponse(404, {"error": "recipe 9 not found"})):
        assert recipes_client.get_scaled_ingredients(9, 2) is None


def test_list_recipe_choices_keeps_only_id_and_name():
    body = [{"id": 1, "name": "Bread", "base_servings": 2, "created_at": "2026-11-17"}]
    with fake_get(FakeResponse(200, body)):
        assert recipes_client.list_recipe_choices() == [{"id": 1, "name": "Bread"}]


@pytest.mark.parametrize("status, expected", [(200, True), (404, False)])
def test_recipe_exists(status, expected):
    with fake_get(FakeResponse(status, {"id": 1})):
        assert recipes_client.recipe_exists(1) is expected


@pytest.mark.parametrize("error", [requests.Timeout("too slow"), requests.ConnectionError("refused")])
def test_unreachable_or_slow_service_raises_recipes_unavailable(error):
    with fake_get(error=error):
        with pytest.raises(RecipesUnavailable, match="unreachable"):
            recipes_client.get_scaled_ingredients(1, 2)


def test_server_error_raises_recipes_unavailable():
    with fake_get(FakeResponse(503, {"status": "error"})):
        with pytest.raises(RecipesUnavailable, match="HTTP 503"):
            recipes_client.list_recipe_choices()


def test_unexpected_status_raises_recipes_unavailable():
    with fake_get(FakeResponse(400, {"error": "bad servings"})):
        with pytest.raises(RecipesUnavailable, match="HTTP 400"):
            recipes_client.get_scaled_ingredients(1, 0)


def test_invalid_json_raises_recipes_unavailable():
    with fake_get(FakeResponse(200, None)):
        with pytest.raises(RecipesUnavailable, match="invalid JSON"):
            recipes_client.recipe_exists(1)