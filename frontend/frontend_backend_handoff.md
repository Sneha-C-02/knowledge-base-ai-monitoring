# Frontend Architecture & Backend Handoff Guide

This document outlines the current state of the "Knowledge Base — AI-Assisted Support & Proactive Monitoring Tool" frontend. It serves as a guide for integrating the actual database and backend API.

## 🏗️ Technology Stack (Frontend)

We built a highly premium, modern Single Page Application (SPA) using the following stack:

*   **Core Framework:** React 19
*   **Build Tool:** Vite (for extremely fast Hot Module Replacement and optimized production builds)
*   **Language:** TypeScript (strict typing enabled for maximum reliability)
*   **Routing:** `react-router-dom` (Client-side routing for seamless page transitions)
*   **Styling:** Tailwind CSS v4 (Utility-first styling with custom glassmorphism and modern gradient aesthetics)
*   **Animations:** `tailwindcss-animate` (for smooth micro-animations and page entrance effects)
*   **Icons:** `lucide-react` (Scalable, enterprise-grade vector icons)

## 🧠 Current Data Strategy (Local/Real-time Simulation)

Because the frontend needed to feel 100% real and functional before the backend was ready, we implemented a robust **local simulation layer**. 

Here is how data currently flows, which you will need to replace with real API calls:

### 1. The Knowledge Base (KB)
*   **What we did:** We created a localized JSON-style database in `src/data/kb_database.ts` containing realistic analytical instrument articles.
*   **Backend Integration:** The frontend currently imports this array directly. You will need to replace this by creating a `GET /api/articles` endpoint. The frontend pages (`KnowledgeBasePage.tsx` and `ArticlePage.tsx`) will be updated to `fetch()` this data on mount.

### 2. Reactive Support Engine (AI Querying)
*   **What we did:** In `src/pages/SupportPage.tsx`, we built a client-side **keyword scoring algorithm**. When the user types a query (e.g., "Pressure is too high"), the frontend parses the string, scores it against keywords in our local KB database, and dynamically pulls the best matching article to "simulate" an AI response.
*   **Backend Integration:** You will handle the heavy lifting. The frontend will send the user's natural language string to a `POST /api/support/query` endpoint. Your backend will process the text (via LLM or vector search), and return the generated answer and the ID of the related KB article.

### 3. Proactive Monitoring (Real-time Logs)
*   **What we did:** We use React Context (`SystemContext.tsx`) and the browser's `localStorage` to simulate real-time persistent data. When issues are "detected", they are saved locally so they persist across page refreshes.
*   **Backend Integration:** Instead of reading/writing to `localStorage`, this page should ideally connect to a **WebSocket** or Server-Sent Events (SSE) stream (e.g., `wss://api.yoursite.com/logs/stream`) to receive live instrument telemetry and alerts.

### 4. Authentication
*   **What we did:** `AuthContext.tsx` uses a hardcoded `mockUser` and checks credentials locally, storing the active session in `localStorage`.
*   **Backend Integration:** Replace the `login` function to send a `POST /api/auth/login` request. The backend should return a JWT (JSON Web Token), which the frontend will store and attach to the `Authorization` header of all future requests.

## 🚀 Summary for your Teammate

You can summarize your work to your teammate like this:

> *"I have completed the entire UI/UX frontend architecture using React, Vite, and Tailwind CSS. The app features a premium enterprise design with smooth animations and dynamic routing. To keep development unblocked, I built a local simulation layer using React Context and LocalStorage, including a client-side search algorithm that mimics our AI support engine using a dummy local database. The frontend is fully stateful and ready for integration. We just need to swap out my local Data Contexts and mock functions with your real REST endpoints (and WebSockets for the live monitoring)."*
