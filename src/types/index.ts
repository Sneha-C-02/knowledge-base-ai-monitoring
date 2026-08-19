export interface KBArticle {
  id: string;
  title: string;
  category: string;
  description: string;
  keywords: string[];
  last_updated: string;
  views: number;
  resolution_steps: string[];
}

export interface User {
  username: string;
  name: string;
}

export interface ActivityLog {
  id: string;
  type: 'search' | 'view' | 'alert' | 'system';
  message: string;
  timestamp: string; // Storing as ISO string from API
  user: string;
  metadata?: Record<string, string>;
}

export interface Notification {
  id: string;
  title: string;
  message: string;
  timestamp: string; // ISO string
  read: boolean;
  type: 'info' | 'warning' | 'error' | 'success';
}

export interface SystemStats {
  supportQueries: number;
  activeLogs: number;
  detectedIssues: number;
  kbArticles: number;
}

export interface Pagination {
  current_page: number;
  page_size: number;
  total_items: number;
  total_pages: number;
  has_next_page: boolean;
  has_previous_page: boolean;
  next_page: number | null;
  previous_page: number | null;
}

export interface PaginatedResponse<T> {
  items: T[];
  pagination: Pagination;
}
