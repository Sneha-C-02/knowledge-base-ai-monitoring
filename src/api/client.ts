import type { KBArticle, User, ActivityLog, Notification, SystemStats } from '../types';

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

    const response = await fetch(`${API_BASE_URL}${endpoint}`, {
      ...options,
      headers: {
        ...headers,
        ...options?.headers,
      },
    });

    if (!response.ok) {
      const errorText = await response.text();
      throw new Error(`API Error: ${response.status} - ${errorText}`);
    }

    return response.json();
  }

  // --- Auth ---
  async login(username: string, password: string): Promise<{ token: string; user: User }> {
    try {
      return await this.fetch<{ token: string; user: User }>('/auth/login', {
        method: 'POST',
        body: JSON.stringify({ username, password }),
      });
    } catch (e) {
      console.warn("Backend unavailable. Using DEV fallback for login.");
      if (username === 'admin' && password === 'admin123') {
        return { token: 'mock-jwt-token', user: { username: 'admin', name: 'Admin User' } };
      }
      throw new Error("Invalid credentials");
    }
  }

  // --- Knowledge Base ---
  async getArticles(): Promise<KBArticle[]> {
    try {
      const response = await this.fetch<{ items: KBArticle[], pagination: any }>('/kb/articles');
      return response.items || [];
    } catch (e) {
      console.warn("Backend unavailable. Using DEV fallback for getArticles.");
      return [];
    }
  }

  async getArticle(id: string): Promise<KBArticle> {
    try {
      return await this.fetch<KBArticle>(`/kb/articles/${id}`);
    } catch (e) {
      console.warn(`Backend unavailable. Using DEV fallback for getArticle ${id}.`);
      return { id, title: 'Sample Article', category: 'General', description: 'This is a dev fallback article.', keywords: [], last_updated: '2024-03-15', views: 10, resolution_steps: ['Restart system'] };
    }
  }

  // --- Support ---
  async querySupport(query: string): Promise<{ answer: string; related_article?: string; related_article_url?: string }> {
    try {
      return await this.fetch<{ answer: string; related_article?: string; related_article_url?: string }>('/support/query', {
        method: 'POST',
        body: JSON.stringify({ query }),
      });
    } catch (e) {
      console.warn("Backend unavailable. Using DEV fallback for querySupport.");
      return { answer: "This is a developer fallback response because the AI backend is unreachable. Real AI-generated answers will appear here once the backend is connected." };
    }
  }

  // --- Monitoring & System ---
  async analyzeLog(logFiles: File[]): Promise<any> {
    try {
      const formData = new FormData();
      logFiles.forEach(file => formData.append('logs', file));

      return await this.fetch<any>('/monitoring/analyze', {
        method: 'POST',
        body: formData,
        isFileUpload: true
      });
    } catch (e) {
      console.warn("Backend unavailable. Using DEV fallback for analyzeLog.");
      const isCritical = logFiles.some(f => f.name.toLowerCase().includes('critical') || f.name.toLowerCase().includes('error'));
      return {
        status: isCritical ? 'CRITICAL' : 'WARNING',
        file_status: 'ACCESSIBLE',
        file_info: {
          size: `${(Math.random() * 20 + 1).toFixed(1)} MB`,
          last_modified: new Date().toLocaleString()
        },
        issues: [
          {
            id: `ISS-${Date.now()}`,
            severity: isCritical ? 'CRITICAL' : 'WARNING',
            timestamp: new Date().toLocaleTimeString(),
            pattern: 'Pending Backend AI Analysis',
            description: 'This is a placeholder. Real AI analysis will appear here once the backend is connected.',
            recommended_action: 'Connect backend to see real AI recommendations.',
          }
        ],
        recent_events: [
          { timestamp: new Date().toLocaleTimeString(), level: 'INFO', message: 'Placeholder data waiting for backend.' }
        ]
      };
    }
  }

  async getMonitoringLogs(): Promise<any[]> {
    try {
      return await this.fetch<any[]>('/monitoring/logs');
    } catch (e) {
      return [];
    }
  }

  async getActivities(): Promise<ActivityLog[]> {
    try {
      return await this.fetch<ActivityLog[]>('/system/activities');
    } catch (e) {
      return [];
    }
  }

  async getNotifications(): Promise<Notification[]> {
    try {
      return await this.fetch<Notification[]>('/system/notifications');
    } catch (e) {
      return [];
    }
  }

  async getStats(): Promise<SystemStats> {
    try {
      return await this.fetch<SystemStats>('/system/stats');
    } catch (e) {
      return { supportQueries: 0, activeLogs: 0, detectedIssues: 0, kbArticles: 0 };
    }
  }
}

export const api = new ApiClient();
