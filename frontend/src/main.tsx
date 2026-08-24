import React from 'react'
import ReactDOM from 'react-dom/client'
import App from './App'
import './index.css'

class ErrorBoundary extends React.Component<{children: React.ReactNode}, {hasError: boolean, error: Error | null}> {
  constructor(props: {children: React.ReactNode}) {
    super(props);
    this.state = { hasError: false, error: null };
  }
  static getDerivedStateFromError(error: Error) {
    return { hasError: true, error };
  }
  componentDidCatch(error: Error, errorInfo: React.ErrorInfo) {
    console.error("Uncaught error:", error, errorInfo);
  }
  render() {
    if (this.state.hasError) {
      return (
        <div style={{ padding: '2rem', backgroundColor: '#fee2e2', color: '#991b1b', fontFamily: 'sans-serif', minHeight: '100vh' }}>
          <h1 style={{ fontSize: '2rem', fontWeight: 'bold' }}>Application Error</h1>
          <pre style={{ marginTop: '1rem', whiteSpace: 'pre-wrap', backgroundColor: '#fef2f2', padding: '1rem', border: '1px solid #f87171' }}>
            {this.state.error?.toString()}
            <br/><br/>
            {this.state.error?.stack}
          </pre>
        </div>
      );
    }
    return this.props.children; 
  }
}

ReactDOM.createRoot(document.getElementById('root') as HTMLElement).render(
  <React.StrictMode>
    <ErrorBoundary>
      <App />
    </ErrorBoundary>
  </React.StrictMode>,
)
