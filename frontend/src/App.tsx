import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import { AppLayout } from './components/layout/AppLayout';
import { DashboardPage } from './pages/DashboardPage';
import { SupportPage } from './pages/SupportPage';
import { MonitoringPage } from './pages/MonitoringPage';
import { KeywordDiscoveryPage } from './pages/KeywordDiscoveryPage';
import { NotificationsPage } from './pages/NotificationsPage';
import { KnowledgeBasePage } from './pages/KnowledgeBasePage';
import { ActivityPage } from './pages/ActivityPage';
import { LandingPage } from './pages/LandingPage';
import { LoginPage } from './pages/LoginPage';
import { ArticlePage } from './pages/ArticlePage';
import { AuthProvider, useAuth } from './context/AuthContext';
import { SystemProvider } from './context/SystemContext';
import { MonitoringProvider } from './context/MonitoringContext';
import { SupportProvider } from './context/SupportContext';

function ProtectedRoute({ children }: { children: React.ReactNode }) {
  const { isAuthenticated } = useAuth();
  if (!isAuthenticated) {
    return <Navigate to="/login" replace />;
  }
  return <>{children}</>;
}

function App() {
  return (
    <AuthProvider>
      <SystemProvider>
        <MonitoringProvider>
          <SupportProvider>
            <Router>
              <Routes>
                <Route path="/" element={<LandingPage />} />
                <Route path="/login" element={<LoginPage />} />
                
                <Route element={
                  <ProtectedRoute>
                    <AppLayout />
                  </ProtectedRoute>
                }>
                  <Route path="/dashboard" element={<DashboardPage />} />
                  <Route path="/support" element={<SupportPage />} />
                  <Route path="/monitoring" element={<MonitoringPage />} />
                  <Route path="/keyword-discovery" element={<KeywordDiscoveryPage />} />
                  <Route path="/knowledge-base" element={<KnowledgeBasePage />} />
                  <Route path="/notifications" element={<NotificationsPage />} />
                  <Route path="/activity" element={<ActivityPage />} />
                  <Route path="/article/:id" element={<ArticlePage />} />
                </Route>

                <Route path="*" element={<Navigate to="/" replace />} />
              </Routes>
            </Router>
          </SupportProvider>
        </MonitoringProvider>
      </SystemProvider>
    </AuthProvider>
  )
}

export default App;
