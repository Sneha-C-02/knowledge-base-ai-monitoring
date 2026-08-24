import { useState, useEffect } from 'react';
import { ExternalLink, Loader2, AlertCircle, ChevronLeft, ChevronRight } from 'lucide-react';
import { useNavigate } from 'react-router-dom';
import { Card, CardContent } from '../components/common/Card';
import { Button } from '../components/common/Button';
import { TextInput } from '../components/common/TextInput';
import { Badge } from '../components/common/Badge';
import { useSystem } from '../context/SystemContext';
import { api } from '../api/client';
import type { KBArticle, Pagination } from '../types';

export function KnowledgeBasePage() {
  const [searchTerm, setSearchTerm] = useState('');
  const [debouncedSearch, setDebouncedSearch] = useState('');
  const [articles, setArticles] = useState<KBArticle[]>([]);
  const [pagination, setPagination] = useState<Pagination | null>(null);
  const [currentPage, setCurrentPage] = useState(1);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  
  const { addActivity } = useSystem();
  const navigate = useNavigate();

  // Debounce search input
  useEffect(() => {
    const timer = setTimeout(() => {
      setDebouncedSearch(searchTerm);
      setCurrentPage(1); // Reset to page 1 on new search
      
      if (searchTerm.trim()) {
        addActivity({
          type: 'KB_SEARCH',
          message: 'User searched the knowledge base',
          user: 'Current User',
          severity: 'INFO',
          metadata: { query: searchTerm }
        });
      }
    }, 500);
    return () => clearTimeout(timer);
  }, [searchTerm]);

  useEffect(() => {
    let mounted = true;
    setIsLoading(true);
    setError(null);

    api.getArticles(currentPage, 10, debouncedSearch)
      .then(data => {
        if (mounted) {
          setArticles(data.items);
          setPagination(data.pagination);
          setIsLoading(false);
        }
      })
      .catch(err => {
        if (mounted) {
          console.error(err);
          setError("Failed to load knowledge base articles. Is the backend running?");
          setIsLoading(false);
        }
      });
    return () => { mounted = false; };
  }, [currentPage, debouncedSearch]);

  return (
    <div className="max-w-5xl mx-auto space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold text-slate-800">Knowledge Base</h1>
      </div>

      <div className="flex gap-4 mb-6">
        <div className="relative flex-1">
          <TextInput
            placeholder="Search knowledge base articles by title, ID, or category..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
          />
        </div>
      </div>

      {isLoading ? (
        <div className="flex items-center justify-center p-12">
          <Loader2 className="animate-spin text-indigo-500 mr-2" size={24} />
          <span className="text-slate-600">Loading articles...</span>
        </div>
      ) : error ? (
        <div className="p-4 bg-red-50 border border-red-200 text-red-700 rounded-lg flex items-center">
          <AlertCircle className="mr-2" size={20} />
          {error}
        </div>
      ) : (
        <div className="space-y-4">
          {articles.length === 0 ? (
            <div className="text-center p-8 text-slate-500">No articles match your search.</div>
          ) : articles.map((article) => (
            <Card key={article.id} className="hover:border-primary-300 transition-colors cursor-pointer" onClick={() => navigate(`/article/${article.id}`)}>
              <CardContent className="p-4 flex flex-col sm:flex-row sm:items-center justify-between gap-4">
                <div>
                  <div className="flex items-center gap-2 mb-2">
                    <span className="font-bold text-slate-800">{article.id}</span>
                    <span className="text-slate-400">•</span>
                    <h3 className="text-lg font-medium text-primary-700 hover:underline">{article.title}</h3>
                  </div>
                  <div className="flex items-center gap-4 text-sm text-slate-500">
                    <div className="flex gap-2">
                      <Badge variant="default">{article.category}</Badge>
                    </div>
                    <span>•</span>
                    <span>Views: {article.views}</span>
                  </div>
                </div>
                <Button variant="secondary" className="shrink-0" onClick={(e) => { e.stopPropagation(); navigate(`/article/${article.id}`); }}>
                  <ExternalLink size={16} className="mr-2" />
                  View
                </Button>
              </CardContent>
            </Card>
          ))}

          {/* Pagination Controls */}
          {pagination && pagination.total_pages > 1 && (
            <div className="flex items-center justify-between pt-6 mt-6 border-t border-slate-200">
              <span className="text-sm text-slate-500">
                Showing page {pagination.current_page} of {pagination.total_pages} ({pagination.total_items} total articles)
              </span>
              <div className="flex gap-2">
                <Button 
                  variant="outline" 
                  onClick={() => setCurrentPage(prev => Math.max(prev - 1, 1))}
                  disabled={!pagination.has_previous_page}
                >
                  <ChevronLeft size={16} className="mr-1" /> Previous
                </Button>
                <Button 
                  variant="outline" 
                  onClick={() => setCurrentPage(prev => prev + 1)}
                  disabled={!pagination.has_next_page}
                >
                  Next <ChevronRight size={16} className="ml-1" />
                </Button>
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
