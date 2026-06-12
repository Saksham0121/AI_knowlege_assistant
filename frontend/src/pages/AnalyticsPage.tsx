import { useQuery } from '@tanstack/react-query';
import {
  AreaChart, Area, BarChart, Bar, PieChart, Pie, Cell,
  XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid,
} from 'recharts';
import { TrendingUp, Users, FileText, MessageSquare, CheckCircle, Zap, ThumbsUp, Award } from 'lucide-react';
import api from '../lib/api';
import { useAuth } from '../lib/auth';
import clsx from 'clsx';

const COLORS = ['#6366f1', '#8b5cf6', '#ec4899', '#f59e0b', '#10b981', '#3b82f6'];

const CustomTooltip = ({ active, payload, label }: any) => {
  if (active && payload?.length) {
    return (
      <div className="glass-card px-3 py-2 text-xs">
        <p className="text-slate-400">{label}</p>
        <p className="text-brand-300 font-medium">{payload[0]?.value}</p>
      </div>
    );
  }
  return null;
};

export default function AnalyticsPage() {
  const { user } = useAuth();
  const { data, isLoading } = useQuery({
    queryKey: ['analytics-dashboard'],
    queryFn: async () => {
      const { data } = await api.get('/analytics/dashboard');
      return data;
    },
    refetchInterval: 30000,
  });

  const stats = data?.stats || {};

  const statCards = [
    { label: 'Total Queries', value: stats.total_queries?.toLocaleString() || '0', icon: MessageSquare, color: 'text-brand-400', bg: 'bg-brand-500/10' },
    { label: 'Total Documents', value: stats.total_documents?.toLocaleString() || '0', icon: FileText, color: 'text-blue-400', bg: 'bg-blue-500/10' },
    { label: 'Active Users', value: stats.total_users?.toLocaleString() || '0', icon: Users, color: 'text-green-400', bg: 'bg-green-500/10' },
    { label: 'Avg Confidence', value: `${stats.avg_confidence || 0}%`, icon: CheckCircle, color: 'text-yellow-400', bg: 'bg-yellow-500/10' },
    { label: 'Success Rate', value: `${stats.success_rate || 0}%`, icon: TrendingUp, color: 'text-emerald-400', bg: 'bg-emerald-500/10' },
    { label: 'Avg Response', value: `${Math.round((stats.avg_retrieval_time_ms || 0) + (stats.avg_generation_time_ms || 0))}ms`, icon: Zap, color: 'text-orange-400', bg: 'bg-orange-500/10' },
    { label: 'Positive Feedback', value: `${data?.positive_feedback_rate || 0}%`, icon: ThumbsUp, color: 'text-pink-400', bg: 'bg-pink-500/10' },
    { label: 'Departments', value: data?.department_stats?.length || 0, icon: Award, color: 'text-purple-400', bg: 'bg-purple-500/10' },
  ];

  if (isLoading) {
    return (
      <div className="page-wrapper">
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
          {[...Array(8)].map((_, i) => <div key={i} className="skeleton h-24 rounded-2xl" />)}
        </div>
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {[...Array(4)].map((_, i) => <div key={i} className="skeleton h-72 rounded-2xl" />)}
        </div>
      </div>
    );
  }

  return (
    <div className="page-wrapper">
      <div className="section-header">
        <div>
          <h2 className="section-title">Analytics Dashboard</h2>
          <p className="text-sm text-slate-400">{user?.role === 'manager' ? `${user.department} department` : 'Global'} insights</p>
        </div>
      </div>

      {/* Stat Grid */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-8">
        {statCards.map(({ label, value, icon: Icon, color, bg }) => (
          <div key={label} className="stat-card animate-fade-in">
            <div className={clsx('w-9 h-9 rounded-xl flex items-center justify-center mb-3', bg)}>
              <Icon className={clsx('w-4.5 h-4.5', color)} />
            </div>
            <div className="stat-value text-2xl">{value}</div>
            <div className="stat-label">{label}</div>
          </div>
        ))}
      </div>

      {/* Charts Row 1 */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-6">
        {/* Query Trend */}
        <div className="glass-card p-5">
          <h3 className="font-medium text-white mb-4 text-sm">Query Trend (30 days)</h3>
          <ResponsiveContainer width="100%" height={200}>
            <AreaChart data={data?.query_trend || []}>
              <defs>
                <linearGradient id="trendGrad" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="#6366f1" stopOpacity={0.3} />
                  <stop offset="95%" stopColor="#6366f1" stopOpacity={0} />
                </linearGradient>
              </defs>
              <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" />
              <XAxis dataKey="date" tick={{ fill: '#64748b', fontSize: 10 }} tickFormatter={v => v.slice(5)} />
              <YAxis tick={{ fill: '#64748b', fontSize: 10 }} />
              <Tooltip content={<CustomTooltip />} />
              <Area type="monotone" dataKey="count" stroke="#6366f1" fill="url(#trendGrad)" strokeWidth={2} />
            </AreaChart>
          </ResponsiveContainer>
        </div>

        {/* Department Usage */}
        <div className="glass-card p-5">
          <h3 className="font-medium text-white mb-4 text-sm">Department Activity</h3>
          <ResponsiveContainer width="100%" height={200}>
            <BarChart data={data?.department_stats || []} layout="vertical">
              <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" />
              <XAxis type="number" tick={{ fill: '#64748b', fontSize: 10 }} />
              <YAxis dataKey="department" type="category" tick={{ fill: '#94a3b8', fontSize: 10 }} width={80} />
              <Tooltip content={<CustomTooltip />} />
              <Bar dataKey="query_count" radius={[0, 4, 4, 0]}>
                {(data?.department_stats || []).map((_: any, i: number) => (
                  <Cell key={i} fill={COLORS[i % COLORS.length]} />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </div>
      </div>

      {/* Charts Row 2 */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Top Documents */}
        <div className="glass-card p-5">
          <h3 className="font-medium text-white mb-4 text-sm">Most Referenced Documents</h3>
          <div className="space-y-3">
            {(data?.top_documents || []).slice(0, 6).map((doc: any, i: number) => (
              <div key={doc.document_id} className="flex items-center gap-3">
                <span className="text-xs font-bold text-slate-600 w-5">{i + 1}</span>
                <div className="flex-1 min-w-0">
                  <p className="text-xs text-white truncate">{doc.title || doc.filename}</p>
                  <div className="h-1 bg-surface-50 rounded-full mt-1 overflow-hidden">
                    <div
                      className="h-full bg-brand-gradient rounded-full"
                      style={{ width: `${Math.min(100, (doc.reference_count / ((data?.top_documents?.[0]?.reference_count || 1))) * 100)}%` }}
                    />
                  </div>
                </div>
                <span className="text-xs text-slate-500 shrink-0">{doc.reference_count}x</span>
              </div>
            ))}
            {(!data?.top_documents || data.top_documents.length === 0) && (
              <p className="text-xs text-slate-600 text-center py-4">No data yet — start asking questions!</p>
            )}
          </div>
        </div>

        {/* Dept Distribution Pie */}
        <div className="glass-card p-5">
          <h3 className="font-medium text-white mb-4 text-sm">Department Query Distribution</h3>
          {(data?.department_stats || []).length > 0 ? (
            <div className="flex items-center gap-6">
              <ResponsiveContainer width="60%" height={180}>
                <PieChart>
                  <Pie
                    data={data?.department_stats || []}
                    dataKey="query_count"
                    nameKey="department"
                    cx="50%" cy="50%"
                    innerRadius={45} outerRadius={75}
                    paddingAngle={2}
                  >
                    {(data?.department_stats || []).map((_: any, i: number) => (
                      <Cell key={i} fill={COLORS[i % COLORS.length]} />
                    ))}
                  </Pie>
                  <Tooltip content={<CustomTooltip />} />
                </PieChart>
              </ResponsiveContainer>
              <div className="flex-1 space-y-2">
                {(data?.department_stats || []).slice(0, 5).map((d: any, i: number) => (
                  <div key={d.department} className="flex items-center gap-2">
                    <div className="w-2.5 h-2.5 rounded-full shrink-0" style={{ backgroundColor: COLORS[i % COLORS.length] }} />
                    <span className="text-xs text-slate-300 truncate flex-1">{d.department}</span>
                    <span className="text-xs text-slate-500">{d.query_count}</span>
                  </div>
                ))}
              </div>
            </div>
          ) : (
            <div className="flex items-center justify-center h-40">
              <p className="text-xs text-slate-600">No query data yet</p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
