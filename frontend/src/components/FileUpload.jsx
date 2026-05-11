import React, { useState, useRef } from 'react';
import axios from 'axios';
import { UploadCloud, CheckCircle, Loader2, AlertCircle, Database, Link2, Server } from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';

const API = 'http://localhost:5010';

// ─── Tab definitions ──────────────────────────────────────────────────────────
const TABS = [
  { id: 'sqlite',   label: 'SQLite',     icon: UploadCloud },
  { id: 'postgres', label: 'PostgreSQL', icon: Database },
  { id: 'mysql',    label: 'MySQL',      icon: Server },
];

// ─── Shared status badge ──────────────────────────────────────────────────────
const StatusBadge = ({ status, message }) => (
  <AnimatePresence mode="wait">
    {status === 'loading' && (
      <motion.div key="loading"
        initial={{ opacity: 0, y: 6 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0 }}
        className="flex items-center gap-2 text-blue-400 bg-blue-400/10 px-4 py-2 rounded-lg mt-4"
      >
        <Loader2 className="w-4 h-4 animate-spin" />
        <span className="text-sm">{message || 'Connecting…'}</span>
      </motion.div>
    )}
    {status === 'success' && (
      <motion.div key="success"
        initial={{ scale: 0.85, opacity: 0 }} animate={{ scale: 1, opacity: 1 }} exit={{ opacity: 0 }}
        className="flex items-center gap-2 text-emerald-400 bg-emerald-400/10 px-4 py-2 rounded-lg mt-4"
      >
        <CheckCircle className="w-4 h-4" />
        <span className="text-sm">{message}</span>
      </motion.div>
    )}
    {status === 'error' && (
      <motion.div key="error"
        initial={{ scale: 0.85, opacity: 0 }} animate={{ scale: 1, opacity: 1 }} exit={{ opacity: 0 }}
        className="flex items-start gap-2 text-red-400 bg-red-400/10 px-4 py-2 rounded-lg mt-4 max-w-full"
      >
        <AlertCircle className="w-4 h-4 flex-shrink-0 mt-0.5" />
        <span className="text-sm text-left">{message}</span>
      </motion.div>
    )}
  </AnimatePresence>
);

// ─── Input helper ─────────────────────────────────────────────────────────────
const Field = ({ label, type = 'text', value, onChange, placeholder, required }) => (
  <div className="flex flex-col gap-1 w-full">
    <label className="text-xs font-medium text-zinc-400 uppercase tracking-wider">
      {label}{required && <span className="text-red-400 ml-1">*</span>}
    </label>
    <input
      type={type}
      value={value}
      onChange={e => onChange(e.target.value)}
      placeholder={placeholder}
      className="w-full bg-zinc-800 border border-zinc-700 rounded-lg px-3 py-2 text-sm text-zinc-100
                 placeholder-zinc-600 focus:outline-none focus:border-blue-500 focus:ring-1 focus:ring-blue-500/40
                 transition-colors"
    />
  </div>
);

// ─── SQLite tab ───────────────────────────────────────────────────────────────
const SQLiteTab = ({ onSuccess }) => {
  const [isDragging, setIsDragging] = useState(false);
  const [file, setFile]             = useState(null);
  const [status, setStatus]         = useState('idle');
  const [message, setMessage]       = useState('');
  const fileInputRef                = useRef(null);

  const validate = (f) => {
    if (!f) return;
    if (!f.name.endsWith('.db') && !f.name.endsWith('.sqlite')) {
      setStatus('error');
      setMessage('Please upload a .db or .sqlite file.');
      return;
    }
    if (f.size > 50 * 1024 * 1024) {
      setStatus('error');
      setMessage('File size exceeds 50 MB.');
      return;
    }
    setFile(f);
    setStatus('idle');
    setMessage('');
  };

  const handleUpload = async () => {
    if (!file) return;
    setStatus('loading');
    setMessage('Uploading and indexing…');
    const formData = new FormData();
    formData.append('file', file);
    try {
      const { data } = await axios.post(`${API}/upload_db`, formData, {
        headers: { 'Content-Type': 'multipart/form-data' },
      });
      setStatus('success');
      setMessage(`Connected! ${data.tables} tables indexed.`);
      setTimeout(() => onSuccess(data), 1400);
    } catch (err) {
      setStatus('error');
      setMessage(err.response?.data?.error || 'Upload failed.');
    }
  };

  return (
    <div className="flex flex-col items-center gap-4 w-full">
      {/* Drop zone */}
      <div
        onDragOver={e => { e.preventDefault(); setIsDragging(true); }}
        onDragLeave={e => { e.preventDefault(); setIsDragging(false); }}
        onDrop={e => { e.preventDefault(); setIsDragging(false); validate(e.dataTransfer.files[0]); }}
        onClick={() => fileInputRef.current?.click()}
        className={`w-full rounded-xl border-2 border-dashed p-8 flex flex-col items-center gap-3 cursor-pointer
                    transition-all duration-200
                    ${isDragging ? 'border-blue-500 bg-blue-500/10' : 'border-zinc-700 bg-zinc-900/50 hover:border-zinc-500'}`}
      >
        <input type="file" accept=".db,.sqlite" className="hidden" ref={fileInputRef} onChange={e => validate(e.target.files[0])} />
        <div className="p-3 bg-zinc-800 rounded-full">
          <UploadCloud className="w-8 h-8 text-blue-400" />
        </div>
        {file ? (
          <p className="text-sm text-zinc-200 font-medium">{file.name} ({(file.size / (1024 * 1024)).toFixed(2)} MB)</p>
        ) : (
          <>
            <p className="text-sm font-medium text-zinc-200">Drag &amp; drop a SQLite file</p>
            <p className="text-xs text-zinc-500">or click to browse · Max 50 MB · .db / .sqlite</p>
          </>
        )}
      </div>

      {file && status === 'idle' && (
        <button
          onClick={handleUpload}
          className="w-full py-2.5 bg-blue-600 hover:bg-blue-500 text-white text-sm font-semibold rounded-lg
                     transition-colors flex items-center justify-center gap-2"
        >
          <UploadCloud className="w-4 h-4" />
          Connect Database
        </button>
      )}

      <StatusBadge status={status} message={message} />
    </div>
  );
};

// ─── DSN / form tab (shared by Postgres & MySQL) ──────────────────────────────
const RemoteDbTab = ({ dbType, onSuccess }) => {
  const isPostgres = dbType === 'postgres';

  const [mode, setMode]         = useState('dsn'); // 'dsn' | 'fields'
  const [dsn, setDsn]           = useState('');
  const [host, setHost]         = useState('localhost');
  const [port, setPort]         = useState(isPostgres ? '5432' : '3306');
  const [user, setUser]         = useState('');
  const [password, setPassword] = useState('');
  const [database, setDatabase] = useState('');
  const [schema, setSchema]     = useState('public');
  const [status, setStatus]     = useState('idle');
  const [message, setMessage]   = useState('');

  const dbLabel     = isPostgres ? 'PostgreSQL' : 'MySQL';
  const placeholder = isPostgres
    ? 'postgresql://user:pass@localhost:5432/mydb'
    : 'mysql://user:pass@localhost:3306/mydb';

  const handleConnect = async () => {
    setStatus('loading');
    setMessage(`Connecting to ${dbLabel}…`);

    const payload = { db_type: dbType };
    if (mode === 'dsn') {
      if (!dsn.trim()) { setStatus('error'); setMessage('DSN is required.'); return; }
      payload.dsn = dsn.trim();
    } else {
      if (!host || !user || !database) { setStatus('error'); setMessage('Host, user, and database are required.'); return; }
      Object.assign(payload, { host, port: Number(port) || undefined, user, password, database });
    }
    if (isPostgres && schema) payload.schema = schema;

    try {
      const { data } = await axios.post(`${API}/connect_db`, payload);
      setStatus('success');
      setMessage(data.message);
      setTimeout(() => onSuccess(data), 1400);
    } catch (err) {
      setStatus('error');
      setMessage(err.response?.data?.error || `Failed to connect to ${dbLabel}.`);
    }
  };

  return (
    <div className="flex flex-col gap-4 w-full">
      {/* Mode toggle */}
      <div className="flex rounded-lg overflow-hidden border border-zinc-700 text-sm">
        {['dsn', 'fields'].map(m => (
          <button
            key={m}
            onClick={() => setMode(m)}
            className={`flex-1 py-2 font-medium transition-colors
              ${mode === m ? 'bg-blue-600 text-white' : 'bg-zinc-800 text-zinc-400 hover:text-zinc-200'}`}
          >
            {m === 'dsn' ? 'Connection String' : 'Host / Port / Credentials'}
          </button>
        ))}
      </div>

      <AnimatePresence mode="wait">
        {mode === 'dsn' ? (
          <motion.div key="dsn" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} className="flex flex-col gap-3">
            <Field label="Connection String (DSN)" value={dsn} onChange={setDsn} placeholder={placeholder} required />
            {isPostgres && (
              <Field label="Postgres Schema" value={schema} onChange={setSchema} placeholder="public" />
            )}
          </motion.div>
        ) : (
          <motion.div key="fields" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} className="grid grid-cols-2 gap-3">
            <div className="col-span-2 sm:col-span-1"><Field label="Host" value={host} onChange={setHost} placeholder="localhost" required /></div>
            <div className="col-span-2 sm:col-span-1"><Field label="Port" type="number" value={port} onChange={setPort} placeholder={isPostgres ? '5432' : '3306'} /></div>
            <div className="col-span-2 sm:col-span-1"><Field label="Username" value={user} onChange={setUser} placeholder="user" required /></div>
            <div className="col-span-2 sm:col-span-1"><Field label="Password" type="password" value={password} onChange={setPassword} placeholder="••••••••" /></div>
            <div className="col-span-2"><Field label="Database" value={database} onChange={setDatabase} placeholder="my_database" required /></div>
            {isPostgres && (
              <div className="col-span-2"><Field label="Schema" value={schema} onChange={setSchema} placeholder="public" /></div>
            )}
          </motion.div>
        )}
      </AnimatePresence>

      <button
        onClick={handleConnect}
        disabled={status === 'loading'}
        className="w-full py-2.5 bg-blue-600 hover:bg-blue-500 disabled:opacity-50 text-white text-sm font-semibold
                   rounded-lg transition-colors flex items-center justify-center gap-2 mt-1"
      >
        <Link2 className="w-4 h-4" />
        Connect to {dbLabel}
      </button>

      <StatusBadge status={status} message={message} />
    </div>
  );
};

// ─── Root component ───────────────────────────────────────────────────────────
const FileUpload = ({ onUploadSuccess }) => {
  const [activeTab, setActiveTab] = useState('sqlite');

  return (
    <div className="flex flex-col items-center justify-center min-h-[60vh] px-4">
      {/* Header */}
      <div className="text-center mb-8 mt-10">
        <h1 className="text-4xl font-bold mb-3 tracking-tight">NL2SQL Assistant</h1>
        <p className="text-zinc-400 text-base">
          Connect a database and ask questions in plain English.
        </p>
      </div>

      {/* Card */}
      <motion.div
        initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }}
        className="w-full max-w-xl bg-zinc-900/70 border border-zinc-800 rounded-2xl shadow-2xl overflow-hidden"
      >
        {/* Tab bar */}
        <div className="flex border-b border-zinc-800">
          {TABS.map(({ id, label, icon: Icon }) => (
            <button
              key={id}
              onClick={() => setActiveTab(id)}
              className={`flex-1 flex items-center justify-center gap-1.5 py-3 text-sm font-medium transition-colors
                ${activeTab === id
                  ? 'text-blue-400 border-b-2 border-blue-500 bg-blue-500/5'
                  : 'text-zinc-500 hover:text-zinc-300'}`}
            >
              <Icon className="w-4 h-4" />
              {label}
            </button>
          ))}
        </div>

        {/* Tab content */}
        <div className="p-6">
          <AnimatePresence mode="wait">
            {activeTab === 'sqlite' && (
              <motion.div key="sqlite" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}>
                <SQLiteTab onSuccess={onUploadSuccess} />
              </motion.div>
            )}
            {activeTab === 'postgres' && (
              <motion.div key="postgres" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}>
                <RemoteDbTab dbType="postgres" onSuccess={onUploadSuccess} />
              </motion.div>
            )}
            {activeTab === 'mysql' && (
              <motion.div key="mysql" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}>
                <RemoteDbTab dbType="mysql" onSuccess={onUploadSuccess} />
              </motion.div>
            )}
          </AnimatePresence>
        </div>
      </motion.div>
    </div>
  );
};

export default FileUpload;
