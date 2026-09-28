"""A few end-to-end checks that the recipe pages are wired up correctly."""
import pytest

from app import create_app


@pytest.fixture
def client(tmp_path):
    return create_app(str(tmp_path / "test.db")).test_client()


FORM = {
    "name": "Pancakes",
    "base_servings": "4",
    "instructions": "Mix and fry.",
    "ingredients": "200 g flour\n300 ml milk",
}


def test_create_view_redirect_detail_and_list(client):
    response = client.post("/recipes/new", data=FORM)
    assert response.status_code == 302
    detail = client.get(response.headers["Location"])
    assert b"Pancakes" in detail.data and b"flour" in detail.data
    assert b"Pancakes" in client.get("/recipes/").data


def test_invalid_form_shows_errors(client):
    response = client.post("/recipes/new", data={**FORM, "ingredients": "2 cup milk"})
    assert response.status_code == 200
    assert b"unknown unit" in response.data


def test_edit_and_delete(client):
    location = client.post("/recipes/new", data=FORM).headers["Location"]
    assert b"200 g flour" in client.get(location + "/edit").data  # pre-filled form
    client.post(location + "/edit", data={**FORM, "name": "Crepes"})
    assert b"Crepes" in client.get(location).data
    assert client.post(location + "/delete").status_code == 302
    assert client.get(location).status_code == 404


def test_missing_recipe_is_404(client):
    assert client.get("/recipes/999").status_code == 404
    assert client.post("/recipes/999/delete").status_code == 404