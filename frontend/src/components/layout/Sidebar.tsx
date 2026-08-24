import { NavLink } from 'react-router-dom';
import { LayoutDashboard, MessageSquare, Activity, BookOpen, Bell, History } from 'lucide-react';
import { clsx } from 'clsx';

const navItems = [
  { name: 'Dashboard', path: '/dashboard', icon: LayoutDashboard },
  { name: 'Reactive Support', path: '/support', icon: MessageSquare },
  { name: 'Log Monitoring', path: '/monitoring', icon: Activity },
  { name: 'Knowledge Base', path: '/knowledge-base', icon: BookOpen },
  { name: 'Notifications', path: '/notifications', icon: Bell },
  { name: 'Activity', path: '/activity', icon: History }
];

export function Sidebar() {
  return (
    <aside className="w-64 bg-surface-dark text-slate-300 flex flex-col h-screen fixed top-0 left-0">
      <div className="h-16 flex items-center px-6 border-b border-slate-700">
        <span className="text-lg font-bold text-white">Knowledge Base AI</span>
      </div>
      <nav className="flex-1 py-4 flex flex-col gap-1 px-3">
        {navItems.map((item) => (
          <NavLink
            key={item.name}
            to={item.path}
            className={({ isActive }) => clsx(
              "flex items-center gap-3 px-3 py-2 rounded-md transition-colors",
              isActive 
                ? "bg-primary-600 text-white" 
                : "hover:bg-slate-800 hover:text-white"
            )}
          >
            <item.icon size={20} />
            {item.name}
          </NavLink>
        ))}
      </nav>
    </aside>
  );
}
