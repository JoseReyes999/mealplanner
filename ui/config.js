// Where the two APIs live. These values are for local development with docker compose.
// The CD pipeline overwrites this file with the Azure Container Apps addresses.
window.MEALPLANNER_CONFIG = {
  RECIPES_API: "http://localhost:8001",
  PLANNER_API: "http://localhost:8002",
};
