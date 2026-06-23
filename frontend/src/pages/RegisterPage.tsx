import { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { Brain, Mail, Lock, User, Building2, ChevronDown, ArrowRight } from 'lucide-react';
import { useAuth } from '../lib/auth';
import toast from 'react-hot-toast';

const ROLES = ['employee', 'manager', 'admin'];
const DEPARTMENTS = ['HR', 'Finance', 'Legal', 'Engineering', 'Marketing', 'Operations', 'General'];

export default function RegisterPage() {
  const [form, setForm] = useState({ name: '', email: '', password: '', role: 'employee', department: 'General' });
  const [isLoading, setIsLoading] = useState(false);
  const { register } = useAuth();
  const navigate = useNavigate();

  const update = (field: string, value: string) => setForm(f => ({ ...f, [field]: value }));

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (form.password.length < 8) { toast.error('Password must be at least 8 characters'); return; }
    setIsLoading(true);
    try {
      await register(form);
      toast.success('Account created! Welcome to InsightFlow AI.');
      navigate('/chat');
    } catch (err: any) {
      toast.error(err.response?.data?.detail || 'Registration failed');
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="min-h-screen mesh-bg knowledge-current flex items-center justify-center p-4">
      <div className="absolute inset-0 pointer-events-none">
        <div className="absolute top-1/3 left-1/2 -translate-x-1/2 w-96 h-96 bg-brand-500/10 rounded-full blur-3xl" />
      </div>

      <div className="w-full max-w-md animate-slide-up relative">
        <div className="flex items-center justify-center gap-3 mb-8">
          <div className="w-12 h-12 rounded-2xl bg-brand-gradient flex items-center justify-center shadow-glow">
            <Brain className="w-7 h-7 text-white" />
          </div>
          <div>
            <h1 className="font-display font-bold text-2xl text-white">InsightFlow AI</h1>
            <p className="text-[10px] tracking-[.16em] uppercase text-brand-600 font-bold mt-1">Enterprise knowledge assistant</p>
          </div>
        </div>

        <div className="glass-card p-8 relative overflow-hidden">
          <div className="absolute top-0 left-8 right-8 h-px bg-brand-300" />
          <p className="text-[10px] tracking-[.16em] uppercase text-brand-600 font-bold mb-3">Get started</p>
          <h2 className="text-xl font-display font-bold text-white mb-1">Create your account</h2>
          <p className="text-sm text-slate-400 mb-6">Join your organization's knowledge platform</p>

          <form onSubmit={handleSubmit} className="space-y-4">
            {/* Name */}
            <div>
              <label className="block text-xs font-medium text-slate-400 mb-1.5">Full Name</label>
              <div className="relative">
                <User className="absolute left-3.5 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-500" />
                <input id="reg-name" type="text" value={form.name} onChange={e => update('name', e.target.value)}
                  placeholder="John Doe" required className="input pl-10" />
              </div>
            </div>

            {/* Email */}
            <div>
              <label className="block text-xs font-medium text-slate-400 mb-1.5">Email</label>
              <div className="relative">
                <Mail className="absolute left-3.5 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-500" />
                <input id="reg-email" type="email" value={form.email} onChange={e => update('email', e.target.value)}
                  placeholder="you@company.com" required className="input pl-10" />
              </div>
            </div>

            {/* Password */}
            <div>
              <label className="block text-xs font-medium text-slate-400 mb-1.5">Password</label>
              <div className="relative">
                <Lock className="absolute left-3.5 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-500" />
                <input id="reg-password" type="password" value={form.password} onChange={e => update('password', e.target.value)}
                  placeholder="Min. 8 characters" required className="input pl-10" />
              </div>
            </div>

            {/* Role + Department */}
            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="block text-xs font-medium text-slate-400 mb-1.5">Role</label>
                <div className="relative">
                  <select id="reg-role" value={form.role} onChange={e => update('role', e.target.value)}
                    className="input appearance-none pr-8 capitalize">
                    {ROLES.map(r => <option key={r} value={r} className="bg-surface-50">{r.charAt(0).toUpperCase() + r.slice(1)}</option>)}
                  </select>
                  <ChevronDown className="absolute right-3 top-1/2 -translate-y-1/2 w-3.5 h-3.5 text-slate-500 pointer-events-none" />
                </div>
              </div>
              <div>
                <label className="block text-xs font-medium text-slate-400 mb-1.5">Department</label>
                <div className="relative">
                  <Building2 className="absolute left-3 top-1/2 -translate-y-1/2 w-3.5 h-3.5 text-slate-500" />
                  <select id="reg-dept" value={form.department} onChange={e => update('department', e.target.value)}
                    className="input pl-8 appearance-none pr-6">
                    {DEPARTMENTS.map(d => <option key={d} value={d} className="bg-surface-50">{d}</option>)}
                  </select>
                  <ChevronDown className="absolute right-2 top-1/2 -translate-y-1/2 w-3.5 h-3.5 text-slate-500 pointer-events-none" />
                </div>
              </div>
            </div>

            <div className="text-xs text-slate-500 bg-brand-500/10 border border-brand-500/20 rounded-lg p-3">
              💡 The first user to register automatically becomes <strong className="text-brand-400">Admin</strong>.
            </div>

            <button id="reg-submit" type="submit" disabled={isLoading}
              className="btn btn-primary w-full justify-center py-3 mt-1">
              {isLoading ? (
                <div className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />
              ) : <>Create Account <ArrowRight className="w-4 h-4" /></>}
            </button>
          </form>

          <p className="text-center text-sm text-slate-400 mt-6">
            Already have an account?{' '}
            <Link to="/login" className="text-brand-400 hover:text-brand-300 font-medium transition-colors">Sign In</Link>
          </p>
        </div>
      </div>
    </div>
  );
}
