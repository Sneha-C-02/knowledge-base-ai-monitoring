import { useState, useEffect } from 'react';
import { Play, FileText, AlertTriangle, ShieldCheck, AlertCircle, Clock, Plus, X, Upload, Activity, History, Zap, CheckCircle2, Radio } from 'lucide-react';
import { clsx } from 'clsx';
import { useSystem } from '../context/SystemContext';
import { Card, CardContent, CardHeader, CardTitle } from '../components/common/Card';
import { Button } from '../components/common/Button';
import { Badge } from '../components/common/Badge';
import { api } from '../api/client';
import type { Instrument, DashboardResult, InstrumentMemoryResponse } from '../types';

export function MonitoringPage() {
  const [logFiles, setLogFiles] = useState<(File | null)[]>([null]);
  const [isMonitoring, setIsMonitoring] = useState(false);
  const [result, setResult] = useState<DashboardResult | null>(null);
  const [memory, setMemory] = useState<InstrumentMemoryResponse | null>(null);
  const [showMemory, setShowMemory] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [isLive, setIsLive] = useState(false);
  const { addActivity, addNotification, updateStats, stats } = useSystem();
  
  const MAX_LOGS = 10;

  // Setup SSE for live continuous monitoring
  useEffect(() => {
    let eventSource: EventSource | null = null;
    
    if (result && result.instrument_id && !isMonitoring) {
      setIsLive(true);
      eventSource = api.streamDashboard(result.instrument_id);
      
      eventSource.onmessage = (event) => {
        try {
          const data: DashboardResult = JSON.parse(event.data);
          setResult(data);
          
          // Optionally refetch memory history automatically when a new analysis is complete
          if (showMemory && result?.instrument_id) {
            api.getInstrumentMemory(result.instrument_id).then(setMemory);
          }
          
          // Show toast for incremental updates
          const notifType = data.overall_status === 'CRITICAL' ? 'error' as const
            : data.overall_status === 'WARNING' ? 'warning' as const
            : 'success' as const;

          addNotification({
            type: notifType,
            title: `Live Update: ${data.instrument_name}`,
            message: `New log lines analyzed. Status: ${data.overall_status}`
          });
        } catch (err) {
          console.error("Failed to parse SSE data", err);
        }
      };
      
      eventSource.onerror = () => {
        console.error("SSE connection error");
        setIsLive(false);
      };
    }
    
    return () => {
      if (eventSource) {
        eventSource.close();
        setIsLive(false);
      }
    };
  }, [result?.instrument_id, isMonitoring, showMemory, addNotification]);

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
    setMemory(null);
    setShowMemory(false);

    addActivity({
      type: 'LOG_FILE_SUBMITTED',
      message: `Log analysis started`,
      user: 'Current User',
      severity: 'INFO',
      metadata: { filenames: validFiles.map(f => f.name).join(', ') }
    });

    const processLog = async () => {
      try {
        const dashboardResult = await api.analyzeLogs(validFiles);
        setResult(dashboardResult);
        
        updateStats({ 
          activeLogs: stats.activeLogs + validFiles.length,
          detectedIssues: stats.detectedIssues + dashboardResult.critical_incidents + dashboardResult.errors
        });

        // Generate notification based on severity
        const notifType = dashboardResult.overall_status === 'CRITICAL' ? 'error' as const
          : dashboardResult.overall_status === 'WARNING' ? 'warning' as const
          : 'success' as const;

        addNotification({
          type: notifType,
          title: `AI Dashboard: ${dashboardResult.instrument_name}`,
          message: `Critical: ${dashboardResult.critical_incidents} | Warnings: ${dashboardResult.warnings} | Errors: ${dashboardResult.errors} | Healthy: ${dashboardResult.healthy_apps}`
        });
        
        addActivity({
          type: 'MONITORING_COMPLETED',
          message: `Dashboard analysis completed — ${dashboardResult.overall_status}`,
          user: 'System',
          severity: dashboardResult.overall_status === 'CRITICAL' ? 'CRITICAL' : 'SUCCESS',
          metadata: { 
            filenames: validFiles.map(f => f.name).join(', '),
            critical: dashboardResult.critical_incidents,
            warnings: dashboardResult.warnings,
            errors: dashboardResult.errors
          }
        });
      } catch (err) {
        console.error(err);
        setError("Failed to analyze log. Backend API is unreachable.");
        
        addActivity({
          type: 'MONITORING_ERROR',
          message: 'Log analysis failed',
          user: 'System',
          severity: 'ERROR',
          metadata: { filenames: validFiles.map(f => f.name).join(', ') }
        });
      } finally {
        setIsMonitoring(false);
      }
    };

    processLog();
  };

  const handleViewMemory = async () => {
    if (showMemory && result?.instrument_id) {
      setShowMemory(false);
    } else if (result?.instrument_id) {
      setIsLoadingMemory(true);
      try {
        const memoryData = await api.getInstrumentMemory(result.instrument_id);
        setMemory(memoryData);
        setShowMemory(true);
      } catch (err) {
        console.error('Failed to fetch instrument memory:', err);
      } finally {
        setIsLoadingMemory(false);
      }
    }
  };

  const getAnalysisStatusBadge = (result: DashboardResult) => {
  if (!result.analysis_status) return null;
  
  let label = "AI Analysis: Unknown";
  let colorClass = "bg-gray-100 text-gray-800";
  
  switch(result.analysis_status) {
    case 'FULL_AI_ANALYSIS':
      label = "AI Analysis: Complete";
      colorClass = "bg-green-100 text-green-800 border border-green-200";
      break;
    case 'PARTIAL_AI_ANALYSIS':
      label = `AI Analysis: Partial (${result.fallback_chunks || 0}/${result.total_chunks || 0} fallback)`;
      colorClass = "bg-yellow-100 text-yellow-800 border border-yellow-200";
      break;
    case 'DETERMINISTIC_FALLBACK':
      label = "AI Analysis: Fallback";
      colorClass = "bg-orange-100 text-orange-800 border border-orange-200";
      break;
    case 'AI_ANALYSIS_FAILED':
      label = "AI Analysis: Failed";
      colorClass = "bg-red-100 text-red-800 border border-red-200";
      break;
  }
  
  return (
    <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ml-3 ${colorClass}`}>
      {label}
    </span>
  );
};

const getStatusColor = (status: string) => {
    switch (status) {
      case 'CRITICAL': return 'text-red-700 bg-red-50 border-red-200';
      case 'WARNING': return 'text-amber-700 bg-amber-50 border-amber-200';
      default: return 'text-green-700 bg-green-50 border-green-200';
    }
  };

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'CRITICAL': return <AlertCircle className="text-red-600" size={32} />;
      case 'WARNING': return <AlertTriangle className="text-amber-600" size={32} />;
      default: return <ShieldCheck className="text-green-600" size={32} />;
    }
  };

  const getBulletColor = (severity: string | null) => {
    switch (severity) {
      case 'critical': return 'text-red-700 bg-red-50 border-l-red-500';
      case 'warning': return 'text-amber-700 bg-amber-50 border-l-amber-500';
      default: return 'text-slate-700 bg-blue-50 border-l-blue-500';
    }
  };

  return (
    <div className="max-w-5xl mx-auto space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold text-slate-800">Proactive Log Monitoring</h1>
        {result && (
          <Button variant="outline" onClick={handleViewMemory} className="text-sm" isLoading={isLoadingMemory}>
            <History size={16} className="mr-2" /> {showMemory ? 'Hide History' : 'View Analysis History'}
          </Button>
        )}
      </div>

      {/* Upload Form */}
      <Card>
        <CardContent className="p-6">
          <form onSubmit={handleStartMonitoring} className="space-y-4">

            {/* File Upload */}
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

      {/* ===== AI DASHBOARD RESULT ===== */}
      {result && (
        <div className="space-y-6 animate-in fade-in duration-500">
          {/* Overall Status Banner */}
          <Card className={`border-2 ${getStatusColor(result.overall_status)}`}>
            <CardContent className="p-6">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-4">
                  {getStatusIcon(result.overall_status)}
                  <div>
                    <div className="flex items-center gap-2">
                      <h2 className="text-xl font-bold">{result.instrument_name}</h2>
                      {isLive && (
                        <span className="flex items-center text-xs font-medium text-red-600 bg-red-100 px-2 py-0.5 rounded-full animate-pulse">
                          <Radio size={12} className="mr-1" /> LIVE
                        </span>
                      )}
                      {getAnalysisStatusBadge(result)}
                    </div>
                                        <p className="text-sm opacity-75 flex flex-wrap items-center gap-2 mt-0.5">
                      <span>{result.files_analyzed} file(s) monitored • AI continuous diagnostics</span>
                      {result.was_log_reduced && result.analyzed_line_count && result.original_line_count && (
                        <span className="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-normal bg-slate-200/80 text-slate-800 border border-slate-300/60">
                          Analyzed {result.analyzed_line_count.toLocaleString()} of {result.original_line_count.toLocaleString()} lines (diagnostic focus)
                        </span>
                      )}
                    </p>
                  </div>
                </div>
                <Badge variant={
                  result.overall_status === 'CRITICAL' ? 'error' :
                  result.overall_status === 'WARNING' ? 'warning' : 'success'
                }>
                  {result.overall_status}
                </Badge>
              </div>
            </CardContent>
          </Card>

          {/* Stat Cards Grid */}
          <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
            <Card>
              <CardContent className="p-5 text-center">
                <div className="w-10 h-10 rounded-lg flex items-center justify-center bg-red-100 text-red-600 mx-auto mb-2">
                  <Zap size={22} />
                </div>
                <p className="text-3xl font-bold text-red-700">{result.critical_incidents}</p>
                <p className="text-xs font-medium text-slate-500 mt-1 uppercase tracking-wider">Critical Incidents</p>
              </CardContent>
            </Card>

            <Card>
              <CardContent className="p-5 text-center">
                <div className="w-10 h-10 rounded-lg flex items-center justify-center bg-amber-100 text-amber-600 mx-auto mb-2">
                  <AlertTriangle size={22} />
                </div>
                <p className="text-3xl font-bold text-amber-700">{result.warnings}</p>
                <p className="text-xs font-medium text-slate-500 mt-1 uppercase tracking-wider">Warnings</p>
              </CardContent>
            </Card>

            <Card>
              <CardContent className="p-5 text-center">
                <div className="w-10 h-10 rounded-lg flex items-center justify-center bg-orange-100 text-orange-600 mx-auto mb-2">
                  <AlertCircle size={22} />
                </div>
                <p className="text-3xl font-bold text-orange-700">{result.errors}</p>
                <p className="text-xs font-medium text-slate-500 mt-1 uppercase tracking-wider">Errors</p>
              </CardContent>
            </Card>

            <Card>
              <CardContent className="p-5 text-center">
                <div className="w-10 h-10 rounded-lg flex items-center justify-center bg-green-100 text-green-600 mx-auto mb-2">
                  <CheckCircle2 size={22} />
                </div>
                <p className="text-3xl font-bold text-green-700">{result.healthy_apps}</p>
                <p className="text-xs font-medium text-slate-500 mt-1 uppercase tracking-wider">Healthy Apps</p>
              </CardContent>
            </Card>
          </div>

          {/* AI Daily Summary */}
          <Card>
            <CardHeader>
              <CardTitle className="text-base flex items-center gap-2">
                <Activity size={18} className="text-primary-500" />
                AI Generated Daily Summary
              </CardTitle>
            </CardHeader>
            <CardContent className="p-0">
              {result.daily_summary_bullets.length === 0 ? (
                <div className="p-6 text-center text-slate-500">No findings to report.</div>
              ) : (
                <div className="divide-y divide-slate-100">
                  {result.daily_summary_bullets.map((bullet, idx) => (
                    <div
                      key={idx}
                      className={clsx(
                        "px-5 py-3 border-l-4 transition-colors",
                        getBulletColor(bullet.severity)
                      )}
                    >
                      <div className="flex items-start gap-3">
                        <span className="text-sm leading-relaxed">{bullet.text}</span>
                        {bullet.severity && (
                          <Badge
                            variant={
                              bullet.severity === 'critical' ? 'error' :
                              bullet.severity === 'warning' ? 'warning' : 'info'
                            }
                            className="shrink-0 text-xs"
                          >
                            {bullet.severity.toUpperCase()}
                          </Badge>
                        )}
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </CardContent>
          </Card>
        </div>
      )}

      {/* ===== INSTRUMENT MEMORY / HISTORY ===== */}
      {showMemory && memory && (
        <Card className="animate-in fade-in duration-500">
          <CardHeader>
            <div className="flex items-center justify-between">
              <CardTitle className="text-base flex items-center gap-2">
                <History size={18} className="text-primary-500" />
                Analysis History — {memory.instrument_name}
              </CardTitle>
              <Badge variant="default">{memory.total_analyses} analyses</Badge>
            </div>
          </CardHeader>
          <CardContent className="p-0">
            {memory.history.length === 0 ? (
              <div className="p-6 text-center text-slate-500">No analysis history found.</div>
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full text-sm text-left">
                  <thead className="bg-slate-50 text-slate-500 font-medium border-b border-slate-100">
                    <tr>
                      <th className="px-4 py-2">Timestamp</th>
                      <th className="px-4 py-2">File</th>
                      <th className="px-4 py-2 text-center">Critical</th>
                      <th className="px-4 py-2 text-center">Warnings</th>
                      <th className="px-4 py-2 text-center">Errors</th>
                      <th className="px-4 py-2 text-center">Healthy</th>
                      <th className="px-4 py-2">Summary</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-100">
                    {memory.history.map((entry) => (
                      <tr key={entry.id} className="hover:bg-slate-50">
                        <td className="px-4 py-2 text-slate-500 whitespace-nowrap font-mono text-xs">
                          <Clock size={12} className="inline mr-1" />
                          {new Date(entry.analysis_timestamp).toLocaleString()}
                        </td>
                        <td className="px-4 py-2 font-mono text-xs">{entry.log_filename}</td>
                        <td className="px-4 py-2 text-center">
                          <span className={clsx("font-bold", entry.critical_incidents > 0 ? "text-red-600" : "text-slate-400")}>
                            {entry.critical_incidents}
                          </span>
                        </td>
                        <td className="px-4 py-2 text-center">
                          <span className={clsx("font-bold", entry.warnings > 0 ? "text-amber-600" : "text-slate-400")}>
                            {entry.warnings}
                          </span>
                        </td>
                        <td className="px-4 py-2 text-center">
                          <span className={clsx("font-bold", entry.errors > 0 ? "text-orange-600" : "text-slate-400")}>
                            {entry.errors}
                          </span>
                        </td>
                        <td className="px-4 py-2 text-center">
                          <span className="font-bold text-green-600">{entry.healthy_apps}</span>
                        </td>
                        <td className="px-4 py-2 text-slate-600 text-xs max-w-xs truncate">
                          {entry.ai_summary}
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
