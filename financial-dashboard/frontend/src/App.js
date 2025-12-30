import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer, AreaChart, Area } from 'recharts';
import { Upload, Activity, FileJson, Play, CheckCircle, AlertCircle } from 'lucide-react';

// --- UI Components (Simulating shadcn/ui with Tailwind) ---
const Card = ({ children, className }) => (
  <div className={`bg-slate-800 border border-slate-700 rounded-lg p-6 shadow-xl ${className}`}>{children}</div>
);
const Button = ({ children, onClick, disabled, className }) => (
  <button 
    onClick={onClick} 
    disabled={disabled}
    className={`px-4 py-2 rounded-md font-medium transition-all flex items-center gap-2
      ${disabled ? 'bg-slate-600 cursor-not-allowed' : 'bg-blue-600 hover:bg-blue-500 text-white'} ${className}`}
  >
    {children}
  </button>
);
const Input = ({ ...props }) => (
  <input {...props} className="w-full bg-slate-900 border border-slate-700 rounded px-3 py-2 text-white focus:outline-none focus:ring-2 focus:ring-blue-500" />
);

// --- Main Application ---
function App() {
  const [file, setFile] = useState(null);
  const [jsonParams, setJsonParams] = useState('{"strategy": "mean_reversion", "lookback": 20}');
  const [jobId, setJobId] = useState(null);
  const [status, setStatus] = useState(null); // PENDING, PROCESSING, SUCCESS, FAILED
  const [result, setResult] = useState(null);
  const [activeTab, setActiveTab] = useState('pnl');

  const API_URL = process.env.REACT_APP_API_URL || "http://localhost:8001/api";

  const handleSubmit = async () => {
    const formData = new FormData();
    if (file) formData.append("file", file);
    formData.append("params", jsonParams);

    try {
      const res = await axios.post(`${API_URL}/submit`, formData);
      setJobId(res.data.job_id);
      setStatus("PENDING");
      setResult(null);
    } catch (e) {
      alert("Submission failed");
    }
  };

  // Status Polling
  useEffect(() => {
    if (!jobId || status === "SUCCESS" || status === "FAILED") return;

    const interval = setInterval(async () => {
      try {
        const res = await axios.get(`${API_URL}/job/${jobId}`);
        setStatus(res.data.status);
        if (res.data.status === "SUCCESS") {
          setResult(res.data.result);
        }
      } catch (e) {
        console.error("Polling error", e);
      }
    }, 2000);

    return () => clearInterval(interval);
  }, [jobId, status]);

  // Data formatting for Recharts
  const getChartData = () => {
    if (!result) return [];
    return result.charts.dates.map((date, i) => ({
      date,
      pnl: result.charts.pnl[i],
      drawdown: result.charts.drawdown[i],
      var: result.charts.var[i]
    }));
  };

  const chartData = getChartData();

  return (
    <div className="min-h-screen p-8 max-w-7xl mx-auto">
      <header className="mb-10 flex items-center gap-3">
        <Activity className="text-blue-400 w-8 h-8" />
        <h1 className="text-3xl font-bold bg-clip-text text-transparent bg-gradient-to-r from-blue-400 to-emerald-400">
          Financial Analytics Dashboard
        </h1>
      </header>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
        {/* Left Column: Controls */}
        <div className="lg:col-span-1 space-y-6">
          <Card>
            <h2 className="text-xl font-semibold mb-4 flex items-center gap-2">
              <FileJson className="w-5 h-5 text-slate-400" /> Configuration
            </h2>
            <div className="space-y-4">
              <div>
                <label className="block text-sm text-slate-400 mb-1">Upload CSV Data</label>
                <div className="border-2 border-dashed border-slate-700 rounded-lg p-4 text-center hover:border-blue-500 transition-colors cursor-pointer relative">
                  <input type="file" onChange={(e) => setFile(e.target.files[0])} className="opacity-0 absolute inset-0 cursor-pointer" />
                  <Upload className="w-6 h-6 mx-auto mb-2 text-slate-500" />
                  <span className="text-sm text-slate-400">{file ? file.name : "Click to upload CSV"}</span>
                </div>
              </div>

              <div>
                <label className="block text-sm text-slate-400 mb-1">Strategy Parameters (JSON)</label>
                <textarea 
                  className="w-full bg-slate-950 border border-slate-700 rounded p-3 font-mono text-xs h-32 text-green-400 focus:outline-none focus:border-blue-500"
                  value={jsonParams}
                  onChange={(e) => setJsonParams(e.target.value)}
                />
              </div>

              <Button onClick={handleSubmit} disabled={status === "PENDING" || status === "PROCESSING"} className="w-full justify-center">
                {status === "PROCESSING" ? "Processing..." : "Run Analysis"} <Play className="w-4 h-4 ml-2" />
              </Button>
            </div>
          </Card>

          {/* Status Card */}
          {jobId && (
            <Card>
               <h3 className="text-sm font-semibold text-slate-400 uppercase tracking-wider mb-2">Job Status</h3>
               <div className="flex items-center gap-3">
                 {status === "PENDING" && <span className="text-yellow-500 font-bold animate-pulse">PENDING</span>}
                 {status === "PROCESSING" && <span className="text-blue-500 font-bold animate-pulse">PROCESSING</span>}
                 {status === "SUCCESS" && <span className="text-emerald-500 font-bold flex items-center gap-1"><CheckCircle className="w-4 h-4" /> COMPLETED</span>}
                 {status === "FAILED" && <span className="text-red-500 font-bold flex items-center gap-1"><AlertCircle className="w-4 h-4" /> FAILED</span>}
               </div>
               <div className="text-xs text-slate-500 mt-2 font-mono">{jobId}</div>
            </Card>
          )}
        </div>

        {/* Right Column: Visualization */}
        <div className="lg:col-span-2">
          {result ? (
            <div className="space-y-6">
              {/* KPIs */}
              <div className="grid grid-cols-3 gap-4">
                <Card className="p-4 bg-slate-800/50 border-emerald-900/50">
                   <div className="text-sm text-slate-400">Total PnL</div>
                   <div className={`text-2xl font-bold ${result.summary.total_pnl >= 0 ? 'text-emerald-400' : 'text-red-400'}`}>
                     ${result.summary.total_pnl.toLocaleString()}
                   </div>
                </Card>
                <Card className="p-4 bg-slate-800/50 border-red-900/50">
                   <div className="text-sm text-slate-400">Max Drawdown</div>
                   <div className="text-2xl font-bold text-red-400">{result.summary.max_dd}%</div>
                </Card>
                <Card className="p-4 bg-slate-800/50 border-blue-900/50">
                   <div className="text-sm text-slate-400">Avg VaR</div>
                   <div className="text-2xl font-bold text-blue-400">${result.summary.avg_var}</div>
                </Card>
              </div>

              {/* Tabs */}
              <div className="flex gap-2 border-b border-slate-700 pb-2">
                {['pnl', 'dd', 'var'].map(tab => (
                  <button
                    key={tab}
                    onClick={() => setActiveTab(tab)}
                    className={`px-4 py-1 rounded text-sm font-medium transition-colors ${activeTab === tab ? 'bg-slate-700 text-white' : 'text-slate-400 hover:text-white'}`}
                  >
                    {tab.toUpperCase()}
                  </button>
                ))}
              </div>

              {/* Charts */}
              <div className="h-[400px] w-full bg-slate-800/30 rounded-lg p-4 border border-slate-700/50">
                <ResponsiveContainer width="100%" height="100%">
                  {activeTab === 'pnl' ? (
                     <AreaChart data={chartData}>
                       <defs>
                         <linearGradient id="colorPnl" x1="0" y1="0" x2="0" y2="1">
                           <stop offset="5%" stopColor="#34d399" stopOpacity={0.3}/>
                           <stop offset="95%" stopColor="#34d399" stopOpacity={0}/>
                         </linearGradient>
                       </defs>
                       <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
                       <XAxis dataKey="date" stroke="#94a3b8" />
                       <YAxis stroke="#94a3b8" />
                       <Tooltip contentStyle={{backgroundColor: '#1e293b', borderColor: '#334155', color: '#f1f5f9'}} />
                       <Area type="monotone" dataKey="pnl" stroke="#34d399" fillOpacity={1} fill="url(#colorPnl)" />
                     </AreaChart>
                  ) : activeTab === 'dd' ? (
                     <LineChart data={chartData}>
                       <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
                       <XAxis dataKey="date" stroke="#94a3b8" />
                       <YAxis stroke="#94a3b8" />
                       <Tooltip contentStyle={{backgroundColor: '#1e293b', borderColor: '#334155', color: '#f1f5f9'}} />
                       <Line type="monotone" dataKey="drawdown" stroke="#f87171" dot={false} />
                     </LineChart>
                  ) : (
                     <LineChart data={chartData}>
                       <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
                       <XAxis dataKey="date" stroke="#94a3b8" />
                       <YAxis stroke="#94a3b8" />
                       <Tooltip contentStyle={{backgroundColor: '#1e293b', borderColor: '#334155', color: '#f1f5f9'}} />
                       <Line type="monotone" dataKey="var" stroke="#60a5fa" dot={false} />
                     </LineChart>
                  )}
                </ResponsiveContainer>
              </div>
            </div>
          ) : (
            <div className="h-full flex flex-col items-center justify-center text-slate-500 border border-dashed border-slate-700 rounded-lg p-12">
              <Activity className="w-12 h-12 mb-4 opacity-50" />
              <p>Run an analysis to see the results dashboard.</p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

export default App;