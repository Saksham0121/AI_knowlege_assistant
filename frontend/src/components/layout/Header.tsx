import { useLocation } from 'react-router-dom';
import { LogOut, Bell, Search } from 'lucide-react';
import { useAuth } from '../../lib/auth';

const pageTitles: Record<string, { title: string; subtitle: string }> = {
  '/chat':      { title: 'AI Assistant',       subtitle: 'Ask questions from your knowledge base' },
  '/documents': { title: 'Document Library',   subtitle: 'Upload and manage your documents' },
  '/analytics': { title: 'Analytics',          subtitle: 'Insights into knowledge usage' },
  '/admin':     { title: 'Admin Panel',        subtitle: 'Manage users and system settings' },
};

export default function Header() {
  const { logout } = useAuth();
  const { pathname } = useLocation();
  const page = pageTitles[pathname] || { title: 'InsightFlow AI', subtitle: '' };

  return (
    <header className="flex items-center justify-between px-6 py-4 border-b border-glass-border bg-surface-100/70 backdrop-blur-xl">
      <div>
        <p className="text-[10px] tracking-[.16em] uppercase text-brand-600 font-bold mb-1">InsightFlow AI</p>
        <h1 className="text-lg font-display font-bold text-white leading-none">{page.title}</h1>
        {page.subtitle && (
          <p className="text-xs text-slate-400 mt-0.5">{page.subtitle}</p>
        )}
      </div>

      <div className="flex items-center gap-2">
        <button aria-label="Search knowledge" className="btn-ghost btn p-2 hidden sm:inline-flex">
          <Search className="w-4 h-4" />
        </button>
        <button aria-label="Notifications" className="btn-ghost btn p-2 relative">
          <Bell className="w-4 h-4" />
          <span className="absolute top-2 right-2 w-1.5 h-1.5 rounded-full bg-brand-500 border border-white" />
        </button>
        <button
          id="logout-btn"
          onClick={logout}
          className="btn btn-ghost text-red-400 hover:text-red-300 hover:bg-red-500/10 gap-2"
        >
          <LogOut className="w-4 h-4" />
          <span className="hidden sm:block text-sm">Logout</span>
        </button>
      </div>
    </header>
  );
}
