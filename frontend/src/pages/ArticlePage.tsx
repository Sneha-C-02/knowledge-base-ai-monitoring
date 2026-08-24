import { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { ArrowLeft, Edit, Loader2, AlertCircle, ExternalLink } from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle } from '../components/common/Card';
import { Button } from '../components/common/Button';
import { Badge } from '../components/common/Badge';
import { api } from '../api/client';
import { useSystem } from '../context/SystemContext';
import type { KBArticle } from '../types';

export function ArticlePage() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const { addActivity } = useSystem();
  const [article, setArticle] = useState<KBArticle | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!id) return;
    
    let mounted = true;
    const fetchArticle = async () => {
      try {
        const data = await api.getArticle(id);
        if (mounted) {
          setArticle(data);
          setIsLoading(false);
          
          addActivity({
            type: 'KB_ARTICLE_VIEWED',
            message: 'User viewed knowledge base article',
            user: 'Current User',
            severity: 'INFO',
            metadata: { article_id: id, title: data.title }
          });
        }
      } catch (err) {
        if (mounted) {
          console.error(err);
          setError("Failed to load the article.");
        }
      }
    };
    
    fetchArticle();

    return () => { mounted = false; };
  }, [id]);

  if (isLoading) {
    return (
      <div className="max-w-4xl mx-auto flex items-center justify-center p-24">
        <Loader2 className="animate-spin text-indigo-500 mr-2" size={32} />
        <span className="text-slate-600 text-lg">Loading article...</span>
      </div>
    );
  }

  if (error || !article) {
    return (
      <div className="max-w-4xl mx-auto space-y-6">
        <Button variant="outline" onClick={() => navigate('/kb')} className="mb-4">
          <ArrowLeft size={16} className="mr-2" /> Back to Knowledge Base
        </Button>
        <div className="p-6 bg-red-50 border border-red-200 text-red-700 rounded-lg flex flex-col items-center justify-center py-12">
          <AlertCircle size={48} className="mb-4 text-red-500" />
          <h2 className="text-xl font-bold mb-2">Article Not Found</h2>
          <p>{error || "The article you are looking for does not exist or has been removed."}</p>
        </div>
      </div>
    );
  }

  return (
    <div className="max-w-4xl mx-auto space-y-6 pb-12">
      <Button variant="outline" onClick={() => navigate(-1)} className="mb-4">
        <ArrowLeft size={16} className="mr-2" />
        Back
      </Button>

      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <Badge variant="info" className="text-sm px-3 py-1">{article.id}</Badge>
          <div className="text-sm text-slate-500 mb-6 flex items-center gap-4">
            <span>Last Updated: {article.last_updated}</span>
            <span>•</span>
            <span>{article.views} Views</span>
          </div>
        </div>
        <div className="flex gap-2">
          <Button variant="secondary">
            <Edit size={16} className="mr-2" /> Edit
          </Button>
        </div>
      </div>

      <Card>
        <CardHeader>
          <CardTitle className="text-2xl font-bold">{article.title}</CardTitle>
          <div className="flex flex-wrap gap-2">
            <Badge variant="default">{article.category || 'Knowledge Base'}</Badge>
          </div>
        </CardHeader>
        <CardContent>
          <div className="prose max-w-none text-slate-700">
            {article.description && (
              <>
                <h3 className="text-lg font-semibold mb-2 mt-6">Issue Description</h3>
                <p className="mb-6">{article.description}</p>
              </>
            )}
            


            {/* Render searchable content from backend if resolution steps don't exist */}
            {(article as any).searchable_content && (
              <>
                <h3 className="text-lg font-semibold mb-2 mt-4">Content</h3>
                <div className="bg-slate-50 p-6 rounded-md border border-slate-200 whitespace-pre-wrap font-sans text-sm">
                  {(article as any).searchable_content}
                </div>
              </>
            )}
            
            {(article as any).url && (
              <div className="mt-8">
                <a href={(article as any).url} target="_blank" rel="noopener noreferrer" className="text-primary-600 hover:underline inline-flex items-center">
                  View Original Source on Waters.com <ExternalLink size={14} className="ml-1" />
                </a>
              </div>
            )}
          </div>
        </CardContent>
      </Card>
    </div>
  );
}

// Force Vite Cache Invalidation: 1
