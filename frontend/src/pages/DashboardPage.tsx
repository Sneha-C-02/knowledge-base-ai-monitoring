import { useState } from "react";
import { Activity, MessageSquare, AlertCircle, AlertTriangle, Info, Database, Brain, X, Zap, CheckCircle2, Upload, FileText } from "lucide-react";
import { useSystem } from "../context/SystemContext";
import { useMonitoring } from "../context/MonitoringContext";
import { Card, CardContent, CardHeader, CardTitle } from "../components/common/Card";
import { Badge } from "../components/common/Badge";

export function DashboardPage() {
  const { stats, activities, notifications } = useSystem();
  const { result, setLogFiles, isMonitoring, error, runCompleteAnalysis } = useMonitoring();
  const [showAiSummary, setShowAiSummary] = useState(false);
  const [selectedFile, setSelectedFile] = useState<File | null>(null);

  const displayStats = [
    { title: "Support Queries", value: stats.supportQueries.toString(), icon: MessageSquare, color: "text-blue-600", bg: "bg-blue-100" },
    { title: "Active Monitoring", value: `${stats.activeLogs} Logs`, icon: Activity, color: "text-green-600", bg: "bg-green-100" },
    { title: "Detected Issues", value: stats.detectedIssues.toString(), icon: AlertCircle, color: "text-red-600", bg: "bg-red-100" },
    { title: "KB Articles", value: stats.kbArticles.toString(), icon: Database, color: "text-purple-600", bg: "bg-purple-100" },
  ];

  const recentAlerts = notifications.slice(0, 3);
  const recentActivity = activities.slice(0, 4);

  const getSeverityColor = (severity: string | null) => {
    switch (severity) {
      case "critical":
        return "border-l-red-500 bg-red-50 text-red-700";
      case "warning":
        return "border-l-amber-500 bg-amber-50 text-amber-700";
      default:
        return "border-l-blue-500 bg-blue-50 text-slate-700";
    }
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case "CRITICAL":
        return "bg-red-100 text-red-700 border-red-200";
      case "WARNING":
        return "bg-amber-100 text-amber-700 border-amber-200";
      default:
        return "bg-green-100 text-green-700 border-green-200";
    }
  };

  const handleFileChange = (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0] || null;
    setSelectedFile(file);
    setLogFiles([file]);
  };

  const handleAnalyze = async () => {
    if (!selectedFile) return;
    await runCompleteAnalysis();
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold text-slate-800">System Overview</h1>
        <button type="button" onClick={() => setShowAiSummary(true)} className="flex items-center gap-2 px-4 py-2 rounded-lg bg-primary-600 text-white font-medium hover:bg-primary-700 transition-colors shadow-sm">
          <Brain size={18} />
          AI Log Monitoring
        </button>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        {displayStats.map((stat) => (
          <Card key={stat.title}>
            <CardContent className="p-6 flex items-center gap-4">
              <div className={`w-12 h-12 rounded-lg flex items-center justify-center ${stat.bg} ${stat.color}`}>
                <stat.icon size={24} />
              </div>
              <div>
                <p className="text-sm font-medium text-slate-500">{stat.title}</p>
                <p className="text-2xl font-bold text-slate-800">{stat.value}</p>
              </div>
            </CardContent>
          </Card>
        ))}
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <Card>
          <CardHeader>
            <CardTitle>Recent Alerts</CardTitle>
          </CardHeader>
          <CardContent className="p-0">
            {recentAlerts.length === 0 ? (
              <div className="p-6 text-center text-slate-500 text-sm">No recent alerts.</div>
            ) : (
              <div className="divide-y divide-slate-100">
                {recentAlerts.map((notification) => (
                  <div key={notification.id} className="flex items-start gap-4 p-4 hover:bg-slate-50 transition-colors">
                    <div className="mt-1">
                      {notification.type === "error" ? (
                        <AlertCircle className="text-red-500" size={20} />
                      ) : notification.type === "warning" ? (
                        <AlertTriangle className="text-amber-500" size={20} />
                      ) : (
                        <Info className="text-blue-500" size={20} />
                      )}
                    </div>
                    <div className="flex-1">
                      <div className="flex justify-between items-start">
                        <h4 className={`font-semibold ${notification.type === "error" ? "text-red-700" : notification.type === "warning" ? "text-amber-700" : "text-slate-800"}`}>
                          {notification.title}
                        </h4>
                        <span className="text-xs text-slate-400 font-mono">{new Date(notification.timestamp).toLocaleTimeString()}</span>
                      </div>
                      <p className="text-sm text-slate-600 mt-1">{notification.message}</p>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Recent Activity</CardTitle>
          </CardHeader>
          <CardContent className="p-0">
            {recentActivity.length === 0 ? (
              <div className="p-6 text-center text-slate-500 text-sm">No recent activity.</div>
            ) : (
              <div className="divide-y divide-slate-100">
                {recentActivity.map((activity) => (
                  <div key={activity.id} className="flex items-center justify-between p-3 hover:bg-slate-50 rounded-lg transition-colors">
                    <div className="flex items-center gap-3">
                      <div className="w-2 h-2 rounded-full bg-primary-500"></div>
                      <div>
                        <p className="text-sm font-medium text-slate-800">{activity.message}</p>
                        <p className="text-xs text-slate-500">{new Date(activity.timestamp).toLocaleTimeString()} • {activity.user}</p>
                      </div>
                    </div>
                    <Badge variant={activity.type === "alert" ? "error" : activity.type === "system" ? "warning" : "success"}>
                      {activity.type.toUpperCase()}
                    </Badge>
                  </div>
                ))}
              </div>
            )}
          </CardContent>
        </Card>
      </div>

      {showAiSummary && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4">
          <div className="w-full max-w-5xl max-h-[90vh] overflow-y-auto rounded-xl bg-white shadow-2xl">
            <div className="sticky top-0 z-10 flex items-center justify-between border-b border-slate-200 bg-white px-6 py-4">
              <div>
                <div className="flex items-center gap-2">
                  <Brain className="text-primary-600" size={24} />
                  <h2 className="text-xl font-bold text-slate-800">AI Log Operations Dashboard</h2>
                </div>
                {result && <p className="text-sm text-slate-500 mt-1">{result.instrument_name}</p>}
              </div>
              <button type="button" onClick={() => setShowAiSummary(false)} className="p-2 rounded-lg text-slate-400 hover:text-slate-700 hover:bg-slate-100 transition-colors">
                <X size={22} />
              </button>
            </div>

            <div className="p-6 space-y-6">
              <Card>
                <CardHeader>
                  <CardTitle className="flex items-center gap-2">
                    <Upload size={18} className="text-primary-600" />
                    Upload Log File
                  </CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="flex flex-col md:flex-row gap-4 items-start md:items-center">
                    <label className="flex-1 w-full cursor-pointer">
                      <div className="border-2 border-dashed border-slate-300 rounded-lg p-6 text-center hover:border-primary-500 hover:bg-slate-50 transition-colors">
                        <FileText className="mx-auto text-slate-400 mb-2" size={32} />
                        <p className="text-sm font-medium text-slate-700">{selectedFile ? selectedFile.name : "Click to select a log file"}</p>
                        <p className="text-xs text-slate-500 mt-1">Select the log file you want the AI to analyze</p>
                      </div>
                      <input type="file" className="hidden" onChange={handleFileChange} />
                    </label>

                    <button type="button" onClick={handleAnalyze} disabled={!selectedFile || isMonitoring} className="w-full md:w-auto px-5 py-3 rounded-lg bg-primary-600 text-white font-medium hover:bg-primary-700 disabled:bg-slate-300 disabled:cursor-not-allowed transition-colors">
                      {isMonitoring ? "Analyzing..." : "Analyze Log"}
                    </button>
                  </div>

                  {error && <p className="mt-3 text-sm text-red-600">{error}</p>}
                </CardContent>
              </Card>

              {!result ? (
                <div className="p-8 text-center">
                  <Brain className="mx-auto text-slate-300" size={56} />
                  <h3 className="mt-4 text-lg font-semibold text-slate-700">Upload a log to start AI analysis</h3>
                  <p className="mt-2 text-sm text-slate-500 max-w-md mx-auto">Select a log file above and click Analyze Log. The AI analysis will appear here.</p>
                </div>
              ) : (
                <>
                  <div className="flex items-center justify-between">
                    <div>
                      <p className="text-sm text-slate-500">Overall Monitoring Status</p>
                      <p className="text-lg font-semibold text-slate-800 mt-1">{result.instrument_name}</p>
                    </div>
                    <span className={`px-3 py-1.5 rounded-full border text-sm font-semibold ${getStatusColor(result.overall_status)}`}>
                      {result.overall_status}
                    </span>
                  </div>

                  <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
                    <Card>
                      <CardContent className="p-5 text-center">
                        <div className="w-10 h-10 rounded-lg flex items-center justify-center bg-red-100 text-red-600 mx-auto mb-2"><Zap size={22} /></div>
                        <p className="text-3xl font-bold text-red-700">{result.critical_incidents}</p>
                        <p className="text-xs font-medium text-slate-500 mt-1 uppercase tracking-wider">Critical Incidents</p>
                      </CardContent>
                    </Card>

                    <Card>
                      <CardContent className="p-5 text-center">
                        <div className="w-10 h-10 rounded-lg flex items-center justify-center bg-amber-100 text-amber-600 mx-auto mb-2"><AlertTriangle size={22} /></div>
                        <p className="text-3xl font-bold text-amber-700">{result.warnings}</p>
                        <p className="text-xs font-medium text-slate-500 mt-1 uppercase tracking-wider">Warnings</p>
                      </CardContent>
                    </Card>

                    <Card>
                      <CardContent className="p-5 text-center">
                        <div className="w-10 h-10 rounded-lg flex items-center justify-center bg-orange-100 text-orange-600 mx-auto mb-2"><AlertCircle size={22} /></div>
                        <p className="text-3xl font-bold text-orange-700">{result.errors}</p>
                        <p className="text-xs font-medium text-slate-500 mt-1 uppercase tracking-wider">Errors</p>
                      </CardContent>
                    </Card>

                    <Card>
                      <CardContent className="p-5 text-center">
                        <div className="w-10 h-10 rounded-lg flex items-center justify-center bg-green-100 text-green-600 mx-auto mb-2"><CheckCircle2 size={22} /></div>
                        <p className="text-3xl font-bold text-green-700">{result.healthy_apps}</p>
                        <p className="text-xs font-medium text-slate-500 mt-1 uppercase tracking-wider">Healthy Apps</p>
                      </CardContent>
                    </Card>
                  </div>

                  <Card>
                    <CardHeader>
                      <CardTitle className="flex items-center gap-2">
                        <Activity size={18} className="text-primary-600" />
                        AI Generated Daily Summary
                      </CardTitle>
                    </CardHeader>
                    <CardContent className="p-0">
                      {result.daily_summary_bullets.length === 0 ? (
                        <div className="p-6 text-center text-slate-500">No findings to report.</div>
                      ) : (
                        <div className="divide-y divide-slate-100">
                          {result.daily_summary_bullets.map((bullet, index) => (
                            <div key={index} className={`border-l-4 px-5 py-4 ${getSeverityColor(bullet.severity)}`}>
                              <div className="flex items-start gap-3">
                                <span className="font-bold text-sm">{index + 1}.</span>
                                <div className="flex-1">
                                  <p className="text-sm font-medium leading-relaxed">{bullet.pattern_name ? `[${bullet.pattern_name}] ` : ""}{bullet.text}</p>

                                  {bullet.confidence_score !== undefined && (
                                    <div className="mt-2 flex items-center gap-2 text-xs text-slate-600">
                                      <span className="font-semibold">AI Confidence:</span>
                                      <div className="w-24 h-2 bg-slate-200 rounded-full overflow-hidden">
                                        <div className="h-full bg-primary-500" style={{ width: `${Math.min(Math.max(bullet.confidence_score, 0), 100)}%` }} />
                                      </div>
                                      <span>{bullet.confidence_score}%</span>
                                    </div>
                                  )}

                                  {bullet.possible_root_causes && bullet.possible_root_causes.length > 0 && (
                                    <div className="mt-2 text-xs text-slate-600">
                                      <span className="font-semibold">Possible Root Causes:</span>
                                      <ul className="list-disc list-inside mt-1">
                                        {bullet.possible_root_causes.map((cause, causeIndex) => <li key={causeIndex}>{cause}</li>)}
                                      </ul>
                                    </div>
                                  )}
                                </div>

                                {bullet.severity && (
                                  <Badge variant={bullet.severity === "critical" ? "error" : bullet.severity === "warning" ? "warning" : "info"}>
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

                  <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
                    <div className="rounded-lg bg-slate-50 border border-slate-200 p-3">
                      <p className="text-xs text-slate-500">Files Analyzed</p>
                      <p className="text-lg font-bold text-slate-800">{result.files_analyzed}</p>
                    </div>

                    <div className="rounded-lg bg-slate-50 border border-slate-200 p-3">
                      <p className="text-xs text-slate-500">Analysis Status</p>
                      <p className="text-sm font-bold text-slate-800 mt-1">{result.analysis_status || "N/A"}</p>
                    </div>

                    <div className="rounded-lg bg-slate-50 border border-slate-200 p-3">
                      <p className="text-xs text-slate-500">Lines Analyzed</p>
                      <p className="text-lg font-bold text-slate-800">{result.analyzed_line_count?.toLocaleString() ?? 0}</p>
                    </div>

                    <div className="rounded-lg bg-slate-50 border border-slate-200 p-3">
                      <p className="text-xs text-slate-500">Coverage</p>
                      <p className="text-sm font-bold text-slate-800 mt-1">{result.coverage_mode === "fast" ? "FAST" : "EXHAUSTIVE"}</p>
                    </div>
                  </div>

                  {result.complete_findings && result.complete_findings.length > 0 && (
                    <Card>
                      <CardHeader>
                        <CardTitle>Detected Findings</CardTitle>
                      </CardHeader>
                      <CardContent className="space-y-3">
                        {result.complete_findings.map((finding, index) => (
                          <div key={index} className="border border-slate-200 rounded-lg p-4">
                            <div className="flex justify-between gap-4">
                              <div>
                                <p className="text-sm font-semibold text-slate-800">{finding.filename} — Line {finding.line_number}</p>
                                <p className="text-sm text-slate-600 mt-1">{finding.snippet}</p>
                              </div>
                              <Badge variant={finding.severity === "critical" ? "error" : finding.severity === "warning" ? "warning" : "info"}>
                                {finding.severity.toUpperCase()}
                              </Badge>
                            </div>
                            <p className="text-sm text-slate-600 mt-3">{finding.explanation}</p>
                            <p className="text-xs text-slate-500 mt-2">Detected by: {finding.detected_by}</p>
                          </div>
                        ))}
                      </CardContent>
                    </Card>
                  )}
                </>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}