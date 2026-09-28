import { useState, useEffect } from "react";
import { Link } from "react-router-dom";
import {
  BookOpen,
  Sparkles,
  ChevronDown,
  ChevronUp,
  ArrowUpRight,
  Activity,
  Layers,
  FileText,
  Search,
} from "lucide-react";
import { Badge } from "../common/Badge";
import { Button } from "../common/Button";
import { api } from "../../api/client";
import type { DashboardFinding, KeywordArticle } from "../../types";

interface FindingCardProps {
  finding: DashboardFinding;
  instrumentName?: string;
}

export function FindingCard({ finding, instrumentName }: FindingCardProps) {
  const [kbArticle, setKbArticle] = useState<KeywordArticle | null | undefined>(
    finding.kb_article,
  );
  const [isSearchingKb, setIsSearchingKb] = useState(false);
  const [kbSearched, setKbSearched] = useState(!!finding.kb_article);
  const [showForensics, setShowForensics] = useState(false);

  useEffect(() => {
    setKbArticle(finding.kb_article);
    setKbSearched(!!finding.kb_article);
  }, [finding.kb_article]);

  const handleSearchKb = async () => {
    setIsSearchingKb(true);
    try {
      const res = await api.searchFindingKb({
        snippet: finding.snippet,
        explanation: finding.explanation,
        filename: finding.filename,
        line_number: finding.line_number,
        search_query: finding.suggested_search_query || finding.explanation,
        instrument_name: instrumentName,
      });
      setKbArticle(res.kb_article);
      setKbSearched(true);
    } catch (err) {
      console.error("Failed to retrieve KB article for finding:", err);
      setKbSearched(true);
    } finally {
      setIsSearchingKb(false);
    }
  };

  const getSeverityBadgeVariant = (severity: string) => {
    const s = severity.toLowerCase();
    if (s === "critical") return "error";
    if (s === "error") return "error";
    if (s === "warning") return "warning";
    return "info";
  };

  const hasForensics =
    (finding.pre_incident_events && finding.pre_incident_events.length > 0) ||
    (finding.major_events && finding.major_events.length > 0) ||
    (finding.system_changes && finding.system_changes.length > 0) ||
    (finding.grounding_citations && finding.grounding_citations.length > 0);

  return (
    <div
      className={`border-l-4 rounded-r-lg bg-white p-4 sm:p-5 shadow-xs space-y-3.5 border transition-all ${
        finding.severity.toLowerCase() === "critical"
          ? "border-l-red-600 border-slate-200"
          : finding.severity.toLowerCase() === "error"
            ? "border-l-orange-500 border-slate-200"
            : "border-l-amber-500 border-slate-200"
      }`}
    >
      {/* 1. Header: Pinpoint issue line, filename, severity & confidence */}
      <div className="flex flex-wrap items-center justify-between gap-2">
        <div className="flex items-center gap-2 flex-wrap">
          <span className="flex items-center gap-1.5 text-xs font-semibold text-slate-800">
            <FileText size={14} className="text-slate-500" />
            {finding.filename}
          </span>
          <span className="inline-flex items-center rounded-md bg-slate-100 px-2 py-0.5 text-xs font-mono font-medium text-slate-700 border border-slate-200">
            Line #{finding.line_number}
          </span>
          {finding.confidence_score && (
            <span className="inline-flex items-center rounded-full bg-emerald-50 px-2 py-0.5 text-[11px] font-medium text-emerald-700 border border-emerald-200">
              {Math.round(finding.confidence_score * 100)}% Grounded
            </span>
          )}
        </div>

        <Badge variant={getSeverityBadgeVariant(finding.severity)}>
          {finding.severity.toUpperCase()}
        </Badge>
      </div>

      {/* 2. Pinpoint issue log line snippet */}
      <div className="space-y-1">
        <span className="text-[11px] font-medium text-slate-500 uppercase tracking-wider">
          Pinpointed Issue Line:
        </span>
        <pre className="whitespace-pre-wrap break-words font-mono text-xs bg-slate-900 text-slate-100 p-2.5 rounded-md border border-slate-800 overflow-x-auto">
          {finding.snippet}
        </pre>
      </div>

      {/* 3. Simple Plain-English AI Explanation */}
      {/* 3. AI Summary */}
      <div className="rounded-lg bg-gradient-to-r from-blue-50/80 via-indigo-50/50 to-slate-50 border border-blue-200/70 p-3">
        <div className="flex items-center gap-1.5 mb-1 text-xs font-semibold text-primary-700">
          <Sparkles size={14} className="text-primary-600 animate-pulse" />
          <span>Simple Plain-English Explanation</span>
          <span>AI Summary</span>
        </div>
        <p className="text-xs text-slate-700 leading-relaxed font-sans">
          {finding.simple_summary || finding.explanation}
        </p>
      </div>

      {/* 4. Deep Forensic Analysis Section (Collapsible) */}
      {hasForensics && (
        <div className="pt-1">
          <button
            type="button"
            onClick={() => setShowForensics(!showForensics)}
            className="flex items-center gap-1.5 text-xs font-medium text-primary-700 hover:text-primary-800 hover:underline transition-colors"
          >
            <Activity size={14} />
            <span>
              {showForensics
                ? "Hide Forensic Precursors & Changes"
                : "View Pre-Incident Events, Major Events & System Changes"}
            </span>
            {showForensics ? <ChevronUp size={14} /> : <ChevronDown size={14} />}
          </button>

          {showForensics && (
            <div className="mt-3 space-y-3.5 rounded-lg border border-slate-200 bg-slate-50/60 p-3.5 text-xs">
              {/* Pre-incident pattern & summary */}
              {finding.pre_incident_summary && (
                <div className="space-y-1.5">
                  <div className="flex items-center gap-2">
                    <span className="font-semibold text-slate-700">
                      Pre-Incident Pattern:
                    </span>
                    {finding.pre_incident_pattern && (
                      <span className="rounded-sm bg-purple-100 px-2 py-0.5 text-[11px] font-medium text-purple-800">
                        {finding.pre_incident_pattern}
                      </span>
                    )}
                  </div>
                  <p className="text-slate-600 leading-relaxed">
                    {finding.pre_incident_summary}
                  </p>
                </div>
              )}

              {/* Pre-incident sequence events */}
              {finding.pre_incident_events &&
                finding.pre_incident_events.length > 0 && (
                  <div className="space-y-1.5">
                    <span className="font-semibold text-slate-700">
                      Precursor Sequence Events:
                    </span>
                    <div className="space-y-1 max-h-36 overflow-y-auto pr-1">
                      {finding.pre_incident_events.map((ev, i) => (
                        <div
                          key={i}
                          className="flex items-start gap-2 bg-white p-1.5 rounded border border-slate-200 font-mono text-[11px]"
                        >
                          <span className="text-slate-400 shrink-0">
                            Line {ev.line}:
                          </span>
                          <span className="text-slate-700 break-words flex-1">
                            {ev.snippet}
                          </span>
                        </div>
                      ))}
                    </div>
                  </div>
                )}

              {/* Matching major events */}
              {finding.major_events && finding.major_events.length > 0 && (
                <div className="space-y-1.5">
                  <span className="font-semibold text-red-700 flex items-center gap-1">
                    <Layers size={13} /> Matching Correlated Major System Events:
                  </span>
                  <div className="space-y-1.5">
                    {finding.major_events.map((me, i) => (
                      <div
                        key={i}
                        className="rounded border border-red-200 bg-red-50/50 p-2 text-xs text-red-900"
                      >
                        <div className="flex items-center justify-between font-semibold">
                          <span>{me.event_type}</span>
                          <span className="text-[11px] text-red-700 font-mono">
                            Line {me.line_number}
                          </span>
                        </div>
                        <p className="font-mono text-[11px] mt-0.5 text-slate-800">
                          {me.description}
                        </p>
                        <p className="text-[11px] text-red-700 italic mt-0.5">
                          {me.match_reason}
                        </p>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Before vs After system changes */}
              {finding.system_changes && finding.system_changes.length > 0 && (
                <div className="space-y-1.5">
                  <span className="font-semibold text-slate-700">
                    System State: Before vs. After Incident:
                  </span>
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-2">
                    {finding.system_changes.map((sc, i) => (
                      <div
                        key={i}
                        className="rounded border border-slate-200 bg-white p-2 text-[11px] space-y-1"
                      >
                        <span className="font-semibold text-slate-800 block">
                          {sc.aspect}
                        </span>
                        <div className="flex items-center justify-between text-slate-500">
                          <span>Before: {sc.before_incident}</span>
                          <span>After: {sc.after_incident}</span>
                        </div>
                        <p className="text-slate-600 italic">
                          {sc.change_summary}
                        </p>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Grounding citations */}
              {finding.grounding_citations &&
                finding.grounding_citations.length > 0 && (
                  <div className="space-y-1 pt-1 border-t border-slate-200">
                    <span className="font-semibold text-slate-600 text-[11px]">
                      Verified Grounding Citations:
                    </span>
                    <ul className="list-disc list-inside text-[11px] text-slate-500 space-y-0.5">
                      {finding.grounding_citations.map((c, i) => (
                        <li key={i}>
                          Line {c.line_number} ({c.log_file}):{" "}
                          <span className="italic">{c.relevance_reason}</span>
                        </li>
                      ))}
                    </ul>
                  </div>
                )}
            </div>
          )}
        </div>
      )}

      {/* 5. On-Demand Knowledge Base Retrieval (Strict Button Trigger) */}
      <div className="pt-2 border-t border-slate-100">
        {!kbArticle && !kbSearched && (
          <Button
            type="button"
            variant="outline"
            size="sm"
            onClick={handleSearchKb}
            isLoading={isSearchingKb}
            className="text-xs text-primary-700 border-primary-300 hover:bg-primary-50 bg-white"
          >
            <BookOpen size={14} className="mr-1.5 text-primary-600" />
            Search Knowledge Base Article
          </Button>
        )}

        {isSearchingKb && (
          <div className="flex items-center gap-2 py-2 text-xs text-slate-600">
            <Search size={14} className="animate-spin text-primary-600" />
            <span>Searching Waters Knowledge Base database on-demand...</span>
          </div>
        )}

        {kbArticle && (
          <div className="rounded-lg border border-indigo-100 bg-gradient-to-br from-indigo-50/80 via-blue-50/60 to-white p-3.5 shadow-xs">
            <div className="flex items-center justify-between gap-2 mb-1.5">
              <div className="flex items-center gap-1.5 text-xs font-bold uppercase tracking-wider text-indigo-900">
                <BookOpen size={14} className="text-indigo-600" />
                <span>Matching Knowledge Base Article</span>
              </div>
              <span className="inline-flex items-center rounded-full bg-indigo-100 px-2 py-0.5 text-[10px] font-semibold text-indigo-800">
                Article {kbArticle.article_number}
              </span>
            </div>

            <Link
              to={kbArticle.url || `/article/${kbArticle.article_number}`}
              className="text-xs font-bold text-indigo-700 hover:text-indigo-900 hover:underline flex items-center gap-1 group"
            >
              <span>{kbArticle.title}</span>
              <ArrowUpRight
                size={13}
                className="text-indigo-500 group-hover:translate-x-0.5 group-hover:-translate-y-0.5 transition-transform"
              />
            </Link>

            {kbArticle.summary && (
              <p className="text-xs text-slate-600 line-clamp-2 mt-1 leading-relaxed">
                {kbArticle.summary}
              </p>
            )}

            <div className="mt-2.5 pt-1.5 flex items-center justify-between gap-2 border-t border-indigo-100/60">
              <span className="text-[11px] text-indigo-600 font-medium">
                {kbArticle.relevance_score
                  ? `${Math.round(kbArticle.relevance_score * 100)}% Match`
                  : "Relevant Resolution"}
              </span>
              <Link to={kbArticle.url || `/article/${kbArticle.article_number}`}>
                <Button
                  variant="outline"
                  size="sm"
                  className="text-[11px] h-7 px-2.5 text-indigo-700 border-indigo-300 hover:bg-indigo-100 bg-white"
                >
                  View Article
                </Button>
              </Link>
            </div>
          </div>
        )}

        {kbSearched && !kbArticle && !isSearchingKb && (
          <div className="flex items-center justify-between text-xs text-slate-500 bg-slate-50 p-2.5 rounded border border-slate-200">
            <span>No matching Knowledge Base article found in database for this specific finding.</span>
            <button
              type="button"
              onClick={handleSearchKb}
              className="text-primary-600 hover:underline font-medium ml-2 shrink-0"
            >
              Retry Search
            </button>
          </div>
        )}
      </div>
    </div>
  );
}
