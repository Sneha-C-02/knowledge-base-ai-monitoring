import { useState } from 'react';
import { Bot, Search, BookOpen } from 'lucide-react';
import { Card, CardContent } from '../components/common/Card';
import { Button } from '../components/common/Button';
import { TextArea } from '../components/common/TextArea';
import { Badge } from '../components/common/Badge';
import { api } from '../api/client';

export function SupportPage() {
  const [query, setQuery] = useState('');
  const [isSearching, setIsSearching] = useState(false);
  const [answer, setAnswer] = useState<{
    text: string;
    related_article?: string;
    related_article_url?: string;
  } | null>(null);
  const [error, setError] = useState<string | null>(null);

  const handleSearch = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!query.trim()) return;

    setIsSearching(true);
    setError(null);
    setAnswer(null);

    try {
      const response = await api.querySupport(query);
      setAnswer({
        text: response.answer,
        related_article: response.related_article,
        related_article_url: response.related_article_url
      });
    } catch (err) {
      console.error(err);
      setError("Failed to generate an answer. Please check your connection to the backend API.");
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
                {answer.related_article && (
                  <div className="bg-white border border-slate-200 rounded-lg p-4 mt-4">
                    <div className="flex items-center justify-between mb-4">
                      <div className="flex items-center gap-2 text-indigo-600">
                        <BookOpen size={18} />
                        <span className="font-semibold text-sm">Source Article</span>
                      </div>
                      <Badge variant="default" className="text-xs">High Confidence</Badge>
                    </div>
                    <h4 className="font-bold text-slate-800 mb-2">{answer.related_article}</h4>
                    
                    <div className="mt-4 pt-4 border-t border-slate-100 flex justify-end">
                      <Button 
                        variant="outline" 
                        onClick={() => window.open(answer.related_article_url || `/article/${answer.related_article}`, '_blank')}
                      >
                        View Full Article
                      </Button>
                    </div>
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
