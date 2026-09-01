import type { KBArticle, User, ActivityLog, Notification, SystemStats, PaginatedResponse, Instrument, DashboardResult, InstrumentMemoryResponse } from '../types';

// Use environment variable for API URL or fallback to localhost
const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:3000/api';

class ApiClient {
  private getHeaders() {
    const token = localStorage.getItem('auth_token');
    return {
      'Content-Type': 'application/json',
      ...(token ? { 'Authorization': `Bearer ${token}` } : {})
    };
  }

  private async fetch<T>(endpoint: string, options?: RequestInit & { isFileUpload?: boolean }): Promise<T> {
    const headers: Record<string, string> = this.getHeaders();
    
    // For FormData, the browser must set the Content-Type with the correct boundary
    if (options?.isFileUpload) {
      delete headers['Content-Type'];
    }

    try {
      const response = await fetch(`${API_BASE_URL}${endpoint}`, {
        ...options,
        headers: {
          ...headers,
          ...options?.headers,
        },
      });

      if (!response.ok) {
        // Industry-level interceptor: Handle 401 Unauthorized globally
        if (response.status === 401) {
          localStorage.removeItem('auth_token');
          if (window.location.pathname !== '/login') {
            window.location.href = '/login'; // Force redirect to login
          }
          throw new Error('Session expired. Please log in again.');
        }

        const errorText = await response.text();
        throw new Error(`API Error: ${response.status} - ${errorText}`);
      }

      return response.json();
    } catch (error) {
      console.error(`Network or API Error on ${endpoint}:`, error);
      throw error; // Rethrow so the UI can catch it and display a Toast or Error Boundary
    }
  }

  // --- Auth ---
  async login(username: string, password: string): Promise<{ token: string; user: User }> {
    return this.fetch<{ token: string; user: User }>('/auth/login', {
      method: 'POST',
      body: JSON.stringify({ username, password }),
    });
  }

  // --- Knowledge Base ---
  async getArticles(page: number = 1, pageSize: number = 100, search?: string): Promise<PaginatedResponse<KBArticle>> {
    let url = `/kb/articles?page=${page}&page_size=${pageSize}`;
    if (search) {
      url += `&search=${encodeURIComponent(search)}`;
    }
    return this.fetch<PaginatedResponse<KBArticle>>(url);
  }

  async getArticle(id: string): Promise<KBArticle> {
    return this.fetch<KBArticle>(`/kb/articles/${id}`);
  }

  // --- Support ---
  async querySupport(query: string): Promise<{ 
    answer: string; 
    related_articles?: {
      article_number: string;
      title: string;
      article_url: string;
      snippet: string;
      retrieval_reason: string;
      relevance_score: number;
    }[] 
  }> {
    return this.fetch<{ 
      answer: string; 
      related_articles?: {
        article_number: string;
        title: string;
        article_url: string;
        snippet: string;
        retrieval_reason: string;
        relevance_score: number;
      }[] 
    }>('/support/query', {
      method: 'POST',
      body: JSON.stringify({ query }),
    });
  }

  // --- Monitoring & Dashboard ---

  /** Legacy endpoint (kept for backward compatibility) */
  async analyzeLog(logFiles: File[]): Promise<any> {
    const formData = new FormData();
    logFiles.forEach(file => formData.append('logs', file));

    return this.fetch<any>('/monitoring/analyze', {
      method: 'POST',
      body: formData,
      isFileUpload: true
    });
  }

  /** New dashboard analysis with instrument memory */
  async analyzeLogs(files: File[]): Promise<DashboardResult> {
    const formData = new FormData();
    files.forEach(file => {
      formData.append('logs', file);
    });

    return this.fetch<DashboardResult>('/monitoring/dashboard/analyze', {
      method: 'POST',
      body: formData,
      isFileUpload: true
    });
  }

  /** Get list of instruments for the monitoring dropdown */
  async getInstruments(): Promise<Instrument[]> {
    return this.fetch<Instrument[]>('/monitoring/dashboard/instruments');
  }

  /** Get analysis history for an instrument */
  async getInstrumentMemory(instrumentId: number): Promise<InstrumentMemoryResponse> {
    return this.fetch<InstrumentMemoryResponse>(`/monitoring/dashboard/memory/${instrumentId}`);
  }

  /** Connect to the live dashboard stream (SSE) */
  streamDashboard(instrumentId: number): EventSource {
    return new EventSource(`${API_BASE_URL}/monitoring/dashboard/stream/${instrumentId}`);
  }

  async getMonitoringLogs(): Promise<any[]> {
    return this.fetch<any[]>('/monitoring/logs');
  }

  // --- System ---
  async getActivities(): Promise<ActivityLog[]> {
    const response = await this.fetch<PaginatedResponse<ActivityLog>>('/system/activities');
    return response.items || [];
  }

  async createActivity(type: string, message: string, severity: string = 'INFO', metadata?: Record<string, any>): Promise<void> {
    return this.fetch<void>('/system/activities', {
      method: 'POST',
      body: JSON.stringify({ type, message, severity, metadata })
    });
  }

  async getNotifications(): Promise<Notification[]> {
    const response = await this.fetch<PaginatedResponse<Notification>>('/system/notifications');
    return response.items || [];
  }

  async getStats(): Promise<SystemStats> {
    return this.fetch<SystemStats>('/system/stats');
  }
}

export const api = new ApiClient();
