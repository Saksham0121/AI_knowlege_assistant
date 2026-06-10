import { useState, useRef, useEffect } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { Send, Sparkles, BookOpen, Clock, Trash2, ThumbsUp, ThumbsDown, ChevronDown, Brain } from 'lucide-react';
import api from '../lib/api';
import { useAuth } from '../lib/auth';
import toast from 'react-hot-toast';
import clsx from 'clsx';
import { formatDistanceToNow } from 'date-fns';

interface Citation {
  document_id: string;
  document: string;
  title: string;
  page?: number;
  chunk_id: string;
  excerpt: string;
  relevance_score: number;
}

interface Message {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  citations?: Citation[];
  confidence?: number;
  timestamp: Date;
  query_id?: string;
}

const SUGGESTIONS = [
  'What are the leave policies?',
  'Explain the expense reimbursement process',
  'What is the code of conduct?',
  'How do I submit a compliance report?',
];

export default function ChatPage() {
  const [input, setInput] = useState('');
  const [messages, setMessages] = useState<Message[]>([]);
  const [sessionId] = useState(() => Math.random().toString(36).slice(2));
  const [showHistory, setShowHistory] = useState(false);
  const [feedbackGiven, setFeedbackGiven] = useState<Record<string, string>>({});
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);
  const { user } = useAuth();
  const qc = useQueryClient();

  const scrollToBottom = () => messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  useEffect(scrollToBottom, [messages]);

  const { data: historyData } = useQuery({
    queryKey: ['chat-history'],
    queryFn: async () => {
      const { data } = await api.get('/chat/history?page_size=15');
      return data;
    },
    enabled: showHistory,
  });

  const queryMutation = useMutation({
    mutationFn: async (question: string) => {
      const { data } = await api.post('/chat/query', { question, session_id: sessionId });
      return data;
    },
    onSuccess: (data) => {
      const assistantMsg: Message = {
        id: data.query_id,
        role: 'assistant',
        content: data.answer,
        citations: data.citations,
        confidence: data.confidence,
        timestamp: new Date(),
        query_id: data.query_id,
      };
      setMessages(prev => [...prev, assistantMsg]);
      qc.invalidateQueries({ queryKey: ['chat-history'] });
    },
    onError: (err: any) => {
      toast.error(err.response?.data?.detail || 'Failed to get answer');
      setMessages(prev => prev.slice(0, -1));
    },
  });

  const feedbackMutation = useMutation({
    mutationFn: async ({ query_id, feedback }: { query_id: string; feedback: string }) => {
      await api.post('/feedback/submit', { query_id, feedback });
    },
    onSuccess: (_, vars) => {
      setFeedbackGiven(prev => ({ ...prev, [vars.query_id]: vars.feedback }));
      toast.success('Feedback submitted!');
    },
  });

  const deleteHistoryMutation = useMutation({
    mutationFn: async (query_id: string) => {
      await api.delete(`/chat/history/${query_id}`);
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['chat-history'] });
      toast.success('Chat deleted');
    },
  });

  const handleSend = async () => {
    if (!input.trim() || queryMutation.isPending) return;
    const question = input.trim();
    setInput('');

    const userMsg: Message = {
      id: Math.random().toString(36),
      role: 'user',
      content: question,
      timestamp: new Date(),
    };
    setMessages(prev => [...prev, userMsg]);
    queryMutation.mutate(question);
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); handleSend(); }
  };

  const confidenceColor = (c: number) => {
    if (c >= 0.7) return 'text-green-400';
    if (c >= 0.4) return 'text-yellow-400';
    return 'text-red-400';
  };

  return (
    <div className="flex h-full overflow-hidden">
      {/* History Sidebar */}
      {showHistory && (
        <aside className="w-72 border-r border-glass-border bg-surface-100 flex flex-col animate-slide-in-right">
          <div className="flex items-center justify-between p-4 border-b border-glass-border">
            <span className="font-medium text-sm text-white flex items-center gap-2">
              <Clock className="w-4 h-4 text-brand-400" /> Chat History
            </span>
            <button onClick={() => setShowHistory(false)} className="text-slate-500 hover:text-white">
              <ChevronDown className="w-4 h-4 rotate-90" />
            </button>
          </div>
          <div className="flex-1 overflow-y-auto p-3 space-y-2">
            {historyData?.history?.map((h: any) => (
              <div key={h.id} className="glass-card p-3 group cursor-pointer hover:bg-glass-hover transition-colors">
                <div className="flex items-start justify-between gap-2">
                  <p className="text-xs text-slate-300 line-clamp-2 flex-1">{h.question}</p>
                  <button
                    onClick={() => deleteHistoryMutation.mutate(h.query_id)}
                    className="opacity-0 group-hover:opacity-100 text-red-400 hover:text-red-300 transition-opacity shrink-0"
                  >
                    <Trash2 className="w-3 h-3" />
                  </button>
                </div>
                <p className="text-[10px] text-slate-600 mt-1">
                  {h.created_at ? formatDistanceToNow(new Date(h.created_at), { addSuffix: true }) : ''}
                </p>
              </div>
            ))}
            {(!historyData?.history || historyData.history.length === 0) && (
              <p className="text-xs text-slate-600 text-center py-4">No history yet</p>
            )}
          </div>
        </aside>
      )}

      {/* Main Chat */}
      <div className="flex flex-col flex-1 min-w-0">
        {/* Toolbar */}
        <div className="flex items-center gap-2 px-4 py-3 border-b border-glass-border">
          <button
            id="toggle-history"
            onClick={() => setShowHistory(!showHistory)}
            className={clsx('btn btn-sm btn-ghost gap-1.5', showHistory && 'bg-brand-500/20 text-brand-300')}
          >
            <Clock className="w-3.5 h-3.5" /> History
          </button>
          <div className="ml-auto text-xs text-slate-500">
            Department: <span className="text-slate-300 font-medium">{user?.department}</span>
          </div>
        </div>

        {/* Messages */}
        <div className="flex-1 overflow-y-auto px-4 py-6 space-y-6">
          {messages.length === 0 && (
            <div className="flex flex-col items-center justify-center h-full gap-8 animate-fade-in">
              <div className="text-center">
                <div className="w-16 h-16 rounded-2xl bg-brand-gradient flex items-center justify-center shadow-glow mx-auto mb-4">
                  <Brain className="w-9 h-9 text-white" />
                </div>
                <h2 className="text-xl font-display font-bold text-white mb-2">Ask your Knowledge Base</h2>
                <p className="text-sm text-slate-400 max-w-md">
                  Ask any question and I'll search through your organization's documents to provide accurate, cited answers.
                </p>
              </div>
              <div className="grid grid-cols-2 gap-3 w-full max-w-lg">
                {SUGGESTIONS.map((s) => (
                  <button
                    key={s}
                    onClick={() => { setInput(s); inputRef.current?.focus(); }}
                    className="glass-card-hover p-3 text-left"
                  >
                    <Sparkles className="w-3.5 h-3.5 text-brand-400 mb-1.5" />
                    <p className="text-xs text-slate-300">{s}</p>
                  </button>
                ))}
              </div>
            </div>
          )}

          {messages.map((msg) => (
            <div
              key={msg.id}
              className={clsx('flex gap-3 animate-slide-up', msg.role === 'user' ? 'justify-end' : 'justify-start')}
            >
              {msg.role === 'assistant' && (
                <div className="w-8 h-8 rounded-xl bg-brand-gradient flex items-center justify-center shrink-0 shadow-glow-sm">
                  <Brain className="w-4 h-4 text-white" />
                </div>
              )}

              <div className={clsx('max-w-2xl space-y-3', msg.role === 'user' ? 'items-end' : 'items-start', 'flex flex-col')}>
                <div className={clsx(
                  'rounded-2xl px-4 py-3 text-sm leading-relaxed',
                  msg.role === 'user'
                    ? 'bg-brand-gradient text-white rounded-tr-sm shadow-glow-sm'
                    : 'glass-card text-slate-200 rounded-tl-sm'
                )}>
                  {msg.content}
                </div>

                {/* AI message extras */}
                {msg.role === 'assistant' && (
                  <div className="space-y-2 w-full">
                    {/* Confidence */}
                    {msg.confidence !== undefined && (
                      <div className="flex items-center gap-2">
                        <div className="flex-1 h-1 bg-surface-50 rounded-full overflow-hidden">
                          <div
                            className="h-full bg-brand-gradient rounded-full transition-all duration-700"
                            style={{ width: `${Math.round(msg.confidence * 100)}%` }}
                          />
                        </div>
                        <span className={clsx('text-xs font-medium', confidenceColor(msg.confidence))}>
                          {Math.round(msg.confidence * 100)}% confident
                        </span>
                      </div>
                    )}

                    {/* Citations */}
                    {msg.citations && msg.citations.length > 0 && (
                      <div className="space-y-1.5">
                        <p className="text-xs text-slate-500 flex items-center gap-1">
                          <BookOpen className="w-3 h-3" /> Sources
                        </p>
                        {msg.citations.map((c, i) => (
                          <div key={c.chunk_id} className="glass-card p-2.5 hover:bg-glass-hover transition-colors cursor-pointer">
                            <div className="flex items-center justify-between mb-1">
                              <span className="text-xs font-medium text-brand-300">
                                [{i + 1}] {c.title || c.document}
                                {c.page && <span className="text-slate-500"> — Page {c.page}</span>}
                              </span>
                              <span className="text-[10px] text-slate-600">
                                {Math.round(c.relevance_score * 100)}% relevant
                              </span>
                            </div>
                            <p className="text-xs text-slate-400 line-clamp-2">{c.excerpt}</p>
                          </div>
                        ))}
                      </div>
                    )}

                    {/* Feedback */}
                    {msg.query_id && (
                      <div className="flex items-center gap-2">
                        <span className="text-xs text-slate-600">Helpful?</span>
                        {feedbackGiven[msg.query_id] ? (
                          <span className="text-xs text-slate-500">
                            {feedbackGiven[msg.query_id] === 'positive' ? '👍 Thanks!' : '👎 Got it'}
                          </span>
                        ) : (
                          <>
                            <button
                              onClick={() => feedbackMutation.mutate({ query_id: msg.query_id!, feedback: 'positive' })}
                              className="text-slate-500 hover:text-green-400 transition-colors"
                            >
                              <ThumbsUp className="w-3.5 h-3.5" />
                            </button>
                            <button
                              onClick={() => feedbackMutation.mutate({ query_id: msg.query_id!, feedback: 'negative' })}
                              className="text-slate-500 hover:text-red-400 transition-colors"
                            >
                              <ThumbsDown className="w-3.5 h-3.5" />
                            </button>
                          </>
                        )}
                      </div>
                    )}
                  </div>
                )}
              </div>

              {msg.role === 'user' && (
                <div className="w-8 h-8 rounded-xl bg-surface-50 border border-glass-border flex items-center justify-center shrink-0 text-sm font-bold text-white">
                  {user?.name?.charAt(0)}
                </div>
              )}
            </div>
          ))}

          {/* Typing indicator */}
          {queryMutation.isPending && (
            <div className="flex gap-3 animate-fade-in">
              <div className="w-8 h-8 rounded-xl bg-brand-gradient flex items-center justify-center shadow-glow-sm">
                <Brain className="w-4 h-4 text-white" />
              </div>
              <div className="glass-card px-4 py-3 flex items-center gap-1">
                <div className="flex gap-1">
                  {[0, 1, 2].map(i => (
                    <div key={i} className="w-1.5 h-1.5 rounded-full bg-brand-400 animate-bounce" style={{ animationDelay: `${i * 0.15}s` }} />
                  ))}
                </div>
                <span className="text-xs text-slate-500 ml-2">Searching knowledge base...</span>
              </div>
            </div>
          )}

          <div ref={messagesEndRef} />
        </div>

        {/* Input */}
        <div className="px-4 py-4 border-t border-glass-border">
          <div className="glass-card p-2 flex items-end gap-2">
            <textarea
              ref={inputRef}
              id="chat-input"
              value={input}
              onChange={e => setInput(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder="Ask anything about your documents... (Enter to send)"
              rows={1}
              className="flex-1 bg-transparent text-white placeholder-slate-500 text-sm resize-none outline-none px-2 py-1.5 max-h-32"
              style={{ minHeight: '36px' }}
            />
            <button
              id="send-btn"
              onClick={handleSend}
              disabled={!input.trim() || queryMutation.isPending}
              className="btn btn-primary p-2.5 rounded-xl shrink-0"
            >
              <Send className="w-4 h-4" />
            </button>
          </div>
          <p className="text-xs text-slate-600 mt-2 text-center">
            Answers grounded in your knowledge base • Shift+Enter for new line
          </p>
        </div>
      </div>
    </div>
  );
}
