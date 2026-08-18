# UI Architecture Guide

## Presentation Layer
The UI is strictly separated from business logic. We use Tailwind CSS for all styling, ensuring no external CSS bloat.
We rely heavily on Composition (e.g., `Card`, `CardHeader`, `CardTitle`, `CardContent`) to keep components reusable.

## State Management
Local state is used for most forms (Support query, Log path input). When the backend is integrated, React Query or SWR is recommended to handle caching and loading states for data fetching.

## Alignment to Requirements
- **FR-01, FR-04 - FR-09**: Handled by `SupportPage.tsx` and its components.
- **FR-10, FR-11**: Handled by `MonitoringPage.tsx` and `NotificationsPage.tsx`.
- **FR-12**: Handled by `ActivityPage.tsx`.

## Replacing Mock APIs
To connect to the real FastAPI backend:
1. Create `src/services/apiClient.ts` using `axios`.
2. Move the mock `setTimeout` blocks from the pages into `src/services/supportService.ts` and `monitoringService.ts`.
3. Toggle `VITE_USE_MOCK_API` to `false` to point the services to `apiClient.post()`.
