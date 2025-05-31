# 🚀 GameLens Implementation Roadmap

## Phase 0: Project Foundations

| **Task**                     | **Details**                                              | **Tools**               | **Deliverables**                                   |
| ---------------------------- | -------------------------------------------------------- | ----------------------- | -------------------------------------------------- |
| 0.1. Finalise Requirements   | Define scope, features, user stories, success criteria   | Notion/Markdown         | Requirements document (v1.0)                       |
| 0.2. Select Tech Stack       | Confirm stack: Python (FastAPI), PostgreSQL, React, etc. | Markdown, Diagrams      | Tech stack decision document                       |
| 0.3. Set Up Repository       | Initialise GitHub repo, define branching strategy        | GitHub, Git             | GitHub repository with `main` and `dev` branches   |
| 0.4. Development Environment | Create Docker dev environment, VSCode setup, linters     | Docker, VSCode          | Dockerfile + Docker Compose, `.devcontainer` files |
| 0.5. Create API Keys         | Steam Web API, prepare keys for sellers (CDKeys, etc.)   | Steam Dev, Scraping API | API key files in `.env` (not committed to Git)     |

---

## Phase 1: Core Backend – Steam Profile Analysis

| **Task**                      | **Details**                                             | **Tools**                  | **Deliverables**                                             |
| ----------------------------- | ------------------------------------------------------- | -------------------------- | ------------------------------------------------------------ |
| 1.1. FastAPI Project Skeleton | Create basic FastAPI project with `/health` endpoint    | FastAPI, Pydantic, Uvicorn | Basic running API with healthcheck endpoint                  |
| 1.2. Steam API Integration    | Fetch owned games, user details using Steam API         | requests / aiohttp         | `/user/{steam_id}/profile` endpoint returning raw data       |
| 1.3. Data Model Design        | Define Pydantic models for game metadata, user profiles | Pydantic                   | `Game`, `UserProfile`, `PlayStats` models                    |
| 1.4. PostgreSQL Integration   | Set up DB, connect via SQLAlchemy (async)               | PostgreSQL, SQLAlchemy     | Tables: `users`, `games`, `playtime`, migrations via Alembic |
| 1.5. Data Ingestion           | Parse and store Steam profile data into database        | SQLAlchemy                 | User profile fully stored in DB                              |
| 1.6. Unit Tests               | Write unit tests for Steam fetching logic               | Pytest                     | 80%+ test coverage for Phase 1 modules                       |

---

## Phase 2: Game Categorisation Engine

| **Task**                         | **Details**                                                        | **Tools**                        | **Deliverables**                                       |
| -------------------------------- | ------------------------------------------------------------------ | -------------------------------- | ------------------------------------------------------ |
| 2.1. Define Categorisation Logic | Group by genre, tags, playtime thresholds (e.g., >20h = favourite) | Pandas, SQLAlchemy               | Categorisation script + `category` field in DB         |
| 2.2. ML Model (Optional)         | Prototype collaborative filtering using scikit-learn               | scikit-learn                     | Jupyter notebook for ML model; stored recommendations  |
| 2.3. API Endpoint                | `/user/{steam_id}/categories` – return categorised games           | FastAPI                          | JSON response for categories (genre, engagement, etc.) |
| 2.4. Cron Job for Updates        | Implement background tasks to refresh profiles daily               | Celery / FastAPI BackgroundTasks | Profile update service running on schedule             |
| 2.5. Integration Tests           | Ensure categorisation API works with real data                     | Pytest, Mock                     | Test cases for categorisation API                      |

---

## Phase 3: Web Scraper Module for Game Deals

| **Task**                          | **Details**                                                   | **Tools**             | **Deliverables**                                           |
| --------------------------------- | ------------------------------------------------------------- | --------------------- | ---------------------------------------------------------- |
| 3.1. Static Scraping Setup        | Build scrapers for static sites (e.g., CDKeys)                | Scrapy, BeautifulSoup | Scraper module with product URLs, prices, descriptions     |
| 3.2. Dynamic Scraping (if needed) | Use Selenium/Playwright for JS-heavy sites                    | Selenium, Playwright  | Selenium integration for dynamic pages (optional fallback) |
| 3.3. Rate Limiting & Retry Logic  | Implement per-site rate limiting, retries, and error handling | time, asyncio         | Scrapers robust against site bans and errors               |
| 3.4. Database Model               | Add `deals` table: game name, price, URL, timestamp           | SQLAlchemy            | Deals stored and timestamped in DB                         |
| 3.5. API Endpoint                 | `/deals/{game_name}` – fetch latest deals                     | FastAPI               | Deals API response formatted and filtered                  |
| 3.6. Automated Scraping           | Schedule scraping jobs daily                                  | Celery / APScheduler  | Automated scraper running on schedule                      |

---

## Phase 4: Recommendation Engine

| **Task**                         | **Details**                                                      | **Tools**          | **Deliverables**                           |
| -------------------------------- | ---------------------------------------------------------------- | ------------------ | ------------------------------------------ |
| 4.1. Define Recommendation Logic | Match user categories to external deals and unplayed owned games | Pandas, SQLAlchemy | Core recommendation algorithm              |
| 4.2. API Endpoint                | `/user/{steam_id}/recommendations` – return suggestions          | FastAPI            | Personalised recommendation API response   |
| 4.3. Scoring System              | Weight factors: genre match, price discount, playtime, etc.      | Python logic       | Scoring formula with tunable weights       |
| 4.4. Backend Caching             | Cache recommendations for performance                            | Redis (optional)   | Caching layer for recommendations          |
| 4.5. Performance Tests           | Load test API with concurrent users                              | Locust             | Reports on API scalability and bottlenecks |

---

## Phase 5: Frontend Web Application

| **Task**                            | **Details**                                                    | **Tools**                      | **Deliverables**                            |
| ----------------------------------- | -------------------------------------------------------------- | ------------------------------ | ------------------------------------------- |
| 5.1. Frontend Skeleton              | React or Next.js project setup, TailwindCSS integration        | React, TailwindCSS, TypeScript | Basic UI layout, routing, and static assets |
| 5.2. API Integration                | Connect to FastAPI endpoints (profile, deals, recommendations) | Axios / Fetch API              | Data fetched and displayed on frontend      |
| 5.3. User Authentication (optional) | Steam OpenID login (optional scope)                            | Passport.js / NextAuth.js      | Auth flow, login/logout, session management |
| 5.4. UI Components                  | Profile view, recommendations list, deal listings              | React Components               | Modular components for each feature         |
| 5.5. Responsive Design              | Optimise for desktop and mobile                                | TailwindCSS                    | Fully responsive UI                         |
| 5.6. Frontend Tests                 | Unit and integration tests for UI components                   | Jest, React Testing Library    | >80% coverage for frontend logic            |

---

## Phase 6: Deployment & Monitoring

| **Task**                  | **Details**                                                              | **Tools**                   | **Deliverables**                          |
| ------------------------- | ------------------------------------------------------------------------ | --------------------------- | ----------------------------------------- |
| 6.1. Containerisation     | Build Docker images for backend and frontend                             | Docker, Docker Compose      | Production-ready Docker setup             |
| 6.2. CI/CD Pipeline       | Automate builds, tests, and deployments                                  | GitHub Actions, Docker Hub  | CI/CD pipelines for automated deployments |
| 6.3. Production Hosting   | Deploy to cloud platform (e.g., DigitalOcean, Hetzner, or AWS Lightsail) | Nginx, Uvicorn, PostgreSQL  | Live production instance                  |
| 6.4. Monitoring & Logging | Set up error tracking, performance monitoring                            | Prometheus, Grafana, Sentry | Dashboards for metrics and error alerts   |
| 6.5. Documentation        | Finalise technical documentation                                         | Markdown, MkDocs            | Full project documentation                |

---

## Estimated Timeline (High-Level)

| Phase                           | Duration (Weeks) | Notes                                             |
| ------------------------------- | ---------------- | ------------------------------------------------- |
| Phase 0 – Foundations           | 1                | Project setup, planning, and tools                |
| Phase 1 – Steam Integration     | 2                | User profile parsing, DB storage                  |
| Phase 2 – Categorisation Engine | 2                | Game grouping, ML (optional)                      |
| Phase 3 – Web Scraper           | 2–3              | Web scraping core and deal data integration       |
| Phase 4 – Recommendation Engine | 2                | Algorithm, API endpoints, scoring                 |
| Phase 5 – Frontend              | 3                | UI development, API integration, auth (optional)  |
| Phase 6 – Deployment            | 1–2              | Docker, CI/CD, cloud hosting                      |
| **Total Estimate**              | **13–15 weeks**  | Parallel work possible for frontend/backend tasks |
