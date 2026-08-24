import { useState } from 'react';
import { Bot, Search, BookOpen } from 'lucide-react';
import { Card, CardContent } from '../components/common/Card';
import { Button } from '../components/common/Button';
import { TextArea } from '../components/common/TextArea';
import { Badge } from '../components/common/Badge';
import { api } from '../api/client';
import { useSystem } from '../context/SystemContext';

export function SupportPage() {
  const [query, setQuery] = useState('');
  const [isSearching, setIsSearching] = useState(false);
  const [answer, setAnswer] = useState<{
    text: string;
    related_articles?: {
      article_number: string;
      title: string;
      article_url: string;
      snippet: string;
      retrieval_reason: string;
      relevance_score: number;
    }[];
  } | null>(null);
  const [error, setError] = useState<string | null>(null);
  const { addActivity } = useSystem();

  const handleSearch = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!query.trim()) return;

    setAnswer(null);
    setError(null);
    setIsSearching(true);
    
    // Log QUERY_SUBMITTED
    addActivity({ 
      type: 'QUERY_SUBMITTED', 
      message: 'User submitted a support query', 
      user: 'Current User', 
      severity: 'INFO', 
      metadata: { query } 
    });

    try {
      const startTime = Date.now();
      const response = await api.querySupport(query);
      const durationMs = Date.now() - startTime;
      
      setAnswer({
        text: response.answer,
        related_articles: response.related_articles
      });
      
      // Log SYSTEM_RESPONSE
      addActivity({ 
        type: 'SYSTEM_RESPONSE', 
        message: 'System generated a response', 
        user: 'System', 
        severity: 'SUCCESS',
        metadata: { duration_ms: durationMs, related_articles_count: response.related_articles?.length || 0 }
      });
    } catch (err) {
      console.error(err);
      setError("Failed to generate an answer. Please check your connection to the backend API.");
      
      // Log QUERY_ERROR
      addActivity({ 
        type: 'QUERY_ERROR', 
        message: 'Failed to generate system response', 
        user: 'System', 
        severity: 'ERROR',
        metadata: { query }
      });
    } finally {
      setIsSearching(false);
    }
  };

  return (
    <div className="max-w-4xl mx-auto space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold text-slate-800">Reactive Support</h1>
        <Badge variant="info">AI Assistant</Badge>
      </div>

      <Card>
        <CardContent className="p-6">
          <form onSubmit={handleSearch} className="space-y-4">
            <div>
              <label htmlFor="query" className="block text-sm font-medium text-slate-700 mb-1">
                Describe your instrument issue
              </label>
              <TextArea
                id="query"
                rows={4}
                placeholder="e.g. Why is my instrument not communicating with the server?"
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                disabled={isSearching}
              />
            </div>
            <div className="flex justify-end gap-3">
              <Button type="button" variant="secondary" onClick={() => setQuery('')} disabled={isSearching || !query}>
                Clear
              </Button>
              <Button type="submit" isLoading={isSearching}>
                <Search size={18} className="mr-2" />
                Find Solution
              </Button>
            </div>
          </form>
        </CardContent>
      </Card>

      {answer && (
        <div className="mt-8 space-y-6 animate-in fade-in slide-in-from-bottom-4 duration-500">
          <div className="bg-indigo-50 border border-indigo-100 rounded-lg p-6">
            <div className="flex items-start gap-4">
              <div className="bg-indigo-600 text-white p-2 rounded-lg mt-1">
                <Bot size={20} />
              </div>
              <div>
                <h3 className="text-lg font-semibold text-slate-800 mb-2">Generated Answer</h3>
                <p className="text-slate-600 leading-relaxed mb-4">
                  {answer.text}
                </p>
                {answer.related_articles && answer.related_articles.length > 0 && (
                  <div className="mt-6 space-y-4">
                    <div className="flex items-center gap-2 text-indigo-600 mb-2">
                      <BookOpen size={18} />
                      <span className="font-semibold text-sm">Source Articles</span>
                    </div>
                    {answer.related_articles.map((article, idx) => (
                      <div key={idx} className="bg-white border border-slate-200 rounded-lg p-4">
                        <div className="flex items-center justify-between mb-2">
                          <h4 className="font-bold text-slate-800">{article.article_number} - {article.title}</h4>
                          <Badge variant="default" className="text-xs">
                            Score: {article.relevance_score.toFixed(2)}
                          </Badge>
                        </div>
                        <p className="text-sm text-slate-600 mb-2">{article.snippet}...</p>
                        <p className="text-xs text-slate-500 mb-4 italic">Matched by: {article.retrieval_reason}</p>
                        
                        <div className="pt-3 border-t border-slate-100 flex justify-end">
                          <Button 
                            variant="outline" 
                            size="sm"
                            onClick={() => window.open(article.article_url || `/article/${article.article_number}`, '_blank')}
                          >
                            View Full Article
                          </Button>
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            </div>
          </div>
        </div>
      )}

      {error && (
        <div className="mt-8 p-4 bg-red-50 border border-red-200 text-red-700 rounded-lg">
          {error}
        </div>
      )}
    </div>
  );
}
