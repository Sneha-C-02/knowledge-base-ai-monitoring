import { useState, useEffect } from "react";
import {
  Play,
  FileText,
  AlertTriangle,
  ShieldCheck,
  AlertCircle,
  Clock,
  Plus,
  X,
  Upload,
  Activity,
  History,
  Zap,
  CheckCircle2,
  Radio,
  ThumbsUp,
  ThumbsDown,
  Search,
  Tags,
  Calendar,
} from "lucide-react";
import { clsx } from "clsx";
import { KeywordSearchSection } from "../components/monitoring/KeywordSearchSection";
import { AutoKbSolution } from "../components/monitoring/AutoKbSolution";
import { NoYearDateTimePicker } from "../components/common/NoYearDateTimePicker";
import { useSystem } from "../context/SystemContext";
import { useMonitoring } from "../context/MonitoringContext";
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from "../components/common/Card";
import { Button } from "../components/common/Button";
import { Badge } from "../components/common/Badge";
import { api } from "../api/client";
import type {
  DashboardResult,
  InstrumentMemoryResponse,
  DashboardBullet,
} from "../types";

function FeedbackForm({ bullet }: { bullet: DashboardBullet }) {
  const [actualAction, setActualAction] = useState("");
  const [helpfulPoints, setHelpfulPoints] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [submitted, setSubmitted] = useState(false);
  const [isCorrect, setIsCorrect] = useState<boolean | null>(null);
  const { addNotification } = useSystem();

  const handleSubmit = async (result: boolean) => {
    setIsSubmitting(true);
    setIsCorrect(result);
    try {
      await api.submitFeedback({
        pattern_number: bullet.pattern_name || "Unknown Pattern",
        ai_recommendation: bullet.text,
        actual_action:
          actualAction ||
          (result ? "Followed AI Recommendation" : "Ignored AI Recommendation"),
        result,
        helpful_points: helpfulPoints,
      });
      setSubmitted(true);
      addNotification({
        type: "success",
        title: "Feedback Submitted",
        message:
          "Thank you! Your feedback will train the AI to be more accurate.",
      });
    } catch (err) {
      console.error(err);
      addNotification({
        type: "error",
        title: "Submission Failed",
        message: "Could not submit feedback.",
      });
      setIsCorrect(null);
    } finally {
      setIsSubmitting(false);
    }
  };

  if (submitted) {
    return (
      <div className="mt-4 p-3 bg-green-50 border border-green-200 rounded-md flex items-center gap-2 text-green-700 text-sm">
        <CheckCircle2 size={16} />
        Feedback saved! This pattern will be used to improve future AI
        diagnostics.
      </div>
    );
  }

  return (
    <div className="mt-4 p-4 bg-slate-50 border border-slate-200 rounded-lg">
      <h4 className="text-sm font-semibold text-slate-700 mb-2">
        Human Verification
      </h4>
      <p className="text-xs text-slate-500 mb-4">
        Help the AI learn. Did this recommendation accurately solve the issue?
      </p>

      <div className="space-y-3">
        <input
          type="text"
          value={actualAction}
          onChange={(e) => setActualAction(e.target.value)}
          placeholder="What action did you actually take? (Optional)"
          className="w-full text-sm border-slate-300 rounded-md focus:ring-primary-500 focus:border-primary-500"
        />
        <input
          type="text"
          value={helpfulPoints}
          onChange={(e) => setHelpfulPoints(e.target.value)}
          placeholder="Any helpful notes for next time? (Optional)"
          className="w-full text-sm border-slate-300 rounded-md focus:ring-primary-500 focus:border-primary-500"
        />

        <div className="flex gap-2 pt-2">
          <Button
            variant="outline"
            size="sm"
            onClick={() => handleSubmit(true)}
            isLoading={isSubmitting && isCorrect === true}
            className="flex-1 text-green-700 border-green-200 hover:bg-green-50"
          >
            <ThumbsUp size={16} className="mr-2" />
            AI was Correct
          </Button>
          <Button
            variant="outline"
            size="sm"
            onClick={() => handleSubmit(false)}
            isLoading={isSubmitting && isCorrect === false}
            className="flex-1 text-red-700 border-red-200 hover:bg-red-50"
          >
            <ThumbsDown size={16} className="mr-2" />
            AI was Incorrect
          </Button>
        </div>
      </div>
    </div>
  );
}

export function MonitoringPage() {
  const [memory, setMemory] = useState<InstrumentMemoryResponse | null>(null);
  const [showMemory, setShowMemory] = useState(false);
  const [isLoadingMemory, setIsLoadingMemory] = useState(false);
  const [isLive, setIsLive] = useState(false);
  const {
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
    clearKeywordResult,
    addKeywords,
    runCompleteAnalysis,
    runKeywordSearch,
  } = useMonitoring();
  const { addNotification } = useSystem();

  const MAX_LOGS = 10;
  // Fallback terms shown until the system has learned real error-related keywords from analyzed logs.
  const DEFAULT_KEYWORD_SUGGESTIONS = [
    "error",
    "exception",
    "timeout",
    "failed",
    "fatal",
    "disconnect",
  ];

  // Merge system-learned, error-related keywords (most frequent first) ahead of the static defaults,
  // without duplicating terms that already appear in the learned list.
  const learnedTerms = learnedKeywordSuggestions.map((s) =>
    s.keyword.toLowerCase(),
  );
  const KEYWORD_SUGGESTIONS = [
    ...learnedKeywordSuggestions.map((s) => s.keyword),
    ...DEFAULT_KEYWORD_SUGGESTIONS.filter(
      (term) => !learnedTerms.includes(term.toLowerCase()),
    ),
  ];

  useEffect(() => {
    refreshKeywordSuggestions(result?.instrument_id);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const clearResultsForNewFiles = () => {
    resetAnalysisResults();
    setMemory(null);
    setShowMemory(false);
  };

  // Setup SSE for live continuous monitoring
  useEffect(() => {
    let eventSource: EventSource | null = null;

    if (result && result.instrument_id && !isMonitoring) {
      setIsLive(true);
      eventSource = api.streamDashboard(result.instrument_id);

      eventSource.onmessage = (event) => {
        try {
          const data: DashboardResult = JSON.parse(event.data);
          setResult(data);

          // Optionally refetch memory history automatically when a new analysis is complete
          if (showMemory && result?.instrument_id) {
            api.getInstrumentMemory(result.instrument_id).then(setMemory);
          }

          // Show toast for incremental updates
          const notifType =
            data.overall_status === "CRITICAL"
              ? ("error" as const)
              : data.overall_status === "WARNING"
                ? ("warning" as const)
                : ("success" as const);

          addNotification({
            type: notifType,
            title: `Live Update: ${data.instrument_name}`,
            message: `New log lines analyzed. Status: ${data.overall_status}`,
          });
        } catch (err) {
          console.error("Failed to parse SSE data", err);
        }
      };

      eventSource.onerror = () => {
        console.error("SSE connection error");
        setIsLive(false);
      };
    }

    return () => {
      if (eventSource) {
        eventSource.close();
        setIsLive(false);
      }
    };
  }, [result?.instrument_id, isMonitoring, showMemory, addNotification]);

  const handleViewMemory = async () => {
    if (showMemory && result?.instrument_id) {
      setShowMemory(false);
    } else if (result?.instrument_id) {
      setIsLoadingMemory(true);
      try {
        const memoryData = await api.getInstrumentMemory(result.instrument_id);
        setMemory(memoryData);
        setShowMemory(true);
      } catch (err) {
        console.error("Failed to fetch instrument memory:", err);
      } finally {
        setIsLoadingMemory(false);
      }
    }
  };

  const getAnalysisStatusBadge = (result: DashboardResult) => {
    if (!result.analysis_status) return null;

    let label = "AI Analysis: Unknown";
    let colorClass = "bg-gray-100 text-gray-800";

    switch (result.analysis_status) {
      case "FULL_AI_ANALYSIS":
        label = "AI Analysis: Complete";
        colorClass = "bg-green-100 text-green-800 border border-green-200";
        break;
      case "PARTIAL_AI_ANALYSIS":
        label = `AI Analysis: Partial (${result.fallback_chunks || 0}/${result.total_chunks || 0} fallback)`;
        colorClass = "bg-yellow-100 text-yellow-800 border border-yellow-200";
        break;
      case "DETERMINISTIC_FALLBACK":
        label = "AI Analysis: Fallback";
        colorClass = "bg-orange-100 text-orange-800 border border-orange-200";
        break;
      case "AI_ANALYSIS_FAILED":
        label = "AI Analysis: Failed";
        colorClass = "bg-red-100 text-red-800 border border-red-200";
        break;
    }

    return (
      <span
        className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ml-3 ${colorClass}`}
      >
        {label}
      </span>
    );
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case "CRITICAL":
        return "text-red-700 bg-red-50 border-red-200";
      case "WARNING":
        return "text-amber-700 bg-amber-50 border-amber-200";
      default:
        return "text-green-700 bg-green-50 border-green-200";
    }
  };

  const getStatusIcon = (status: string) => {
    switch (status) {
      case "CRITICAL":
        return <AlertCircle className="text-red-600" size={32} />;
      case "WARNING":
        return <AlertTriangle className="text-amber-600" size={32} />;
      default:
        return <ShieldCheck className="text-green-600" size={32} />;
    }
  };

  const getBulletColor = (severity: string | null) => {
    switch (severity) {
      case "critical":
        return "text-red-700 bg-red-50 border-l-red-500";
      case "warning":
        return "text-amber-700 bg-amber-50 border-l-amber-500";
      default:
        return "text-slate-700 bg-blue-50 border-l-blue-500";
    }
  };

  return (
    <div className="max-w-5xl mx-auto space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold text-slate-800">
          Proactive Log Monitoring
        </h1>
        {result && (
          <Button
            variant="outline"
            onClick={handleViewMemory}
            className="text-sm"
            isLoading={isLoadingMemory}
          >
            <History size={16} className="mr-2" />{" "}
            {showMemory ? "Hide History" : "View Analysis History"}
          </Button>
        )}
      </div>

      {/* Upload Form */}
      <Card>
        <CardContent className="p-6">
          <div className="space-y-5">
            {/* File Upload */}
            <div>
              <label className="block text-sm font-medium text-slate-700 mb-2">
                Upload Machine Log Files (Max {MAX_LOGS})
              </label>

              <div className="space-y-3">
                {logFiles.map((file, index) => (
                  <div key={index} className="flex items-center gap-3">
                    <div className="relative flex-1 flex items-center border border-slate-300 rounded-md bg-white overflow-hidden h-10">
                      <input
                        type="file"
                        id={`file-upload-${index}`}
                        className="sr-only"
                        onChange={(e) => {
                          const selectedFile = e.target.files?.[0] || null;
                          const newFiles = [...logFiles];
                          newFiles[index] = selectedFile;
                          setLogFiles(newFiles);
                          clearResultsForNewFiles();
                        }}
                        disabled={isMonitoring}
                      />
                      <label
                        htmlFor={`file-upload-${index}`}
                        className={`cursor-pointer h-full px-4 flex items-center border-r border-slate-300 font-medium text-sm transition-colors ${
                          isMonitoring
                            ? "bg-slate-50 text-slate-400"
                            : "bg-slate-100 hover:bg-slate-200 text-slate-700"
                        }`}
                      >
                        <Upload size={16} className="mr-2" />
                        Browse
                      </label>
                      <div className="px-3 flex items-center gap-2 text-slate-500 font-mono text-sm truncate flex-1">
                        <FileText
                          size={16}
                          className={
                            file ? "text-primary-500" : "text-slate-300"
                          }
                        />
                        {file ? file.name : "No file selected..."}
                      </div>
                    </div>
                    {logFiles.length > 1 && (
                      <button
                        type="button"
                        className="text-slate-400 hover:text-red-500 shrink-0 p-2 rounded hover:bg-slate-50 transition-colors"
                        onClick={() => {
                          setLogFiles(logFiles.filter((_, i) => i !== index));
                          clearResultsForNewFiles();
                        }}
                        disabled={isMonitoring || isKeywordSearching}
                      >
                        <X size={20} />
                      </button>
                    )}
                  </div>
                ))}
              </div>
            </div>

            <div className="flex items-center justify-between pt-1">
              <Button
                type="button"
                variant="outline"
                onClick={() => {
                  setLogFiles([...logFiles, null]);
                  clearResultsForNewFiles();
                }}
                disabled={
                  isMonitoring ||
                  isKeywordSearching ||
                  logFiles.length >= MAX_LOGS
                }
                className="text-sm"
              >
                <Plus size={16} className="mr-1" /> Add Another File
              </Button>
            </div>

            {/* Date & Time Range Filter */}
            <div className="border-t border-slate-200 pt-5 space-y-3">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2 text-sm font-semibold text-slate-800">
                  <Calendar size={17} className="text-primary-600" />
                  <span>Date &amp; Time Range Filter (Optional)</span>
                </div>
                {(dateFrom || dateTo) && (
                  <button
                    type="button"
                    onClick={() => {
                      setDateFrom("");
                      setDateTo("");
                    }}
                    className="text-xs text-primary-600 hover:text-primary-800 font-medium flex items-center gap-1 cursor-pointer"
                  >
                    <X size={13} /> Clear Date Filter
                  </button>
                )}
              </div>
              <p className="text-xs text-slate-500">
                Filter and analyze only log entries within a specific timestamp window (matching Waters log format without year). Leave empty to analyze all log lines.
              </p>
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <NoYearDateTimePicker
                  label="Start Date / Time (From)"
                  value={dateFrom}
                  onChange={setDateFrom}
                  disabled={isMonitoring || isKeywordSearching}
                  defaultTime="00:00:00"
                />
                <NoYearDateTimePicker
                  label="End Date / Time (To)"
                  value={dateTo}
                  onChange={setDateTo}
                  disabled={isMonitoring || isKeywordSearching}
                  defaultTime="23:59:59"
                />
              </div>
            </div>

            <div className="border-t border-slate-200 pt-5 space-y-3">
              <div className="flex items-center gap-2 text-sm font-semibold text-slate-800">
                <Tags size={17} className="text-primary-600" /> Keyword-focused
                search
              </div>
              <p className="text-xs text-slate-500">
                Only the selected terms are searched. Suggestions marked with a
                count were learned from error/warning lines in previously
                analyzed logs — the rest are generic defaults.
                {isLoadingKeywordSuggestions && " Refreshing suggestions..."}
              </p>
              <div className="flex flex-wrap gap-2">
                {KEYWORD_SUGGESTIONS.map((suggestion) => {
                  const selected = keywords.some(
                    (keyword) =>
                      keyword.toLowerCase() === suggestion.toLowerCase(),
                  );
                  const learned = learnedKeywordSuggestions.find(
                    (item) =>
                      item.keyword.toLowerCase() === suggestion.toLowerCase(),
                  );
                  return (
                    <button
                      key={suggestion}
                      type="button"
                      onClick={() => {
                        setKeywords((current) =>
                          selected
                            ? current.filter(
                                (keyword) =>
                                  keyword.toLowerCase() !==
                                  suggestion.toLowerCase(),
                              )
                            : [...current, suggestion],
                        );
                        clearKeywordResult();
                      }}
                      title={
                        learned
                          ? `Learned from ${learned.occurrence_count} ${learned.severity} occurrence(s) in analyzed logs`
                          : "Generic default suggestion"
                      }
                      className={clsx(
                        "inline-flex items-center gap-1.5 rounded-full border px-3 py-1 text-xs font-medium transition-colors",
                        selected
                          ? "border-primary-500 bg-primary-50 text-primary-700"
                          : learned
                            ? "border-amber-300 bg-amber-50 text-amber-800 hover:bg-amber-100"
                            : "border-slate-300 bg-white text-slate-600 hover:bg-slate-50",
                      )}
                    >
                      {suggestion}
                      {learned && (
                        <span className="rounded-full bg-white/70 px-1.5 text-[10px] font-semibold">
                          {learned.occurrence_count}
                        </span>
                      )}
                    </button>
                  );
                })}
              </div>
              <div className="flex gap-2">
                <input
                  value={keywordInput}
                  onChange={(event) => setKeywordInput(event.target.value)}
                  onKeyDown={(event) => {
                    if (event.key === "Enter") {
                      event.preventDefault();
                      addKeywords(keywordInput);
                    }
                  }}
                  placeholder="Enter keywords or phrases, separated by commas"
                  className="flex-1 rounded-md border border-slate-300 px-3 py-2 text-sm focus:border-primary-500 focus:ring-primary-500"
                  disabled={isKeywordSearching}
                />
                <Button
                  type="button"
                  variant="outline"
                  onClick={() => addKeywords(keywordInput)}
                  disabled={!keywordInput.trim() || isKeywordSearching}
                >
                  Add
                </Button>
              </div>
              {keywords.length > 0 && (
                <div className="flex flex-wrap gap-2">
                  {keywords.map((keyword) => (
                    <span
                      key={keyword.toLowerCase()}
                      className="inline-flex items-center gap-1 rounded bg-primary-50 px-2 py-1 text-xs text-primary-800"
                    >
                      {keyword}
                      <button
                        type="button"
                        aria-label={`Remove ${keyword}`}
                        onClick={() => {
                          setKeywords((current) =>
                            current.filter((item) => item !== keyword),
                          );
                          clearKeywordResult();
                        }}
                      >
                        <X size={13} />
                      </button>
                    </span>
                  ))}
                </div>
              )}
              <Button
                type="button"
                onClick={runKeywordSearch}
                isLoading={isKeywordSearching}
                disabled={isMonitoring}
              >
                <Search size={17} className="mr-2" /> Search selected keywords
              </Button>
              {keywordError && (
                <p className="text-red-500 text-sm">{keywordError}</p>
              )}
            </div>

            <div className="border-t border-slate-200 pt-5 flex flex-col gap-3 sm:flex-row sm:items-end sm:justify-between">
              <div>
                <p className="text-sm font-semibold text-slate-800">
                  Complete file analysis
                </p>
                <div className="mt-2 flex gap-4 text-sm text-slate-600">
                  <label className="flex items-center gap-1.5">
                    <input
                      type="radio"
                      checked={analysisMode === "exhaustive"}
                      onChange={() => setAnalysisMode("exhaustive")}
                    />{" "}
                    Exhaustive (all lines)
                  </label>
                  <label className="flex items-center gap-1.5">
                    <input
                      type="radio"
                      checked={analysisMode === "fast"}
                      onChange={() => setAnalysisMode("fast")}
                    />{" "}
                    Fast sampled
                  </label>
                </div>
              </div>
              <Button
                type="button"
                onClick={runCompleteAnalysis}
                isLoading={isMonitoring}
                disabled={isKeywordSearching}
              >
                <Play size={18} className="mr-2" /> Run Complete Analysis
              </Button>
            </div>
          </div>
          {error && <p className="text-red-500 text-sm mt-4">{error}</p>}
        </CardContent>
      </Card>

      {/* ===== DEDICATED KEYWORD SEARCH RESULTS SECTION ===== */}
      {keywordResult && (
        <KeywordSearchSection
          keywordResult={keywordResult}
          onClear={clearKeywordResult}
        />
      )}

      {/* ===== COMPLETE FILE ANALYSIS DASHBOARD SECTION ===== */}
      {result && (
        <div className="space-y-6 min-w-0 animate-in fade-in duration-500">
          {/* Overall Status Banner */}
          <Card
            className={`border-2 ${getStatusColor(result.overall_status)}`}
          >
                <CardContent className="p-6">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-4">
                      {getStatusIcon(result.overall_status)}
                      <div>
                        <div className="flex items-center gap-2">
                          <h2 className="text-xl font-bold">
                            {result.instrument_name}
                          </h2>
                          {isLive && (
                            <span className="flex items-center text-xs font-medium text-red-600 bg-red-100 px-2 py-0.5 rounded-full animate-pulse">
                              <Radio size={12} className="mr-1" /> LIVE
                            </span>
                          )}
                          {getAnalysisStatusBadge(result)}
                        </div>
                        <p className="text-sm opacity-75 flex flex-wrap items-center gap-2 mt-0.5">
                          <span>
                            {result.files_analyzed} file(s) monitored • AI
                            continuous diagnostics
                          </span>
                          {result.was_log_reduced &&
                            result.analyzed_line_count &&
                            result.original_line_count && (
                              <span className="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-normal bg-slate-200/80 text-slate-800 border border-slate-300/60">
                                Analyzed{" "}
                                {result.analyzed_line_count.toLocaleString()} of{" "}
                                {result.original_line_count.toLocaleString()}{" "}
                                lines (diagnostic focus)
                              </span>
                            )}
                        </p>
                      </div>
                    </div>
                    <Badge
                      variant={
                        result.overall_status === "CRITICAL"
                          ? "error"
                          : result.overall_status === "WARNING"
                            ? "warning"
                            : "success"
                      }
                    >
                      {result.overall_status}
                    </Badge>
                  </div>
                </CardContent>
              </Card>

              {/* Stat Cards Grid */}
              <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
                <Card>
                  <CardContent className="p-5 text-center">
                    <div className="w-10 h-10 rounded-lg flex items-center justify-center bg-red-100 text-red-600 mx-auto mb-2">
                      <Zap size={22} />
                    </div>
                    <p className="text-3xl font-bold text-red-700">
                      {result.critical_incidents}
                    </p>
                    <p className="text-xs font-medium text-slate-500 mt-1 uppercase tracking-wider">
                      Critical Incidents
                    </p>
                  </CardContent>
                </Card>

                <Card>
                  <CardContent className="p-5 text-center">
                    <div className="w-10 h-10 rounded-lg flex items-center justify-center bg-amber-100 text-amber-600 mx-auto mb-2">
                      <AlertTriangle size={22} />
                    </div>
                    <p className="text-3xl font-bold text-amber-700">
                      {result.warnings}
                    </p>
                    <p className="text-xs font-medium text-slate-500 mt-1 uppercase tracking-wider">
                      Warnings
                    </p>
                  </CardContent>
                </Card>

                <Card>
                  <CardContent className="p-5 text-center">
                    <div className="w-10 h-10 rounded-lg flex items-center justify-center bg-orange-100 text-orange-600 mx-auto mb-2">
                      <AlertCircle size={22} />
                    </div>
                    <p className="text-3xl font-bold text-orange-700">
                      {result.errors}
                    </p>
                    <p className="text-xs font-medium text-slate-500 mt-1 uppercase tracking-wider">
                      Errors
                    </p>
                  </CardContent>
                </Card>

                <Card>
                  <CardContent className="p-5 text-center">
                    <div className="w-10 h-10 rounded-lg flex items-center justify-center bg-green-100 text-green-600 mx-auto mb-2">
                      <CheckCircle2 size={22} />
                    </div>
                    <p className="text-3xl font-bold text-green-700">
                      {result.healthy_apps}
                    </p>
                    <p className="text-xs font-medium text-slate-500 mt-1 uppercase tracking-wider">
                      Healthy Apps
                    </p>
                  </CardContent>
                </Card>
              </div>

              {/* AI Daily Summary */}
              <Card>
                <CardHeader>
                  <CardTitle className="text-base flex items-center gap-2">
                    <Activity size={18} className="text-primary-500" />
                    AI Generated Daily Summary
                  </CardTitle>
                </CardHeader>
                <CardContent className="p-0">
                  {result.daily_summary_bullets.length === 0 ? (
                    <div className="p-6 text-center text-slate-500">
                      No findings to report.
                    </div>
                  ) : (
                    <div className="divide-y divide-slate-100">
                      {result.daily_summary_bullets.map((bullet, idx) => (
                        <div
                          key={idx}
                          className={clsx(
                            "px-5 py-4 border-l-4 transition-colors",
                            getBulletColor(bullet.severity),
                          )}
                        >
                          <div className="flex items-start gap-3">
                            <div className="flex-1">
                              <span className="text-sm font-medium leading-relaxed block mb-1">
                                {bullet.pattern_name
                                  ? `[${bullet.pattern_name}] `
                                  : ""}
                                {bullet.text}
                              </span>

                              {/* Confidence Score & Root Causes */}
                              <div className="mt-2 text-xs text-slate-600 space-y-1">
                                {bullet.confidence_score && (
                                  <div className="flex items-center gap-2">
                                    <span className="font-semibold">
                                      AI Confidence:
                                    </span>
                                    <div className="w-24 h-2 bg-slate-200 rounded-full overflow-hidden">
                                      <div
                                        className={`h-full ${bullet.confidence_score > 80 ? "bg-green-500" : bullet.confidence_score > 50 ? "bg-yellow-500" : "bg-red-500"}`}
                                        style={{
                                          width: `${bullet.confidence_score}%`,
                                        }}
                                      />
                                    </div>
                                    <span>{bullet.confidence_score}%</span>
                                  </div>
                                )}
                                {bullet.possible_root_causes &&
                                  bullet.possible_root_causes.length > 0 && (
                                    <div className="mt-1">
                                      <span className="font-semibold">
                                        Possible Root Causes:
                                      </span>
                                      <ul className="list-disc list-inside pl-1 mt-0.5 space-y-0.5">
                                        {bullet.possible_root_causes.map(
                                          (cause, cidx) => (
                                            <li key={cidx}>{cause}</li>
                                          ),
                                        )}
                                      </ul>
                                    </div>
                                  )}
                              </div>

                              {/* Feedback Verification Form */}
                              <FeedbackForm bullet={bullet} />
                            </div>

                            {bullet.severity && (
                              <Badge
                                variant={
                                  bullet.severity === "critical"
                                    ? "error"
                                    : bullet.severity === "warning"
                                      ? "warning"
                                      : "info"
                                }
                                className="shrink-0 text-xs"
                              >
                                {bullet.severity.toUpperCase()}
                              </Badge>
                            )}
                          </div>
                        </div>
                      ))}
                    </div>
                  )}
                </CardContent>
              </Card>

              <Card>
                <CardHeader>
                  <div className="flex items-center justify-between gap-3">
                    <CardTitle className="text-base flex items-center gap-2">
                      <FileText size={18} className="text-primary-500" />{" "}
                      Complete file findings
                    </CardTitle>
                    <Badge variant="default">
                      {result.coverage_mode === "fast"
                        ? "FAST SAMPLED"
                        : "EXHAUSTIVE"}
                    </Badge>
                  </div>
                  <p className="text-xs text-slate-500 mt-1">
                    {result.analyzed_line_count?.toLocaleString() ?? 0} of{" "}
                    {result.original_line_count?.toLocaleString() ?? 0} lines
                    analyzed
                  </p>
                </CardHeader>
                <CardContent className="p-0">
                  {!result.complete_findings?.length ? (
                    <p className="p-6 text-center text-slate-500">
                      No error, warning, or critical lines were detected.
                    </p>
                  ) : (
                    <div className="divide-y divide-slate-100 max-h-[38rem] overflow-y-auto">
                      {result.complete_findings.map((finding, index) => (
                        <div
                          key={`${finding.filename}-${finding.line_number}-${index}`}
                          className={clsx(
                            "border-l-4 px-4 py-3 space-y-2",
                            finding.severity === "critical"
                              ? "border-l-red-600 bg-red-50/70"
                              : finding.severity === "error"
                                ? "border-l-orange-500 bg-orange-50/70"
                                : "border-l-amber-500 bg-amber-50/70",
                          )}
                        >
                          <div className="flex items-center justify-between gap-2">
                            <span className="text-xs font-semibold text-slate-700">
                              {finding.filename} · line {finding.line_number}
                            </span>
                            <Badge
                              variant={
                                finding.severity === "critical" ||
                                finding.severity === "error"
                                  ? "error"
                                  : "warning"
                              }
                            >
                              {finding.severity.toUpperCase()}
                            </Badge>
                          </div>
                          <pre className="whitespace-pre-wrap break-words font-mono text-xs text-slate-700 bg-white/80 p-2 rounded border border-slate-200/60">
                            {finding.snippet}
                          </pre>
                          <p className="text-xs text-slate-600">
                            {finding.explanation} ({finding.detected_by})
                          </p>

                          {/* Automatic Knowledge Base Article Resolution */}
                          <AutoKbSolution
                            initialArticle={finding.kb_article}
                            searchQuery={finding.explanation}
                            candidateQueries={[
                              finding.explanation,
                              finding.snippet,
                            ]}
                            isError={
                              finding.severity === "error" ||
                              finding.severity === "critical"
                            }
                            compact={true}
                          />
                        </div>
                      ))}
                    </div>
                  )}
                </CardContent>
              </Card>
            </div>
          )}

      {/* ===== INSTRUMENT MEMORY / HISTORY ===== */}
      {showMemory && memory && (
        <Card className="animate-in fade-in duration-500">
          <CardHeader>
            <div className="flex items-center justify-between">
              <CardTitle className="text-base flex items-center gap-2">
                <History size={18} className="text-primary-500" />
                Analysis History — {memory.instrument_name}
              </CardTitle>
              <Badge variant="default">{memory.total_analyses} analyses</Badge>
            </div>
          </CardHeader>
          <CardContent className="p-0">
            {memory.history.length === 0 ? (
              <div className="p-6 text-center text-slate-500">
                No analysis history found.
              </div>
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full text-sm text-left">
                  <thead className="bg-slate-50 text-slate-500 font-medium border-b border-slate-100">
                    <tr>
                      <th className="px-4 py-2">Timestamp</th>
                      <th className="px-4 py-2">File</th>
                      <th className="px-4 py-2 text-center">Critical</th>
                      <th className="px-4 py-2 text-center">Warnings</th>
                      <th className="px-4 py-2 text-center">Errors</th>
                      <th className="px-4 py-2 text-center">Healthy</th>
                      <th className="px-4 py-2">Summary</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-100">
                    {memory.history.map((entry) => (
                      <tr key={entry.id} className="hover:bg-slate-50">
                        <td className="px-4 py-2 text-slate-500 whitespace-nowrap font-mono text-xs">
                          <Clock size={12} className="inline mr-1" />
                          {new Date(entry.analysis_timestamp).toLocaleString()}
                        </td>
                        <td className="px-4 py-2 font-mono text-xs">
                          {entry.log_filename}
                        </td>
                        <td className="px-4 py-2 text-center">
                          <span
                            className={clsx(
                              "font-bold",
                              entry.critical_incidents > 0
                                ? "text-red-600"
                                : "text-slate-400",
                            )}
                          >
                            {entry.critical_incidents}
                          </span>
                        </td>
                        <td className="px-4 py-2 text-center">
                          <span
                            className={clsx(
                              "font-bold",
                              entry.warnings > 0
                                ? "text-amber-600"
                                : "text-slate-400",
                            )}
                          >
                            {entry.warnings}
                          </span>
                        </td>
                        <td className="px-4 py-2 text-center">
                          <span
                            className={clsx(
                              "font-bold",
                              entry.errors > 0
                                ? "text-orange-600"
                                : "text-slate-400",
                            )}
                          >
                            {entry.errors}
                          </span>
                        </td>
                        <td className="px-4 py-2 text-center">
                          <span className="font-bold text-green-600">
                            {entry.healthy_apps}
                          </span>
                        </td>
                        <td className="px-4 py-2 text-slate-600 text-xs max-w-xs truncate">
                          {entry.ai_summary}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </CardContent>
        </Card>
      )}
    </div>
  );
}
