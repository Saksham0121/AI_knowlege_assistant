import { NavLink } from 'react-router-dom';
import { MessageSquare, FileText, BarChart2, Brain, Shield, Orbit } from 'lucide-react';
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
    <aside className="flex flex-col w-64 border-r border-glass-border bg-surface-100/90 backdrop-blur-xl shrink-0">
      {/* Logo */}
      <div className="flex items-center gap-3 px-5 py-5">
        <div className="w-10 h-10 rounded-2xl bg-brand-gradient flex items-center justify-center shadow-glow-sm">
          <Brain className="w-5 h-5 text-white" />
        </div>
        <div>
          <div className="font-display font-bold text-white leading-none">InsightFlow</div>
          <div className="text-[10px] tracking-[.16em] uppercase text-brand-600 font-bold mt-1">Knowledge workspace</div>
        </div>
      </div>

      {/* Nav */}
      <nav className="flex-1 px-3 py-4 space-y-1">
        <p className="px-3 pb-2 text-[10px] tracking-[.16em] uppercase text-slate-500 font-bold">Workspace</p>
        {navItems
          .filter(item => item.roles.includes(user?.role || ''))
          .map(({ to, label, icon: Icon }) => (
            <NavLink
              key={to}
              to={to}
              className={({ isActive }) => clsx(
                'flex items-center gap-3 px-3 py-2.5 rounded-xl text-sm font-medium transition-all duration-200',
                isActive
                  ? 'bg-brand-500/15 text-brand-300 border border-brand-500/25'
                  : 'text-slate-400 hover:text-white hover:bg-glass-hover'
              )}
            >
              <Icon className="w-4 h-4 shrink-0" />
              {label}
            </NavLink>
          ))}
      </nav>

      {/* User info */}
      <div className="px-4 py-4">
        <div className="flex items-center gap-2 px-2 pb-3 text-[10px] tracking-[.12em] uppercase text-slate-500 font-bold"><Orbit className="w-3 h-3 text-brand-500" /> Your space</div>
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
