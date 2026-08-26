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
  type: string;
  message: string;
  timestamp: string; // Storing as ISO string from API
  user: string;
  severity?: 'INFO' | 'SUCCESS' | 'WARNING' | 'ERROR' | 'CRITICAL';
  metadata?: Record<string, any>;
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

// --- Log Monitoring Dashboard Types ---

export interface Instrument {
  id: number;
  name: string;
}

export interface DashboardBullet {
  text: string;
  severity: 'critical' | 'warning' | 'info' | null;
}

export interface DashboardResult {
  instrument_id: number;
  instrument_name: string;
  critical_incidents: number;
  warnings: number;
  errors: number;
  healthy_apps: number;
  overall_status: 'CRITICAL' | 'WARNING' | 'OK';
  files_analyzed: number;
  daily_summary_bullets: DashboardBullet[];
}

export interface InstrumentMemoryEntry {
  id: number;
  instrument_id: number;
  instrument_name: string;
  analysis_timestamp: string;
  log_filename: string;
  critical_incidents: number;
  warnings: number;
  errors: number;
  healthy_apps: number;
  ai_summary: string;
}

export interface InstrumentMemoryResponse {
  instrument_id: number;
  instrument_name: string;
  total_analyses: number;
  history: InstrumentMemoryEntry[];
}
