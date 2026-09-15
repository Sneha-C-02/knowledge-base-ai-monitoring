import { useState, useEffect } from "react";
import { Link } from "react-router-dom";
import { BookOpen, ArrowUpRight, Loader2 } from "lucide-react";
import { Button } from "../common/Button";
import { api } from "../../api/client";
import type { KeywordArticle } from "../../types";

interface AutoKbSolutionProps {
  initialArticle?: KeywordArticle | null;
  searchQuery?: string;
  candidateQueries?: (string | undefined | null)[];
  isError?: boolean;
  compact?: boolean;
}

export function AutoKbSolution({
  initialArticle,
  searchQuery,
  candidateQueries = [],
  isError = true,
  compact = false,
}: AutoKbSolutionProps) {
  const [article, setArticle] = useState<KeywordArticle | null>(
    initialArticle || null,
  );
  const [isLoading, setIsLoading] = useState<boolean>(false);
  const [hasSearched, setHasSearched] = useState<boolean>(!!initialArticle);

  const candidatesKey = candidateQueries.filter(Boolean).join("::");

  useEffect(() => {
    if (initialArticle) {
      setArticle(initialArticle);
      setHasSearched(true);
      return;
    }

    if (!isError) {
      return;
    }

    // Build deduplicated candidate queries
    const candidates: string[] = [];
    if (searchQuery && searchQuery.trim()) {
      candidates.push(searchQuery.trim());
    }
    const rawCandidates = candidatesKey ? candidatesKey.split("::") : [];
    for (const q of rawCandidates) {
      if (q && !candidates.includes(q)) {
        candidates.push(q);
      }
    }

    if (candidates.length === 0) {
      return;
    }

    let isMounted = true;
    setIsLoading(true);

    const performAutomaticSearch = async () => {
      try {
        for (const candidate of candidates) {
          // Clean candidate query of problematic symbols
          const cleaned = candidate
            .replace(/[^\w\s-]/g, " ")
            .replace(/\s+/g, " ")
            .trim();
          if (cleaned.length < 3) continue;

          try {
            const res = await api.getArticles(1, 1, cleaned);
            if (isMounted && res.items && res.items.length > 0) {
              const item = res.items[0];
              const matched: KeywordArticle = {
                id: item.id,
                database_id: item.database_id,
                article_number: item.article_number || item.id,
                title: item.title,
                url: item.url || `/article/${item.article_number || item.id}`,
                summary: item.description,
                relevance_score: 0.85,
                retrieval_reason: "Direct database match for diagnosed error",
              };
              setArticle(matched);
              setIsLoading(false);
              setHasSearched(true);
              return;
            }
          } catch {
            // try next candidate
            continue;
          }
        }
      } finally {
        if (isMounted) {
          setIsLoading(false);
          setHasSearched(true);
        }
      }
    };

    performAutomaticSearch();

    return () => {
      isMounted = false;
    };
  }, [initialArticle, searchQuery, isError, candidatesKey]);

  // Compact layout (for MonitoringPage complete log findings)
  if (compact) {
    if (isLoading) {
      return (
        <div className="mt-2 flex items-center gap-2 rounded-lg border border-indigo-100 bg-indigo-50/40 p-2.5 text-xs text-indigo-700">
          <Loader2 size={13} className="animate-spin text-indigo-600" />
          <span>Locating matching Knowledge Base solution in database...</span>
        </div>
      );
    }

    if (article) {
      return (
        <div className="mt-2 rounded-lg border border-indigo-100 bg-gradient-to-br from-indigo-50/80 via-blue-50/60 to-white p-3 shadow-xs">
          <div className="flex items-center justify-between gap-2 mb-1.5">
            <div className="flex items-center gap-1.5 text-xs font-bold uppercase tracking-wider text-indigo-900">
              <BookOpen size={13} className="text-indigo-600" />
              <span>Suggested Knowledge Base Solution</span>
            </div>
            <span className="inline-flex items-center rounded-full bg-indigo-100 px-2 py-0.5 text-[10px] font-semibold text-indigo-800">
              Article {article.article_number}
            </span>
          </div>

          <Link
            to={`/article/${article.article_number}`}
            className="text-xs font-bold text-indigo-700 hover:text-indigo-900 hover:underline flex items-center gap-1 group"
          >
            <span>{article.title}</span>
            <ArrowUpRight
              size={13}
              className="text-indigo-500 group-hover:translate-x-0.5 group-hover:-translate-y-0.5 transition-transform"
            />
          </Link>

          {article.summary && (
            <p className="text-xs text-slate-600 line-clamp-2 mt-1 leading-relaxed">
              {article.summary}
            </p>
          )}

          <div className="mt-2 pt-1.5 flex items-center justify-between gap-2 border-t border-indigo-100/60">
            <span className="text-[10px] text-indigo-600 font-medium">
              {article.relevance_score
                ? `${Math.round(article.relevance_score * 100)}% Match`
                : "Relevant Resolution"}
            </span>
            <Link to={`/article/${article.article_number}`}>
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
      );
    }

    if (hasSearched && isError) {
      return (
        <div className="mt-2 text-[11px] text-slate-500 italic">
          No matching Knowledge Base article found in database for this error signature.
        </div>
      );
    }

    return null;
  }

  // Full card layout (for KeywordSearchSection)
  return (
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
        {article && (
          <span className="inline-flex items-center rounded-full bg-indigo-100 px-2 py-0.5 text-[11px] font-semibold text-indigo-800">
            Article {article.article_number}
          </span>
        )}
      </div>

      {isLoading ? (
        <div className="flex items-center gap-2 py-3 text-xs text-indigo-700">
          <Loader2 size={14} className="animate-spin text-indigo-600" />
          <span>Searching database for matching Waters article...</span>
        </div>
      ) : article ? (
        <div className="space-y-2 mt-2">
          <Link
            to={`/article/${article.article_number}`}
            className="text-sm font-bold text-indigo-700 hover:text-indigo-900 hover:underline flex items-center gap-1.5 group"
          >
            <span>{article.title}</span>
            <ArrowUpRight
              size={15}
              className="text-indigo-500 group-hover:translate-x-0.5 group-hover:-translate-y-0.5 transition-transform"
            />
          </Link>

          {article.summary && (
            <p className="text-xs text-slate-600 line-clamp-3 leading-relaxed">
              {article.summary}
            </p>
          )}

          <div className="pt-2 flex items-center justify-between gap-2 border-t border-indigo-100/60">
            <span className="text-[11px] text-indigo-600 font-medium">
              {article.relevance_score
                ? `${Math.round(article.relevance_score * 100)}% Match`
                : "Relevant Resolution"}
            </span>

            <Link to={`/article/${article.article_number}`}>
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
        <div className="mt-1">
          <p className="text-xs text-slate-500 italic">
            {isError
              ? "No matching Knowledge Base article found in database for this error signature."
              : "Informational log finding — no Knowledge Base resolution required."}
          </p>
        </div>
      )}
    </div>
  );
}
