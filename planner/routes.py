"""HTTP layer for the planner domain.

Recipe data (names, existence) comes ONLY from recipes.service, never from the
recipes tables or repository (ADR-2).
"""
from datetime import date, timedelta

from flask import Blueprint, abort, redirect, render_template, request, url_for

import db
from planner import repository
from planner.shopping import build_shopping_list, collect_lines
from planner.validation import DAYS, MEAL_SLOTS, parse_entry_form, parse_plan_form
from recipes import service as recipes_service

bp = Blueprint("planner", __name__, url_prefix="/plans")

DAY_NAMES = {
    "mon": "Monday", "tue": "Tuesday", "wed": "Wednesday", "thu": "Thursday",
    "fri": "Friday", "sat": "Saturday", "sun": "Sunday",
}


def build_week(plan, recipe_names):
    """Turn a plan's entries into rows for the weekly grid, one per day:

    [{'key': 'mon', 'name': 'Monday', 'date': date(2026, 10, 5),
      'meals': {'breakfast': None, 'lunch': None, 'dinner': {...entry, 'recipe_name': 'Pancakes'}}}, ...]

    A recipe that was deleted after being planned shows as '(deleted recipe)',
    because recipe_id is a soft reference (no foreign key).
    """
    monday = date.fromisoformat(plan["week_start"])
    by_slot = {(e["day"], e["meal_slot"]): e for e in plan["entries"]}
    week = []
    for offset, day in enumerate(DAYS):
        meals = {}
        for slot in MEAL_SLOTS:
            entry = by_slot.get((day, slot))
            if entry is not None:
                entry = {**entry, "recipe_name": recipe_names.get(entry["recipe_id"], "(deleted recipe)")}
            meals[slot] = entry
        week.append({"key": day, "name": DAY_NAMES[day], "date": monday + timedelta(days=offset), "meals": meals})
    return week


def _render_detail(plan, errors=(), form=None):
    recipes = recipes_service.list_recipe_choices()
    names = {r["id"]: r["name"] for r in recipes}
    return render_template(
        "planner/detail.html",
        plan=plan,
        week=build_week(plan, names),
        recipes=recipes,
        days=[(d, DAY_NAMES[d]) for d in DAYS],
        slots=MEAL_SLOTS,
        errors=errors,
        form=form or {},
    )


@bp.route("/")
def list_view():
    return render_template("planner/list.html", plans=repository.list_plans(db.get_db()))


@bp.route("/new", methods=["GET", "POST"])
def create_view():
    form, errors = {}, []
    if request.method == "POST":
        form = request.form
        data, errors = parse_plan_form(form)
        if not errors:
            plan_id = repository.create_plan(db.get_db(), **data)
            return redirect(url_for("planner.detail_view", plan_id=plan_id))
    return render_template("planner/form.html", form=form, errors=errors)


@bp.route("/<int:plan_id>")
def detail_view(plan_id):
    plan = repository.get_plan(db.get_db(), plan_id)
    if plan is None:
        abort(404)
    return _render_detail(plan)


@bp.route("/<int:plan_id>/entries", methods=["POST"])
def add_entry_view(plan_id):
    conn = db.get_db()
    plan = repository.get_plan(conn, plan_id)
    if plan is None:
        abort(404)
    data, errors = parse_entry_form(request.form)
    # Validation checks the shape; the recipes domain answers whether the recipe exists.
    if not errors and not recipes_service.recipe_exists(data["recipe_id"]):
        errors.append("That recipe doesn't exist.")
    if errors:
        return _render_detail(plan, errors=errors, form=request.form)
    repository.set_entry(conn, plan_id, **data)
    return redirect(url_for("planner.detail_view", plan_id=plan_id))


@bp.route("/<int:plan_id>/entries/<int:entry_id>/delete", methods=["POST"])
def remove_entry_view(plan_id, entry_id):
    if not repository.remove_entry(db.get_db(), plan_id, entry_id):
        abort(404)
    return redirect(url_for("planner.detail_view", plan_id=plan_id))


@bp.route("/<int:plan_id>/shopping-list")
def shopping_list_view(plan_id):
    plan = repository.get_plan(db.get_db(), plan_id)
    if plan is None:
        abort(404)
    lines, missing = collect_lines(plan["entries"], recipes_service.get_scaled_ingredients)
    return render_template(
        "planner/shopping.html",
        plan=plan,
        items=build_shopping_list(lines),
        missing_count=len(missing),
    )


@bp.route("/<int:plan_id>/delete", methods=["POST"])
def delete_view(plan_id):
    if not repository.delete_plan(db.get_db(), plan_id):
        abort(404)
    return redirect(url_for("planner.list_view"))