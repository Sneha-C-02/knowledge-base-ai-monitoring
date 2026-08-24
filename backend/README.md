# Knowledge Base AI Support & Proactive Monitoring Tool

This is a production-quality, modular FastAPI backend built with Clean Architecture and SOLID principles. It connects to a Supabase PostgreSQL database and supports both full-text and semantic vector retrieval using pgvector.

## 1. System Overview
The backend provides APIs for user authentication, Knowledge Base article browsing and search, AI-powered reactive support queries, and proactive machine log analysis and monitoring. It acts as the intelligent data foundation for the frontend application.

## 2. Architecture Explanation
The application strictly follows Clean Architecture:
- **Domain Layer**: Contains enterprise logic (Entities, Value Objects, Repository Interfaces, Service Interfaces, Exceptions). Has no external dependencies.
- **Application Layer**: Contains Use Cases orchestrating business flows and Models for data transfer. Depends only on the Domain Layer.
- **Infrastructure Layer**: Contains concrete implementations for databases (SQLAlchemy), authentication (JWT/Argon2), AI (OpenAI/Local), and file storage.
- **Presentation Layer**: Exposes the REST API (FastAPI routers, schemas, dependencies, middleware).
- **Bootstrap Layer**: Wires everything together using dependency injection (`dependency-injector`).

## 3. SOLID Principle Mapping
- **SRP**: Controllers only handle HTTP; Use Cases handle workflows; Repositories handle database I/O.
- **OCP**: You can add new AI models or Vector stores by creating new classes that implement `EmbeddingGenerationService` without changing `SubmitSupportQueryUseCase`.
- **LSP**: Any concrete class implementing `ArticleRepository` can be substituted safely.
- **ISP**: Large interfaces are broken down (e.g., separate `ArticleSimilaritySearchService` and `ArticleRepository`).
- **DIP**: High-level Use Cases depend on abstract Domain Interfaces. `ApplicationContainer` handles runtime injection.

## 4. Project Structure
```
knowledge_base_backend/
├── pyproject.toml, Makefile, .env.example, .gitignore, Dockerfile, docker-compose.yml, alembic.ini
├── scripts/
├── alembic/
├── src/
│   └── knowledge_base_backend/
│       ├── main.py
│       ├── bootstrap/
│       ├── configuration/
│       ├── domain/
│       ├── application/
│       ├── infrastructure/
│       └── presentation/
├── tests/
└── docs/
```

## 5. Prerequisites
- Python 3.11+
- Poetry (for dependency management)
- PostgreSQL (Supabase with `pgvector` enabled)
- Docker (optional)

## 6. Supabase PostgreSQL Connection Setup
Obtain your Supabase connection string and add it to `.env`:
`DATABASE_CONNECTION_URL=postgresql+asyncpg://postgres:[YOUR-PASSWORD]@[YOUR-HOST]:6543/postgres`

## 7. Environment Variable Setup
Copy `.env.example` to `.env` and fill out the details.
```bash
cp .env.example .env
```

## 8. Virtual Environment Setup & 9. Dependency Installation
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install poetry
make install
```

## 10. Alembic Migration Commands
```bash
make migrate
```

## 11. Initial User Creation Command
```bash
make create-user
```

## 12. Database Connection Test
```bash
make test-database
```

## 13. Development Server Command
```bash
make run
```

## 14. API Documentation URL
Once running, visit: http://localhost:3000/docs

## 15. Frontend Connection Configuration
In your React `.env` file:
`VITE_API_URL=http://localhost:3000/api`

## 16. Knowledge Base Pagination Example
`GET /api/kb/articles?page=1&page_size=100`

`GET /api/kb/articles?page=2&page_size=100`

## 17. Search & Instrument-Filter Example
`GET /api/kb/articles?page=1&page_size=100&search=pressure&instrument=ACQUITY%20Arc`

## 18. Authentication Example
```bash
curl -X POST "http://localhost:3000/api/auth/login" \
     -H "Content-Type: application/json" \
     -d '{"username": "admin", "password": "password123"}'
```

## 19. Log Upload Example
```bash
curl -X POST "http://localhost:3000/api/monitoring/analyze" \
     -H "Authorization: Bearer <token>" \
     -F "logs=@/path/to/machine.log"
```

## 20. Automated Test Commands
```bash
make test
```

## 21. Ruff and mypy commands
```bash
make lint
make format
make type-check
make quality
```

## 22. Docker Setup
```bash
docker-compose up --build
```

## 23. Production Deployment Considerations
- Set `APPLICATION_ENVIRONMENT=production`
- Use a strong, rotated `JWT_SECRET_KEY`
- Limit `ALLOWED_FRONTEND_ORIGINS` to the exact production domain
- Run behind a reverse proxy (Nginx, Traefik, AWS ALB)

## 24. Security Guidance
- Do not log raw API keys, tokens, or passwords.
- The default AI provider is "disabled". Change it to "configurable_external" and set an API key safely.

## 25. Troubleshooting
If you encounter `Database unavailable`, verify `DATABASE_CONNECTION_URL` in `.env`. Ensure that the `pgvector` extension is enabled in Supabase if `VECTOR_SEARCH_ENABLED=true`.

## 26. How to Replace Implementations
To switch the answer generator, write a class extending `GroundedAnswerGenerationService`, and update `src/knowledge_base_backend/bootstrap/dependency_container.py` to register your new provider.