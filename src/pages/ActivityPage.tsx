import { Search, Filter, Check, MessageCircle, AlertTriangle, AlertCircle, Info, User, FileText, Activity, FileOutput } from 'lucide-react';
import { useSystem } from '../context/SystemContext';
import { Card, CardContent } from '../components/common/Card';
import { Button } from '../components/common/Button';
import { TextInput } from '../components/common/TextInput';
import { Badge } from '../components/common/Badge';

export function ActivityPage() {
  const { activities } = useSystem();

  const getSeverityIcon = (severity?: string, type?: string) => {
    if (type === 'USER_LOGIN' || type === 'USER_LOGOUT') return <User size={18} className="text-blue-500" />;
    if (type === 'QUERY_SUBMITTED' || type === 'SYSTEM_RESPONSE') return <MessageCircle size={18} className="text-blue-500" />;
    if (type === 'LOG_FILE_SUBMITTED') return <FileText size={18} className="text-blue-500" />;
    if (type === 'MONITORING_STARTED' || type === 'MONITORING_COMPLETED') return <Activity size={18} className="text-green-500" />;
    
    switch (severity) {
      case 'SUCCESS': return <Check size={18} className="text-green-500" />;
      case 'WARNING': return <AlertTriangle size={18} className="text-amber-500" />;
      case 'ERROR': return <AlertCircle size={18} className="text-red-500" />;
      case 'CRITICAL': return <AlertCircle size={18} className="text-red-700" />;
      default: return <Info size={18} className="text-blue-500" />;
    }
  };

  const getSeverityBadgeVariant = (severity?: string) => {
    switch (severity) {
      case 'SUCCESS': return 'success';
      case 'WARNING': return 'warning';
      case 'ERROR': return 'error';
      case 'CRITICAL': return 'error';
      default: return 'default';
    }
  };

  const formatDate = (dateStr: string) => {
    const d = new Date(dateStr);
    return d.toLocaleString('en-GB', { 
      day: 'numeric', month: 'short', year: 'numeric',
      hour: 'numeric', minute: '2-digit', second: '2-digit', hour12: true
    }).replace(',', '');
  };

  return (
    <div className="max-w-4xl mx-auto space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-slate-800">Activity & Traceability</h1>
          <p className="text-slate-500 mt-1">Complete history of important application events</p>
        </div>
        <Button variant="outline">
          <FileOutput size={16} className="mr-2" />
          Export Log
        </Button>
      </div>

      <div className="flex gap-4 mb-6">
        <div className="relative flex-1">
          <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none text-slate-400">
            <Search size={18} />
          </div>
          <TextInput
            className="pl-10"
            placeholder="Search events, users, or details..."
          />
        </div>
        <Button variant="outline">
          <Filter size={18} className="mr-2" />
          Filter
        </Button>
      </div>

      <Card>
        <CardContent className="p-0">
          <div className="divide-y divide-slate-100">
            {activities.length === 0 ? (
              <div className="p-8 text-center text-slate-500">No activities recorded yet.</div>
            ) : (
              activities.map((activity) => (
                <div key={activity.id} className="p-4 hover:bg-slate-50 transition-colors flex gap-4 items-start">
                  <div className="mt-1 shrink-0">
                    {getSeverityIcon(activity.severity, activity.type)}
                  </div>
                  <div className="flex-1 min-w-0">
                    <p className="text-slate-800 font-medium mb-1">{activity.message || activity.type}</p>
                    <div className="flex flex-wrap items-center gap-x-4 gap-y-2 text-sm text-slate-500">
                      <span className="font-medium text-slate-700">{activity.user}</span>
                      <span>{formatDate(activity.timestamp)}</span>
                      <Badge variant={getSeverityBadgeVariant(activity.severity)}>
                        {(activity.severity || 'INFO').toUpperCase()}
                      </Badge>
                    </div>
                    {activity.metadata && Object.keys(activity.metadata).length > 0 && (
                      <div className="mt-2 bg-white border border-slate-100 rounded p-2 text-xs font-mono text-slate-600 overflow-x-auto">
                        {JSON.stringify(activity.metadata)}
                      </div>
                    )}
                  </div>
                </div>
              ))
            )}
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
