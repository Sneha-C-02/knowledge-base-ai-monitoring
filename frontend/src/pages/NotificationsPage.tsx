import { Bell, AlertTriangle, ShieldCheck, AlertCircle } from 'lucide-react';
import { useSystem } from '../context/SystemContext';
import { Card, CardContent } from '../components/common/Card';
import { Button } from '../components/common/Button';

export function NotificationsPage() {
  const { notifications, markNotificationRead, clearNotifications, addActivity } = useSystem();

  const handleMarkAllAsRead = () => {
    notifications.forEach(n => {
      if (!n.read) markNotificationRead(n.id);
    });
  };

  const handleNotificationClick = (notification: any) => {
    if (!notification.read) {
      markNotificationRead(notification.id);
      
      addActivity({
        type: 'NOTIFICATION_READ',
        message: 'User viewed notification',
        user: 'Current User',
        severity: 'INFO',
        metadata: { notification_id: notification.id, title: notification.title }
      });
    }
  };

  const getIcon = (type: string) => {
    switch (type) {
      case 'CRITICAL': return <AlertCircle className="text-red-600" size={24} />;
      case 'WARNING': return <AlertTriangle className="text-yellow-600" size={24} />;
      case 'INFO': return <Bell className="text-blue-600" size={24} />;
      case 'ERROR': return <AlertTriangle className="text-red-600" size={24} />;
      default: return <ShieldCheck className="text-green-600" size={24} />;
    }
  };

  return (
    <div className="max-w-4xl mx-auto space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold text-slate-800">Notifications</h1>
        <div className="flex gap-2">
          <Button variant="secondary" onClick={handleMarkAllAsRead}>
            Mark all as read
          </Button>
          <Button variant="danger" onClick={clearNotifications}>
            Clear All
          </Button>
        </div>
      </div>

      <Card>
        <CardContent className="p-0">
          {notifications.length === 0 ? (
            <div className="p-8 text-center text-slate-500">No notifications yet. Monitor a log file to generate alerts.</div>
          ) : (
            <div className="divide-y divide-slate-100">
              {notifications.map(notif => (
                <div key={notif.id} onClick={() => handleNotificationClick(notif)} className={`p-4 flex gap-4 cursor-pointer hover:bg-slate-100 transition-colors ${notif.read ? 'bg-white opacity-70' : 'bg-slate-50'}`}>
                <div className="shrink-0 mt-1">
                  {getIcon(notif.type)}
                </div>
                <div className="flex-1 min-w-0">
                  <div className="flex items-center justify-between mb-1">
                    <h3 className={`font-semibold text-lg truncate ${
                      notif.type === 'error' ? 'text-red-700' :
                      notif.type === 'warning' ? 'text-amber-700' :
                      notif.type === 'success' ? 'text-green-700' : 'text-slate-800'
                    }`}>
                      {notif.title}
                    </h3>
                    <span className="text-sm font-mono text-slate-400 shrink-0 ml-4">
                      {new Date(notif.timestamp).toLocaleString()}
                    </span>
                  </div>
                  <p className="text-slate-600 mb-3">{notif.message}</p>
                  
                  {!notif.read && (
                    <Button variant="secondary" onClick={() => markNotificationRead(notif.id)}>
                      Mark as Read
                    </Button>
                  )}
                </div>
              </div>
            ))}
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
