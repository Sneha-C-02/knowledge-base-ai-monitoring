import type { KBArticle, User, ActivityLog, Notification, SystemStats, PaginatedResponse, Instrument, DashboardResult, InstrumentMemoryResponse } from '../types';

// In development, Vite proxies this relative path to the backend. A deployed
// frontend can still provide its backend URL through VITE_API_URL.
const API_BASE_URL = import.meta.env.VITE_API_URL || '';
const API_ROOT_URL = API_BASE_URL.endsWith('/api')
  ? API_BASE_URL.slice(0, -'/api'.length)
  : API_BASE_URL;

export interface ManagedUser {
  id: number;
  username: string;
  group_id: number | null;
}

class ApiClient {
  private getHeaders() {
    const token = localStorage.getItem('auth_token');
    return {
      'Content-Type': 'application/json',
      ...(token ? { 'Authorization': `Bearer ${token}` } : {})
    };
  }

  private async fetch<T>(
    endpoint: string,
    options?: RequestInit & { isFileUpload?: boolean },
    useApiPrefix: boolean = true,
  ): Promise<T> {
    const headers: Record<string, string> = this.getHeaders();

    // For FormData, the browser must set the Content-Type with the correct boundary
    if (options?.isFileUpload) {
      delete headers['Content-Type'];
    }

    try {
      const baseUrl = useApiPrefix ? API_BASE_URL : API_ROOT_URL;
      const response = await fetch(`${baseUrl}${endpoint}`, {
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
        let message = `API Error: ${response.status} - ${errorText}`;
        try {
          const parsed = JSON.parse(errorText);
          if (parsed?.detail) {
            message = parsed.detail;
          } else if (parsed?.error?.message) {
            message = parsed.error.message;
          }
        } catch {
          // ignore JSON parse error
        }
        throw new Error(message);
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

  async register(
    username: string,
    password: string,
    confirm_password: string,
    display_name?: string
  ): Promise<{ token: string; user: User }> {
    return this.fetch<{ token: string; user: User }>('/auth/register', {
      method: 'POST',
      body: JSON.stringify({
        username,
        password,
        confirm_password,
        display_name,
      }),
    });
  }

  // --- User Management ---
  async getManagedUsers(): Promise<ManagedUser[]> {
    return this.fetch<ManagedUser[]>('/users/management/users', undefined, false);
  }

  async changeManagedUserGroup(userId: number, groupId: number): Promise<void> {
    return this.fetch<void>(`/users/management/users/${userId}/group`, {
      method: 'PUT',
      body: JSON.stringify({ group_id: groupId }),
    }, false);
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
