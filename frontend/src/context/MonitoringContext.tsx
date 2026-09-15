import { createContext, useCallback, useContext, useState } from "react";
import type { Dispatch, ReactNode, SetStateAction } from "react";
import { api } from "../api/client";
import type {
  DashboardResult,
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
  const { addActivity, addNotification, updateStats, stats } = useSystem();

  const validFiles = () =>
    logFiles.filter((file): file is File => file !== null);

  const resetAnalysisResults = () => {
    setResult(null);
    setKeywordResult(null);
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
