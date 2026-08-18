import { useState } from 'react';
import { Play, FileText, AlertTriangle, ShieldCheck, Clock, ExternalLink, Plus, X, Upload } from 'lucide-react';
import { clsx } from 'clsx';
import { useSystem } from '../context/SystemContext';
import { Card, CardContent, CardHeader, CardTitle } from '../components/common/Card';
import { Button } from '../components/common/Button';
import { Badge } from '../components/common/Badge';
import { api } from '../api/client';

export function MonitoringPage() {
  const [logFiles, setLogFiles] = useState<(File | null)[]>([null]);
  const [isMonitoring, setIsMonitoring] = useState(false);
  const [result, setResult] = useState<any>(null);
  const [error, setError] = useState<string | null>(null);
  const { addActivity, addNotification, updateStats, stats } = useSystem();
  
  const MAX_LOGS = 10;

  const handleStartMonitoring = (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    
    const validFiles = logFiles.filter((f): f is File => f !== null);
    if (validFiles.length === 0) {
      setError("Please select at least one log file to upload.");
      return;
    }

    setIsMonitoring(true);
    setResult(null);

    addActivity({
      type: 'system',
      message: 'MANUAL_DIAGNOSTIC_RUN',
      user: 'Admin User',
    });

    const processLog = async () => {
      try {
        const analysisResult = await api.analyzeLog(validFiles);
        setResult(analysisResult);
        
        updateStats({ 
          activeLogs: stats.activeLogs + validFiles.length,
          detectedIssues: stats.detectedIssues + 1
        });

        addNotification({
          type: analysisResult.status === 'CRITICAL' ? 'error' : 'warning',
          title: 'Log Analysis Complete',
          message: `System analyzed ${validFiles.length} uploaded log file(s).`,
        });
        
        addActivity({
          type: 'system',
          message: 'LOG_ANALYZED',
          user: 'System',
        });
      } catch (err) {
        console.error(err);
        setError("Failed to analyze log. Backend API is unreachable.");
      } finally {
        setIsMonitoring(false);
      }
    };

    processLog();
  };

  return (
    <div className="max-w-5xl mx-auto space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold text-slate-800">Proactive Log Monitoring</h1>
      </div>

      <Card>
        <CardContent className="p-6">
          <form onSubmit={handleStartMonitoring} className="space-y-4">
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
                        }}
                        disabled={isMonitoring}
                      />
                      <label
                        htmlFor={`file-upload-${index}`}
                        className={`cursor-pointer h-full px-4 flex items-center border-r border-slate-300 font-medium text-sm transition-colors ${
                          isMonitoring ? 'bg-slate-50 text-slate-400' : 'bg-slate-100 hover:bg-slate-200 text-slate-700'
                        }`}
                      >
                        <Upload size={16} className="mr-2" />
                        Browse
                      </label>
                      <div className="px-3 flex items-center gap-2 text-slate-500 font-mono text-sm truncate flex-1">
                        <FileText size={16} className={file ? "text-primary-500" : "text-slate-300"} />
                        {file ? file.name : 'No file selected...'}
                      </div>
                    </div>
                    {logFiles.length > 1 && (
                      <button
                        type="button"
                        className="text-slate-400 hover:text-red-500 shrink-0 p-2 rounded hover:bg-slate-50 transition-colors"
                        onClick={() => setLogFiles(logFiles.filter((_, i) => i !== index))}
                        disabled={isMonitoring}
                      >
                        <X size={20} />
                      </button>
                    )}
                  </div>
                ))}
              </div>
            </div>

            <div className="flex items-center justify-between pt-2">
              <Button
                type="button"
                variant="outline"
                onClick={() => setLogFiles([...logFiles, null])}
                disabled={isMonitoring || logFiles.length >= MAX_LOGS}
                className="text-sm"
              >
                <Plus size={16} className="mr-1" /> Add Another File
              </Button>
              
              <Button type="submit" isLoading={isMonitoring}>
                <Play size={18} className="mr-2" />
                Start Monitoring
              </Button>
            </div>
          </form>
          {error && <p className="text-red-500 text-sm mt-4">{error}</p>}
        </CardContent>
      </Card>

      {result && (
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 animate-in fade-in duration-500">
          <div className="lg:col-span-1 space-y-6">
            <Card>
              <CardHeader>
                <CardTitle className="text-base">File Status</CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="flex justify-between items-center">
                  <span className="text-slate-500">Access</span>
                  <Badge variant="success">{result.file_status}</Badge>
                </div>
                <div className="flex justify-between items-center">
                  <span className="text-slate-500">Size</span>
                  <span className="font-medium text-slate-800">{result.file_info.size}</span>
                </div>
                <div className="flex justify-between items-center">
                  <span className="text-slate-500">Modified</span>
                  <span className="font-medium text-slate-800">{result.file_info.last_modified}</span>
                </div>
              </CardContent>
            </Card>

            <Card className={result.status === 'WARNING' ? 'bg-yellow-50 border-yellow-200' : ''}>
              <CardContent className="p-6 text-center">
                <h3 className="text-sm font-medium text-slate-500 mb-2">Overall Status</h3>
                <div className="flex items-center justify-center gap-2">
                  {result.status === 'WARNING' ? (
                    <AlertTriangle className="text-yellow-600" size={32} />
                  ) : (
                    <ShieldCheck className="text-green-600" size={32} />
                  )}
                  <span className={`text-2xl font-bold ${result.status === 'WARNING' ? 'text-yellow-700' : 'text-green-700'}`}>
                    {result.status}
                  </span>
                </div>
              </CardContent>
            </Card>
          </div>

          <div className="lg:col-span-2 space-y-6">
            <Card>
              <CardHeader>
                <CardTitle className="text-base">Detected Issues</CardTitle>
              </CardHeader>
              <CardContent className="p-0">
                {result.issues.length === 0 ? (
                  <div className="p-6 text-center text-slate-500">No issues detected.</div>
                ) : (
                  <div className="divide-y divide-slate-100">
                    {result.issues.map((issue: any) => (
                      <div key={issue.id} className="p-4">
                        <div className="flex items-start justify-between mb-2">
                          <div className="flex items-center gap-2">
                            <Badge variant={issue.severity === 'WARNING' ? 'warning' : 'error'}>
                              {issue.severity}
                            </Badge>
                            <span className="font-bold text-slate-800">{issue.pattern}</span>
                          </div>
                          <span className="text-sm text-slate-500 flex items-center gap-1">
                            <Clock size={14} /> {issue.timestamp}
                          </span>
                        </div>
                        <p className="text-slate-700 text-sm mb-3">{issue.description}</p>
                        <div className="bg-slate-50 p-3 rounded border border-slate-100 flex justify-between items-center">
                          <div>
                            <span className="text-xs font-semibold text-slate-500 uppercase tracking-wider block mb-1">Recommended Action</span>
                            <p className="mt-1 font-medium">{issue.recommended_action}</p>
                          </div>
                          {issue.related_article && (
                            <div>
                              <span className="text-slate-500 text-xs font-semibold uppercase tracking-wider block mb-1">Related Article</span>
                              <div className="mt-1">
                                <Button variant="outline" className="px-2 py-1 text-sm h-auto" onClick={() => window.open(issue.related_article_url || `/article/${issue.related_article}`, '_blank')}>
                                  {issue.related_article} <ExternalLink size={14} className="ml-2" />
                                </Button>
                              </div>
                            </div>
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
                <CardTitle className="text-base">Recent Log Events</CardTitle>
              </CardHeader>
              <CardContent className="p-0">
                <div className="overflow-x-auto">
                  <table className="w-full text-sm text-left">
                    <thead className="bg-slate-50 text-slate-500 font-medium border-b border-slate-100">
                      <tr>
                        <th className="px-4 py-2 w-24">Time</th>
                        <th className="px-4 py-2 w-20">Level</th>
                        <th className="px-4 py-2">Message</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-slate-100 font-mono text-xs">
                      {result.recent_events.map((evt: any, i: number) => (
                        <tr key={i} className="hover:bg-slate-50">
                          <td className="px-4 py-2 text-slate-500">{evt.timestamp}</td>
                          <td className="px-4 py-2">
                            <span className={clsx(
                              "px-1.5 py-0.5 rounded font-bold",
                              evt.level === 'ERROR' ? 'text-red-700 bg-red-50' :
                              evt.level === 'WARN' ? 'text-yellow-700 bg-yellow-50' : 'text-slate-600 bg-slate-100'
                            )}>
                              {evt.level}
                            </span>
                          </td>
                          <td className="px-4 py-2 text-slate-800">{evt.message}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </CardContent>
            </Card>
          </div>
        </div>
      )}
    </div>
  );
}
