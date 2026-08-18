# Knowledge Base AI Support & Proactive Monitoring Tool

A modern, responsive frontend application designed to provide AI-assisted technical support and proactive machine log monitoring.

##  Features
- **Reactive Support**: Natural language query interface to search the knowledge base for instant answers and resolution steps.
- **Proactive Log Monitoring**: Multi-file upload interface to submit machine `.log` files for AI-driven anomaly detection and health analysis.
- **Knowledge Base**: Searchable directory of technical articles and guides.
- **System Dashboard**: Real-time metrics, system activities, and notification feeds.
- **Modern UI**: Clean, glassmorphism-inspired design with dynamic interactions built on Tailwind CSS.

##  Technology Stack
- **Framework**: React 18
- **Build Tool**: Vite
- **Language**: TypeScript
- **Styling**: Tailwind CSS
- **Routing**: React Router DOM
- **Icons**: Lucide React

---

##  Getting Started (Local Development)

Follow these steps to run the frontend application on your local machine.

### Prerequisites
Make sure you have [Node.js](https://nodejs.org/) (version 18+ recommended) installed on your machine.

### 1. Installation
Clone the repository and install the dependencies:
```bash
git clone https://github.com/Sneha-C-02/knowledge-base-ai-monitoring.git
cd knowledge-base-ai-monitoring
npm install
```

### 2. Environment Setup
Create a `.env` file in the root directory to point to your backend API. If you are developing locally with the backend running on port 3000, use:
```env
VITE_API_URL=http://localhost:3000/api
```

### 3. Run the Development Server
Start the Vite development server:
```bash
npm run dev
```
The application will be available at `http://localhost:5173`.

---

##  Building for Production

To create an optimized production build:
```bash
npm run build
```
This will compile the TypeScript code and generate static files in the `dist/` directory, which can be hosted on any static web server (Nginx, Vercel, Netlify, etc.).

---

## 🔗 Backend Integration
The frontend is built as a completely separated "Dumb UI" and relies on the backend API for all data, parsing, and AI logic.
- Ensure your backend matches the required JSON structures and API endpoints.
- See the `docs/` folder (specifically `BACKEND_INTEGRATION_GUIDE.md` and `FRONTEND_DOCUMENTATION.md`) for detailed API contracts and architectural decisions.
