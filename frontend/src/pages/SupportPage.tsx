import React, { useState, useRef } from "react";
import {
  Bot,
  Search,
  BookOpen,
  FolderUp,
  FileText,
  UploadCloud,
  CheckCircle2,
  XCircle,
  AlertTriangle,
  Flame,
  ArrowRight,
  ShieldCheck,
  RotateCcw,
  Sparkles,
  ChevronRight,
  Info,
  Layers,
  ThumbsUp,
  ThumbsDown,
  Clock,
  Check,
} from "lucide-react";
import { Card, CardContent } from "../components/common/Card";
import { Button } from "../components/common/Button";
import { TextArea } from "../components/common/TextArea";
import { Badge } from "../components/common/Badge";
import { useSupport } from "../context/SupportContext";

export function SupportPage() {
  const {
    problemDescription,
    setProblemDescription,
    uploadMode,
    setUploadMode,
    selectedFiles,
    setSelectedFiles,
    folderName,
    setFolderName,
    isInvestigating,
    investigationResult,
    investigationError,
    setInvestigationError,
    isSearchingKb,
    kbSolution,
    kbError,
    feedbackSubmitted,
    isCorrectVote,
    feedbackNotes,
    setFeedbackNotes,
    isSubmittingFeedback,
    hasLogFiles,
    hasEmptyFilesOnly,
    handleInvestigate,
    handleSearchKb,
    handleVote,
    clearSupportState,
  } = useSupport();

  const fileInputRef = useRef<HTMLInputElement>(null);
  const folderInputRef = useRef<HTMLInputElement>(null);
  const [isDragging, setIsDragging] = useState(false);

  // Quick symptom prompt templates
  const quickTemplates = [
    "Instrument lost communication during sample injection",
    "Pump pressure limit exceeded error 1205",
    "Detector baseline drift and noise during acquisition",
    "Autosampler needle position failure or vial missing",
  ];

  // Handle Folder selection
  const handleFolderSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files.length > 0) {
      const filesArray = Array.from(e.target.files);
      setSelectedFiles(filesArray);

      // Extract folder name from first relative path if available
      const firstRelativePath = (filesArray[0] as any).webkitRelativePath;
      if (firstRelativePath) {
        const rootFolder = firstRelativePath.split("/")[0];
        setFolderName(rootFolder);
      } else {
        setFolderName("Selected Folder");
      }
    }
  };

  // Handle Individual Files selection
  const handleFilesSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files.length > 0) {
      setSelectedFiles(Array.from(e.target.files));
      setFolderName(null);
    }
  };

  // Handle Drag and Drop
  const handleDrop = (e: React.DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    setIsDragging(false);

    if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
      const filesArray = Array.from(e.dataTransfer.files);
      setSelectedFiles(filesArray);

      const firstRelativePath = (filesArray[0] as any).webkitRelativePath;
      if (firstRelativePath) {
        const rootFolder = firstRelativePath.split("/")[0];
        setFolderName(rootFolder);
      } else if (filesArray.length > 1) {
        setFolderName("Dropped Bundle");
      } else {
        setFolderName(null);
      }
    }
  };

  const handleClearFiles = () => {
    clearSupportState();
    if (fileInputRef.current) fileInputRef.current.value = "";
    if (folderInputRef.current) folderInputRef.current.value = "";
  };

  return (
    <div className="max-w-5xl mx-auto space-y-8 pb-16">
      {/* Page Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-slate-200 pb-5">
        <div>
          <h1 className="text-2xl font-bold text-slate-900 tracking-tight flex items-center gap-2.5">
            <span className="p-2 bg-indigo-100 text-indigo-700 rounded-lg">
              <Bot size={24} />
            </span>
            Reactive Support & Incident Investigation
          </h1>
          <p className="text-sm text-slate-500 mt-1">
            Upload log files or a full instrument folder. The AI pinpoints the
            issue line, summarizes pre-incident events, detects matching major
            incidents, and checks before/after system changes.
          </p>
        </div>
        <Badge variant="info" className="self-start sm:self-auto py-1 px-3">
          AI Forensic Assistant
        </Badge>
      </div>

      {/* Main Input Card: Folder/File Upload + Chat Description */}
      <Card className="shadow-sm border-slate-200">
        <CardContent className="p-6 space-y-6">
          <form onSubmit={handleInvestigate} className="space-y-6">
            {/* Upload Selector: Folder vs Files */}
            <div>
              <div className="flex items-center justify-between mb-2">
                <label className="text-sm font-semibold text-slate-800 flex items-center gap-2">
                  <UploadCloud size={18} className="text-indigo-600" />
                  Upload Log Files or Instrument Folder
                </label>
                <div className="inline-flex rounded-md shadow-xs bg-slate-100 p-0.5">
                  <button
                    type="button"
                    onClick={() => setUploadMode("folder")}
                    className={`px-3 py-1 text-xs font-medium rounded transition-colors ${
                      uploadMode === "folder"
                        ? "bg-white text-indigo-600 shadow-xs font-semibold"
                        : "text-slate-600 hover:text-slate-900"
                    }`}
                  >
                    Select Folder
                  </button>
                  <button
                    type="button"
                    onClick={() => setUploadMode("files")}
                    className={`px-3 py-1 text-xs font-medium rounded transition-colors ${
                      uploadMode === "files"
                        ? "bg-white text-indigo-600 shadow-xs font-semibold"
                        : "text-slate-600 hover:text-slate-900"
                    }`}
                  >
                    Select Files
                  </button>
                </div>
              </div>

              {/* Upload Dropzone / Button Area */}
              <div
                onDragOver={(e) => {
                  e.preventDefault();
                  setIsDragging(true);
                }}
                onDragLeave={() => setIsDragging(false)}
                onDrop={handleDrop}
                className={`border-2 border-dashed rounded-xl p-5 text-center transition-colors ${
                  isDragging
                    ? "border-indigo-600 bg-indigo-50/70"
                    : "border-slate-300 hover:border-indigo-400 bg-slate-50/70"
                }`}
              >
                {selectedFiles.length === 0 ? (
                  <div className="flex flex-col items-center justify-center space-y-3">
                    {uploadMode === "folder" ? (
                      <>
                        <div className="p-3 bg-indigo-50 text-indigo-600 rounded-full">
                          <FolderUp size={28} />
                        </div>
                        <div>
                          <p className="text-sm font-medium text-slate-700">
                            Select an entire log folder to inspect
                          </p>
                          <p className="text-xs text-slate-500 mt-0.5">
                            All log files inside the folder will be indexed and
                            analyzed
                          </p>
                        </div>
                        <input
                          type="file"
                          ref={folderInputRef}
                          onChange={handleFolderSelect}
                          {...({
                            webkitdirectory: "",
                            directory: "",
                            multiple: true,
                          } as any)}
                          className="hidden"
                          id="folder-upload-input"
                        />
                        <Button
                          type="button"
                          variant="outline"
                          size="sm"
                          onClick={() => folderInputRef.current?.click()}
                          className="mt-1"
                        >
                          <FolderUp size={16} className="mr-1.5" />
                          Browse Folder
                        </Button>
                      </>
                    ) : (
                      <>
                        <div className="p-3 bg-indigo-50 text-indigo-600 rounded-full">
                          <FileText size={28} />
                        </div>
                        <div>
                          <p className="text-sm font-medium text-slate-700">
                            Upload one or multiple log files
                          </p>
                          <p className="text-xs text-slate-500 mt-0.5">
                            Supports .log and .txt files
                          </p>
                        </div>
                        <input
                          type="file"
                          ref={fileInputRef}
                          onChange={handleFilesSelect}
                          multiple
                          accept=".log,.txt"
                          className="hidden"
                          id="files-upload-input"
                        />
                        <Button
                          type="button"
                          variant="outline"
                          size="sm"
                          onClick={() => fileInputRef.current?.click()}
                          className="mt-1"
                        >
                          <FileText size={16} className="mr-1.5" />
                          Browse Files
                        </Button>
                      </>
                    )}
                  </div>
                ) : (
                  <div className="flex flex-col sm:flex-row items-center justify-between gap-3 bg-white p-3.5 rounded-lg border border-slate-200">
                    <div className="flex items-center gap-3 text-left">
                      <div className="p-2 bg-indigo-100 text-indigo-700 rounded-md">
                        {folderName ? (
                          <FolderUp size={22} />
                        ) : (
                          <FileText size={22} />
                        )}
                      </div>
                      <div>
                        <p className="text-sm font-semibold text-slate-800">
                          {folderName ? `Folder: ${folderName}` : "Uploaded Files"}
                        </p>
                        <p className="text-xs text-slate-500">
                          {selectedFiles.length} file
                          {selectedFiles.length > 1 ? "s" : ""} selected (
                          {(
                            selectedFiles.reduce((acc, f) => acc + f.size, 0) /
                            1024
                          ).toFixed(1)}{" "}
                          KB total{hasEmptyFilesOnly ? " — empty files" : ""})
                        </p>
                      </div>
                    </div>
                    <div className="flex items-center gap-2">
                      <Button
                        type="button"
                        variant="outline"
                        size="sm"
                        onClick={handleClearFiles}
                        className="text-red-600 hover:text-red-700 hover:bg-red-50 text-xs"
                      >
                        <RotateCcw size={14} className="mr-1" /> Clear
                      </Button>
                      <Button
                        type="button"
                        variant="outline"
                        size="sm"
                        onClick={() =>
                          uploadMode === "folder"
                            ? folderInputRef.current?.click()
                            : fileInputRef.current?.click()
                        }
                        className="text-xs"
                      >
                        Change
                      </Button>
                    </div>
                  </div>
                )}
              </div>
            </div>

            {/* Chat / Problem Description Input */}
            <div>
              <div className="flex items-center justify-between mb-1.5">
                <label
                  htmlFor="problemDescription"
                  className="block text-sm font-semibold text-slate-800"
                >
                  Describe the problem or symptom observed
                </label>
                {!hasLogFiles && (
                  <span className="text-xs text-amber-700 font-medium bg-amber-50 border border-amber-200 px-2.5 py-0.5 rounded-full flex items-center gap-1">
                    <AlertTriangle size={12} className="text-amber-600" />
                    {hasEmptyFilesOnly
                      ? "Empty log file(s) uploaded"
                      : "Upload required to enable chat"}
                  </span>
                )}
              </div>

              {!hasLogFiles && (
                <div className="mb-3 p-3 bg-amber-50/80 border border-amber-200/90 rounded-lg text-xs text-amber-800 flex items-center gap-2">
                  <AlertTriangle size={16} className="text-amber-600 shrink-0" />
                  <span>
                    <strong>Reactive chat inactive:</strong>{" "}
                    {hasEmptyFilesOnly
                      ? "The selected file(s) are empty (0 bytes). Please upload a valid log file or folder with content."
                      : "Please upload log files or select an instrument folder above to enable AI incident investigation."}
                  </span>
                </div>
              )}

              <TextArea
                id="problemDescription"
                rows={3}
                placeholder={
                  !hasLogFiles
                    ? hasEmptyFilesOnly
                      ? "Uploaded file(s) are empty. Upload non-empty log files to unlock reactive support chat..."
                      : "Upload log files or a folder above to unlock reactive support chat..."
                    : "e.g. Instrument lost communication during sample injection, or Pump pressure limit exceeded Error 1205"
                }
                value={problemDescription}
                onChange={(e) => setProblemDescription(e.target.value)}
                disabled={isInvestigating || !hasLogFiles}
                className={`resize-y ${
                  !hasLogFiles
                    ? "bg-slate-50 cursor-not-allowed opacity-75"
                    : ""
                }`}
              />

              {/* Quick Template Chips */}
              <div className="mt-2.5 flex flex-wrap items-center gap-1.5">
                <span className="text-xs text-slate-600 font-medium mr-1 flex items-center gap-1">
                  <Sparkles size={13} className="text-amber-500" /> Quick
                  queries:
                </span>
                {quickTemplates.map((tpl, i) => (
                  <button
                    key={i}
                    type="button"
                    onClick={() => {
                      if (!hasLogFiles) {
                        setInvestigationError(
                          hasEmptyFilesOnly
                            ? "Please upload non-empty log files before selecting a query template."
                            : "Please upload at least one log file or select a folder before selecting a query template.",
                        );
                        return;
                      }
                      setProblemDescription(tpl);
                    }}
                    disabled={!hasLogFiles || isInvestigating}
                    className={`text-xs px-2.5 py-1 rounded-full border transition-colors ${
                      !hasLogFiles || isInvestigating
                        ? "bg-slate-100 text-slate-400 border-slate-200 cursor-not-allowed"
                        : "bg-slate-100 hover:bg-indigo-50 hover:text-indigo-700 text-slate-600 border-slate-200"
                    }`}
                  >
                    {tpl}
                  </button>
                ))}
              </div>
            </div>

            {/* Actions */}
            <div className="flex justify-end gap-3 pt-2">
              <Button
                type="button"
                variant="secondary"
                onClick={() => setProblemDescription("")}
                disabled={isInvestigating || !problemDescription}
              >
                Clear Query
              </Button>
              <Button
                type="submit"
                isLoading={isInvestigating}
                disabled={!hasLogFiles || !problemDescription.trim()}
                title={
                  !hasLogFiles
                    ? hasEmptyFilesOnly
                      ? "Uploaded log files are empty (0 bytes). Upload valid log files to enable investigation."
                      : "Upload log files or a folder to enable investigation"
                    : "Investigate Incident Logs"
                }
                className="bg-indigo-600 hover:bg-indigo-700 text-white shadow-xs"
              >
                <Search size={18} className="mr-2" />
                Investigate Incident Logs
              </Button>
            </div>
          </form>
        </CardContent>
      </Card>

      {/* Error Alert */}
      {investigationError && (
        <div className="p-4 bg-red-50 border border-red-200 text-red-700 rounded-xl flex items-start gap-3">
          <XCircle size={20} className="shrink-0 mt-0.5" />
          <div className="text-sm">
            <p className="font-semibold">Investigation Failed</p>
            <p>{investigationError}</p>
          </div>
        </div>
      )}

      {/* Investigation Results Section */}
      {investigationResult && (
        <div className="space-y-6 animate-in fade-in slide-in-from-bottom-4 duration-500">
          {/* Main Finding Card */}
          <Card className="border-indigo-200 shadow-md overflow-hidden">
            {/* Finding Header Banner */}
            <div
              className={`p-5 text-white flex flex-col md:flex-row md:items-center justify-between gap-3 ${
                investigationResult.found
                  ? investigationResult.severity === "CRITICAL"
                    ? "bg-gradient-to-r from-red-600 to-rose-700"
                    : "bg-gradient-to-r from-indigo-700 to-blue-800"
                  : "bg-slate-700"
              }`}
            >
              <div>
                <div className="flex items-center gap-2">
                  <span className="p-1.5 bg-white/20 rounded-md">
                    <Bot size={20} />
                  </span>
                  <h2 className="text-lg font-bold">
                    {investigationResult.found
                      ? "Log Incident Pinpointed"
                      : "No Direct Match in Logs"}
                  </h2>
                </div>
                <p className="text-xs text-white/80 mt-1">
                  Scanned {investigationResult.files_scanned} file(s) and{" "}
                  {investigationResult.lines_scanned} lines across uploaded
                  content.
                </p>
              </div>

              {/* Badges: File, Line, Anti-Hallucination Shield */}
              <div className="flex flex-wrap items-center gap-2">
                {investigationResult.found && investigationResult.log_file && (
                  <span className="bg-white/20 backdrop-blur-xs text-white text-xs font-semibold px-3 py-1 rounded-full flex items-center gap-1.5">
                    <FileText size={13} />
                    {investigationResult.log_file}
                  </span>
                )}
                {investigationResult.found && investigationResult.line_number && (
                  <span className="bg-amber-400 text-slate-900 text-xs font-black px-3 py-1 rounded-full">
                    Line #{investigationResult.line_number}
                  </span>
                )}
                <span className="bg-emerald-500/90 text-white text-xs font-semibold px-3 py-1 rounded-full flex items-center gap-1">
                  <ShieldCheck size={13} />
                  {Math.round(investigationResult.confidence_score * 100)}% Grounded
                </span>
              </div>
            </div>

            <CardContent className="p-6 space-y-6">
              {/* Exact Line Snippet */}
              {investigationResult.found && investigationResult.matched_line && (
                <div>
                  <h3 className="text-xs font-bold uppercase tracking-wider text-slate-500 mb-1.5 flex items-center gap-1.5">
                    <CheckCircle2 size={14} className="text-indigo-600" />
                    Exact Incident Line in Log
                  </h3>
                  <div className="bg-slate-900 text-slate-100 rounded-lg p-3.5 font-mono text-xs overflow-x-auto border border-slate-800 flex items-start gap-3">
                    <span className="text-amber-400 font-bold select-none shrink-0 border-r border-slate-700 pr-3">
                      L{investigationResult.line_number}
                    </span>
                    <span className="text-rose-300">
                      {investigationResult.matched_line}
                    </span>
                  </div>
                </div>
              )}

              {/* Pre-Incident Pattern & Precursor Summary */}
              <div className="bg-indigo-50/70 border border-indigo-100 rounded-xl p-5 space-y-3">
                <div className="flex items-center justify-between flex-wrap gap-2">
                  <h3 className="text-sm font-bold text-slate-900 flex items-center gap-2">
                    <Clock size={16} className="text-indigo-600" />
                    Pattern / Incident in Log Before the Mentioned Issue
                  </h3>
                  {investigationResult.pre_incident_pattern && (
                    <Badge variant="info" className="text-xs font-medium">
                      {investigationResult.pre_incident_pattern}
                    </Badge>
                  )}
                </div>
                <p className="text-sm text-slate-700 leading-relaxed font-normal">
                  {investigationResult.pre_incident_summary}
                </p>

                {/* Pre-Incident Sequence Events if any */}
                {investigationResult.pre_incident_events &&
                  investigationResult.pre_incident_events.length > 0 && (
                    <div className="mt-3 pt-3 border-t border-indigo-100/80 space-y-1.5">
                      <p className="text-xs font-semibold text-slate-500 uppercase tracking-wider">
                        Precursor Sequence:
                      </p>
                      <div className="space-y-1">
                        {investigationResult.pre_incident_events.map(
                          (ev, idx) => (
                            <div
                              key={idx}
                              className="text-xs font-mono text-slate-600 flex items-start gap-2 bg-white/70 p-1.5 rounded border border-indigo-100"
                            >
                              <span className="text-indigo-600 font-semibold shrink-0">
                                Line {ev.line}:
                              </span>
                              <span className="truncate">{ev.snippet}</span>
                            </div>
                          ),
                        )}
                      </div>
                    </div>
                  )}
              </div>

              {/* Major System Events (ONLY IF MATCHES THE PROBLEM) */}
              {investigationResult.major_events &&
              investigationResult.major_events.length > 0 ? (
                <div className="bg-rose-50 border border-rose-200 rounded-xl p-5 space-y-3">
                  <div className="flex items-center gap-2 text-rose-800">
                    <Flame size={18} className="text-rose-600" />
                    <h3 className="text-sm font-bold">
                      Major Correlated System Events
                    </h3>
                    <Badge variant="error" className="text-xs">
                      Matched to Problem
                    </Badge>
                  </div>
                  <p className="text-xs text-rose-700">
                    The following critical system outage or event occurred on the
                    system timeline and directly matches the reported problem:
                  </p>
                  <div className="space-y-2">
                    {investigationResult.major_events.map((ev, idx) => (
                      <div
                        key={idx}
                        className="bg-white p-3.5 rounded-lg border border-rose-200 shadow-2xs space-y-1"
                      >
                        <div className="flex items-center justify-between">
                          <span className="font-bold text-xs text-slate-800 flex items-center gap-1.5">
                            <AlertTriangle size={14} className="text-rose-500" />
                            {ev.event_type}
                          </span>
                          <span className="text-xs text-slate-500 font-mono">
                            {ev.timestamp} • Line {ev.line_number} in {ev.log_file}
                          </span>
                        </div>
                        <p className="text-xs text-slate-600 font-mono bg-slate-50 p-1.5 rounded">
                          {ev.description}
                        </p>
                        <p className="text-xs text-indigo-700 font-medium italic pt-0.5">
                          Match reason: {ev.match_reason}
                        </p>
                      </div>
                    ))}
                  </div>
                </div>
              ) : (
                <div className="bg-slate-50 border border-slate-200 rounded-lg p-3 text-xs text-slate-600 flex items-center gap-2">
                  <Info size={14} className="text-slate-400 shrink-0" />
                  <span>
                    No catastrophic system outages on other timelines matched
                    this specific issue.
                  </span>
                </div>
              )}

              {/* Changes in System: After Incident vs Before Incident */}
              {investigationResult.system_changes &&
                investigationResult.system_changes.length > 0 && (
                  <div>
                    <h3 className="text-sm font-bold text-slate-900 mb-2.5 flex items-center gap-2">
                      <Layers size={16} className="text-indigo-600" />
                      Changes in System: After Incident vs. Before Incident
                    </h3>
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                      {investigationResult.system_changes.map(
                        (change, idx) => (
                          <div
                            key={idx}
                            className="bg-white border border-slate-200 rounded-lg p-4 shadow-2xs space-y-2"
                          >
                            <span className="text-xs font-bold text-indigo-700 uppercase tracking-wider block">
                              {change.aspect}
                            </span>
                            <div className="grid grid-cols-2 gap-2 text-xs">
                              <div className="bg-slate-50 p-2 rounded border border-slate-100">
                                <span className="text-slate-400 block font-semibold mb-0.5">
                                  Before Incident
                                </span>
                                <span className="text-slate-700 font-medium">
                                  {change.before_incident}
                                </span>
                              </div>
                              <div className="bg-amber-50/70 p-2 rounded border border-amber-100">
                                <span className="text-amber-700 block font-semibold mb-0.5">
                                  After Incident
                                </span>
                                <span className="text-slate-900 font-medium">
                                  {change.after_incident}
                                </span>
                              </div>
                            </div>
                            <p className="text-xs text-slate-600 italic">
                              {change.change_summary}
                            </p>
                          </div>
                        ),
                      )}
                    </div>
                  </div>
                )}

              {/* Anti-Hallucination Grounding Evidence */}
              {investigationResult.grounding_citations &&
                investigationResult.grounding_citations.length > 0 && (
                  <div className="pt-2 border-t border-slate-100">
                    <details className="group text-xs">
                      <summary className="cursor-pointer font-semibold text-slate-700 hover:text-indigo-600 flex items-center gap-1.5 select-none py-1">
                        <ChevronRight
                          size={14}
                          className="transition-transform group-open:rotate-90 text-slate-400"
                        />
                        <ShieldCheck size={14} className="text-emerald-600" />
                        Verified Grounding Evidence ({investigationResult.grounding_citations.length} literal log excerpts)
                      </summary>
                      <div className="mt-2 space-y-2 pl-4 border-l-2 border-slate-200">
                        {investigationResult.grounding_citations.map(
                          (cit, idx) => (
                            <div
                              key={idx}
                              className="bg-slate-50 p-2 rounded border border-slate-200 space-y-0.5 font-mono"
                            >
                              <div className="flex items-center justify-between text-slate-500">
                                <span className="font-bold text-indigo-600">
                                  {cit.log_file} : L{cit.line_number}
                                </span>
                                <span className="text-slate-400 text-3xs italic">
                                  {cit.relevance_reason}
                                </span>
                              </div>
                              <p className="text-slate-800 truncate">
                                {cit.snippet}
                              </p>
                            </div>
                          ),
                        )}
                      </div>
                    </details>
                  </div>
                )}

              {/* Feedback Section: Correct or Wrong buttons */}
              <div className="bg-slate-50 border border-slate-200 rounded-xl p-4 space-y-3">
                <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
                  <div>
                    <span className="text-xs font-bold text-slate-800 block">
                      Was this AI log analysis accurate?
                    </span>
                    <span className="text-xs text-slate-500">
                      Your verification is saved to the database to improve future
                      searches.
                    </span>
                  </div>

                  {!feedbackSubmitted ? (
                    <div className="flex items-center gap-2">
                      <Button
                        type="button"
                        variant="outline"
                        size="sm"
                        onClick={() => handleVote(true)}
                        isLoading={isSubmittingFeedback && isCorrectVote === true}
                        disabled={isSubmittingFeedback}
                        className="border-emerald-300 hover:bg-emerald-50 text-emerald-700"
                      >
                        <ThumbsUp size={14} className="mr-1.5" /> Correct
                      </Button>
                      <Button
                        type="button"
                        variant="outline"
                        size="sm"
                        onClick={() => handleVote(false)}
                        isLoading={isSubmittingFeedback && isCorrectVote === false}
                        disabled={isSubmittingFeedback}
                        className="border-rose-300 hover:bg-rose-50 text-rose-700"
                      >
                        <ThumbsDown size={14} className="mr-1.5" /> Wrong
                      </Button>
                    </div>
                  ) : (
                    <div className="flex items-center gap-1.5 text-xs text-emerald-700 font-semibold bg-emerald-50 border border-emerald-200 px-3 py-1.5 rounded-lg">
                      <Check size={14} /> Response stored! Newer searches will
                      utilize this feedback.
                    </div>
                  )}
                </div>

                {!feedbackSubmitted && (
                  <div>
                    <input
                      type="text"
                      placeholder="Optional feedback notes / corrections (e.g. 'Correct root line is 24 on pump')"
                      value={feedbackNotes}
                      onChange={(e) => setFeedbackNotes(e.target.value)}
                      disabled={isSubmittingFeedback}
                      className="w-full text-xs px-3 py-1.5 rounded-md border border-slate-200 bg-white placeholder-slate-400 focus:outline-hidden focus:ring-1 focus:ring-indigo-500"
                    />
                  </div>
                )}
              </div>

              {/* DEDICATED BUTTON TO SEARCH KB ARTICLE (Provided ONLY after pressing which KB article is found) */}
              <div className="pt-4 border-t border-slate-200 flex flex-col sm:flex-row sm:items-center justify-between gap-3 bg-gradient-to-r from-indigo-50/50 to-blue-50/50 p-4 rounded-xl border border-indigo-100">
                <div>
                  <h4 className="text-sm font-bold text-slate-900 flex items-center gap-1.5">
                    <BookOpen size={16} className="text-indigo-600" />
                    Ready to troubleshoot with Knowledge Base?
                  </h4>
                  <p className="text-xs text-slate-500">
                    Retrieve official Waters Knowledge Base documentation and
                    grounded solutions for this incident.
                  </p>
                </div>
                <Button
                  type="button"
                  onClick={handleSearchKb}
                  isLoading={isSearchingKb}
                  className="bg-indigo-600 hover:bg-indigo-700 text-white font-semibold shadow-xs shrink-0"
                >
                  <Search size={16} className="mr-2" />
                  Search Knowledge Base Article
                </Button>
              </div>

              {/* KB Solution Results (Displayed ONLY AFTER pressing the button) */}
              {kbError && (
                <div className="p-3 bg-red-50 border border-red-200 text-red-700 text-xs rounded-lg">
                  {kbError}
                </div>
              )}

              {kbSolution && (
                <div className="mt-4 p-5 bg-white border border-indigo-200 rounded-xl shadow-xs space-y-4 animate-in fade-in slide-in-from-bottom-2 duration-300">
                  <div className="flex items-center gap-2 text-indigo-700">
                    <BookOpen size={20} />
                    <h3 className="text-base font-bold">
                      Knowledge Base Grounded Resolution
                    </h3>
                  </div>

                  <p className="text-sm text-slate-700 leading-relaxed bg-slate-50 p-4 rounded-lg border border-slate-100">
                    {kbSolution.answer}
                  </p>

                  {/* Related Articles */}
                  {kbSolution.related_articles &&
                    kbSolution.related_articles.length > 0 && (
                      <div className="space-y-3 pt-2">
                        <span className="text-xs font-bold text-slate-500 uppercase tracking-wider block">
                          Referenced Knowledge Base Articles
                        </span>
                        <div className="grid grid-cols-1 gap-3">
                          {kbSolution.related_articles.map((art, idx) => (
                            <div
                              key={idx}
                              className="bg-slate-50/70 border border-slate-200 rounded-lg p-3.5 flex flex-col sm:flex-row sm:items-center justify-between gap-3 hover:border-indigo-300 transition-colors"
                            >
                              <div className="space-y-1">
                                <div className="flex items-center gap-2">
                                  <span className="font-bold text-xs text-indigo-700">
                                    {art.article_number}
                                  </span>
                                  <span className="font-semibold text-sm text-slate-800">
                                    {art.title}
                                  </span>
                                  <Badge
                                    variant="default"
                                    className="text-3xs"
                                  >
                                    Score: {art.relevance_score.toFixed(2)}
                                  </Badge>
                                </div>
                                <p className="text-xs text-slate-600 line-clamp-2">
                                  {art.snippet}
                                </p>
                              </div>
                              <Button
                                variant="outline"
                                size="sm"
                                onClick={() =>
                                  window.open(
                                    art.article_url ||
                                      `/article/${art.article_number}`,
                                    "_blank",
                                  )
                                }
                                className="shrink-0 text-xs"
                              >
                                View Article <ArrowRight size={13} className="ml-1" />
                              </Button>
                            </div>
                          ))}
                        </div>
                      </div>
                    )}
                </div>
              )}
            </CardContent>
          </Card>
        </div>
      )}
    </div>
  );
}
