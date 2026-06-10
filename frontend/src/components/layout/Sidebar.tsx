import { NavLink } from 'react-router-dom';
import { MessageSquare, FileText, BarChart2, Brain, Shield } from 'lucide-react';
import { useAuth } from '../../lib/auth';
import clsx from 'clsx';

const navItems = [
  { to: '/chat',      label: 'Chat',       icon: MessageSquare, roles: ['employee', 'manager', 'admin'] },
  { to: '/documents', label: 'Documents',  icon: FileText,      roles: ['employee', 'manager', 'admin'] },
  { to: '/analytics', label: 'Analytics',  icon: BarChart2,     roles: ['manager', 'admin'] },
  { to: '/admin',     label: 'Admin',      icon: Shield,        roles: ['admin'] },
];

export default function Sidebar() {
  const { user } = useAuth();

  return (
    <aside className="flex flex-col w-64 border-r border-glass-border bg-surface-100 shrink-0">
      {/* Logo */}
      <div className="flex items-center gap-3 px-6 py-5 border-b border-glass-border">
        <div className="w-9 h-9 rounded-xl bg-brand-gradient flex items-center justify-center shadow-glow-sm">
          <Brain className="w-5 h-5 text-white" />
        </div>
        <div>
          <div className="font-display font-bold text-white leading-none">InsightFlow</div>
          <div className="text-[11px] text-brand-400 font-medium">AI Knowledge Assistant</div>
        </div>
      </div>

      {/* Nav */}
      <nav className="flex-1 px-3 py-4 space-y-1">
        {navItems
          .filter(item => item.roles.includes(user?.role || ''))
          .map(({ to, label, icon: Icon }) => (
            <NavLink
              key={to}
              to={to}
              className={({ isActive }) => clsx(
                'flex items-center gap-3 px-3 py-2.5 rounded-xl text-sm font-medium transition-all duration-200',
                isActive
                  ? 'bg-brand-500/20 text-brand-300 border border-brand-500/30 shadow-glow-sm'
                  : 'text-slate-400 hover:text-white hover:bg-glass-hover'
              )}
            >
              <Icon className="w-4 h-4 shrink-0" />
              {label}
            </NavLink>
          ))}
      </nav>

      {/* User info */}
      <div className="px-4 py-4 border-t border-glass-border">
        <div className="glass-card p-3 flex items-center gap-3">
          <div className="w-8 h-8 rounded-full bg-brand-gradient flex items-center justify-center text-white text-sm font-bold shrink-0">
            {user?.name?.charAt(0).toUpperCase()}
          </div>
          <div className="min-w-0">
            <p className="text-sm font-medium text-white truncate">{user?.name}</p>
            <div className="flex items-center gap-1.5">
              <span className={clsx('badge badge-sm', {
                'badge-primary': user?.role === 'admin',
                'badge-success': user?.role === 'manager',
                'badge-gray': user?.role === 'employee',
              })} style={{ fontSize: '10px', padding: '1px 6px' }}>
                {user?.role}
              </span>
              <span className="text-[10px] text-slate-500 truncate">{user?.department}</span>
            </div>
          </div>
        </div>
      </div>
    </aside>
  );
}
