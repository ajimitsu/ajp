import React, { useEffect, useState } from 'react';
import axios from 'axios';
import {
  LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer, BarChart, Bar, Brush, ComposedChart
} from 'recharts';
import ActivityDetail from './ActivityDetail';
import './App.css';

// 10進法の数値を「分:秒」の文字列に変換する関数
const formatPace = (decimal) => {
  if (!decimal || decimal === 0 || !isFinite(decimal)) return "--:--";

  // 秒数に換算して四捨五入（5.99分 → 6:00 になるように）
  const totalSeconds = Math.round(decimal * 60);
  const min = Math.floor(totalSeconds / 60);
  const sec = totalSeconds % 60;

  // 秒が1桁なら0埋めする (例: 5:5 → 5:05)
  return `${min}:${sec.toString().padStart(2, '0')}`;
};


// --- ラモス流・移動平均計算ロジック ---
// windowSize (例: 7) の平均を計算してデータに追加する
const calculateMovingAverage = (data, key, windowSize) => {
  if (!data || data.length === 0) return [];

  return data.map((item, index) => {
    // 過去 windowSize 分のデータを取得
    const start = Math.max(0, index - windowSize + 1);
    const subset = data.slice(start, index + 1);

    // 有効な数値だけを抽出
    const validValues = subset
      .map(d => d[key])
      .filter(v => v !== null && v !== undefined && v > 0);

    if (validValues.length === 0) return { ...item, [`${key}_ma`]: null };

    const sum = validValues.reduce((a, b) => a + b, 0);
    const avg = sum / validValues.length;

    // 新しいキー (例: efficiency_score_ma) として追加
    return { ...item, [`${key}_ma`]: round(avg, 2) };
  });
};

const round = (num, decimals) => {
  return Math.round(num * Math.pow(10, decimals)) / Math.pow(10, decimals);
};

function App() {
  const [data, setData] = useState(null);
  const [syncing, setSyncing] = useState(false);
  const [selectedActivityId, setSelectedActivityId] = useState(null);
  const [processedData, setProcessedData] = useState([]);

  const fetchData = () => {
    axios.get('http://localhost:8002/api/dashboard')
      .then(response => {
        setData(response.data);
        // データが来たら移動平均を計算する
        if (response.data.activities) {
          // Efficiencyの7回移動平均 (トレンドライン)
          const withMA = calculateMovingAverage(response.data.activities, 'efficiency_score', 7);
          setProcessedData(withMA);
        }
      })
      .catch(error => console.error("Error:", error));
  };

  useEffect(() => { fetchData(); }, []);

  const handleSync = () => {
    setSyncing(true);
    axios.get('http://localhost:8002/api/sync').then(() => {
        alert("同期開始。しばらくしてリロードしろ。");
        setTimeout(() => { fetchData(); setSyncing(false); }, 5000);
      });
  };

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
        <h1>🏃 Run Analytics (Trend View)</h1>
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
        {/* メインチャート: 複合チャートに変更 */}
        <div className="chart-card">
          <h3>Efficiency Trend (Raw vs 7-Run Avg)</h3>
          <p className="chart-desc">
            薄い線: 毎回の記録 / <b>太い線: 7回移動平均(トレンド)</b><br/>
            下のバーをスライドして拡大・縮小できるぞ。
          </p>
          <ResponsiveContainer width="100%" height={400}>
            <ComposedChart data={processedData} onClick={handleChartClick} style={{cursor:'pointer'}}>
              <CartesianGrid strokeDasharray="3 3" vertical={false} />
              <XAxis dataKey="date" tick={{fontSize: 12}} minTickGap={30}/>

              {/* 左軸: Efficiency */}
              <YAxis yAxisId="left" domain={['auto', 'auto']} label={{ value: 'Efficiency', angle: -90, position: 'insideLeft' }}/>

              {/* 右軸: Pace (今回は表示をシンプルにするため線は隠すが軸は残してもいい) */}
              <YAxis yAxisId="right" orientation="right" domain={['auto', 'auto']} reversed={true} unit="" tickFormatter={formatPace}/>

              <Tooltip />
            // formatterを使うと、ポップアップの中身を書き換えられる
              formatter={(value, name) => {
                if (name === "Pace (min/km)") return [formatPace(value), name];
                return [value, name];
              }}
              labelFormatter={(label) => `Date: ${label}`}
              <Legend verticalAlign="top" height={36}/>

              {/* 1. 生データ (薄く表示、ドットなし) */}
              <Line yAxisId="left" type="monotone" dataKey="efficiency_score" stroke="#8884d8" strokeOpacity={0.3} strokeWidth={1} dot={false} name="Raw Efficiency" />

              {/* 2. 移動平均線 (太く強調、ドットなし) */}
              <Line yAxisId="left" type="monotone" dataKey="efficiency_score_ma" stroke="#8884d8" strokeWidth={3} dot={false} name="7-Run Avg (Trend)" />

              {/* 3. ペース (緑色、ドットなし) */}
              <Line yAxisId="right" type="monotone" dataKey="pace_min_km" stroke="#82ca9d" strokeWidth={2} dot={false} name="Pace (min/km)"/>

              {/* 4. ズーム用ブラシ (ここがキモだ！) */}
              <Brush dataKey="date" height={30} stroke="#8884d8" />
            </ComposedChart>
          </ResponsiveContainer>
        </div>

        <div className="chart-card">
          <h3>Distance History</h3>
          <ResponsiveContainer width="100%" height={300}>
            <BarChart data={processedData}>
              <CartesianGrid strokeDasharray="3 3" vertical={false}/>
              <XAxis dataKey="date" tick={{fontSize: 12}} minTickGap={30}/>
              <YAxis />
              <Tooltip />
              <Bar dataKey="distance_km" fill="#82ca9d" name="Distance (km)" radius={[4, 4, 0, 0]} />
              <Brush dataKey="date" height={30} stroke="#82ca9d" />
            </BarChart>
          </ResponsiveContainer>
        </div>
      </div>

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