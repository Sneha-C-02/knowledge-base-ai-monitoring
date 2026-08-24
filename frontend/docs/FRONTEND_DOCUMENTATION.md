# Frontend Documentation: Knowledge Base AI Support & Proactive Monitoring Tool

This document provides a comprehensive overview of the frontend architecture, features, and design decisions for the Knowledge Base AI Support and Proactive Monitoring Tool.

## 1. Technology Stack

- **Core Framework**: React 18 (with TypeScript for strict type-safety)
- **Build Engine**: Vite (for ultra-fast hot module replacement and optimized bundling)
- **Styling**: Tailwind CSS (Utility-first CSS framework for rapid UI development)
- **Icons**: Lucide React (Clean, modern SVG icons)
- **Routing**: React Router DOM (Client-side, single-page application routing)
- **Component Utilities**: `clsx` and `tailwind-merge` (for dynamic class name composition)

## 2. Directory Structure

The project follows a modular, feature-based directory structure inside the `src/` folder:

```text
src/
├── api/             # Centralized API client (fetch wrapper) handling all backend communication
├── components/      # Reusable UI building blocks
│   ├── common/      # Generic components (Buttons, Cards, Inputs, Badges)
│   └── layout/      # Structural components (Sidebar, Topbar, Main Layout wrappers)
├── context/         # React Context providers for global state (SystemContext, AuthContext)
├── pages/           # High-level page components mapping to application routes
├── types/           # TypeScript interfaces and type definitions
├── index.css        # Global CSS, Tailwind directives, and root CSS variables (Colors/Themes)
└── App.tsx          # Application entry point defining routes and context providers
```

## 3. Design System & Aesthetics

The application features a modern, premium design system specifically tailored to provide an excellent user experience.

- **Theme**: A custom Lavender and deep slate color palette. Primary interactions use vibrant indigo/lavender shades, ensuring high visibility and a clean, modern aesthetic.
- **Glassmorphism**: Subtle translucent backgrounds with background-blur effects are used on the top navigation bar to create a premium depth effect.
- **Typography**: Uses modern, highly legible sans-serif fonts with distinct hierarchies.
- **Interactions**: All clickable elements (buttons, inputs, cards) feature dynamic micro-animations and hover state transformations to make the application feel responsive and alive.

## 4. Key Features & Pages

The application is divided into several primary functional areas:

### 4.1 Dashboard (`DashboardPage.tsx`)
A high-level command center displaying real-time system metrics (Support Queries, Active Logs, Detected Issues). It provides a quick glance at recent critical alerts and recent system activity.

### 4.2 Reactive Support (`SupportPage.tsx`)
A chat-style interface allowing users to describe instrument issues in natural language. The UI handles loading states while waiting for the AI backend and gracefully displays the generated answer alongside a link to the "Source Article" (if provided by the backend).

### 4.3 Proactive Log Monitoring (`MonitoringPage.tsx`)
A sophisticated file-upload interface where users can submit machine `.log` files for AI analysis.
- **Multi-File Upload**: Users can browse and upload up to **10 files** simultaneously.
- **Payload**: The frontend seamlessly bundles these selected files into a `multipart/form-data` payload to be processed by the backend.
- **Results Display**: Renders a rich summary of file access status, overall health severity (WARNING, CRITICAL, OK), specific detected issues with recommended actions, and a chronologically sorted table of recent log events.

### 4.4 Knowledge Base (`KnowledgeBasePage.tsx`)
A searchable library of technical documentation. Users can browse articles by ID, Title, or Category. The UI is built to handle empty states gracefully when no matching articles are returned from the database.

### 4.5 System Feeds (`ActivityPage.tsx` & `NotificationsPage.tsx`)
Dedicated pages rendering timeline-based feeds of system actions. These pages utilize distinct color-coded badges to differentiate between `info`, `warning`, `error`, and `success` events.

## 5. State Management

The frontend relies on a hybrid approach to state management:
1. **Local State**: Managed via standard `useState` hooks for page-specific UI behaviors (e.g., toggling a modal, tracking the current typed search query).
2. **Global State (`SystemContext.tsx`)**: Provides application-wide access to essential non-persistent data, such as:
   - System Statistics (for the Dashboard overview cards)
   - Real-time Activity Logs
   - Real-time Notifications
   - Helper methods (`addActivity`, `addNotification`, `updateStats`) so any component can trigger a global system event.

## 6. Architecture Constraints: "Dumb UI" Approach

Per project requirements, the frontend is strictly a **"Dumb UI"**. 

- **No Data Logic**: The React components do not contain any business logic, keyword matching, or log parsing algorithms.
- **API Driven**: Every piece of data displayed on the screen is fetched from the backend via the `ApiClient` (`src/api/client.ts`).
- **Developer Fallbacks**: To ensure the frontend can be demonstrated and worked on even while the backend is offline, the `ApiClient` utilizes explicit `try/catch` blocks. If a network request fails, the API client catches the error and returns a predefined "Placeholder" or empty array. **This ensures the UI never crashes**, while maintaining strict architectural separation.

## 7. Build & Deployment

The application is strictly typed and optimized for production.
- **Development**: Run `npm run dev` to start the Vite HMR server.
- **Production Build**: Run `npm run build` to compile the TypeScript, strip development warnings, and generate a highly optimized static bundle in the `dist/` directory, ready to be served by any static file host (e.g., Nginx, Vercel, Netlify).
