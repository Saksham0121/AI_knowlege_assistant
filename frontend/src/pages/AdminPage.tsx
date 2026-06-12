import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { Users, Shield, Settings, Trash2, Edit3, ChevronDown, Check } from 'lucide-react';
import api from '../lib/api';
import { useAuth } from '../lib/auth';
import toast from 'react-hot-toast';
import clsx from 'clsx';

const ROLES = ['employee', 'manager', 'admin'];
const DEPARTMENTS = ['HR', 'Finance', 'Legal', 'Engineering', 'Marketing', 'Operations', 'General'];

export default function AdminPage() {
  const { user } = useAuth();
  const qc = useQueryClient();
  const [activeTab, setActiveTab] = useState<'users' | 'settings'>('users');
  const [editingUser, setEditingUser] = useState<string | null>(null);
  const [editForm, setEditForm] = useState<{ role: string; department: string; is_active: boolean }>({ role: 'employee', department: 'General', is_active: true });

  if (user?.role !== 'admin') {
    return (
      <div className="page-wrapper flex items-center justify-center">
        <div className="text-center">
          <Shield className="w-12 h-12 text-slate-600 mx-auto mb-3" />
          <p className="text-slate-400">Admin access required</p>
        </div>
      </div>
    );
  }

  const { data: usersData, isLoading } = useQuery({
    queryKey: ['admin-users'],
    queryFn: async () => {
      const { data } = await api.get('/admin/users?page_size=50');
      return data;
    },
  });

  const { data: settingsData } = useQuery({
    queryKey: ['admin-settings'],
    queryFn: async () => {
      const { data } = await api.get('/admin/settings');
      return data;
    },
  });

  const updateMutation = useMutation({
    mutationFn: async ({ userId, updates }: { userId: string; updates: any }) => {
      const { data } = await api.patch(`/admin/users/${userId}`, updates);
      return data;
    },
    onSuccess: () => { qc.invalidateQueries({ queryKey: ['admin-users'] }); toast.success('User updated'); setEditingUser(null); },
    onError: () => toast.error('Update failed'),
  });

  const deleteMutation = useMutation({
    mutationFn: (userId: string) => api.delete(`/admin/users/${userId}`),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ['admin-users'] }); toast.success('User deleted'); },
    onError: () => toast.error('Delete failed'),
  });

  return (
    <div className="page-wrapper">
      <div className="section-header">
        <h2 className="section-title">Admin Panel</h2>
      </div>

      {/* Tabs */}
      <div className="flex gap-1 mb-6 glass-card p-1 w-fit">
        {(['users', 'settings'] as const).map(tab => (
          <button
            key={tab}
            onClick={() => setActiveTab(tab)}
            className={clsx(
              'flex items-center gap-2 px-4 py-2 rounded-xl text-sm font-medium transition-all',
              activeTab === tab ? 'bg-brand-gradient text-white shadow-glow-sm' : 'text-slate-400 hover:text-white'
            )}
          >
            {tab === 'users' ? <Users className="w-4 h-4" /> : <Settings className="w-4 h-4" />}
            {tab.charAt(0).toUpperCase() + tab.slice(1)}
          </button>
        ))}
      </div>

      {/* Users Tab */}
      {activeTab === 'users' && (
        <div className="glass-card overflow-hidden">
          <div className="p-4 border-b border-glass-border flex items-center justify-between">
            <span className="text-sm font-medium text-white">{usersData?.total || 0} Users</span>
          </div>
          {isLoading ? (
            <div className="p-4 space-y-3">
              {[...Array(5)].map((_, i) => <div key={i} className="skeleton h-14 rounded-xl" />)}
            </div>
          ) : (
            <div className="divide-y divide-glass-border">
              {usersData?.users?.map((u: any) => (
                <div key={u.id} className="flex items-center gap-4 p-4 hover:bg-glass-hover transition-colors">
                  <div className="w-9 h-9 rounded-full bg-brand-gradient flex items-center justify-center text-white text-sm font-bold shrink-0">
                    {u.name?.charAt(0)}
                  </div>
                  <div className="flex-1 min-w-0">
                    <p className="text-sm font-medium text-white truncate">{u.name}</p>
                    <p className="text-xs text-slate-500 truncate">{u.email}</p>
                  </div>

                  {editingUser === u.id ? (
                    <div className="flex items-center gap-2">
                      <select value={editForm.role} onChange={e => setEditForm(f => ({ ...f, role: e.target.value }))}
                        className="input py-1.5 text-xs w-28">
                        {ROLES.map(r => <option key={r} value={r}>{r}</option>)}
                      </select>
                      <select value={editForm.department} onChange={e => setEditForm(f => ({ ...f, department: e.target.value }))}
                        className="input py-1.5 text-xs w-32">
                        {DEPARTMENTS.map(d => <option key={d} value={d}>{d}</option>)}
                      </select>
                      <button
                        onClick={() => updateMutation.mutate({ userId: u.id, updates: editForm })}
                        className="btn btn-primary btn-sm p-1.5"
                      >
                        <Check className="w-3.5 h-3.5" />
                      </button>
                      <button onClick={() => setEditingUser(null)} className="btn btn-ghost btn-sm p-1.5">
                        <ChevronDown className="w-3.5 h-3.5" />
                      </button>
                    </div>
                  ) : (
                    <div className="flex items-center gap-2">
                      <span className={clsx('badge', {
                        'badge-primary': u.role === 'admin',
                        'badge-success': u.role === 'manager',
                        'badge-gray': u.role === 'employee',
                      })}>
                        {u.role}
                      </span>
                      <span className="badge badge-gray hidden sm:flex">{u.department}</span>
                      {u.id !== user?.id && (
                        <>
                          <button
                            onClick={() => { setEditingUser(u.id); setEditForm({ role: u.role, department: u.department, is_active: u.is_active }); }}
                            className="btn btn-ghost btn-sm p-1.5"
                          >
                            <Edit3 className="w-3.5 h-3.5" />
                          </button>
                          <button
                            onClick={() => { if (confirm(`Delete ${u.name}?`)) deleteMutation.mutate(u.id); }}
                            className="btn btn-danger btn-sm p-1.5"
                          >
                            <Trash2 className="w-3.5 h-3.5" />
                          </button>
                        </>
                      )}
                    </div>
                  )}
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* Settings Tab */}
      {activeTab === 'settings' && settingsData && (
        <div className="glass-card p-6 space-y-4">
          <h3 className="font-medium text-white mb-4">System Configuration</h3>
          {Object.entries(settingsData).map(([key, value]) => (
            <div key={key} className="flex items-center justify-between py-3 border-b border-glass-border last:border-0">
              <div>
                <p className="text-sm text-white font-medium">{key.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase())}</p>
                <p className="text-xs text-slate-500">{key}</p>
              </div>
              <span className="text-sm text-brand-300 font-mono">{String(value)}</span>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
