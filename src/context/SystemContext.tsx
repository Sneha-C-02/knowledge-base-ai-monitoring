import { createContext, useContext, useState, useEffect } from 'react';
import type { ReactNode } from 'react';
import { api } from '../api/client';
import type { ActivityLog, Notification, SystemStats } from '../types';
import { useAuth } from './AuthContext';

interface SystemContextType {
  activities: ActivityLog[];
  notifications: Notification[];
  stats: SystemStats;
  isLoaded: boolean;
  addActivity: (activity: Omit<ActivityLog, 'id' | 'timestamp'>) => void;
  addNotification: (notification: Omit<Notification, 'id' | 'timestamp' | 'read'>) => void;
  markNotificationRead: (id: string) => void;
  clearNotifications: () => void;
  updateStats: (updates: Partial<SystemStats>) => void;
}

const SystemContext = createContext<SystemContextType | undefined>(undefined);

export function SystemProvider({ children }: { children: ReactNode }) {
  const [activities, setActivities] = useState<ActivityLog[]>([]);
  const [notifications, setNotifications] = useState<Notification[]>([]);
  const [stats, setStats] = useState<SystemStats>({
    supportQueries: 0,
    activeLogs: 0,
    detectedIssues: 0,
    kbArticles: 0
  });
  const [isLoaded, setIsLoaded] = useState(false);

  const { isAuthenticated } = useAuth();

  useEffect(() => {
    let mounted = true;

    const fetchData = async () => {
      if (!isAuthenticated) return;
      try {
        const [acts, notifs, st] = await Promise.all([
          api.getActivities().catch(() => []),
          api.getNotifications().catch(() => []),
          api.getStats().catch(() => ({ supportQueries: 0, activeLogs: 0, detectedIssues: 0, kbArticles: 0 }))
        ]);
        
        if (mounted) {
          setActivities(acts);
          setNotifications(notifs);
          setStats(st);
          setIsLoaded(true);
        }
      } catch (err) {
        console.error("Failed to fetch system data", err);
        if (mounted) setIsLoaded(true);
      }
    };

    fetchData();
    
    // Simulate polling for real-time updates until WebSockets are implemented
    const interval = setInterval(fetchData, 30000);

    return () => {
      mounted = false;
      clearInterval(interval);
    };
  }, [isAuthenticated]);

  // These functions would typically trigger POST requests to the backend
  const addActivity = (activity: Omit<ActivityLog, 'id' | 'timestamp'>) => {
    // Optimistic UI update
    const newActivity: ActivityLog = {
      ...activity,
      id: Math.random().toString(36).substr(2, 9),
      timestamp: new Date().toISOString(),
    };
    setActivities(prev => [newActivity, ...prev]);

    // Persist to backend
    api.createActivity(activity.type, activity.message, activity.severity, activity.metadata).catch(err => {
      console.error("Failed to persist activity to backend", err);
    });
  };

  const addNotification = (notification: Omit<Notification, 'id' | 'timestamp' | 'read'>) => {
    const newNotification: Notification = {
      ...notification,
      id: Math.random().toString(36).substr(2, 9),
      timestamp: new Date().toISOString(),
      read: false,
    };
    setNotifications(prev => [newNotification, ...prev]);

    // Log the notification generation as an activity
    api.createActivity('system', 'NOTIFICATION_GENERATED').catch(err => {
      console.error("Failed to log notification activity", err);
    });
  };

  const markNotificationRead = (id: string) => {
    setNotifications(prev => prev.map(n => n.id === id ? { ...n, read: true } : n));
  };

  const clearNotifications = () => {
    setNotifications([]);
  };

  const updateStats = (updates: Partial<SystemStats>) => {
    setStats(prev => ({ ...prev, ...updates }));
  };

  return (
    <SystemContext.Provider value={{
      activities,
      notifications,
      stats,
      isLoaded,
      addActivity,
      addNotification,
      markNotificationRead,
      clearNotifications,
      updateStats
    }}>
      {children}
    </SystemContext.Provider>
  );
}

export function useSystem() {
  const context = useContext(SystemContext);
  if (context === undefined) {
    throw new Error('useSystem must be used within a SystemProvider');
  }
  return context;
}
