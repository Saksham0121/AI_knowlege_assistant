import { useState, useCallback } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { useDropzone } from 'react-dropzone';
import { FileText, Upload, Trash2, Download, Search, Filter, RefreshCw, CheckCircle, Clock, AlertCircle, X, Plus, Tag } from 'lucide-react';
import api from '../lib/api';
import { useAuth } from '../lib/auth';
import toast from 'react-hot-toast';
import clsx from 'clsx';
import { formatDistanceToNow } from 'date-fns';

const STATUS_ICONS: Record<string, any> = {
  processed:  { icon: CheckCircle, color: 'text-green-400' },
  processing: { icon: RefreshCw,   color: 'text-yellow-400 animate-spin' },
  uploading:  { icon: Clock,       color: 'text-blue-400' },
  failed:     { icon: AlertCircle, color: 'text-red-400' },
};

const DEPT_COLORS: Record<string, string> = {
  HR: 'dept-HR', Finance: 'dept-Finance', Legal: 'dept-Legal',
  Engineering: 'dept-Engineering', Marketing: 'dept-Marketing',
  Operations: 'dept-Operations', General: 'dept-General',
};

const DEPARTMENTS = ['HR', 'Finance', 'Legal', 'Engineering', 'Marketing', 'Operations', 'General'];

export default function DocumentsPage() {
  const { user } = useAuth();
  const qc = useQueryClient();
  const canUpload = user?.role === 'manager' || user?.role === 'admin';

  const [search, setSearch] = useState('');
  const [deptFilter, setDeptFilter] = useState('');
  const [showUpload, setShowUpload] = useState(false);
  const [uploadDept, setUploadDept] = useState(user?.department || 'General');
  const [uploadTitle, setUploadTitle] = useState('');
  const [uploadFile, setUploadFile] = useState<File | null>(null);

  const { data, isLoading, refetch } = useQuery({
    queryKey: ['documents', deptFilter],
    queryFn: async () => {
      const params: any = {};
      if (deptFilter) params.department = deptFilter;
      const { data } = await api.get('/documents/', { params });
      return data;
    },
    refetchInterval: 5000, // poll for status updates
  });

  const deleteMutation = useMutation({
    mutationFn: (doc_id: string) => api.delete(`/documents/${doc_id}`),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ['documents'] }); toast.success('Document deleted'); },
    onError: () => toast.error('Delete failed'),
  });

  const uploadMutation = useMutation({
    mutationFn: async () => {
      if (!uploadFile) throw new Error('No file selected');
      const fd = new FormData();
      fd.append('file', uploadFile);
      fd.append('department', uploadDept);
      if (uploadTitle) fd.append('title', uploadTitle);
      const { data } = await api.post('/documents/upload', fd, {
        headers: { 'Content-Type': 'multipart/form-data' },
      });
      return data;
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['documents'] });
      toast.success('Document uploaded! Processing in background...');
      setShowUpload(false);
      setUploadFile(null);
      setUploadTitle('');
    },
    onError: (err: any) => toast.error(err.response?.data?.detail || 'Upload failed'),
  });

  const onDrop = useCallback((accepted: File[]) => {
    if (accepted[0]) setUploadFile(accepted[0]);
  }, []);

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: { 'application/pdf': ['.pdf'], 'application/vnd.openxmlformats-officedocument.wordprocessingml.document': ['.docx'], 'application/vnd.openxmlformats-officedocument.presentationml.presentation': ['.pptx'], 'text/plain': ['.txt'] },
    multiple: false,
    maxSize: 100 * 1024 * 1024,
  });

  const filtered = data?.documents?.filter((d: any) =>
    !search || d.title.toLowerCase().includes(search.toLowerCase()) || d.filename.toLowerCase().includes(search.toLowerCase())
  ) || [];

  return (
    <div className="page-wrapper">
      {/* Header */}
      <div className="section-header">
        <div>
          <h2 className="section-title">Document Library</h2>
          <p className="text-sm text-slate-400 mt-0.5">{data?.total || 0} documents</p>
        </div>
        <div className="flex gap-2">
          <button onClick={() => refetch()} className="btn btn-outline btn-sm"><RefreshCw className="w-3.5 h-3.5" /></button>
          {canUpload && (
            <button id="upload-btn" onClick={() => setShowUpload(true)} className="btn btn-primary btn-sm">
              <Plus className="w-3.5 h-3.5" /> Upload
            </button>
          )}
        </div>
      </div>

      {/* Filters */}
      <div className="flex gap-3 mb-6">
        <div className="relative flex-1 max-w-xs">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-500" />
          <input
            id="doc-search"
            value={search}
            onChange={e => setSearch(e.target.value)}
            placeholder="Search documents..."
            className="input pl-9 py-2"
          />
        </div>
        <div className="relative">
          <Filter className="absolute left-3 top-1/2 -translate-y-1/2 w-3.5 h-3.5 text-slate-500" />
          <select
            id="dept-filter"
            value={deptFilter}
            onChange={e => setDeptFilter(e.target.value)}
            className="input pl-8 pr-4 py-2 w-44"
          >
            <option value="">All Departments</option>
            {DEPARTMENTS.map(d => <option key={d} value={d}>{d}</option>)}
          </select>
        </div>
      </div>

      {/* Documents Grid */}
      {isLoading ? (
        <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
          {[...Array(6)].map((_, i) => <div key={i} className="skeleton h-40 rounded-2xl" />)}
        </div>
      ) : filtered.length === 0 ? (
        <div className="flex flex-col items-center justify-center py-24 gap-4">
          <FileText className="w-12 h-12 text-slate-600" />
          <p className="text-slate-400 text-sm">No documents found</p>
          {canUpload && <button onClick={() => setShowUpload(true)} className="btn btn-primary btn-sm">Upload your first document</button>}
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
          {filtered.map((doc: any) => {
            const statusInfo = STATUS_ICONS[doc.status] || STATUS_ICONS.processing;
            const StatusIcon = statusInfo.icon;
            return (
              <div key={doc.document_id} className="glass-card-hover p-5 flex flex-col gap-3">
                <div className="flex items-start justify-between gap-2">
                  <div className="flex items-center gap-2.5">
                    <div className="w-9 h-9 rounded-xl bg-brand-500/20 flex items-center justify-center">
                      <FileText className="w-4.5 h-4.5 text-brand-400" />
                    </div>
                    <div className="min-w-0">
                      <p className="font-medium text-sm text-white truncate">{doc.title}</p>
                      <p className="text-xs text-slate-500 truncate">{doc.filename}</p>
                    </div>
                  </div>
                  <StatusIcon className={clsx('w-4 h-4 shrink-0', statusInfo.color)} />
                </div>

                <div className="flex items-center gap-2 flex-wrap">
                  <span className={clsx('badge text-xs', DEPT_COLORS[doc.department] || 'badge-gray')}>
                    {doc.department}
                  </span>
                  {doc.total_chunks > 0 && (
                    <span className="badge badge-gray">{doc.total_chunks} chunks</span>
                  )}
                  <span className="badge badge-gray">{doc.file_type?.toUpperCase()}</span>
                </div>

                {doc.summary && (
                  <p className="text-xs text-slate-400 line-clamp-2">{doc.summary}</p>
                )}

                {doc.keywords?.length > 0 && (
                  <div className="flex gap-1 flex-wrap">
                    {doc.keywords.slice(0, 4).map((kw: string) => (
                      <span key={kw} className="flex items-center gap-0.5 text-[10px] text-slate-500 bg-surface-50 rounded-full px-2 py-0.5">
                        <Tag className="w-2.5 h-2.5" />{kw}
                      </span>
                    ))}
                  </div>
                )}

                <div className="flex items-center justify-between mt-auto pt-2 border-t border-glass-border">
                  <span className="text-[10px] text-slate-600">
                    {doc.upload_date ? formatDistanceToNow(new Date(doc.upload_date), { addSuffix: true }) : ''}
                    {doc.uploaded_by_name && ` · ${doc.uploaded_by_name}`}
                  </span>
                  <div className="flex gap-1">
                    <a href={`${import.meta.env.VITE_API_URL || 'http://localhost:8080'}/documents/${doc.document_id}/download`}
                       target="_blank" rel="noreferrer"
                       className="btn btn-ghost btn-sm p-1.5">
                      <Download className="w-3.5 h-3.5" />
                    </a>
                    {canUpload && (
                      <button
                        onClick={() => { if (confirm('Delete this document?')) deleteMutation.mutate(doc.document_id); }}
                        className="btn btn-danger btn-sm p-1.5"
                      >
                        <Trash2 className="w-3.5 h-3.5" />
                      </button>
                    )}
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      )}

      {/* Upload Modal */}
      {showUpload && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 backdrop-blur-sm animate-fade-in">
          <div className="glass-card w-full max-w-md p-6 animate-slide-up">
            <div className="flex items-center justify-between mb-5">
              <h3 className="font-display font-bold text-white">Upload Document</h3>
              <button onClick={() => setShowUpload(false)} className="text-slate-500 hover:text-white">
                <X className="w-5 h-5" />
              </button>
            </div>

            <div className="space-y-4">
              {/* Drop zone */}
              <div
                {...getRootProps()}
                className={clsx(
                  'border-2 border-dashed rounded-xl p-8 text-center cursor-pointer transition-all',
                  isDragActive ? 'border-brand-500 bg-brand-500/10' : 'border-glass-border hover:border-brand-500/50'
                )}
              >
                <input {...getInputProps()} />
                {uploadFile ? (
                  <div className="flex items-center justify-center gap-2 text-sm text-white">
                    <FileText className="w-5 h-5 text-brand-400" />
                    {uploadFile.name}
                  </div>
                ) : (
                  <>
                    <Upload className="w-8 h-8 text-slate-500 mx-auto mb-2" />
                    <p className="text-sm text-slate-400">Drop your file here, or <span className="text-brand-400">browse</span></p>
                    <p className="text-xs text-slate-600 mt-1">PDF, DOCX, PPTX, TXT · Max 100MB</p>
                  </>
                )}
              </div>

              <input value={uploadTitle} onChange={e => setUploadTitle(e.target.value)}
                placeholder="Document title (optional)" className="input" />

              <select value={uploadDept} onChange={e => setUploadDept(e.target.value)} className="input">
                {DEPARTMENTS.map(d => <option key={d} value={d}>{d}</option>)}
              </select>

              <div className="flex gap-2">
                <button onClick={() => setShowUpload(false)} className="btn btn-ghost flex-1">Cancel</button>
                <button
                  id="confirm-upload"
                  onClick={() => uploadMutation.mutate()}
                  disabled={!uploadFile || uploadMutation.isPending}
                  className="btn btn-primary flex-1"
                >
                  {uploadMutation.isPending ? (
                    <div className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                  ) : 'Upload'}
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
