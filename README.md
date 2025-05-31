# GameLens API

## Project Description

GameLens API is a Python-based backend service designed to provide information about games, user profiles, game deals, and personalized recommendations. It simulates interactions with external services like the Steam API and game deal scrapers, storing and retrieving data from a PostgreSQL database. The API is built using FastAPI, with SQLAlchemy for ORM, Alembic for database migrations, and Docker for containerization.

Key features include:
- User profile management with owned games and playtime.
- Game information, including genres and tags.
- Categorization of games by genre for users.
- Simulated fetching and display of game deals.
- Recommendation engine for game deals based on user's played genres.

## Prerequisites

- Docker
- Docker Compose

## How to Run

1.  **Clone the repository**:
    ```bash
    git clone <repository_url>
    cd <repository_name>
    ```

2.  **Start the application**:
    Use Docker Compose to build and start the services (FastAPI backend and PostgreSQL database):
    ```bash
    docker-compose up -d --build
    ```
    This command will run the services in detached mode. To view logs, you can use `docker-compose logs -f backend`.

3.  **API Availability**:
    *   The API will be available at `http://localhost:8000`.
    *   Basic API documentation (listing available endpoints) can be found at the root URL: `http://localhost:8000/`.

## Running Migrations

Database migrations are managed by Alembic. To apply the latest migrations (e.g., create tables initially or update schema), run the following command after the services are up:

```bash
docker-compose exec backend alembic -c backend/alembic.ini upgrade head
```

## Running Tests

Unit and integration tests are written using Pytest. To run the tests, execute:

```bash
docker-compose exec backend pytest backend/tests
```
This command runs the tests within the `backend` service container. Ensure `PYTHONPATH` is set correctly if running tests outside Docker (e.g., `export PYTHONPATH=. ; pytest backend/tests`). The provided Docker setup should handle this.

## Available API Endpoints

The following are the main API endpoints. For more details, visit `http://localhost:8000/` when the application is running.

*   `GET /`: Serves a simple HTML page listing these API endpoints.
*   `GET /health`: Checks the health status of the API.
*   `GET /user/{steam_id}/profile`: Retrieves user profile and owned games.
*   `GET /user/{steam_id}/categories`: Retrieves user's games categorized by genre.
*   `GET /deals/{game_name}`: Fetches latest deals for a specific game.
*   `GET /user/{steam_id}/recommendations`: Provides game deal recommendations for the user.

*(Note: Replace `{steam_id}` and `{game_name}` with actual values when calling the endpoints.)*

## Tech Stack

*   **Backend**: Python, FastAPI
*   **Database**: PostgreSQL
*   **ORM**: SQLAlchemy (with async support using `asyncpg`)
*   **Migrations**: Alembic
*   **Containerization**: Docker, Docker Compose
*   **Testing**: Pytest, pytest-asyncio, HTTPX
*   **Linters/Formatters**: Flake8, Black, Isort (configured in Dockerfile/devcontainer)

---

This README provides a basic guide to getting the GameLens API up and running.
