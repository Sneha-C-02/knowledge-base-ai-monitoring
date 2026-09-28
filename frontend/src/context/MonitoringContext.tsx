import { createContext, useCallback, useContext, useEffect, useRef, useState } from "react";
import type { Dispatch, ReactNode, SetStateAction } from "react";
import { api } from "../api/client";
import type {
  DashboardResult,
  InstrumentMemoryResponse,
  KeywordSearchResult,
  KeywordSuggestion,
} from "../types";
import { useSystem } from "./SystemContext";

type AnalysisMode = "exhaustive" | "fast";

interface MonitoringContextType {
  logFiles: (File | null)[];
  setLogFiles: Dispatch<SetStateAction<(File | null)[]>>;
  result: DashboardResult | null;
  setResult: Dispatch<SetStateAction<DashboardResult | null>>;
  keywordResult: KeywordSearchResult | null;
  keywords: string[];
  setKeywords: Dispatch<SetStateAction<string[]>>;
  keywordInput: string;
  setKeywordInput: Dispatch<SetStateAction<string>>;
  learnedKeywordSuggestions: KeywordSuggestion[];
  isLoadingKeywordSuggestions: boolean;
  refreshKeywordSuggestions: (instrumentId?: number) => Promise<void>;
  analysisMode: AnalysisMode;
  setAnalysisMode: Dispatch<SetStateAction<AnalysisMode>>;
  dateFrom: string;
  setDateFrom: Dispatch<SetStateAction<string>>;
  dateTo: string;
  setDateTo: Dispatch<SetStateAction<string>>;
  isMonitoring: boolean;
  isKeywordSearching: boolean;
  error: string | null;
  keywordError: string | null;
  isLive: boolean;
  isContinuousMonitoringActive: boolean;
  startContinuousMonitoring: (instrumentId?: number) => void;
  stopContinuousMonitoring: () => void;
  memory: InstrumentMemoryResponse | null;
  setMemory: Dispatch<SetStateAction<InstrumentMemoryResponse | null>>;
  showMemory: boolean;
  setShowMemory: Dispatch<SetStateAction<boolean>>;
  isLoadingMemory: boolean;
  fetchMemory: (instrumentId?: number) => Promise<void>;
  toggleMemoryView: () => Promise<void>;
  resetAnalysisResults: () => void;
  clearKeywordResult: () => void;
  addKeywords: (value: string) => void;
  runCompleteAnalysis: () => Promise<void>;
  runKeywordSearch: () => Promise<void>;
}


const MonitoringContext = createContext<MonitoringContextType | undefined>(
  undefined,
);

export function MonitoringProvider({ children }: { children: ReactNode }) {
  const [logFiles, setLogFiles] = useState<(File | null)[]>([null]);
  const [result, setResult] = useState<DashboardResult | null>(null);
  const [keywordResult, setKeywordResult] =
    useState<KeywordSearchResult | null>(null);
  const [keywords, setKeywords] = useState<string[]>([]);
  const [keywordInput, setKeywordInput] = useState("");
  const [learnedKeywordSuggestions, setLearnedKeywordSuggestions] = useState<
    KeywordSuggestion[]
  >([]);
  const [isLoadingKeywordSuggestions, setIsLoadingKeywordSuggestions] =
    useState(false);
  const [analysisMode, setAnalysisMode] = useState<AnalysisMode>("exhaustive");
  const [dateFrom, setDateFrom] = useState("");
  const [dateTo, setDateTo] = useState("");
  const [isMonitoring, setIsMonitoring] = useState(false);
  const [isKeywordSearching, setIsKeywordSearching] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [keywordError, setKeywordError] = useState<string | null>(null);

  // Continuous monitoring and memory state preserved across routes
  const [isLive, setIsLive] = useState(false);
  const [isContinuousMonitoringActive, setIsContinuousMonitoringActive] = useState(false);
  const [memory, setMemory] = useState<InstrumentMemoryResponse | null>(null);
  const [showMemory, setShowMemory] = useState(false);
  const [isLoadingMemory, setIsLoadingMemory] = useState(false);
  const eventSourceRef = useRef<EventSource | null>(null);

  const { addActivity, addNotification, updateStats, stats } = useSystem();

  const validFiles = () =>
    logFiles.filter((file): file is File => file !== null);

  const stopContinuousMonitoring = useCallback(() => {
    if (eventSourceRef.current) {
      eventSourceRef.current.close();
      eventSourceRef.current = null;
    }
    setIsLive(false);
    setIsContinuousMonitoringActive(false);
  }, []);

  const startContinuousMonitoring = useCallback(
    (instrumentId?: number) => {
      const targetId = instrumentId || result?.instrument_id;
      if (!targetId) return;

      if (eventSourceRef.current) {
        eventSourceRef.current.close();
        eventSourceRef.current = null;
      }

      setIsContinuousMonitoringActive(true);
      setIsLive(true);
      const es = api.streamDashboard(targetId);
      eventSourceRef.current = es;

      es.onopen = () => {
        setIsLive(true);
      };

      es.onmessage = (event) => {
        try {
          const data: DashboardResult = JSON.parse(event.data);
          setResult((prev) => {
            if (!prev) return data;
            const existingKeys = new Set(
              (prev.complete_findings || []).map(
                (f) => `${f.filename}-${f.line_number}-${f.snippet}`,
              ),
            );
            const newFindings = (data.complete_findings || []).filter(
              (f) =>
                !existingKeys.has(`${f.filename}-${f.line_number}-${f.snippet}`),
            );
            const mergedFindings = [
              ...(prev.complete_findings || []),
              ...newFindings,
            ];

            const existingBullets = new Set(
              (prev.daily_summary_bullets || []).map((b) => b.text),
            );
            const newBullets = (data.daily_summary_bullets || []).filter(
              (b) => !existingBullets.has(b.text),
            );
            const mergedBullets = [
              ...(prev.daily_summary_bullets || []),
              ...newBullets,
            ];

            return {
              ...data,
              critical_incidents:
                prev.critical_incidents + data.critical_incidents,
              warnings: prev.warnings + data.warnings,
              errors: prev.errors + data.errors,
              overall_status:
                data.overall_status === "CRITICAL" ||
                prev.overall_status === "CRITICAL"
                  ? "CRITICAL"
                  : data.overall_status === "WARNING" ||
                      prev.overall_status === "WARNING"
                    ? "WARNING"
                    : "OK",
              complete_findings: mergedFindings,
              daily_summary_bullets: mergedBullets,
              analyzed_line_count:
                (prev.analyzed_line_count || 0) +
                (data.analyzed_line_count || 0),
              original_line_count:
                data.original_line_count || prev.original_line_count,
            };
          });

          const notifType =
            data.overall_status === "CRITICAL"
              ? ("error" as const)
              : data.overall_status === "WARNING"
                ? ("warning" as const)
                : ("success" as const);

          addNotification({
            type: notifType,
            title: `Continuous Monitoring: ${data.instrument_name}`,
            message: `New log lines analyzed. Status: ${data.overall_status}`,
          });
        } catch (err) {
          console.error("Failed to parse live SSE data", err);
        }
      };

      es.onerror = () => {
        if (es.readyState === EventSource.CLOSED) {
          console.error("SSE connection closed");
          setIsLive(false);
        }
      };
    },
    [result?.instrument_id, addNotification],
  );

  const fetchMemory = useCallback(async (instrumentId?: number) => {
    const targetId = instrumentId || result?.instrument_id;
    if (!targetId) return;
    setIsLoadingMemory(true);
    try {
      const data = await api.getInstrumentMemory(targetId);
      setMemory(data);
    } catch (err) {
      console.error("Failed to fetch instrument memory:", err);
    } finally {
      setIsLoadingMemory(false);
    }
  }, [result?.instrument_id]);

  const toggleMemoryView = useCallback(async () => {
    if (showMemory) {
      setShowMemory(false);
    } else {
      await fetchMemory();
      setShowMemory(true);
    }
  }, [showMemory, fetchMemory]);

  useEffect(() => {
    return () => {
      if (eventSourceRef.current) {
        eventSourceRef.current.close();
        eventSourceRef.current = null;
      }
    };
  }, []);

  const resetAnalysisResults = () => {
    stopContinuousMonitoring();
    setResult(null);
    setKeywordResult(null);
    setMemory(null);
    setShowMemory(false);
    setError(null);
    setKeywordError(null);
  };


  const addKeywords = (value: string) => {
    const additions = value
      .split(/[\n,]/)
      .map((term) => term.trim().replace(/\s+/g, " "))
      .filter(Boolean);
    if (additions.length) {
      setKeywords((current) =>
        [...current, ...additions].filter(
          (term, index, all) =>
            all.findIndex(
              (candidate) => candidate.toLowerCase() === term.toLowerCase(),
            ) === index,
        ),
      );
      setKeywordResult(null);
    }
    setKeywordInput("");
  };

  const runCompleteAnalysis = async () => {
    setError(null);
    const files = validFiles();
    if (!files.length) {
      setError("Please select at least one log file to upload.");
      return;
    }

    setIsMonitoring(true);
    setResult(null);
    addActivity({
      type: "LOG_FILE_SUBMITTED",
      message: "Log analysis started",
      user: "Current User",
      severity: "INFO",
      metadata: {
        filenames: files.map((file) => file.name).join(", "),
        analysis_mode: analysisMode,
        date_from: dateFrom || undefined,
        date_to: dateTo || undefined,
      },
    });

    try {
      const dashboardResult = await api.analyzeLogs(
        files,
        analysisMode,
        dateFrom || undefined,
        dateTo || undefined,
      );
      setResult(dashboardResult);
      updateStats({
        activeLogs: stats.activeLogs + files.length,
        detectedIssues:
          stats.detectedIssues +
          dashboardResult.critical_incidents +
          dashboardResult.errors,
      });
      addNotification({
        type:
          dashboardResult.overall_status === "CRITICAL"
            ? "error"
            : dashboardResult.overall_status === "WARNING"
              ? "warning"
              : "success",
        title: `AI Dashboard: ${dashboardResult.instrument_name}`,
        message: `Critical: ${dashboardResult.critical_incidents} | Warnings: ${dashboardResult.warnings} | Errors: ${dashboardResult.errors} | Healthy: ${dashboardResult.healthy_apps}`,
      });
      addActivity({
        type: "MONITORING_COMPLETED",
        message: `Dashboard analysis completed — ${dashboardResult.overall_status}`,
        user: "System",
        severity:
          dashboardResult.overall_status === "CRITICAL"
            ? "CRITICAL"
            : "SUCCESS",
        metadata: {
          filenames: files.map((file) => file.name).join(", "),
          critical: dashboardResult.critical_incidents,
          warnings: dashboardResult.warnings,
          errors: dashboardResult.errors,
        },
      });
      // Automatically initiate live continuous line monitoring for this instrument
      startContinuousMonitoring(dashboardResult.instrument_id);
      // Pick up any newly learned error-related keywords from this run.
      refreshKeywordSuggestions(dashboardResult.instrument_id);
    } catch (requestError) {
      console.error(requestError);
      setError(
        "The analysis result could not be loaded. If you received a completion notification, reopen Log Monitoring or check the API logs.",
      );
      addActivity({
        type: "MONITORING_ERROR",
        message: "Log analysis result could not be loaded",
        user: "System",
        severity: "ERROR",
        metadata: { filenames: files.map((file) => file.name).join(", ") },
      });
    } finally {
      setIsMonitoring(false);
    }
  };

  const refreshKeywordSuggestions = useCallback(
    async (instrumentId?: number) => {
      setIsLoadingKeywordSuggestions(true);
      try {
        const response = await api.getKeywordSuggestions(instrumentId);
        setLearnedKeywordSuggestions(response.suggestions);
      } catch (requestError) {
        console.error(requestError);
      } finally {
        setIsLoadingKeywordSuggestions(false);
      }
    },
    [],
  );

  const runKeywordSearch = async () => {
    setKeywordError(null);
    const files = validFiles();
    if (!files.length) {
      setKeywordError("Please select at least one log file to search.");
      return;
    }
    if (!keywords.length) {
      setKeywordError("Select a suggestion or enter at least one keyword.");
      return;
    }
    setIsKeywordSearching(true);
    setKeywordResult(null);
    try {
      setKeywordResult(
        await api.searchLogKeywords(
          files,
          keywords,
          dateFrom || undefined,
          dateTo || undefined,
        ),
      );
    } catch (requestError) {
      console.error(requestError);
      setKeywordError(
        "Failed to search the selected keywords. Please try again.",
      );
    } finally {
      setIsKeywordSearching(false);
    }
  };

  return (
    <MonitoringContext.Provider
      value={{
        logFiles,
        setLogFiles,
        result,
        setResult,
        keywordResult,
        keywords,
        setKeywords,
        keywordInput,
        setKeywordInput,
        learnedKeywordSuggestions,
        isLoadingKeywordSuggestions,
        refreshKeywordSuggestions,
        analysisMode,
        setAnalysisMode,
        dateFrom,
        setDateFrom,
        dateTo,
        setDateTo,
        isMonitoring,
        isKeywordSearching,
        error,
        keywordError,
        isLive,
        isContinuousMonitoringActive,
        startContinuousMonitoring,
        stopContinuousMonitoring,
        memory,
        setMemory,
        showMemory,
        setShowMemory,
        isLoadingMemory,
        fetchMemory,
        toggleMemoryView,
        resetAnalysisResults,
        clearKeywordResult: () => setKeywordResult(null),
        addKeywords,
        runCompleteAnalysis,
        runKeywordSearch,
      }}
    >
      {children}
    </MonitoringContext.Provider>
  );
}


export function useMonitoring() {
  const context = useContext(MonitoringContext);
  if (!context)
    throw new Error("useMonitoring must be used within MonitoringProvider");
  return context;
}
