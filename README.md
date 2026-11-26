# MealPlanner

Recipes, weekly meal plans and one merged shopping list for a shared flat of 4–6 people.

**Live:** https://jmreyesieu2024ui.z28.web.core.windows.net
(the services scale to zero: the first load after a quiet period can take up to a minute)

## Architecture

Two services split along the seam from ADR-2 and ADR-6, each with its own SQL Server database, plus a static UI:

| Part    | Folder             | What it does                                                                                                                     |
| ------- | ------------------ | -------------------------------------------------------------------------------------------------------------------------------- |
| recipes | `services/recipes` | Recipes and ingredients, and scales a recipe to any number of servings                                                           |
| planner | `services/planner` | Weekly plans and the shopping list. Gets recipe names and scaled ingredients from recipes over HTTP (`RECIPES_URL`, 2 s timeout) |
| UI      | `ui/`              | Static HTML/JS that calls both APIs from the browser. `ui/config.js` holds their addresses                                       |

If recipes is down, the planner still serves its plans (without recipe names and with a notice), adding a recipe to a meal returns 503 and saves nothing, and the shopping list returns 503 with a clear message.

Each service has `GET /health` (200 when it can read and write its own database, 503 otherwise, with the running commit SHA), logs one line per request to stdout, and applies its versioned migrations (`services/<name>/migrations/`) at startup. The full description is in `system.yaml`, and each API is in `services/<name>/openapi.yaml`.

## Run locally with docker compose

Requirements: Docker Desktop.

```bash
git clone https://github.com/JoseReyes999/mealplanner.git
cd mealplanner
cp .env.example .env      # then set your own MSSQL_SA_PASSWORD in .env
docker compose up -d --build
```

| URL                          |         |
| ---------------------------- | ------- |
| http://localhost:8080        | UI      |
| http://localhost:8001/health | recipes |
| http://localhost:8002/health | planner |

Compose starts SQL Server, runs `db/init.sql` once (creates the `recipes` and `planner` databases, plus `*_test` databases for the tests), then starts both services and the UI. The first start downloads about 1.5 GB.

To see partial failure: `docker compose stop recipes`, reload a plan in the UI, then `docker compose start recipes`.

## Run a single service

With the database from compose running (`docker compose up -d db`) and Python 3.12:

```bash
cd services/recipes
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
DATABASE_URL="mssql://sa:<password>@localhost:1433/recipes" PORT=8001 python app.py
```

The planner works the same way, plus the address of recipes:

```bash
cd services/planner
DATABASE_URL="mssql://sa:<password>@localhost:1433/planner" RECIPES_URL="http://localhost:8001" PORT=8002 python app.py
```

Every environment variable each service reads, with its default, is listed in `system.yaml`.

## Tests, coverage and lint

The tests run against the `*_test` databases on the local SQL Server, which they empty before every test:

```bash
docker compose up -d db
cd services/recipes
TEST_DATABASE_URL="mssql://sa:<password>@localhost:1433/recipes_test" python -m pytest --cov=. --cov-report=term-missing
cd ../planner
TEST_DATABASE_URL="mssql://sa:<password>@localhost:1433/planner_test" python -m pytest --cov=. --cov-report=term-missing
ruff check services       # from the repository root
```

Coverage is measured on the service code only (`.coveragerc` leaves out the tests); CI fails below 70% per service. The cross-seam test (`services/planner/tests/test_api.py`) replaces recipes with a stub that answers the same endpoints, including when it is down (ADR-9).

## How deployment works

- **CI** (`.github/workflows/ci.yml`) runs on every push to a branch and on every pull request:
  - validates `system.yaml` and both OpenAPI documents
  - lints each service, and runs its tests against a SQL Server container with coverage ≥70%
  - builds both images
- **CD** (`.github/workflows/cd.yml`) runs only on `main`, which changes only through pull requests:
  - runs CI again on the same commit
  - pushes both images to GHCR, tagged with the commit SHA
  - signs in to Azure as a managed identity (OIDC, no stored password)
  - points both Container Apps at the new images
  - writes `ui/config.js` with the services' addresses and uploads `ui/` to the storage static website
  - fails unless both `/health` endpoints answer 200 with that commit's SHA

Azure resources, all in `rg-jmreyes-ieu2024` (France Central):

- the storage account `jmreyesieu2024ui` (UI)
- the Container Apps environment `jmreyes-ieu2024-env`, with `jmreyes-ieu2024-recipes` and `jmreyes-ieu2024-planner` (min 0, max 1 replica)
- the SQL server `jmreyes-ieu2024-sql`, with `jmreyes-ieu2024-recipes-db` and `jmreyes-ieu2024-planner-db` (serverless, free offer)
- the managed identity `jmreyes-ieu2024-github`

## Initial Azure setup (done once)

These are the commands used for the first setup, following the course deployment guide. Run them in bash, not zsh. No password is written here: each one is typed with `read -s`.

```bash
PREFIX="jmreyes-ieu2024"; LOCATION="francecentral"; RG="rg-$PREFIX"
UI_STORAGE="$(echo "$PREFIX" | tr -d '-')ui"

# 1. Subscription and allowed regions
az login
az account set --subscription "Azure for Students"
az policy assignment list --query "[?contains(displayName,'region')].parameters.listOfAllowedLocations.value" -o json

# 2. Providers and resource group
for p in Microsoft.App Microsoft.OperationalInsights Microsoft.Sql Microsoft.Storage Microsoft.ManagedIdentity; do
  az provider register --namespace $p
done
az group create --name "$RG" --location "$LOCATION"

# 3. UI: storage static website
az storage account create --name "$UI_STORAGE" --resource-group "$RG" --location "$LOCATION" \
  --kind StorageV2 --sku Standard_LRS --min-tls-version TLS1_2
az storage blob service-properties update --account-name "$UI_STORAGE" --static-website --index-document index.html
UI_ORIGIN="$(az storage account show -n "$UI_STORAGE" -g "$RG" --query primaryEndpoints.web -o tsv | sed 's:/*$::')"

# 4. SQL server, two free serverless databases, one contained user each
read -s -p "SQL admin password: " SQL_ADMIN_PASSWORD; echo
az sql server create --name "$PREFIX-sql" -g "$RG" -l "$LOCATION" --admin-user sqladmin --admin-password "$SQL_ADMIN_PASSWORD"
for svc in recipes planner; do
  az sql db create -g "$RG" --server "$PREFIX-sql" --name "$PREFIX-$svc-db" \
    --edition GeneralPurpose --family Gen5 --capacity 1 --compute-model Serverless --min-capacity 0.5 \
    --backup-storage-redundancy Local --use-free-limit true --free-limit-exhaustion-behavior AutoPause
done
az sql server firewall-rule create -g "$RG" --server "$PREFIX-sql" --name AllowAzureServices \
  --start-ip-address 0.0.0.0 --end-ip-address 0.0.0.0
RECIPES_DB_PASSWORD="$(openssl rand -hex 16)Aa1"; PLANNER_DB_PASSWORD="$(openssl rand -hex 16)Aa1"
MY_IP="$(curl -s https://api.ipify.org)"
az sql server firewall-rule create -g "$RG" --server "$PREFIX-sql" --name setup-my-ip --start-ip-address "$MY_IP" --end-ip-address "$MY_IP"
# run with sqlcmd (here from the local SQL Server container) as sqladmin, in each database:
#   CREATE USER recipes_app WITH PASSWORD = '<RECIPES_DB_PASSWORD>';    (planner_app in the planner db)
#   ALTER ROLE db_ddladmin ADD MEMBER recipes_app;
#   ALTER ROLE db_datareader ADD MEMBER recipes_app;
#   ALTER ROLE db_datawriter ADD MEMBER recipes_app;
az sql server firewall-rule delete -g "$RG" --server "$PREFIX-sql" --name setup-my-ip

# 5. Container Apps (placeholder image, replaced by the first deploy)
az containerapp env create --name "$PREFIX-env" -g "$RG" -l "$LOCATION" --logs-destination none
az containerapp create --name "$PREFIX-recipes" -g "$RG" --environment "$PREFIX-env" \
  --image mcr.microsoft.com/k8se/quickstart:latest --ingress external --target-port 8000 \
  --min-replicas 0 --max-replicas 1 --cpu 0.25 --memory 0.5Gi \
  --secrets "db-url=mssql://recipes_app:${RECIPES_DB_PASSWORD}@${PREFIX}-sql.database.windows.net:1433/${PREFIX}-recipes-db?encrypt=require" \
  --env-vars "DATABASE_URL=secretref:db-url" "UI_ORIGIN=$UI_ORIGIN"
RECIPES_URL="https://$(az containerapp show -n "$PREFIX-recipes" -g "$RG" --query properties.configuration.ingress.fqdn -o tsv)"
az containerapp create --name "$PREFIX-planner" -g "$RG" --environment "$PREFIX-env" \
  --image mcr.microsoft.com/k8se/quickstart:latest --ingress external --target-port 8000 \
  --min-replicas 0 --max-replicas 1 --cpu 0.25 --memory 0.5Gi \
  --secrets "db-url=mssql://planner_app:${PLANNER_DB_PASSWORD}@${PREFIX}-sql.database.windows.net:1433/${PREFIX}-planner-db?encrypt=require" \
  --env-vars "DATABASE_URL=secretref:db-url" "UI_ORIGIN=$UI_ORIGIN" "RECIPES_URL=$RECIPES_URL"

# 6. Pipeline identity: Contributor on the resource group only, federated credentials for main
az identity create --name "$PREFIX-github" -g "$RG" -l "$LOCATION"
PRINCIPAL_ID="$(az identity show -n "$PREFIX-github" -g "$RG" --query principalId -o tsv)"
az role assignment create --assignee-object-id "$PRINCIPAL_ID" --assignee-principal-type ServicePrincipal \
  --role Contributor --scope "$(az group show -n "$RG" --query id -o tsv)"
GH_REPO="$(gh repo view --json nameWithOwner -q .nameWithOwner)"
GH_OWNER_ID="$(gh api "repos/${GH_REPO}" --jq .owner.id)"; GH_REPO_ID="$(gh api "repos/${GH_REPO}" --jq .id)"
for subject in "repo:${GH_REPO}:ref:refs/heads/main" \
               "repo:${GH_REPO%%/*}@${GH_OWNER_ID}/${GH_REPO##*/}@${GH_REPO_ID}:ref:refs/heads/main"; do
  az identity federated-credential create --name "github-main-$RANDOM" --identity-name "$PREFIX-github" -g "$RG" \
    --issuer https://token.actions.githubusercontent.com --audiences api://AzureADTokenExchange --subject "$subject"
done

# 7. GitHub secrets and variables (values piped, never written in a file)
az identity show -n "$PREFIX-github" -g "$RG" --query clientId -o tsv | gh secret set AZURE_CLIENT_ID
az account show --query tenantId -o tsv | gh secret set AZURE_TENANT_ID
az account show --query id -o tsv | gh secret set AZURE_SUBSCRIPTION_ID
printf %s "$RECIPES_DB_PASSWORD" | gh secret set RECIPES_DB_PASSWORD
printf %s "$PLANNER_DB_PASSWORD" | gh secret set PLANNER_DB_PASSWORD
gh variable set PREFIX --body "$PREFIX"
gh variable set RESOURCE_GROUP --body "$RG"
gh variable set UI_STORAGE --body "$UI_STORAGE"

# 8. Reader access for the professors
for prof in amartini@faculty.ie.edu bserra@faculty.ie.edu; do
  az role assignment create --assignee "$prof" --role Reader --scope "$(az group show -n "$RG" --query id -o tsv)"
done
```

After this, only the pipeline changes anything on Azure.

## Project structure

```
services/
  recipes/            app.py, api.py, db.py, migrate.py, config.py, recipes/ (domain logic),
                      migrations/, tests/, openapi.yaml, Dockerfile
  planner/            same layout, plus recipes_client.py (HTTP client for recipes)
ui/                   static UI (index.html, app.js, style.css, config.js)
db/init.sql           creates the databases in the local SQL Server
docker-compose.yml    db, db-init, recipes, planner, ui
system.yaml           the whole system, validated against system.schema.json
.github/workflows/    ci.yml, cd.yml
ADR.md, AI_USAGE.md   decisions and AI usage log
```

## Known limitations

- The shopping list makes one call to recipes per planned meal (ADR-10).
- Cold starts: after a quiet period, the first request can take up to a minute (ADR-8).
- There is no login: anyone with the link can edit any recipe or plan (ADR-5).
- `tsp` and `tbsp` are shown as `ml` on the shopping list.
