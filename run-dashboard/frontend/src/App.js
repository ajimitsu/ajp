import React, { useEffect, useState } from 'react';
import axios from 'axios';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from 'recharts';
import ActivityDetail from './ActivityDetail';
import './App.css';

function App() {
  const [data, setData] = useState(null);
  const [syncing, setSyncing] = useState(false);
  // 選択されたアクティビティIDを管理
  const [selectedActivityId, setSelectedActivityId] = useState(null);

  const fetchData = () => {
    axios.get('http://localhost:8000/api/dashboard')
      .then(response => setData(response.data))
      .catch(error => console.error("Error:", error));
  };

  useEffect(() => { fetchData(); }, []);

  const handleSync = () => {
    setSyncing(true);
    axios.get('http://localhost:8000/api/sync').then(() => {
        alert("同期開始。しばらくしてリロードしろ。");
        setTimeout(() => { fetchData(); setSyncing(false); }, 5000);
      });
  };

  // グラフの点をクリックした時の処理
  const handleChartClick = (point) => {
    if (point && point.activePayload) {
      const activityId = point.activePayload[0].payload.activity_id;
      setSelectedActivityId(activityId);
    }
  };

  if (!data) return <div style={{padding:'20px'}}>Loading Dashboard...</div>;

  return (
    <div className="dashboard-container">
      <header className="header">
        <h1>🏃 Ramos Analytics v3 (Deep Dive)</h1>
        <button className="sync-btn" onClick={handleSync} disabled={syncing}>
          {syncing ? "Syncing..." : "🔄 Sync Garmin"}
        </button>
      </header>

      {data.feedback && (
        <div className="feedback-section">
           <p style={{margin:0, fontWeight:'bold'}}>📢 Ramos Feedback: "{data.feedback}"</p>
        </div>
      )}

      <div className="charts-container">
        <div className="chart-card">
          <h3>Efficiency vs Pace Trend (Click points for details!)</h3>
          <p style={{fontSize:'0.9em'}}>点をクリックすると詳細分析画面が開くぞ。</p>
          <ResponsiveContainer width="100%" height={300}>
            <LineChart data={data.activities} onClick={handleChartClick} style={{cursor:'pointer'}}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="date" />
              <YAxis yAxisId="left" domain={['auto', 'auto']} label={{ value: 'Efficiency', angle: -90, position: 'insideLeft' }}/>
              <YAxis yAxisId="right" orientation="right" domain={['auto', 'auto']} reversed={true} unit=" min/km" label={{ value: 'Pace (min/km)', angle: 90, position: 'insideRight' }}/>
              <Tooltip />
              <Legend />
              <Line yAxisId="left" type="monotone" dataKey="efficiency_score" stroke="#8884d8" strokeWidth={3} name="Efficiency" dot={{ r: 5 }} activeDot={{ r: 8 }} />
              <Line yAxisId="right" type="monotone" dataKey="pace_min_km" stroke="#82ca9d" name="Pace (min/km)" dot={{ r: 5 }} activeDot={{ r: 8 }}/>
            </LineChart>
          </ResponsiveContainer>
        </div>
      </div>

      {/* 詳細モーダル表示 */}
      {selectedActivityId && (
        <ActivityDetail 
          activityId={selectedActivityId} 
          onClose={() => setSelectedActivityId(null)} 
        />
      )}
    </div>
  );
}

export default App;
