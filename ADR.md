## [N]. <Title>

Date: YYYY-MM-DD
Status: Decided
Context: 1-3 sentences, what forced this decision
Decision: 1-2 sentences, what you chose
Alternatives considered: at least one real alternative, and why you rejected it
Consequences: 1-2 sentences, what this costs or enables later

## 1. Project schema

Date: 2026-09-26
Status: Decided
Context: MealPlanner must hold a few HTML pages and read/write SQLite in a singl process for a shared flat of 4-6 users with no heavy traffic. In order to do so, I am building a simple Python stack so I can build and explain myself.
Decision: I decided to use Flask with Jinja HTML templates and Python's built in sqlite built in module. Where the connection is handled in db.py; where, there are functions like connect, get_db, close_db, and init_db¿ to help me manage the database.
Alternatives considered: Django was not an option because it offers many features that would be ideal for heavy traffic in users, but because MealPlanner needs a lot of tables and no logins, plain sqlite3 makes it simpler in terms of code and more managable from a database perspective. FastAPI rejected because it is designed for async JSON APIs, when I render HTML pages, so async is not necessary. React was also rejected because it adds additional Java Script build.
Consequence: Flask gives me no ORM or admin, so I write my own SQL and form validation. Because the pages are plain templates, I can later implement Java Script or JSON endpoints for a React frontend, without messing up the current structure.
