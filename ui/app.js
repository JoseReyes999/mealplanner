// MealPlanner UI: one static page that talks to the recipes and planner APIs.
// The page shown depends on the part of the URL after # (e.g. #/plans/3), so it
// works as plain files on the storage static website, with no server-side code.

const { RECIPES_API, PLANNER_API } = window.MEALPLANNER_CONFIG;

const DAYS = [["mon", "Monday"], ["tue", "Tuesday"], ["wed", "Wednesday"], ["thu", "Thursday"],
              ["fri", "Friday"], ["sat", "Saturday"], ["sun", "Sunday"]];
const SLOTS = ["breakfast", "lunch", "dinner"];
const UNITS = ["g", "kg", "ml", "l", "tsp", "tbsp", "pcs"];

const STARTING_UP = "The service is starting up (it sleeps when nobody uses it). Please try again in a minute.";

// ---------- talking to the APIs ----------

class Unavailable extends Error {}

const sleep = (ms) => new Promise((resolve) => setTimeout(resolve, ms));

function showStatus(text) {
  const box = document.getElementById("status");
  box.textContent = text || "";
  box.hidden = !text;
}

// Calls an API and returns {status, body}. On Azure an idle service is stopped (min 0 replicas):
// the first request wakes it up, and until it is ready Azure answers 503 "App port is not ready"
// or the connection fails. GETs are retried for about half a minute while that happens; other
// methods are not retried, so a click never saves something twice.
async function call(base, path, { method = "GET", body } = {}) {
  const attempts = method === "GET" ? 7 : 1;
  for (let attempt = 1; attempt <= attempts; attempt++) {
    let response = null;
    try {
      response = await fetch(base + path, {
        method,
        headers: body ? { "Content-Type": "application/json" } : {},
        body: body ? JSON.stringify(body) : undefined,
      });
    } catch (err) {
      response = null; // no answer at all: down or still starting
    }
    const data = response ? await response.json().catch(() => null) : null;
    // A 503 with our own JSON (e.g. the planner saying recipes is down) is a real answer.
    const ours = data && (data.error || data.errors);
    if (response && !(response.status === 503 && !ours)) {
      showStatus("");
      return { status: response.status, body: data };
    }
    if (attempt < attempts) {
      showStatus(`The service is starting up, retrying... (${attempt}/${attempts - 1})`);
      await sleep(5000);
    }
  }
  showStatus("");
  throw new Unavailable(STARTING_UP);
}

// ---------- small helpers ----------

function esc(value) {
  // Everything that comes from the API goes through this before it is put in the page.
  return String(value ?? "").replace(/[&<>"']/g, (c) =>
    ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[c]);
}

const qty = (n) => String(Number(Number(n).toFixed(3))); // 300.0 -> "300", 1.25 -> "1.25"

function render(html) {
  document.getElementById("app").innerHTML = html;
}

function errorsBox(errors) {
  if (!errors || !errors.length) return "";
  return `<div class="errors"><ul>${errors.map((e) => `<li>${esc(e)}</li>`).join("")}</ul></div>`;
}

function showErrors(errors) {
  document.getElementById("errors").innerHTML = errorsBox(errors);
}

// The API's error message(s) for a failed request.
const errorsOf = (body) => (body && (body.errors || (body.error ? [body.error] : null))) || ["Something went wrong."];

// Send a form's fields as JSON when it is submitted, with the button disabled meanwhile.
function onSubmit(formId, handler) {
  const form = document.getElementById(formId);
  form.addEventListener("submit", async (event) => {
    event.preventDefault();
    const button = form.querySelector("button[type=submit]");
    button.disabled = true;
    try {
      await handler(Object.fromEntries(new FormData(form)));
    } catch (err) {
      showErrors([err.message]);
    } finally {
      button.disabled = false;
    }
  });
}

function onClick(selector, handler) {
  document.querySelectorAll(selector).forEach((el) =>
    el.addEventListener("click", async () => {
      try {
        await handler(el);
      } catch (err) {
        showErrors([err.message]);
      }
    }));
}

function weekDates(weekStart) {
  const [y, m, d] = weekStart.split("-").map(Number);
  return DAYS.map((_, i) => new Date(y, m - 1, d + i));
}

function nextMonday() {
  const day = new Date();
  day.setDate(day.getDate() + ((8 - day.getDay()) % 7 || 7));
  return `${day.getFullYear()}-${String(day.getMonth() + 1).padStart(2, "0")}-${String(day.getDate()).padStart(2, "0")}`;
}

// ---------- pages ----------

function home() {
  render(`
    <h1>MealPlanner</h1>
    <p>Recipes and weekly meal plans for a shared flat.</p>
    <p><a href="#/recipes">Browse recipes</a></p>
    <p><a href="#/plans">Plan the week</a></p>`);
}

async function recipeList() {
  const { body: recipes } = await call(RECIPES_API, "/recipes");
  const rows = recipes.map((r) =>
    `<tr><td><a href="#/recipes/${r.id}">${esc(r.name)}</a></td><td>${esc(r.base_servings)}</td></tr>`).join("");
  render(`
    <div class="actions"><h1>Recipes</h1><a class="button" href="#/recipes/new">+ New recipe</a></div>
    ${recipes.length ? `<table><tr><th>Name</th><th>Servings</th></tr>${rows}</table>` : "<p>No recipes yet.</p>"}`);
}

async function recipeDetail(id) {
  const { status, body: recipe } = await call(RECIPES_API, `/recipes/${id}`);
  if (status === 404) return render("<p>That recipe doesn't exist.</p>");
  const rows = recipe.ingredients.map((i) =>
    `<tr><td>${qty(i.quantity)} ${esc(i.unit)}</td><td>${esc(i.name)}</td></tr>`).join("");
  render(`
    <h1>${esc(recipe.name)}</h1>
    <p>Serves ${esc(recipe.base_servings)}</p>
    <h2>Ingredients</h2><table>${rows}</table>
    <h2>Instructions</h2><p class="pre">${esc(recipe.instructions)}</p>
    <div id="errors"></div>
    <div class="actions">
      <a class="button" href="#/recipes/${id}/edit">Edit</a>
      <button id="delete">Delete</button>
    </div>`);
  onClick("#delete", async () => {
    if (!confirm(`Delete ${recipe.name}?`)) return;
    await call(RECIPES_API, `/recipes/${id}`, { method: "DELETE" });
    location.hash = "#/recipes";
  });
}

async function recipeForm(id) {
  let recipe = { name: "", base_servings: "", ingredients: [], instructions: "" };
  if (id) {
    const { status, body } = await call(RECIPES_API, `/recipes/${id}`);
    if (status === 404) return render("<p>That recipe doesn't exist.</p>");
    recipe = body;
  }
  const lines = recipe.ingredients.map((i) => `${qty(i.quantity)} ${i.unit} ${i.name}`).join("\n");
  render(`
    <h1>${id ? "Edit recipe" : "New recipe"}</h1>
    <div id="errors"></div>
    <form id="form">
      <label for="name">Name</label>
      <input id="name" name="name" value="${esc(recipe.name)}" required>
      <label for="base_servings">Servings</label>
      <input id="base_servings" name="base_servings" type="number" min="1" value="${esc(recipe.base_servings)}" required>
      <label for="ingredients">Ingredients</label>
      <p class="hint">One per line: quantity, unit, name. Units: ${UNITS.join(", ")}. Example: <code>200 g flour</code></p>
      <textarea id="ingredients" name="ingredients" rows="8">${esc(lines)}</textarea>
      <label for="instructions">Instructions</label>
      <textarea id="instructions" name="instructions" rows="6">${esc(recipe.instructions)}</textarea>
      <button type="submit">Save</button>
    </form>`);
  onSubmit("form", async (data) => {
    const { status, body } = await call(RECIPES_API, id ? `/recipes/${id}` : "/recipes",
                                        { method: id ? "PUT" : "POST", body: data });
    if (status >= 400) return showErrors(errorsOf(body));
    location.hash = `#/recipes/${body.id}`;
  });
}

async function planList() {
  const { body: plans } = await call(PLANNER_API, "/plans");
  const rows = plans.map((p) =>
    `<tr><td><a href="#/plans/${p.id}">${esc(p.name)}</a></td><td>${esc(p.week_start)}</td></tr>`).join("");
  render(`
    <div class="actions"><h1>Meal plans</h1><a class="button" href="#/plans/new">+ New plan</a></div>
    ${plans.length ? `<table><tr><th>Name</th><th>Week of</th></tr>${rows}</table>` : "<p>No meal plans yet.</p>"}`);
}

function planForm() {
  render(`
    <h1>New meal plan</h1>
    <div id="errors"></div>
    <form id="form">
      <label for="name">Name</label>
      <input id="name" name="name" placeholder="Week 48" required>
      <label for="week_start">Week starting (Monday)</label>
      <input id="week_start" name="week_start" type="date" value="${nextMonday()}" required>
      <button type="submit">Create plan</button>
    </form>`);
  onSubmit("form", async (data) => {
    const { status, body } = await call(PLANNER_API, "/plans", { method: "POST", body: data });
    if (status >= 400) return showErrors(errorsOf(body));
    location.hash = `#/plans/${body.id}`;
  });
}

async function planDetail(id) {
  const { status, body: plan } = await call(PLANNER_API, `/plans/${id}`);
  if (status === 404) return render("<p>That plan doesn't exist.</p>");

  // The planner tells us whether it could reach recipes. Only then do we load the recipe
  // dropdown; otherwise the plan is still shown (partial failure) with a notice.
  let recipes = [];
  if (plan.recipes_available) {
    recipes = (await call(RECIPES_API, "/recipes")).body;
  }

  const dates = weekDates(plan.week_start);
  const grid = DAYS.map(([key, name], i) => {
    const cells = SLOTS.map((slot) => {
      const entry = plan.entries.find((e) => e.day === key && e.meal_slot === slot);
      if (!entry) return `<td><span class="hint">-</span></td>`;
      const label = entry.recipe_name ?? `recipe #${entry.recipe_id}`;
      return `<td>${esc(label)} <span class="hint">(${entry.servings})</span>
              <button class="small remove" data-entry="${entry.id}" title="Remove">×</button></td>`;
    }).join("");
    const date = dates[i].toLocaleDateString("en-GB", { day: "2-digit", month: "short" });
    return `<tr><td><strong>${name}</strong><br><span class="hint">${date}</span></td>${cells}</tr>`;
  }).join("");

  let addForm;
  if (!plan.recipes_available) {
    addForm = `<p class="hint">Recipes can't be added while the recipes service is unavailable.</p>`;
  } else if (!recipes.length) {
    addForm = `<p>You need at least one recipe first. <a href="#/recipes/new">Create a recipe</a>.</p>`;
  } else {
    addForm = `
      <form id="form">
        <label for="day">Day</label>
        <select id="day" name="day">${DAYS.map(([k, n]) => `<option value="${k}">${n}</option>`).join("")}</select>
        <label for="meal_slot">Meal</label>
        <select id="meal_slot" name="meal_slot">${SLOTS.map((s) => `<option value="${s}">${s[0].toUpperCase() + s.slice(1)}</option>`).join("")}</select>
        <label for="recipe_id">Recipe</label>
        <select id="recipe_id" name="recipe_id">${recipes.map((r) => `<option value="${r.id}">${esc(r.name)}</option>`).join("")}</select>
        <label for="servings">Servings</label>
        <input id="servings" name="servings" type="number" min="1" value="4" required>
        <p class="hint">If the meal already has a recipe, it will be replaced.</p>
        <button type="submit">Add to plan</button>
      </form>`;
  }

  render(`
    <div class="actions"><h1>${esc(plan.name)}</h1><a class="button" href="#/plans/${id}/shopping">Shopping list</a></div>
    <p>Week of ${esc(plan.week_start)}</p>
    ${plan.recipes_available ? "" : `<div class="notice">${esc(plan.notice)}</div>`}
    <table><tr><th>Day</th>${SLOTS.map((s) => `<th>${s[0].toUpperCase() + s.slice(1)}</th>`).join("")}</tr>${grid}</table>
    <h2>Add a recipe to a meal</h2>
    <div id="errors"></div>
    ${addForm}
    <div class="actions"><button id="delete">Delete plan</button></div>`);

  if (document.getElementById("form")) {
    onSubmit("form", async (data) => {
      const { status, body } = await call(PLANNER_API, `/plans/${id}/entries`, { method: "POST", body: data });
      if (status >= 400) return showErrors(errorsOf(body));
      route();
    });
  }
  onClick(".remove", async (button) => {
    await call(PLANNER_API, `/plans/${id}/entries/${button.dataset.entry}`, { method: "DELETE" });
    route();
  });
  onClick("#delete", async () => {
    if (!confirm(`Delete ${plan.name}?`)) return;
    await call(PLANNER_API, `/plans/${id}`, { method: "DELETE" });
    location.hash = "#/plans";
  });
}

async function shoppingList(id) {
  const { status, body } = await call(PLANNER_API, `/plans/${id}/shopping-list`);
  const back = `<p><a href="#/plans/${id}">← Back to the plan</a></p>`;
  if (status === 404) return render("<p>That plan doesn't exist.</p>");
  if (status >= 400) {
    return render(`<h1>Shopping list</h1>${errorsBox(errorsOf(body))}
                   <button onclick="route()">Try again</button>${back}`);
  }
  const rows = body.items.map((i) =>
    `<tr><td>${esc(i.name)}</td><td>${qty(i.quantity)} ${esc(i.unit)}</td></tr>`).join("");
  render(`
    <h1>Shopping list</h1>
    ${body.missing_recipes ? `<div class="notice">${body.missing_recipes} planned meal(s) use a recipe that was deleted, so they are not included.</div>` : ""}
    ${body.items.length ? `<table><tr><th>Ingredient</th><th>Quantity</th></tr>${rows}</table>`
                        : "<p>Nothing to buy yet. Add recipes to the plan first.</p>"}
    ${back}`);
}

// ---------- routing ----------

const routes = [
  [/^#\/$/, home],
  [/^#\/recipes$/, recipeList],
  [/^#\/recipes\/new$/, () => recipeForm(null)],
  [/^#\/recipes\/(\d+)$/, recipeDetail],
  [/^#\/recipes\/(\d+)\/edit$/, recipeForm],
  [/^#\/plans$/, planList],
  [/^#\/plans\/new$/, planForm],
  [/^#\/plans\/(\d+)$/, planDetail],
  [/^#\/plans\/(\d+)\/shopping$/, shoppingList],
];

async function route() {
  const hash = location.hash || "#/";
  const found = routes.find(([pattern]) => pattern.test(hash));
  if (!found) return render("<p>Page not found.</p>");
  const [pattern, page] = found;
  try {
    await page(...hash.match(pattern).slice(1));
  } catch (err) {
    const message = err instanceof Unavailable ? err.message : `Something went wrong: ${err.message}`;
    render(`<div class="errors">${esc(message)}</div>
            <button onclick="route()">Try again</button>`);
  }
}

window.addEventListener("hashchange", route);
route();