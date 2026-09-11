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
  severity?: "INFO" | "SUCCESS" | "WARNING" | "ERROR" | "CRITICAL";
  metadata?: Record<string, any>;
}

export interface Notification {
  id: string;
  title: string;
  message: string;
  timestamp: string; // ISO string
  read: boolean;
  type: "info" | "warning" | "error" | "success";
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
  severity: "critical" | "warning" | "info" | null;
  confidence_score?: number;
  possible_root_causes?: string[];
  pattern_name?: string;
}

export interface DashboardFinding {
  filename: string;
  line_number: number;
  snippet: string;
  severity: "critical" | "warning" | "error" | string;
  explanation: string;
  detected_by: string;
}

export interface KeywordArticle {
  id?: string;
  database_id?: number;
  article_number: string;
  title: string;
  url?: string;
  summary?: string;
  relevance_score?: number;
  retrieval_reason?: string;
}

export interface KeywordFinding {
  keyword: string;
  filename: string;
  line_number: number;
  matched_text: string;
  context: string[];
  context_start_line?: number;
  is_error: boolean;
  error_type?: string;
  problem_summary?: string;
  search_query?: string;
  rationale: string;
  confidence_score: number;
  classification_source: "ai" | "deterministic_fallback" | string;
  recommended_action?: string;
  kb_article?: KeywordArticle | null;
}

export interface KeywordSearchResult {
  keywords: string[];
  total_matches: number;
  findings: KeywordFinding[];
}

export interface KeywordSuggestion {
  keyword: string;
  severity: "critical" | "warning" | string;
  occurrence_count: number;
}

export interface KeywordSuggestionsResult {
  suggestions: KeywordSuggestion[];
}

export interface DashboardResult {
  instrument_id: number;
  instrument_name: string;
  critical_incidents: number;
  warnings: number;
  errors: number;
  healthy_apps: number;
  overall_status: "CRITICAL" | "WARNING" | "OK";
  files_analyzed: number;
  daily_summary_bullets: DashboardBullet[];
  analysis_status?: string;
  total_chunks?: number;
  successful_ai_chunks?: number;
  fallback_chunks?: number;
  failed_chunks?: number;
  original_line_count?: number;
  analyzed_line_count?: number;
  was_log_reduced?: boolean;
  coverage_mode?: "exhaustive" | "fast";
  complete_findings?: DashboardFinding[];
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
