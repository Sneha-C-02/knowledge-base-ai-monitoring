import type {
  KBArticle,
  User,
  ActivityLog,
  Notification,
  SystemStats,
  PaginatedResponse,
  Instrument,
  DashboardResult,
  InstrumentMemoryResponse,
  KeywordSearchResult,
  KeywordSuggestionsResult,
  IncidentInvestigationResponse,
  KbSolutionResponse,
  SupportFeedbackRequest,
  SupportFeedbackResponse,
  FindingKbSearchRequest,
  FindingKbSearchResponse,
  DiscoverKeywordsResponse,
  AcceptKeywordRequest,
  AcceptedKeyword,
  AcceptedKeywordsListResponse,
  RejectKeywordRequest,
} from "../types";


// Use environment variable for API URL or fallback to localhost
const API_BASE_URL =
  import.meta.env.VITE_API_URL || "http://localhost:3000/api";

class ApiClient {
  private getHeaders() {
    const token = localStorage.getItem("auth_token");
    return {
      "Content-Type": "application/json",
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
    };
  }

  private async fetch<T>(
    endpoint: string,
    options?: RequestInit & { isFileUpload?: boolean },
  ): Promise<T> {
    const headers: Record<string, string> = this.getHeaders();

    // For FormData, the browser must set the Content-Type with the correct boundary
    if (options?.isFileUpload) {
      delete headers["Content-Type"];
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
          localStorage.removeItem("auth_token");
          if (window.location.pathname !== "/login") {
            window.location.href = "/login"; // Force redirect to login
          }
          throw new Error("Session expired. Please log in again.");
        }

        const errorText = await response.text();
        let message = `API Error: ${response.status} - ${errorText}`;
        try {
          const parsed = JSON.parse(errorText);
          if (parsed?.error?.message) {
            message = parsed.error.message;
          } else if (parsed?.detail) {
            message = typeof parsed.detail === "string" ? parsed.detail : JSON.stringify(parsed.detail);
          }
        } catch {
          // ignore json parse error
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
  async login(
    username: string,
    password: string,
  ): Promise<{ token: string; user: User }> {
    return this.fetch<{ token: string; user: User }>("/auth/login", {
      method: "POST",
      body: JSON.stringify({ username, password }),
    });
  }

  // --- Knowledge Base ---
  async getArticles(
    page: number = 1,
    pageSize: number = 100,
    search?: string,
  ): Promise<PaginatedResponse<KBArticle>> {
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
  /** Legacy support query - reactive support requires log files */
  async querySupport(_query: string): Promise<{
    answer: string;
    related_articles?: {
      article_number: string;
      title: string;
      article_url: string;
      snippet: string;
      retrieval_reason: string;
      relevance_score: number;
    }[];
  }> {
    throw new Error(
      "No log files or folder uploaded. Reactive support chat requires at least one log file or folder to investigate.",
    );
  }

  /** Ask a reactive support question to get grounded KB answers - requires log files */
  async submitSupportQuery(_query: string): Promise<{
    answer: string;
    related_articles?: {
      article_number: string;
      title: string;
      article_url: string;
      snippet: string;
      retrieval_reason: string;
      relevance_score: number;
    }[];
  }> {
    throw new Error(
      "No log files or folder uploaded. Reactive support chat requires at least one log file or folder to investigate.",
    );
  }

  /** Reactive support incident investigation over multi-file/folder logs */
  async investigateIncident(
    files: File[],
    problemDescription: string,
  ): Promise<IncidentInvestigationResponse> {
    if (
      !files ||
      files.length === 0 ||
      files.every((f) => !f.name || !f.name.trim() || f.size === 0)
    ) {
      throw new Error(
        "No log files or folder uploaded. At least one non-empty log file or folder is required for incident investigation.",
      );
    }
    const formData = new FormData();
    files.forEach((file) => {
      const path = (file as any).webkitRelativePath || file.name;
      formData.append("logs", file, path);
    });
    formData.append("problem_description", problemDescription);

    return this.fetch<IncidentInvestigationResponse>("/support/investigate", {
      method: "POST",
      body: formData,
      isFileUpload: true,
    });
  }

  /** Search KB articles and generate solution for an investigated incident (Called ONLY on user button click) */
  async searchKbSolution(
    query: string,
    matchedLogFile?: string,
    lineNumber?: number,
    incidentPattern?: string,
    instrumentName?: string,
  ): Promise<KbSolutionResponse> {
    return this.fetch<KbSolutionResponse>("/support/kb-solution", {
      method: "POST",
      body: JSON.stringify({
        query,
        matched_log_file: matchedLogFile,
        line_number: lineNumber,
        incident_pattern: incidentPattern,
        instrument_name: instrumentName,
      }),
    });
  }

  /** Record user verification feedback (correct/wrong) to improve newer searches */
  async submitSupportFeedback(
    feedback: SupportFeedbackRequest,
  ): Promise<SupportFeedbackResponse> {
    return this.fetch<SupportFeedbackResponse>("/support/feedback", {
      method: "POST",
      body: JSON.stringify(feedback),
    });
  }

  // --- Monitoring & Dashboard ---

  /** Legacy endpoint (kept for backward compatibility) */
  async analyzeLog(logFiles: File[]): Promise<any> {
    const formData = new FormData();
    logFiles.forEach((file) => formData.append("logs", file));

    return this.fetch<any>("/monitoring/analyze", {
      method: "POST",
      body: formData,
      isFileUpload: true,
    });
  }

  /** New dashboard analysis with instrument memory */
  async analyzeLogs(
    files: File[],
    analysisMode: "exhaustive" | "fast" = "exhaustive",
    dateFrom?: string,
    dateTo?: string,
  ): Promise<DashboardResult> {
    const formData = new FormData();
    files.forEach((file) => {
      formData.append("logs", file);
    });
    formData.append("analysis_mode", analysisMode);
    if (dateFrom) {
      formData.append("date_from", dateFrom);
    }
    if (dateTo) {
      formData.append("date_to", dateTo);
    }

    return this.fetch<DashboardResult>("/monitoring/dashboard/analyze", {
      method: "POST",
      body: formData,
      isFileUpload: true,
    });
  }

  /** Read-only search for terms explicitly selected by the user. */
  async searchLogKeywords(
    files: File[],
    keywords: string[],
    dateFrom?: string,
    dateTo?: string,
  ): Promise<KeywordSearchResult> {
    const formData = new FormData();
    files.forEach((file) => formData.append("logs", file));
    keywords.forEach((keyword) => formData.append("keywords", keyword));
    if (dateFrom) {
      formData.append("date_from", dateFrom);
    }
    if (dateTo) {
      formData.append("date_to", dateTo);
    }
    return this.fetch<KeywordSearchResult>(
      "/monitoring/dashboard/keyword-search",
      {
        method: "POST",
        body: formData,
        isFileUpload: true,
      },
    );
  }

  /** Error-related keyword suggestions the system has learned from analyzed logs. */
  async getKeywordSuggestions(
    instrumentId?: number,
    limit: number = 10,
  ): Promise<KeywordSuggestionsResult> {
    const params = new URLSearchParams();
    if (instrumentId) params.set("instrument_id", String(instrumentId));
    params.set("limit", String(limit));
    return this.fetch<KeywordSuggestionsResult>(
      `/monitoring/dashboard/keyword-suggestions?${params.toString()}`,
    );
  }

  /** Get list of instruments for the monitoring dropdown */
  async getInstruments(): Promise<Instrument[]> {
    return this.fetch<Instrument[]>("/monitoring/dashboard/instruments");
  }

  /** Get analysis history for an instrument */
  async getInstrumentMemory(
    instrumentId: number,
  ): Promise<InstrumentMemoryResponse> {
    return this.fetch<InstrumentMemoryResponse>(
      `/monitoring/dashboard/memory/${instrumentId}`,
    );
  }

  /** Connect to the live dashboard stream (SSE) */
  streamDashboard(instrumentId: number): EventSource {
    return new EventSource(
      `${API_BASE_URL}/monitoring/dashboard/stream/${instrumentId}`,
    );
  }

  async getMonitoringLogs(): Promise<any[]> {
    return this.fetch<any[]>("/monitoring/logs");
  }

  // --- Feedback ---
  async submitFeedback(data: {
    pattern_number: string;
    ai_recommendation: string;
    actual_action: string;
    result: boolean;
    helpful_points?: string;
  }): Promise<any> {
    return this.fetch<any>("/monitoring/dashboard/feedback", {
      method: "POST",
      body: JSON.stringify(data),
    });
  }

  // --- On-Demand Finding KB Search ---
  async searchFindingKb(
    req: FindingKbSearchRequest,
  ): Promise<FindingKbSearchResponse> {
    return this.fetch<FindingKbSearchResponse>(
      "/monitoring/dashboard/search-finding-kb",
      {
        method: "POST",
        body: JSON.stringify(req),
      },
    );
  }

  // --- Keyword Discovery & Human Acceptance ---
  async discoverFailureKeywords(
    files: File[],
  ): Promise<DiscoverKeywordsResponse> {
    const formData = new FormData();
    files.forEach((file) => {
      formData.append("files", file);
    });

    return this.fetch<DiscoverKeywordsResponse>(
      "/monitoring/dashboard/keywords/discover",
      {
        method: "POST",
        body: formData,
        isFileUpload: true,
      },
    );
  }

  async acceptDiscoveredKeyword(
    req: AcceptKeywordRequest,
  ): Promise<AcceptedKeyword> {
    return this.fetch<AcceptedKeyword>("/monitoring/dashboard/keywords/accept", {
      method: "POST",
      body: JSON.stringify(req),
    });
  }

  async rejectDiscoveredKeyword(
    req: RejectKeywordRequest,
  ): Promise<{ status: string; keyword: string }> {
    return this.fetch<{ status: string; keyword: string }>(
      "/monitoring/dashboard/keywords/reject",
      {
        method: "POST",
        body: JSON.stringify(req),
      },
    );
  }

  async listAcceptedKeywords(
    instrumentId?: number,
  ): Promise<AcceptedKeywordsListResponse> {
    const query = instrumentId ? `?instrument_id=${instrumentId}` : "";
    return this.fetch<AcceptedKeywordsListResponse>(
      `/monitoring/dashboard/keywords/accepted${query}`,
    );
  }

  async deleteAcceptedKeyword(
    keywordId: number,
  ): Promise<{ status: string; id: number }> {
    return this.fetch<{ status: string; id: number }>(
      `/monitoring/dashboard/keywords/accepted/${keywordId}`,
      {
        method: "DELETE",
      },
    );
  }


  // --- System ---
  async getActivities(): Promise<ActivityLog[]> {
    const response =
      await this.fetch<PaginatedResponse<ActivityLog>>("/system/activities");
    return response.items || [];
  }

  async createActivity(
    type: string,
    message: string,
    severity: string = "INFO",
    metadata?: Record<string, any>,
  ): Promise<void> {
    return this.fetch<void>("/system/activities", {
      method: "POST",
      body: JSON.stringify({ type, message, severity, metadata }),
    });
  }

  async getNotifications(): Promise<Notification[]> {
    const response = await this.fetch<PaginatedResponse<Notification>>(
      "/system/notifications",
    );
    return response.items || [];
  }

  async getStats(): Promise<SystemStats> {
    return this.fetch<SystemStats>("/system/stats");
  }
}

export const api = new ApiClient();
