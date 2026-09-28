"""HTTP layer for the recipes domain: reads the request, calls validation/repository, renders a page."""
from flask import Blueprint, abort, redirect, render_template, request, url_for

import db
from recipes import repository
from recipes.validation import UNITS, format_ingredient_line, parse_recipe_form

bp = Blueprint("recipes", __name__, url_prefix="/recipes")


@bp.route("/")
def list_view():
    recipes = repository.list_recipes(db.get_db())
    return render_template("recipes/list.html", recipes=recipes)


@bp.route("/new", methods=["GET", "POST"])
def create_view():
    form, errors = {}, []
    if request.method == "POST":
        form = request.form
        data, errors = parse_recipe_form(form)
        if not errors:
            recipe_id = repository.create_recipe(db.get_db(), **data)
            return redirect(url_for("recipes.detail_view", recipe_id=recipe_id))
    return render_template(
        "recipes/form.html", title="New recipe", form=form, errors=errors, units=UNITS
    )


@bp.route("/<int:recipe_id>")
def detail_view(recipe_id):
    recipe = repository.get_recipe(db.get_db(), recipe_id)
    if recipe is None:
        abort(404)
    return render_template("recipes/detail.html", recipe=recipe)


@bp.route("/<int:recipe_id>/edit", methods=["GET", "POST"])
def edit_view(recipe_id):
    conn = db.get_db()
    recipe = repository.get_recipe(conn, recipe_id)
    if recipe is None:
        abort(404)

    errors = []
    if request.method == "POST":
        form = request.form
        data, errors = parse_recipe_form(form)
        if not errors:
            repository.update_recipe(conn, recipe_id, **data)
            return redirect(url_for("recipes.detail_view", recipe_id=recipe_id))
    else:
        # Pre-fill the form with the saved recipe.
        form = {
            "name": recipe["name"],
            "base_servings": recipe["base_servings"],
            "instructions": recipe["instructions"],
            "ingredients": "\n".join(format_ingredient_line(i) for i in recipe["ingredients"]),
        }
    return render_template(
        "recipes/form.html", title=f"Edit {recipe['name']}", form=form, errors=errors, units=UNITS
    )


@bp.route("/<int:recipe_id>/delete", methods=["POST"])
def delete_view(recipe_id):
    if not repository.delete_recipe(db.get_db(), recipe_id):
        abort(404)
    return redirect(url_for("recipes.list_view"))