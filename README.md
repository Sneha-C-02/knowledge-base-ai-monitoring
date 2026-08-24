# Knowledge Base AI Support Monitoring

A comprehensive monorepo application providing an intelligent Reactive Support interface and Knowledge Base management system. The platform combines a React frontend with a FastAPI backend, utilizing hybrid Retrieval-Augmented Generation (RAG) to deliver grounded, accurate solutions based on technical documentation.

## Architecture Overview

The system is organized as a monorepo containing both the frontend application and the backend service:

- /frontend: A modern React single-page application built with Vite and Tailwind CSS.
- /backend: A robust Python FastAPI backend integrating PostgreSQL, pgvector for semantic search, and Groq LLMs for grounded answer generation.

### Key Features

- Intelligent Support Resolution: Users can submit technical queries, which are processed using a weighted hybrid retrieval system.
- Hybrid Retrieval (RAG): Combines lexical (full-text) search and semantic (vector) search to find the most relevant Knowledge Base articles.
- Grounded Answers: AI-generated responses are strictly grounded in retrieved context, eliminating hallucinations and preventing internal reasoning leakage.
- Direct Article Navigation: Generated answers include references and direct links to the relevant knowledge base articles for further reading.
- Integrated Knowledge Base: A complete interface for browsing, reading, and managing technical documentation and articles.

## Prerequisites

- Node.js (v18 or higher)
- Python (3.10 or higher)
- Docker and Docker Compose
- PostgreSQL (if not using the Dockerized test database)
- Groq API Key (for answer generation)

## Project Structure

knowledge-base-ai-monitoring/
  ├── frontend/                 # React/Vite frontend application
  │   ├── src/                  # React components, contexts, and API clients
  │   ├── package.json          # Node.js dependencies
  │   └── vite.config.ts        # Vite configuration
  │
  ├── backend/                  # FastAPI/Python backend service
  │   ├── src/                  # Application domains, use cases, and infrastructure
  │   ├── tests/                # Unit, integration, and contract tests
  │   ├── pyproject.toml        # Python dependencies (Poetry)
  │   └── docker-compose.yml    # Backend Docker configuration
  │
  └── README.md                 # Project documentation

## Getting Started

### Backend Setup

1. Navigate to the backend directory:
   cd backend

2. Set up environment variables:
   Copy `.env.example` to `.env` and fill in your credentials.
   Required credentials include `DATABASE_URL` and `GROQ_API_KEY`.

3. Run using Docker (Recommended):
   docker compose up -d

   This will start the FastAPI application and a PostgreSQL test database container. The API will be available at `http://localhost:8000`.

### Frontend Setup

1. Navigate to the frontend directory:
   cd frontend

2. Install dependencies:
   npm install

3. Start the development server:
   npm run dev

   The frontend will be available at `http://localhost:5174` (or the port specified in your console).

## Environment Variables

### Backend (.env)

DATABASE_URL=postgresql+asyncpg://user:password@host:port/dbname
GROQ_API_KEY=your_groq_api_key
JWT_SECRET_KEY=your_secure_jwt_secret
ANSWER_GENERATION_MODEL_NAME=llama3-8b-8192

### Frontend (.env)

VITE_API_URL=http://localhost:8000/api

## Development Workflow

- The backend architecture adheres to Domain-Driven Design (DDD) principles with clear separation of concerns across application, domain, infrastructure, and presentation layers.
- The frontend utilizes React Context for state management and interacts with the backend via secure API endpoints.
- Tests for the backend can be executed using pytest from within the backend directory.
