import { Activity, MessageSquare, AlertCircle, AlertTriangle, Info, Database } from 'lucide-react';
import { useSystem } from '../context/SystemContext';
import { Card, CardContent, CardHeader, CardTitle } from '../components/common/Card';
import { Badge } from '../components/common/Badge';

export function DashboardPage() {
  const { stats, activities, notifications } = useSystem();

  const displayStats = [
    { title: 'Support Queries', value: stats.supportQueries.toString(), icon: MessageSquare, color: 'text-blue-600', bg: 'bg-blue-100' },
    { title: 'Active Monitoring', value: `${stats.activeLogs} Logs`, icon: Activity, color: 'text-green-600', bg: 'bg-green-100' },
    { title: 'Detected Issues', value: stats.detectedIssues.toString(), icon: AlertCircle, color: 'text-red-600', bg: 'bg-red-100' },
    { title: 'KB Articles', value: stats.kbArticles.toString(), icon: Database, color: 'text-purple-600', bg: 'bg-purple-100' },
  ];

  const recentAlerts = notifications.slice(0, 3);
  const recentActivity = activities.slice(0, 4);

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold text-slate-800">System Overview</h1>
      </div>

      {/* Stats Grid */}
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
        {/* Recent Alerts */}
        <Card>
          <CardHeader>
            <CardTitle>Recent Alerts</CardTitle>
          </CardHeader>
          <CardContent className="p-0">
            {recentAlerts.length === 0 ? (
              <div className="p-6 text-center text-slate-500 text-sm">No recent alerts.</div>
            ) : (
              <div className="divide-y divide-slate-100">
                {recentAlerts.map(notification => (
                    <div key={notification.id} className="flex items-start gap-4 p-4 hover:bg-slate-50 transition-colors">
                      <div className="mt-1">
                        {notification.type === 'error' ? <AlertCircle className="text-red-500" size={20} /> :
                         notification.type === 'warning' ? <AlertTriangle className="text-amber-500" size={20} /> :
                         <Info className="text-blue-500" size={20} />}
                      </div>
                      <div className="flex-1">
                        <div className="flex justify-between items-start">
                          <h4 className={`font-semibold ${
                            notification.type === 'error' ? 'text-red-700' :
                            notification.type === 'warning' ? 'text-amber-700' : 'text-slate-800'
                          }`}>{notification.title}</h4>
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

        {/* Recent Activity */}
        <Card>
          <CardHeader>
            <CardTitle>Recent Activity</CardTitle>
          </CardHeader>
          <CardContent className="p-0">
            {recentActivity.length === 0 ? (
              <div className="p-6 text-center text-slate-500 text-sm">No recent activity.</div>
            ) : (
              <div className="divide-y divide-slate-100">
                {recentActivity.map(activity => (
                    <div key={activity.id} className="flex items-center justify-between p-3 hover:bg-slate-50 rounded-lg transition-colors">
                      <div className="flex items-center gap-3">
                        <div className="w-2 h-2 rounded-full bg-primary-500"></div>
                        <div>
                          <p className="text-sm font-medium text-slate-800">{activity.message}</p>
                          <p className="text-xs text-slate-500">{new Date(activity.timestamp).toLocaleTimeString()} • {activity.user}</p>
                        </div>
                      </div>
                      <Badge variant={
                        activity.type === 'alert' ? 'error' : 
                        activity.type === 'system' ? 'warning' : 'success'
                      }>
                        {activity.type.toUpperCase()}
                      </Badge>
                    </div>
                ))}
              </div>
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
