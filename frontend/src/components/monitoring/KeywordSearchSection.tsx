import { useState, useMemo } from "react";
import { Link } from "react-router-dom";
import {
  Search,
  AlertCircle,
  CheckCircle2,
  FileText,
  BookOpen,
  Copy,
  Check,
  Filter,
  X,
  Zap,
  Activity,
  ArrowUpRight,
} from "lucide-react";
import { clsx } from "clsx";
import { Button } from "../common/Button";
import type { KeywordSearchResult, KeywordFinding } from "../../types";

interface KeywordSearchSectionProps {
  keywordResult: KeywordSearchResult;
  onClear?: () => void;
}

export function KeywordSearchSection({
  keywordResult,
  onClear,
}: KeywordSearchSectionProps) {
  const [filterType, setFilterType] = useState<"all" | "errors" | "info">("all");
  const [selectedKeyword, setSelectedKeyword] = useState<string>("all");
  const [copiedIndex, setCopiedIndex] = useState<number | null>(null);

  const errorCount = useMemo(
    () => keywordResult.findings.filter((f) => f.is_error).length,
    [keywordResult.findings],
  );

  const infoCount = keywordResult.findings.length - errorCount;

  const filteredFindings = useMemo(() => {
    return keywordResult.findings.filter((finding) => {
      if (filterType === "errors" && !finding.is_error) return false;
      if (filterType === "info" && finding.is_error) return false;
      if (
        selectedKeyword !== "all" &&
        finding.keyword.toLowerCase() !== selectedKeyword.toLowerCase()
      ) {
        return false;
      }
      return true;
    });
  }, [keywordResult.findings, filterType, selectedKeyword]);

  const handleCopyContext = (context: string[], index: number) => {
    navigator.clipboard.writeText(context.join("\n"));
    setCopiedIndex(index);
    setTimeout(() => setCopiedIndex(null), 2000);
  };

  // Helper to render log lines with highlighted keyword and target line
  const renderLogLine = (
    line: string,
    lineNum: number,
    isTargetLine: boolean,
    keyword: string,
    matchedText: string,
  ) => {
    // If target line, highlight the keyword or matched text inside it
    if (isTargetLine) {
      const termToHighlight = matchedText || keyword;
      const regex = new RegExp(`(${termToHighlight.replace(/[.*+?^${}()|[\]\\]/g, "\\$&")})`, "gi");
      const parts = line.split(regex);

      return (
        <div
          key={lineNum}
          className="flex items-start bg-red-950/40 border-l-4 border-red-500 py-1 px-2 -mx-2 rounded-r"
        >
          <span className="w-12 shrink-0 select-none text-red-400 font-mono text-[11px] opacity-80 text-right pr-3">
            {lineNum}
          </span>
          <span className="text-white font-mono text-xs break-all flex-1">
            {parts.map((part, pIdx) =>
              part.toLowerCase() === termToHighlight.toLowerCase() ? (
                <mark
                  key={pIdx}
                  className="bg-amber-400 text-slate-950 font-bold px-1 py-0.5 rounded shadow-xs"
                >
                  {part}
                </mark>
              ) : (
                part
              ),
            )}
          </span>
        </div>
      );
    }

    return (
      <div key={lineNum} className="flex items-start py-0.5 px-2 -mx-2 hover:bg-slate-800/50 rounded">
        <span className="w-12 shrink-0 select-none text-slate-500 font-mono text-[11px] text-right pr-3">
          {lineNum}
        </span>
        <span className="text-slate-300 font-mono text-xs break-all flex-1">
          {line}
        </span>
      </div>
    );
  };

  return (
    <section className="space-y-4 animate-in fade-in duration-300">
      {/* ===== SECTION HEADER & METRICS BAR ===== */}
      <div className="rounded-xl border border-slate-200 bg-white p-5 shadow-xs">
        <div className="flex flex-col gap-4 md:flex-row md:items-center md:justify-between">
          <div className="space-y-1">
            <div className="flex items-center gap-2.5">
              <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-primary-100 text-primary-700">
                <Search size={18} />
              </div>
              <h2 className="text-lg font-bold text-slate-900">
                Keyword Diagnostic Analysis
              </h2>
            </div>
            <p className="text-xs text-slate-500">
              Analyzed surrounding lines for search terms:{" "}
              <span className="font-semibold text-slate-700">
                {keywordResult.keywords.join(", ")}
              </span>
            </p>
          </div>

          <div className="flex flex-wrap items-center gap-2">
            <span className="inline-flex items-center rounded-full bg-slate-100 px-3 py-1 text-xs font-semibold text-slate-700">
              {keywordResult.total_matches} Total Matches
            </span>
            <span className="inline-flex items-center gap-1 rounded-full bg-red-100 px-3 py-1 text-xs font-semibold text-red-700">
              <AlertCircle size={13} />
              {errorCount} {errorCount === 1 ? "Error" : "Errors"}
            </span>
            <span className="inline-flex items-center gap-1 rounded-full bg-emerald-100 px-3 py-1 text-xs font-semibold text-emerald-800">
              <CheckCircle2 size={13} />
              {infoCount} Informational
            </span>
            {onClear && (
              <button
                type="button"
                onClick={onClear}
                className="ml-1 inline-flex items-center gap-1 rounded-md border border-slate-200 bg-slate-50 px-2.5 py-1 text-xs font-medium text-slate-600 hover:bg-slate-100 transition-colors"
                title="Dismiss keyword search results"
              >
                <X size={14} /> Clear
              </button>
            )}
          </div>
        </div>

        {/* Filters & Keyword Chips Toolbar */}
        <div className="mt-4 flex flex-wrap items-center justify-between gap-3 border-t border-slate-100 pt-3.5">
          <div className="flex items-center gap-1.5">
            <span className="text-xs font-medium text-slate-500 flex items-center gap-1 mr-1">
              <Filter size={13} /> Filter:
            </span>
            <button
              type="button"
              onClick={() => setFilterType("all")}
              className={clsx(
                "rounded-md px-2.5 py-1 text-xs font-medium transition-colors",
                filterType === "all"
                  ? "bg-slate-800 text-white shadow-xs"
                  : "bg-slate-100 text-slate-600 hover:bg-slate-200",
              )}
            >
              All ({keywordResult.findings.length})
            </button>
            <button
              type="button"
              onClick={() => setFilterType("errors")}
              className={clsx(
                "rounded-md px-2.5 py-1 text-xs font-medium transition-colors",
                filterType === "errors"
                  ? "bg-red-600 text-white shadow-xs"
                  : "bg-red-50 text-red-700 hover:bg-red-100",
              )}
            >
              Errors Only ({errorCount})
            </button>
            <button
              type="button"
              onClick={() => setFilterType("info")}
              className={clsx(
                "rounded-md px-2.5 py-1 text-xs font-medium transition-colors",
                filterType === "info"
                  ? "bg-emerald-700 text-white shadow-xs"
                  : "bg-emerald-50 text-emerald-700 hover:bg-emerald-100",
              )}
            >
              Informational ({infoCount})
            </button>
          </div>

          {keywordResult.keywords.length > 1 && (
            <div className="flex items-center gap-1.5">
              <span className="text-xs text-slate-400">By Keyword:</span>
              <button
                type="button"
                onClick={() => setSelectedKeyword("all")}
                className={clsx(
                  "rounded-full px-2 py-0.5 text-xs font-medium transition-colors",
                  selectedKeyword === "all"
                    ? "bg-primary-600 text-white"
                    : "bg-slate-100 text-slate-600 hover:bg-slate-200",
                )}
              >
                All
              </button>
              {keywordResult.keywords.map((kw) => (
                <button
                  key={kw}
                  type="button"
                  onClick={() => setSelectedKeyword(kw)}
                  className={clsx(
                    "rounded-full px-2 py-0.5 text-xs font-medium transition-colors",
                    selectedKeyword.toLowerCase() === kw.toLowerCase()
                      ? "bg-primary-600 text-white"
                      : "bg-slate-100 text-slate-600 hover:bg-slate-200",
                  )}
                >
                  "{kw}"
                </button>
              ))}
            </div>
          )}
        </div>
      </div>

      {/* ===== FINDINGS LIST ===== */}
      {filteredFindings.length === 0 ? (
        <div className="rounded-xl border border-dashed border-slate-300 bg-white p-10 text-center text-slate-500">
          <p className="font-medium text-slate-700">No matching occurrences found</p>
          <p className="mt-1 text-xs text-slate-500">
            Try adjusting your filter selection or searching with different keywords.
          </p>
        </div>
      ) : (
        <div className="space-y-4">
          {filteredFindings.map((finding: KeywordFinding, index: number) => {
            const isError = finding.is_error;
            const startLine =
              finding.context_start_line ??
              Math.max(1, finding.line_number - 5);
            const targetLineOffset = finding.line_number - startLine;

            return (
              <div
                key={`${finding.filename}-${finding.line_number}-${finding.keyword}-${index}`}
                className={clsx(
                  "overflow-hidden rounded-xl border bg-white shadow-xs transition-shadow hover:shadow-md",
                  isError ? "border-red-200" : "border-slate-200",
                )}
              >
                {/* 1. CARD TOP BANNER */}
                <div
                  className={clsx(
                    "flex flex-wrap items-center justify-between gap-3 px-5 py-3 border-b",
                    isError
                      ? "bg-red-50/80 border-red-200"
                      : "bg-slate-50 border-slate-200",
                  )}
                >
                  <div className="flex flex-wrap items-center gap-2.5">
                    {/* Status Badge */}
                    <span
                      className={clsx(
                        "inline-flex items-center gap-1.5 rounded-md px-2.5 py-1 text-xs font-bold uppercase tracking-wide",
                        isError
                          ? "bg-red-600 text-white"
                          : "bg-emerald-600 text-white",
                      )}
                    >
                      {isError ? (
                        <>
                          <AlertCircle size={14} /> ERROR DETECTED
                        </>
                      ) : (
                        <>
                          <CheckCircle2 size={14} /> INFORMATIONAL
                        </>
                      )}
                    </span>

                    {/* File & Line Tag */}
                    <span className="inline-flex items-center gap-1 font-mono text-xs font-semibold text-slate-800">
                      <FileText size={14} className="text-slate-500" />
                      {finding.filename} · Line {finding.line_number}
                    </span>

                    {/* Matched Term Tag */}
                    <span className="inline-flex items-center gap-1 rounded bg-white/80 px-2 py-0.5 text-xs text-slate-600 border border-slate-200/80">
                      Keyword:{" "}
                      <span className="font-semibold text-slate-800">
                        "{finding.keyword}"
                      </span>
                    </span>
                  </div>

                  {/* AI Confidence Meter */}
                  <div className="flex items-center gap-2 text-xs">
                    <span className="font-medium text-slate-500">
                      AI Confidence:
                    </span>
                    <div className="flex items-center gap-1.5 font-semibold text-slate-700">
                      <div className="h-2 w-16 overflow-hidden rounded-full bg-slate-200">
                        <div
                          className={clsx(
                            "h-full rounded-full",
                            finding.confidence_score >= 80
                              ? "bg-emerald-500"
                              : finding.confidence_score >= 60
                                ? "bg-amber-500"
                                : "bg-red-500",
                          )}
                          style={{ width: `${finding.confidence_score}%` }}
                        />
                      </div>
                      <span>{finding.confidence_score}%</span>
                    </div>
                  </div>
                </div>

                {/* 2. SPLIT DIAGNOSTIC BODY */}
                <div className="grid grid-cols-1 lg:grid-cols-12 gap-5 p-5">
                  {/* LEFT SIDE: DIAGNOSTIC SUMMARY & KNOWLEDGE BASE SOLUTION (7 cols) */}
                  <div className="lg:col-span-7 space-y-4">
                    {/* A. Problem Summary & Error Identification */}
                    <div className="rounded-lg border border-slate-200 bg-slate-50/50 p-4 space-y-3">
                      <div className="flex items-start gap-2.5">
                        <div
                          className={clsx(
                            "mt-0.5 flex h-6 w-6 shrink-0 items-center justify-center rounded-full",
                            isError
                              ? "bg-red-100 text-red-600"
                              : "bg-emerald-100 text-emerald-700",
                          )}
                        >
                          <Zap size={14} />
                        </div>
                        <div className="space-y-1 flex-1">
                          <h4 className="text-sm font-bold text-slate-900 leading-tight">
                            {finding.error_type ||
                              (isError
                                ? "Detected Log Error"
                                : "Normal Operational Context")}
                          </h4>
                          <p className="text-xs font-normal text-slate-700 leading-relaxed">
                            {finding.problem_summary || finding.rationale}
                          </p>
                        </div>
                      </div>

                      {/* Rationale & Evidence */}
                      {finding.rationale &&
                        finding.problem_summary &&
                        finding.rationale !== finding.problem_summary && (
                          <div className="rounded-md bg-white p-2.5 border border-slate-200/80 text-xs text-slate-600 space-y-0.5">
                            <span className="font-semibold text-slate-700">
                              Diagnostic Evidence:
                            </span>{" "}
                            {finding.rationale}
                          </div>
                        )}

                      {/* Recommended Troubleshooting Action */}
                      {finding.recommended_action && (
                        <div className="rounded-md bg-amber-50/90 border border-amber-200/80 p-2.5 text-xs text-amber-900 space-y-0.5">
                          <span className="font-semibold text-amber-800 flex items-center gap-1">
                            <Activity size={13} /> Recommended Action:
                          </span>
                          <p className="mt-0.5">{finding.recommended_action}</p>
                        </div>
                      )}
                    </div>

                    {/* B. Valid Knowledge Base Article Card */}
                    <div className="rounded-lg border border-indigo-100 bg-gradient-to-br from-indigo-50/70 via-blue-50/50 to-white p-4 shadow-xs">
                      <div className="flex items-center justify-between gap-2 mb-2">
                        <div className="flex items-center gap-2">
                          <div className="flex h-6 w-6 items-center justify-center rounded bg-indigo-600 text-white shadow-xs">
                            <BookOpen size={13} />
                          </div>
                          <span className="text-xs font-bold uppercase tracking-wider text-indigo-900">
                            Knowledge Base Solution
                          </span>
                        </div>
                        {finding.kb_article && (
                          <span className="inline-flex items-center rounded-full bg-indigo-100 px-2 py-0.5 text-[11px] font-semibold text-indigo-800">
                            Article {finding.kb_article.article_number}
                          </span>
                        )}
                      </div>

                      {finding.kb_article ? (
                        <div className="space-y-2 mt-2">
                          <Link
                            to={`/article/${finding.kb_article.article_number}`}
                            className="text-sm font-bold text-indigo-700 hover:text-indigo-900 hover:underline flex items-center gap-1.5 group"
                          >
                            <span>{finding.kb_article.title}</span>
                            <ArrowUpRight
                              size={15}
                              className="text-indigo-500 group-hover:translate-x-0.5 group-hover:-translate-y-0.5 transition-transform"
                            />
                          </Link>

                          {finding.kb_article.summary && (
                            <p className="text-xs text-slate-600 line-clamp-3 leading-relaxed">
                              {finding.kb_article.summary}
                            </p>
                          )}

                          <div className="pt-2 flex items-center justify-between gap-2 border-t border-indigo-100/60">
                            <span className="text-[11px] text-indigo-600 font-medium">
                              {finding.kb_article.relevance_score
                                ? `${Math.round(finding.kb_article.relevance_score * 100)}% Match`
                                : "Relevant Resolution"}
                            </span>

                            <Link
                              to={`/article/${finding.kb_article.article_number}`}
                            >
                              <Button
                                variant="outline"
                                size="sm"
                                className="text-xs text-indigo-700 border-indigo-300 hover:bg-indigo-100 bg-white"
                              >
                                View Knowledge Base Article
                              </Button>
                            </Link>
                          </div>
                        </div>
                      ) : (
                        <div className="space-y-2 mt-1">
                          <p className="text-xs text-slate-600">
                            No direct Waters article in local cache. Search the
                            full Knowledge Base library for this error signature:
                          </p>
                          <div className="flex items-center gap-2 pt-1">
                            <Link
                              to={`/knowledge-base?search=${encodeURIComponent(
                                finding.search_query ||
                                  finding.error_type ||
                                  finding.keyword,
                              )}`}
                            >
                              <Button
                                variant="outline"
                                size="sm"
                                className="text-xs text-indigo-700 border-indigo-300 hover:bg-indigo-100 bg-white"
                              >
                                <Search size={13} className="mr-1.5" />
                                Search KB for "
                                {(finding.error_type || finding.keyword).slice(
                                  0,
                                  28,
                                )}
                                ..."
                              </Button>
                            </Link>
                          </div>
                        </div>
                      )}
                    </div>
                  </div>

                  {/* RIGHT SIDE: SURROUNDING LOG CONTEXT INSPECTOR (5 cols) */}
                  <div className="lg:col-span-5 flex flex-col">
                    <div className="rounded-lg bg-slate-950 border border-slate-800 p-3.5 flex flex-col flex-1 shadow-inner">
                      {/* Terminal Header */}
                      <div className="flex items-center justify-between pb-2 mb-2 border-b border-slate-800 text-xs">
                        <div className="flex items-center gap-2 text-slate-400 font-mono">
                          <span className="inline-block h-2 w-2 rounded-full bg-red-500/80" />
                          <span className="inline-block h-2 w-2 rounded-full bg-amber-500/80" />
                          <span className="inline-block h-2 w-2 rounded-full bg-emerald-500/80" />
                          <span className="text-[11px] text-slate-400 ml-1">
                            Surrounding Log Lines
                          </span>
                        </div>
                        <button
                          type="button"
                          onClick={() =>
                            handleCopyContext(finding.context, index)
                          }
                          className="flex items-center gap-1 rounded bg-slate-800 hover:bg-slate-700 px-2 py-0.5 text-[11px] text-slate-300 transition-colors cursor-pointer"
                          title="Copy context lines"
                        >
                          {copiedIndex === index ? (
                            <>
                              <Check size={12} className="text-emerald-400" />
                              <span className="text-emerald-400">Copied!</span>
                            </>
                          ) : (
                            <>
                              <Copy size={12} />
                              <span>Copy</span>
                            </>
                          )}
                        </button>
                      </div>

                      {/* Terminal Lines Content */}
                      <div className="overflow-x-auto overflow-y-auto max-h-72 flex-1 space-y-0.5 pr-1 select-text">
                        {finding.context.map((line, lIdx) => {
                          const currentLineNum = startLine + lIdx;
                          const isTarget =
                            currentLineNum === finding.line_number ||
                            lIdx === targetLineOffset;
                          return renderLogLine(
                            line,
                            currentLineNum,
                            isTarget,
                            finding.keyword,
                            finding.matched_text,
                          );
                        })}
                      </div>

                      <div className="mt-2 pt-2 border-t border-slate-800/80 flex items-center justify-between text-[10px] text-slate-500 font-mono">
                        <span>
                          Target: Line {finding.line_number}
                        </span>
                        <span>
                          Context window: {finding.context.length} lines
                        </span>
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      )}
    </section>
  );
}
