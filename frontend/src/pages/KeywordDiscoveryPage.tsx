import { useState, useEffect } from "react";
import {
  Sparkles,
  Upload,
  FileText,
  X,
  Check,
  Ban,
  Trash2,
  CheckCircle2,
  AlertTriangle,
  FolderOpen,
  Search,
  BookOpen,
} from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "../components/common/Card";
import { Button } from "../components/common/Button";
import { Badge } from "../components/common/Badge";
import { useSystem } from "../context/SystemContext";
import { useMonitoring } from "../context/MonitoringContext";
import { api } from "../api/client";
import type {
  DiscoveredKeyword,
  AcceptedKeyword,
} from "../types";

export function KeywordDiscoveryPage() {
  const [activeTab, setActiveTab] = useState<"discover" | "library">("discover");
  const [files, setFiles] = useState<File[]>([]);
  const [isDiscovering, setIsDiscovering] = useState(false);
  const [discoveredKeywords, setDiscoveredKeywords] = useState<DiscoveredKeyword[]>([]);
  const [hasScanned, setHasScanned] = useState(false);
  const [acceptedKeywords, setAcceptedKeywords] = useState<AcceptedKeyword[]>([]);
  const [isLoadingAccepted, setIsLoadingAccepted] = useState(false);
  const [librarySearch, setLibrarySearch] = useState("");
  const [actionInProgress, setActionInProgress] = useState<string | null>(null);

  // Editable candidate names and severities before acceptance
  const [editedKeywords, setEditedKeywords] = useState<Record<string, string>>({});
  const [editedSeverities, setEditedSeverities] = useState<Record<string, string>>({});
  const [editedNotes, setEditedNotes] = useState<Record<string, string>>({});

  const { addNotification, addActivity } = useSystem();
  const { refreshKeywordSuggestions } = useMonitoring();

  const loadAcceptedKeywords = async () => {
    setIsLoadingAccepted(true);
    try {
      const res = await api.listAcceptedKeywords();
      setAcceptedKeywords(res.keywords || []);
    } catch (err) {
      console.error("Failed to load accepted keywords:", err);
    } finally {
      setIsLoadingAccepted(false);
    }
  };

  useEffect(() => {
    loadAcceptedKeywords();
  }, []);

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files) {
      const selected = Array.from(e.target.files).filter((file) => {
        const name = file.name.toLowerCase();
        if (name.startsWith(".")) return false;
        return (
          name.endsWith(".log") ||
          name.endsWith(".txt") ||
          name.endsWith(".csv") ||
          name.endsWith(".out") ||
          !name.includes(".")
        );
      });
      setFiles((prev) => [...prev, ...selected]);
    }
  };

  const handleRemoveFile = (index: number) => {
    setFiles((prev) => prev.filter((_, i) => i !== index));
  };

  const handleDiscover = async () => {
    if (!files.length) {
      addNotification({
        type: "warning",
        title: "No Files Selected",
        message: "Please select or drop at least one log file or folder to analyze.",
      });
      return;
    }

    setIsDiscovering(true);
    try {
      const res = await api.discoverFailureKeywords(files);
      setDiscoveredKeywords(res.keywords || []);
      setHasScanned(true);

      // Initialize edit fields
      const initNames: Record<string, string> = {};
      const initSevs: Record<string, string> = {};
      const initNotes: Record<string, string> = {};
      res.keywords.forEach((k) => {
        initNames[k.keyword] = k.keyword;
        initSevs[k.keyword] = k.severity;
        initNotes[k.keyword] = "";
      });
      setEditedKeywords(initNames);
      setEditedSeverities(initSevs);
      setEditedNotes(initNotes);

      addNotification({
        type: "success",
        title: "Keywords Discovered",
        message: `Found ${res.total_discovered} failure keywords across ${res.files_scanned} files.`,
      });

      addActivity({
        type: "KEYWORD_DISCOVERY_SCAN",
        message: `Scanned ${res.files_scanned} log files and discovered ${res.total_discovered} failure terms`,
        user: "Current User",
        severity: "INFO",
      });
    } catch (err) {
      console.error("Keyword discovery failed:", err);
      addNotification({
        type: "error",
        title: "Discovery Failed",
        message: "Failed to scan files for failure keywords. Check API connection.",
      });
    } finally {
      setIsDiscovering(false);
    }
  };

  const handleAccept = async (candidate: DiscoveredKeyword) => {
    const finalKeyword = (editedKeywords[candidate.keyword] || candidate.keyword).trim();
    const finalSeverity = editedSeverities[candidate.keyword] || candidate.severity;
    const finalNotes = editedNotes[candidate.keyword] || "";

    setActionInProgress(candidate.keyword);
    try {
      const saved = await api.acceptDiscoveredKeyword({
        keyword: finalKeyword,
        severity: finalSeverity,
        failure_indicator: candidate.failure_indicator,
        sample_line: candidate.sample_line,
        notes: finalNotes,
      });

      // Remove from candidate list
      setDiscoveredKeywords((prev) => prev.filter((k) => k.keyword !== candidate.keyword));

      // Add to accepted library
      setAcceptedKeywords((prev) => [saved, ...prev.filter((k) => k.keyword !== saved.keyword)]);

      addNotification({
        type: "success",
        title: "Keyword Accepted",
        message: `"${finalKeyword}" is now active in monitoring suggestions.`,
      });

      refreshKeywordSuggestions();

      addActivity({
        type: "KEYWORD_ACCEPTED",
        message: `Accepted failure keyword "${finalKeyword}" (${finalSeverity})`,
        user: "Current User",
        severity: "SUCCESS",
      });
    } catch (err) {
      console.error("Acceptance failed:", err);
      addNotification({
        type: "error",
        title: "Acceptance Failed",
        message: "Could not save the accepted keyword.",
      });
    } finally {
      setActionInProgress(null);
    }
  };

  const handleReject = async (candidate: DiscoveredKeyword) => {
    setActionInProgress(candidate.keyword);
    try {
      await api.rejectDiscoveredKeyword({
        keyword: candidate.keyword,
        reason: "Rejected by human reviewer",
      });

      // Dismiss candidate
      setDiscoveredKeywords((prev) => prev.filter((k) => k.keyword !== candidate.keyword));

      addNotification({
        type: "info",
        title: "Keyword Dismissed",
        message: `"${candidate.keyword}" will not be suggested.`,
      });
    } catch (err) {
      console.error("Rejection failed:", err);
    } finally {
      setActionInProgress(null);
    }
  };

  const handleDeleteAccepted = async (id: number, keyword: string) => {
    try {
      await api.deleteAcceptedKeyword(id);
      setAcceptedKeywords((prev) => prev.filter((k) => k.id !== id));
      addNotification({
        type: "info",
        title: "Keyword Removed",
        message: `"${keyword}" removed from accepted library.`,
      });
    } catch (err) {
      console.error("Deletion failed:", err);
      addNotification({
        type: "error",
        title: "Delete Failed",
        message: "Could not remove keyword from library.",
      });
    }
  };

  const filteredAccepted = acceptedKeywords.filter((k) =>
    k.keyword.toLowerCase().includes(librarySearch.toLowerCase()) ||
    (k.failure_indicator && k.failure_indicator.toLowerCase().includes(librarySearch.toLowerCase())) ||
    (k.notes && k.notes.toLowerCase().includes(librarySearch.toLowerCase()))
  );

  return (
    <div className="max-w-6xl mx-auto space-y-6">
      {/* Header */}
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 className="text-2xl font-bold text-slate-800 flex items-center gap-2">
            <Sparkles className="text-primary-500" size={24} />
            Failure Keyword Discovery & Learning
          </h1>
          <p className="text-xs text-slate-500 mt-1">
            Automated scanning of instrument logs to discover failure terms with human-in-the-loop review and approval.
          </p>
        </div>

        {/* Tab switcher */}
        <div className="flex rounded-lg bg-slate-100 p-1 border border-slate-200">
          <button
            type="button"
            onClick={() => setActiveTab("discover")}
            className={`flex items-center gap-2 px-3 py-1.5 text-xs font-semibold rounded-md transition-all ${
              activeTab === "discover"
                ? "bg-white text-slate-800 shadow-xs"
                : "text-slate-600 hover:text-slate-900"
            }`}
          >
            <Sparkles size={14} className="text-primary-500" />
            Discover Keywords
            {discoveredKeywords.length > 0 && (
              <span className="rounded-full bg-primary-100 px-1.5 py-0.2 text-[10px] font-bold text-primary-700">
                {discoveredKeywords.length}
              </span>
            )}
          </button>

          <button
            type="button"
            onClick={() => {
              setActiveTab("library");
              loadAcceptedKeywords();
            }}
            className={`flex items-center gap-2 px-3 py-1.5 text-xs font-semibold rounded-md transition-all ${
              activeTab === "library"
                ? "bg-white text-slate-800 shadow-xs"
                : "text-slate-600 hover:text-slate-900"
            }`}
          >
            <CheckCircle2 size={14} className="text-emerald-500" />
            Accepted Library
            <span className="rounded-full bg-emerald-100 px-1.5 py-0.2 text-[10px] font-bold text-emerald-800">
              {acceptedKeywords.length}
            </span>
          </button>
        </div>
      </div>

      {activeTab === "discover" ? (
        <div className="space-y-6">
          {/* Upload Zone */}
          <Card>
            <CardHeader>
              <CardTitle className="text-base flex items-center gap-2">
                <FolderOpen size={18} className="text-primary-500" />
                Select Log File or Instrument Folder
              </CardTitle>
              <p className="text-xs text-slate-500 mt-0.5">
                Upload historical Waters instrument logs (.log, .txt). The system will extract vocabulary that indicates failures or anomalies.
              </p>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                {/* File input */}
                <label className="flex flex-col items-center justify-center p-6 border-2 border-dashed border-slate-300 rounded-lg bg-slate-50/60 hover:bg-slate-100/60 cursor-pointer transition-colors text-center">
                  <Upload size={24} className="text-slate-400 mb-2" />
                  <span className="text-xs font-semibold text-slate-700">
                    Upload Single or Multiple Log Files
                  </span>
                  <span className="text-[11px] text-slate-500 mt-0.5">
                    Click to browse files (.log, .txt)
                  </span>
                  <input
                    type="file"
                    multiple
                    accept=".log,.txt"
                    onChange={handleFileChange}
                    className="sr-only"
                    disabled={isDiscovering}
                  />
                </label>

                {/* Folder input */}
                <label className="flex flex-col items-center justify-center p-6 border-2 border-dashed border-primary-200 rounded-lg bg-primary-50/30 hover:bg-primary-50/60 cursor-pointer transition-colors text-center">
                  <FolderOpen size={24} className="text-primary-500 mb-2" />
                  <span className="text-xs font-semibold text-primary-900">
                    Upload Entire Instrument Folder
                  </span>
                  <span className="text-[11px] text-primary-700 mt-0.5">
                    Select a folder with instrument log archives
                  </span>
                  <input
                    type="file"
                    // @ts-expect-error webkitdirectory is standard in modern browsers
                    webkitdirectory="true"
                    directory=""
                    multiple
                    onChange={handleFileChange}
                    className="sr-only"
                    disabled={isDiscovering}
                  />
                </label>
              </div>

              {/* Selected Files List */}
              {files.length > 0 && (
                <div className="space-y-2 pt-2">
                  <div className="flex items-center justify-between text-xs font-medium text-slate-700">
                    <span>Selected Files ({files.length}):</span>
                    <button
                      type="button"
                      onClick={() => setFiles([])}
                      className="text-red-600 hover:underline"
                    >
                      Clear All
                    </button>
                  </div>
                  <div className="flex flex-wrap gap-2 max-h-36 overflow-y-auto p-2 bg-slate-50 rounded-md border border-slate-200">
                    {files.map((file, i) => (
                      <span
                        key={i}
                        className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded bg-white text-xs text-slate-700 border border-slate-200 font-mono shadow-xs"
                      >
                        <FileText size={12} className="text-slate-400" />
                        <span className="max-w-[180px] truncate">{file.name}</span>
                        <button
                          type="button"
                          onClick={() => handleRemoveFile(i)}
                          className="text-slate-400 hover:text-red-500 ml-1"
                        >
                          <X size={12} />
                        </button>
                      </span>
                    ))}
                  </div>
                </div>
              )}

              <div className="pt-2 flex justify-end">
                <Button
                  onClick={handleDiscover}
                  isLoading={isDiscovering}
                  disabled={files.length === 0}
                  className="px-5 text-sm"
                >
                  <Sparkles size={16} className="mr-2" />
                  Scan & Discover Failure Keywords
                </Button>
              </div>
            </CardContent>
          </Card>

          {/* Discovered Candidates for Human Acceptance */}
          {hasScanned && (
            <Card>
              <CardHeader>
                <div className="flex items-center justify-between">
                  <CardTitle className="text-base flex items-center gap-2">
                    <Sparkles size={18} className="text-primary-500" />
                    Human Review: Discovered Failure Terms ({discoveredKeywords.length})
                  </CardTitle>
                  <span className="text-xs text-slate-500">
                    Review and edit terms before approving into the system
                  </span>
                </div>
              </CardHeader>
              <CardContent className="p-0">
                {discoveredKeywords.length === 0 ? (
                  <div className="p-8 text-center text-slate-500 space-y-2">
                    <CheckCircle2 size={32} className="text-emerald-500 mx-auto" />
                    <p className="font-semibold text-slate-700">All Discovered Keywords Reviewed!</p>
                    <p className="text-xs">
                      No pending failure terms remain. Check the "Accepted Library" tab to view approved keywords.
                    </p>
                  </div>
                ) : (
                  <div className="divide-y divide-slate-100">
                    {discoveredKeywords.map((candidate) => (
                      <div
                        key={candidate.keyword}
                        className="p-5 space-y-3.5 hover:bg-slate-50/50 transition-colors"
                      >
                        {/* Top row: editable keyword input, severity selector, occurrence badge */}
                        <div className="flex flex-wrap items-center justify-between gap-3">
                          <div className="flex items-center gap-2 flex-1 min-w-[280px]">
                            <span className="text-xs font-semibold text-slate-500">Keyword:</span>
                            <input
                              type="text"
                              value={editedKeywords[candidate.keyword] ?? candidate.keyword}
                              onChange={(e) =>
                                setEditedKeywords({
                                  ...editedKeywords,
                                  [candidate.keyword]: e.target.value,
                                })
                              }
                              className="text-sm font-semibold font-mono text-slate-800 border border-slate-300 rounded px-2.5 py-1 focus:ring-primary-500 focus:border-primary-500 bg-white flex-1 max-w-sm"
                            />
                            <select
                              value={editedSeverities[candidate.keyword] ?? candidate.severity}
                              onChange={(e) =>
                                setEditedSeverities({
                                  ...editedSeverities,
                                  [candidate.keyword]: e.target.value,
                                })
                              }
                              className="text-xs border border-slate-300 rounded px-2 py-1 bg-white font-medium text-slate-700 focus:ring-primary-500 focus:border-primary-500"
                            >
                              <option value="critical">Critical</option>
                              <option value="error">Error</option>
                              <option value="warning">Warning</option>
                            </select>
                            <Badge variant="default" className="text-[11px]">
                              {candidate.occurrence_count} occurrences
                            </Badge>
                            <span className="text-[11px] text-emerald-700 bg-emerald-50 px-2 py-0.5 rounded font-medium border border-emerald-200">
                              {Math.round(candidate.confidence_score * 100)}% Confidence
                            </span>
                          </div>

                          {/* Action Buttons: Accept / Reject */}
                          <div className="flex items-center gap-2">
                            <Button
                              size="sm"
                              variant="outline"
                              onClick={() => handleReject(candidate)}
                              disabled={actionInProgress === candidate.keyword}
                              className="text-xs text-slate-600 border-slate-300 hover:bg-slate-100"
                            >
                              <Ban size={14} className="mr-1 text-slate-400" />
                              Reject
                            </Button>
                            <Button
                              size="sm"
                              onClick={() => handleAccept(candidate)}
                              isLoading={actionInProgress === candidate.keyword}
                              className="text-xs bg-emerald-600 hover:bg-emerald-700 text-white"
                            >
                              <Check size={14} className="mr-1" />
                              Accept Keyword
                            </Button>
                          </div>
                        </div>

                        {/* Failure Indicator Explanation */}
                        <div className="rounded-md bg-amber-50/70 border border-amber-200 p-2.5 text-xs text-amber-900 flex items-start gap-2">
                          <AlertTriangle size={15} className="text-amber-600 shrink-0 mt-0.5" />
                          <div className="flex-1">
                            <span className="font-semibold">Failure Indication: </span>
                            <span>{candidate.failure_indicator}</span>
                          </div>
                        </div>

                        {/* Sample Log Line */}
                        <div className="space-y-1">
                          <div className="flex items-center justify-between text-[11px] text-slate-500">
                            <span>Sample Log Excerpt:</span>
                            <span className="font-mono">
                              {candidate.sample_file} · Line #{candidate.sample_line_number}
                            </span>
                          </div>
                          <pre className="text-xs font-mono text-slate-700 bg-slate-100 p-2 rounded border border-slate-200 break-words whitespace-pre-wrap">
                            {candidate.sample_line}
                          </pre>
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </CardContent>
            </Card>
          )}
        </div>
      ) : (
        /* Accepted Keywords Library Tab */
        <Card>
          <CardHeader>
            <div className="flex flex-wrap items-center justify-between gap-3">
              <div>
                <CardTitle className="text-base flex items-center gap-2">
                  <CheckCircle2 size={18} className="text-emerald-500" />
                  Active Accepted Failure Keywords ({acceptedKeywords.length})
                </CardTitle>
                <p className="text-xs text-slate-500 mt-0.5">
                  These keywords have been approved by human reviewers and are actively utilized for log monitoring search suggestions.
                </p>
              </div>

              {/* Search filter */}
              <div className="relative w-64">
                <Search size={14} className="absolute left-3 top-2.5 text-slate-400" />
                <input
                  type="text"
                  placeholder="Filter accepted keywords..."
                  value={librarySearch}
                  onChange={(e) => setLibrarySearch(e.target.value)}
                  className="w-full pl-8 pr-3 py-1.5 text-xs border border-slate-300 rounded-md focus:ring-primary-500 focus:border-primary-500 bg-white"
                />
              </div>
            </div>
          </CardHeader>
          <CardContent className="p-0">
            {isLoadingAccepted ? (
              <div className="p-8 text-center text-xs text-slate-500">
                Loading accepted keywords...
              </div>
            ) : filteredAccepted.length === 0 ? (
              <div className="p-8 text-center text-slate-500 space-y-2">
                <BookOpen size={32} className="text-slate-300 mx-auto" />
                <p className="font-semibold text-slate-700">No Accepted Keywords Found</p>
                <p className="text-xs">
                  {librarySearch
                    ? "No keywords matched your search query."
                    : "No keywords have been accepted yet. Use the 'Discover Keywords' tab to scan log files."}
                </p>
              </div>
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full text-left text-xs">
                  <thead className="bg-slate-50 text-slate-500 border-b border-slate-200">
                    <tr>
                      <th className="px-4 py-2.5 font-semibold">Keyword</th>
                      <th className="px-4 py-2.5 font-semibold">Severity</th>
                      <th className="px-4 py-2.5 font-semibold">Failure Indication</th>
                      <th className="px-4 py-2.5 font-semibold">Sample Line</th>
                      <th className="px-4 py-2.5 font-semibold text-center">Actions</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-100">
                    {filteredAccepted.map((kw) => (
                      <tr key={kw.id} className="hover:bg-slate-50/60">
                        <td className="px-4 py-3 font-semibold font-mono text-slate-900 whitespace-nowrap">
                          {kw.keyword}
                        </td>
                        <td className="px-4 py-3 whitespace-nowrap">
                          <Badge
                            variant={
                              kw.severity.toLowerCase() === "critical"
                                ? "error"
                                : kw.severity.toLowerCase() === "error"
                                  ? "error"
                                  : "warning"
                            }
                          >
                            {kw.severity.toUpperCase()}
                          </Badge>
                        </td>
                        <td className="px-4 py-3 text-slate-600 max-w-xs">
                          {kw.failure_indicator || "Approved instrument problem indicator"}
                        </td>
                        <td className="px-4 py-3 text-slate-500 font-mono text-[11px] max-w-sm truncate">
                          {kw.sample_line || "—"}
                        </td>
                        <td className="px-4 py-3 text-center whitespace-nowrap">
                          <button
                            type="button"
                            onClick={() => handleDeleteAccepted(kw.id, kw.keyword)}
                            title="Delete approved keyword"
                            className="text-slate-400 hover:text-red-600 p-1.5 rounded hover:bg-slate-100 transition-colors"
                          >
                            <Trash2 size={15} />
                          </button>
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
