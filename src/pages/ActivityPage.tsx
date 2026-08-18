import { Search, History, Filter } from 'lucide-react';
import { useSystem } from '../context/SystemContext';
import { Card, CardContent } from '../components/common/Card';
import { Button } from '../components/common/Button';
import { TextInput } from '../components/common/TextInput';
import { Badge } from '../components/common/Badge';

export function ActivityPage() {
  const { activities } = useSystem();

  return (
    <div className="max-w-6xl mx-auto space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold text-slate-800">Activity & Traceability</h1>
        <Button variant="outline">
          <History size={16} className="mr-2" />
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
          <div className="overflow-x-auto">
            <table className="w-full text-left border-collapse">
                <thead>
                  <tr className="bg-slate-50 border-b border-slate-200">
                    <th className="py-3 px-4 font-semibold text-slate-600">Timestamp</th>
                    <th className="py-3 px-4 font-semibold text-slate-600">Message</th>
                    <th className="py-3 px-4 font-semibold text-slate-600">User</th>
                    <th className="py-3 px-4 font-semibold text-slate-600">Type</th>
                    <th className="py-3 px-4 font-semibold text-slate-600">Metadata</th>
                  </tr>
                </thead>
                <tbody>
                  {activities.map((activity) => (
                    <tr key={activity.id} className="border-b border-slate-100 hover:bg-slate-50 transition-colors">
                      <td className="py-3 px-4 text-slate-600">{new Date(activity.timestamp).toLocaleString()}</td>
                      <td className="py-3 px-4 font-medium text-slate-800">{activity.message}</td>
                      <td className="py-3 px-4 text-slate-600">{activity.user}</td>
                      <td className="py-3 px-4">
                        <Badge variant={
                          activity.type === 'alert' ? 'error' :
                          activity.type === 'system' ? 'warning' :
                          activity.type === 'search' ? 'default' : 'success'
                        }>
                          {activity.type.toUpperCase()}
                        </Badge>
                      </td>
                      <td className="py-3 px-4 text-sm text-slate-500 max-w-xs truncate">
                        {JSON.stringify(activity.metadata || {})}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
