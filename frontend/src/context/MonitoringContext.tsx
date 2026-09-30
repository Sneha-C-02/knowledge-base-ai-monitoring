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
export type MonitoringSessionStatus = "IDLE" | "ANALYZING" | "MONITORING" | "PAUSED";
export type MonitoredFileStatus = "READY" | "ANALYZING" | "MONITORING" | "PAUSED";

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
  activeRunningMode: AnalysisMode | null;
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
  sessionStatus: MonitoringSessionStatus;
  fileStatuses: Record<string, MonitoredFileStatus>;
  startContinuousMonitoring: (instrumentId?: number) => void;
  stopContinuousMonitoring: () => void;
  pauseContinuousMonitoring: () => Promise<void>;
  resumeContinuousMonitoring: (instrumentId?: number) => Promise<void>;
  appendLogLines: (filename: string, lines: string) => Promise<void>;
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
  runCompleteAnalysis: (mode?: AnalysisMode) => Promise<void>;
  runFastAnalysis: () => Promise<void>;
  runExhaustiveAnalysis: () => Promise<void>;
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
  const [activeRunningMode, setActiveRunningMode] = useState<AnalysisMode | null>(null);
  const [dateFrom, setDateFrom] = useState("");
  const [dateTo, setDateTo] = useState("");
  const [isMonitoring, setIsMonitoring] = useState(false);
  const [isKeywordSearching, setIsKeywordSearching] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [keywordError, setKeywordError] = useState<string | null>(null);

  // Continuous monitoring and memory state preserved across routes
  const [isLive, setIsLive] = useState(false);
  const [isContinuousMonitoringActive, setIsContinuousMonitoringActive] = useState(false);
  const [sessionStatus, setSessionStatus] = useState<MonitoringSessionStatus>("IDLE");
  const [fileStatuses, setFileStatuses] = useState<Record<string, MonitoredFileStatus>>({});
  const [memory, setMemory] = useState<InstrumentMemoryResponse | null>(null);
  const [showMemory, setShowMemory] = useState(false);
  const [isLoadingMemory, setIsLoadingMemory] = useState(false);
  const eventSourceRef = useRef<EventSource | null>(null);

  const { addActivity, addNotification, updateStats, stats } = useSystem();

  const validFiles = useCallback(() =>
    logFiles.filter((file): file is File => file !== null), [logFiles]);

  // Keep fileStatuses synchronized with loaded files
  useEffect(() => {
    const files = logFiles.filter((file): file is File => file !== null);
    setFileStatuses((prev) => {
      const next: Record<string, MonitoredFileStatus> = {};
      files.forEach((f) => {
        next[f.name] = prev[f.name] || "READY";
      });
      return next;
    });
    if (files.length === 0) {
      setSessionStatus("IDLE");
    }
  }, [logFiles]);

  const stopContinuousMonitoring = useCallback(() => {
    if (eventSourceRef.current) {
      eventSourceRef.current.close();
      eventSourceRef.current = null;
    }
    setIsLive(false);
    setIsContinuousMonitoringActive(false);
    setSessionStatus((prev) => (prev === "MONITORING" ? "PAUSED" : prev));
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
      setSessionStatus("MONITORING");
      setFileStatuses((prev) => {
        const next = { ...prev };
        Object.keys(next).forEach((k) => {
          next[k] = "MONITORING";
        });
        return next;
      });

      const es = api.streamDashboard(targetId);
      eventSourceRef.current = es;

      es.onopen = () => {
        setIsLive(true);
        setIsContinuousMonitoringActive(true);
        setSessionStatus("MONITORING");
      };

      es.onmessage = (event) => {
        try {
          const raw = JSON.parse(event.data);
          if (raw.type === "MONITORING_ACTIVE" || raw.type === "CONNECTION_ESTABLISHED") {
            setSessionStatus("MONITORING");
            setIsLive(true);
            setIsContinuousMonitoringActive(true);
            return;
          }
          const data: DashboardResult = raw;
          if (!data.instrument_id) return;

          setSessionStatus("MONITORING");
          setFileStatuses((prev) => {
            const next = { ...prev };
            if (data.monitored_files && data.monitored_files.length) {
              data.monitored_files.forEach((f) => {
                next[f.filename] = (f.status as MonitoredFileStatus) || "MONITORING";
              });
            } else {
              validFiles().forEach((f) => {
                next[f.name] = "MONITORING";
              });
            }
            return next;
          });

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

            // Safely merge monitored_files by filename so no monitored file is ever lost
            const prevFilesMap = new Map(
              (prev.monitored_files || []).map((f) => [f.filename, f])
            );
            (data.monitored_files || []).forEach((f) => {
              prevFilesMap.set(f.filename, f);
            });
            const mergedFiles = Array.from(prevFilesMap.values());

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
              analyzed_line_count: Math.max(
                (prev.analyzed_line_count || 0) + (data.analyzed_line_count || 0),
                data.analyzed_line_count || 0
              ),
              original_line_count: Math.max(
                prev.original_line_count || 0,
                data.original_line_count || 0
              ),
              monitoring_status: "MONITORING",
              monitored_files: mergedFiles,
              files_analyzed: Math.max(prev.files_analyzed, mergedFiles.length),
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
            message: `New log lines analyzed. Status: MONITORING (${data.overall_status})`,
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
    [result?.instrument_id, addNotification, validFiles],
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
    setActiveRunningMode(null);
    setSessionStatus("IDLE");
    setFileStatuses((prev) => {
      const next = { ...prev };
      Object.keys(next).forEach((k) => {
        next[k] = "READY";
      });
      return next;
    });
  };

  const pauseContinuousMonitoring = useCallback(async () => {
    if (result?.instrument_id) {
      try {
        await api.pauseMonitoring(result.instrument_id);
      } catch (err) {
        console.error("Failed to pause monitoring on backend:", err);
      }
    }
    stopContinuousMonitoring();
    setSessionStatus("PAUSED");
    setFileStatuses((prev) => {
      const next = { ...prev };
      Object.keys(next).forEach((key) => {
        next[key] = "PAUSED";
      });
      return next;
    });
  }, [result?.instrument_id, stopContinuousMonitoring]);

  const resumeContinuousMonitoring = useCallback(
    async (instrumentId?: number) => {
      const targetId = instrumentId || result?.instrument_id;
      if (targetId) {
        try {
          await api.resumeMonitoring(targetId);
        } catch (err) {
          console.error("Failed to resume monitoring on backend:", err);
        }
      }
      startContinuousMonitoring(targetId);
      setSessionStatus("MONITORING");
      setFileStatuses((prev) => {
        const next = { ...prev };
        Object.keys(next).forEach((key) => {
          next[key] = "MONITORING";
        });
        return next;
      });
    },
    [result?.instrument_id, startContinuousMonitoring],
  );

  const appendLogLines = useCallback(
    async (filename: string, lines: string) => {
      if (!result?.instrument_id) return;
      try {
        await api.appendLogLines(result.instrument_id, filename, lines);
        addNotification({
          type: "info",
          title: "Lines Appended",
          message: `Appended new lines to ${filename}. Continuous monitoring active.`,
        });
      } catch (err) {
        console.error("Failed to append lines:", err);
        addNotification({
          type: "error",
          title: "Append Failed",
          message: "Could not append log lines to the monitored file.",
        });
      }
    },
    [result?.instrument_id, addNotification],
  );

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

  const runCompleteAnalysis = useCallback(
    async (mode?: AnalysisMode) => {
      setError(null);
      const files = validFiles();
      if (!files.length) {
        setError("Please select at least one log file to upload.");
        return;
      }

      const effectiveMode = mode || analysisMode;
      if (mode && mode !== analysisMode) {
        setAnalysisMode(mode);
      }

      setIsMonitoring(true);
      setActiveRunningMode(effectiveMode);
      setSessionStatus("ANALYZING");
      setFileStatuses((prev) => {
        const next = { ...prev };
        files.forEach((f) => {
          next[f.name] = "ANALYZING";
        });
        return next;
      });
      setResult(null);
      addActivity({
        type: "LOG_FILE_SUBMITTED",
        message: `Log analysis started (${effectiveMode} mode)`,
        user: "Current User",
        severity: "INFO",
        metadata: {
          filenames: files.map((file) => file.name).join(", "),
          analysis_mode: effectiveMode,
          date_from: dateFrom || undefined,
          date_to: dateTo || undefined,
        },
      });

      try {
        const dashboardResult = await api.analyzeLogs(
          files,
          effectiveMode,
          dateFrom || undefined,
          dateTo || undefined,
        );
        setResult(dashboardResult);
        setSessionStatus("MONITORING");
        setFileStatuses((prev) => {
          const next = { ...prev };
          files.forEach((f) => {
            next[f.name] = "MONITORING";
          });
          if (dashboardResult.monitored_files) {
            dashboardResult.monitored_files.forEach((f) => {
              next[f.filename] = (f.status as MonitoredFileStatus) || "MONITORING";
            });
          }
          return next;
        });
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
          message: `Analysis Complete • Status: MONITORING | Critical: ${dashboardResult.critical_incidents} | Warnings: ${dashboardResult.warnings} | Errors: ${dashboardResult.errors}`,
        });
        addActivity({
          type: "MONITORING_COMPLETED",
          message: `Dashboard analysis completed — ${dashboardResult.overall_status} (Status: MONITORING)`,
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
            monitoring_status: "MONITORING",
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
        setSessionStatus("IDLE");
        setFileStatuses((prev) => {
          const next = { ...prev };
          files.forEach((f) => {
            next[f.name] = "READY";
          });
          return next;
        });
        addActivity({
          type: "MONITORING_ERROR",
          message: "Log analysis result could not be loaded",
          user: "System",
          severity: "ERROR",
          metadata: { filenames: files.map((file) => file.name).join(", ") },
        });
      } finally {
        setIsMonitoring(false);
        setActiveRunningMode(null);
      }
    },
    [validFiles, analysisMode, dateFrom, dateTo, addActivity, addNotification, updateStats, stats, startContinuousMonitoring, refreshKeywordSuggestions],
  );

  const runFastAnalysis = useCallback(
    () => runCompleteAnalysis("fast"),
    [runCompleteAnalysis],
  );

  const runExhaustiveAnalysis = useCallback(
    () => runCompleteAnalysis("exhaustive"),
    [runCompleteAnalysis],
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
        activeRunningMode,
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
        sessionStatus,
        fileStatuses,
        startContinuousMonitoring,
        stopContinuousMonitoring,
        pauseContinuousMonitoring,
        resumeContinuousMonitoring,
        appendLogLines,
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
        runFastAnalysis,
        runExhaustiveAnalysis,
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
