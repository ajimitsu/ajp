import React, { useEffect, useState } from 'react';
import axios from 'axios';
import {
  LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer, BarChart, Bar, Brush, ComposedChart
} from 'recharts';
import ActivityDetail from './ActivityDetail';
import PerformanceChart from './PerformanceChart';
import MetricsGuide from './MetricsGuide';
import companyLogo from './assets/logo.jpg';
import './App.css';

import Login from './Login';

const formatPace = (decimal) => {
  if (!decimal || decimal === 0 || !isFinite(decimal)) return "--:--";
  const totalSeconds = Math.round(decimal * 60);
  const min = Math.floor(totalSeconds / 60);
  const sec = totalSeconds % 60;
  return `${min}:${sec.toString().padStart(2, '0')}`;
};


// --- ラモス流・移動平均計算ロジック ---
const calculateMovingAverage = (data, key, windowSize) => {
  if (!data || data.length === 0) return [];

  return data.map((item, index) => {
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
  const [token, setToken] = useState(localStorage.getItem('token'));
  const [data, setData] = useState(null);
  const [syncing, setSyncing] = useState(false);
  const [selectedActivityId, setSelectedActivityId] = useState(null);
  const [processedData, setProcessedData] = useState([]);
  const API_URL = process.env.REACT_APP_API_URL || "http://localhost:8002/api";

  // 1. ログアウト関数（最優先）
  const handleLogout = () => {
    localStorage.removeItem('token');
    setToken(null);
    setData(null);
  };

  // 2. ★修正ポイント: トークンが変わったらヘッダーを設定する副作用
  useEffect(() => {
    if (token) {
      axios.defaults.headers.common['Authorization'] = `Bearer ${token}`;
    } else {
      delete axios.defaults.headers.common['Authorization'];
    }
  }, [token]);

  // 3. データ取得関数
  // useCallbackを使うのがベストだが、今はシンプルにこのままでいい
  const fetchData = () => {
    if (!token) return; // トークンがないなら何もしない

    axios.get(`${API_URL}/dashboard`)
      .then(response => {
        setData(response.data);
        if (response.data.activities) {
          const withMA = calculateMovingAverage(response.data.activities, 'efficiency_score', 7);
          setProcessedData(withMA);
        }
      })
      .catch(error => {
        console.error("Fetch error:", error);
        if (error.response && error.response.status === 401) {
            handleLogout();
        } else {
            // 401以外（サーバーダウンなど）の時はLoadingを解除するために空データを入れる等の処置も検討
            // setData({ stats: {}, activities: [], feedback: "Error loading data" });
        }
      });
  };

  // 4. ★修正ポイント: 起動時 & ログイン完了時にデータを読み込む
  useEffect(() => {
    fetchData();
  }, [token]); // ← ここに [token] があるのが超重要！！


  // 5. Sync処理
  const handleSync = () => {
    setSyncing(true);

    axios.get(`${API_URL}/sync`)
      .then(response => {
        alert("Syncing... Will reload the data in 5 seconds.");
        setTimeout(() => {
            fetchData();
            setSyncing(false);
        }, 5000);
      })
      .catch(error => {
        console.error("Sync Error:", error);
        setSyncing(false);

        if (error.response) {
            alert(`同期失敗！Server Error: ${error.response.status}\n${JSON.stringify(error.response.data)}`);
        } else {
            alert(`同期失敗！Network Error: ${error.message}`);
        }
      });
  };

  // ... (handleChartClick などはそのまま) ...
  const handleChartClick = (point) => {
      // (省略: お前のコードのままでOK)
      if (!point) return;
        let targetId = null;
        if (point && point.activePayload && point.activePayload.length > 0) {
          targetId = point.activePayload[0].payload.activity_id;
        }
        else if (point.activity_id) {
          targetId = point.activity_id;
        }

        if (targetId) {
          setSelectedActivityId(targetId);
        }
  };

  // --- 描画ロジック ---

  // 検問1: 未ログイン
  if (!token) {
    return <Login onLogin={(t) => setToken(t)} />;
  }

  // 検問2: ロード中
  if (!data) {
    return <div style={{padding:'20px'}}>Loading Dashboard...</div>;
  }

    // 分(float)を受け取って h:mm:ss または mm:ss にする
    const formatDuration = (minutes) => {
      if (!minutes || minutes === 0) return "--:--";
      const totalSeconds = Math.round(minutes * 60);
      const h = Math.floor(totalSeconds / 3600);
      const m = Math.floor((totalSeconds % 3600) / 60);
      const s = totalSeconds % 60;

      if (h > 0) {
        return `${h}:${m.toString().padStart(2, '0')}:${s.toString().padStart(2, '0')}`;
      }
      return `${m}:${s.toString().padStart(2, '0')}`;
    };

  const getBestSplits = (activities, key, distanceKm) => {
    if (!activities) return [];

    return activities
      // 1. そのSplitデータが存在し、0より大きいものだけ残す
      .filter(a => a[key] !== undefined && a[key] !== null && a[key] > 0)
      // 2. タイムが速い順（昇順）に並べ替え
      .sort((a, b) => a[key] - b[key])
      // 3. 上位5つを取得
      .slice(0, 5)
      .map(a => {
        const timeInMin = a[key];

        return {
          ...a,
          pb_display_time: formatDuration(timeInMin), // 分に変換してフォーマット
          pb_pace: formatPace(timeInMin / distanceKm) // 分 / 距離 = ペース(min/km)
        };
      });
  };


    const getBestEfforts = (activities, minDist, maxDist, distanceKm) => {
        if (!activities) return [];
        return activities
          .filter(a => a.distance_km >= minDist && a.distance_km <= maxDist) // 距離でフィルタ
          .sort((a, b) => a.duration_min - b.duration_min) // タイムが速い順 (昇順)
          .slice(0, 5)
          .map(a => {
            const duration_min = a.duration_min;

            return {
              ...a,
              pb_display_time: formatDuration(duration_min), // 分に変換してフォーマット
              pb_pace: formatPace(duration_min / distanceKm) // 分 / 距離 = ペース(min/km)
            };
          });
      };

  // 距離ごとのベスト5を取得
  // GPS誤差を考慮して少し幅を持たせているぞ (例: 5kmは 4.9~5.2km)
  const best1k = getBestEfforts(processedData, 0.9, 1.2, 1.0);
  const best1m = getBestEfforts(processedData, 1.5, 1.8, 1.609);
  const best5k = getBestEfforts(processedData, 4.9, 5.2, 5.0);
  const best10k = getBestEfforts(processedData, 9.8, 10.3, 10.0);
  const bestHalf = getBestEfforts(processedData, 20.9, 21.4, 21.0975);
  const best30k = getBestEfforts(processedData, 29.8, 30.3, 30);
  const bestFull = getBestEfforts(processedData, 42.0, 42.8, 42.195);

  // ※ キー名はバックエンドの実際のレスポンスに合わせて調整しろよ！
  const best1km = getBestSplits(processedData, 'fastestSplit_1km', 1);
  const best1mile = getBestSplits(processedData, 'fastestSplit_1mile', 1.609);
  const best5km = getBestSplits(processedData, 'fastestSplit_5km', 5);
  const best10km = getBestSplits(processedData, 'fastestSplit_10km', 10);

return (
    <div className="App">
      {/* ログアウトボタンはヘッダーに入れたほうがスマートだが、一旦ここでもいい */}
      <button onClick={handleLogout} style={{position:'absolute', top:10, right:10, zIndex:1000}}>Logout</button>

      {/* ▼▼▼ 全体を包むメインコンテナ (ここからスタート) ▼▼▼ */}
      <div className="dashboard-container">

        {/* 1. Header Area */}
        <header className="header" style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          padding: '10px 20px',
          background: '#ffffff',
          boxShadow: '0 2px 4px rgba(0,0,0,0.1)',
          marginBottom: '20px',
          borderRadius: '8px' // コンテナ内なら角丸も合うぞ
        }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '15px' }}>
            <img
              src={companyLogo}
              alt="Company Logo"
              style={{ height: '40px', width: 'auto', borderRadius: '4px' }}
            />
            <h1 style={{ margin: 0, fontSize: '1.5em', color: '#333' }}>
              Run Analytics
            </h1>
          </div>

          <button
            className="sync-btn"
            onClick={handleSync}
            disabled={syncing}
            style={{
              padding: '8px 16px',
              fontSize: '0.9em',
              cursor: syncing ? 'not-allowed' : 'pointer',
              opacity: syncing ? 0.7 : 1
            }}
          >
            {syncing ? "⏳ Syncing..." : "🔄 Sync Garmin"}
          </button>
        </header>

        {/* 2. Feedback Section */}
        {data.feedback && (
          <div className="feedback-section">
            <p style={{ margin: 0, fontWeight: 'bold' }}>Coach Feedback: "{data.feedback}"</p>
          </div>
        )}

        {/* 3. Key Stats Cards (上部に配置) */}
        <div className="stats-container" style={{ display: 'flex', gap: '15px', paddingBottom: '20px', flexWrap: 'wrap' }}>

          {/* Marathon Shape */}
          <div className="card" style={{ flex: 1, background: '#fff', padding: '15px', borderRadius: '8px', boxShadow: '0 2px 5px rgba(0,0,0,0.1)', minWidth: '150px', textAlign: 'center' }}>
            <h3 style={{ margin: '0 0 10px 0', fontSize: '1.1em', color: '#444' }}>Marathon Shape</h3>
            <div className="stat-value" style={{ fontSize: '2em', fontWeight: 'bold', color: '#2c3e50' }}>
              {data.stats?.marathon_shape ?? '-'}
            </div>
            <p style={{ fontSize: '0.8em', color: '#666', margin: '5px 0 0 0' }}>Based on CTL & Long Runs</p>
          </div>

          {/* Weekly Distance */}
          <div className="card" style={{ flex: 1, background: '#fff', padding: '15px', borderRadius: '8px', boxShadow: '0 2px 5px rgba(0,0,0,0.1)', minWidth: '150px', textAlign: 'center' }}>
            <h3 style={{ margin: '0 0 10px 0', fontSize: '1.1em', color: '#444' }}>Weekly Distance</h3>
            <div className="stat-value" style={{ fontSize: '2em', fontWeight: 'bold', color: '#2980b9' }}>
              {data.stats?.weekly_volume_km !== undefined ? Number(data.stats.weekly_volume_km).toFixed(2) : '-'}
            </div>
            <p style={{ fontSize: '0.8em', color: '#666', margin: '5px 0 0 0' }}>Last 7 Days (km)</p>
          </div>

          {/* TSB */}
          <div className="card" style={{ flex: 1, background: '#fff', padding: '15px', borderRadius: '8px', boxShadow: '0 2px 5px rgba(0,0,0,0.1)', minWidth: '150px', textAlign: 'center' }}>
            <h3 style={{ margin: '0 0 10px 0', fontSize: '1.1em', color: '#444' }}>Form (TSB)</h3>
            <div className="stat-value" style={{
              fontSize: '2em', fontWeight: 'bold',
              color: (data.stats?.current_tsb || 0) >= 0 ? '#27ae60' : '#c0392b'
            }}>
              {data.stats?.current_tsb !== undefined ? Number(data.stats.current_tsb).toFixed(2) : '-'}
            </div>
            <p style={{ fontSize: '0.8em', color: '#666', margin: '5px 0 0 0' }}>Current TSB</p>
          </div>

          {/* CTL */}
          <div className="card" style={{ flex: 1, background: '#fff', padding: '15px', borderRadius: '8px', boxShadow: '0 2px 5px rgba(0,0,0,0.1)', minWidth: '150px', textAlign: 'center' }}>
            <h3 style={{ margin: '0 0 10px 0', fontSize: '1.1em', color: '#444' }}>Fitness (CTL)</h3>
            <div className="stat-value" style={{ fontSize: '2em', fontWeight: 'bold', color: '#2980b9' }}>
              {data.stats?.current_ctl !== undefined ? Number(data.stats.current_ctl).toFixed(2) : '-'}
            </div>
            <p style={{ fontSize: '0.8em', color: '#666', margin: '5px 0 0 0' }}>Current CTL</p>
          </div>
        </div>
        {/* 4. Charts Section (表より先にグラフを見せるのが鉄則) */}
        <div className="charts-container" style={{ marginBottom: '30px' }}>
          <PerformanceChart data={processedData} onClick={handleChartClick} />
        </div>

        {/* 5. Metrics Guide (表を見る前のヒントとして配置) */}
        <MetricsGuide />

        {/* 6. Detailed Activity Table */}
        <div className="table-container">
          <table className="activity-table">
            <thead>
              <tr>
                <th>Date</th>
                <th>Dist (km)</th>
                <th>Time (min)</th>
                <th>Pace</th>
                <th>Avg HR</th>
                <th>A:C</th>
                <th>Monotony</th>
                <th>Strain</th>
                <th>Efficiency</th>
                <th>TRIMP</th>
                <th>TSB</th>
                <th>Type</th>
              </tr>
            </thead>
            <tbody>
              {processedData.slice().reverse().map((activity) => (
                <tr key={activity.activity_id} onClick={() => handleChartClick(activity)}>
                  <td>{activity.date}</td>
                  <td style={{ fontWeight: 'bold' }}>{Number(activity.distance_km).toFixed(2)}</td>
                  <td>{formatPace(Number(activity.duration_min).toFixed(1))}</td>
                  <td>{formatPace(activity.pace_min_km)}</td>
                  <td>{activity.avg_hr ? Math.round(activity.avg_hr) : '-'}</td>
                  <td>
                    {activity.ac_ratio ? (
                      <span style={{ color: activity.ac_ratio > 1.5 ? 'red' : 'inherit', fontWeight: 'bold' }}>
                        {Number(activity.ac_ratio).toFixed(2)}
                      </span>
                    ) : '-'}
                  </td>
                  <td>{activity.monotony ? Number(activity.monotony).toFixed(1) : '-'}</td>
                  <td>{activity.training_strain ? Math.round(activity.training_strain) : '-'}</td>
                  <td>
                    {activity.efficiency_score ? (
                      <span style={{ color: activity.efficiency_score > 1.3 ? 'green' : 'inherit', fontWeight: 'bold' }}>
                        {Number(activity.efficiency_score).toFixed(2)}
                      </span>
                    ) : '-'}
                  </td>
                  <td>{activity.trimp ? Math.round(activity.trimp) : '-'}</td>
                  <td>
                    {activity.tsb !== undefined ? (
                      <span style={{ fontWeight: 'bold', color: activity.tsb >= 0 ? 'green' : 'red' }}>
                        {Math.round(activity.tsb)}
                      </span>
                    ) : '-'}
                  </td>
                  <td>
                    <span style={{ padding: '2px 6px', borderRadius: '4px', fontSize: '11px', backgroundColor: '#eee' }}>
                      {activity.detected_type || 'RUN'}
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        {/* 7. Personal Bests Section (ここもコンテナの中に入れる！) */}
        <div className="pb-section" style={{ paddingBottom: '30px' }}>
          <h2 style={{ fontSize: '1.2em', borderLeft: '5px solid #e74c3c', paddingLeft: '10px', marginBottom: '15px', color: '#333' }}>
            Personal Bests & Fastest Splits
          </h2>

          <div style={{
            display: 'grid',
            gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))', // 少し幅を狭めてフィットしやすくした
            gap: '20px',
            alignItems: 'start'
          }}>
            {/* Splits (Garmin Data) */}
            <BestSplitTable title="Fastest 1km" records={best1km} onSelect={handleChartClick} />
            <BestSplitTable title="Fastest 1mile" records={best1mile} onSelect={handleChartClick} />
            <BestSplitTable title="Fastest 5km" records={best5km} onSelect={handleChartClick} />
            <BestSplitTable title="Fastest 10km" records={best10km} onSelect={handleChartClick} />

            {/* Efforts (Calculated) */}
            <BestSplitTable title="Best 1km (Calc)" records={best1k} onSelect={handleChartClick} />
            <BestSplitTable title="Best 1mile (Calc)" records={best1m} onSelect={handleChartClick} />
            <BestSplitTable title="Best 5km (Calc)" records={best5k} onSelect={handleChartClick} />
            <BestSplitTable title="Best 10km (Calc)" records={best10k} onSelect={handleChartClick} />
            <BestSplitTable title="Best Half Marathon" records={bestHalf} onSelect={handleChartClick} />
            <BestSplitTable title="Best 30km" records={best30k} onSelect={handleChartClick} />
            <BestSplitTable title="Best Full Marathon" records={bestFull} onSelect={handleChartClick} />
          </div>
        </div>



        {/* 8. Activity Modal */}
        {selectedActivityId && (
          <ActivityDetail
            activityId={selectedActivityId}
            onClose={() => setSelectedActivityId(null)}
          />
        )}

      </div>
      {/* ▲▲▲ dashboard-container はここで閉じる！これが正解だ！ ▲▲▲ */}

    </div>
  );
}


// Splitデータ専用のランキングテーブル
const BestSplitTable = ({ title, records, onSelect }) => {
  return (
    <div className="card" style={{ flex: '1', minWidth: '280px', background: '#fff', padding: '15px', borderRadius: '8px', boxShadow: '0 2px 5px rgba(0,0,0,0.1)' }}>
      <h3 style={{ margin: '0 0 10px 0', borderBottom:'2px solid #eee', paddingBottom:'8px', color:'#2c3e50', fontSize:'1em' }}>
        {title} 🏆
      </h3>
      {records.length === 0 ? (
        <p style={{ color: '#ccc', fontSize: '0.9em', fontStyle:'italic' }}>No records found.</p>
      ) : (
        <table style={{ width: '100%', fontSize: '0.85em', borderCollapse: 'collapse' }}>
          <thead>
            <tr style={{ color: '#888', textAlign: 'left', borderBottom:'1px solid #f0f0f0' }}>
              <th style={{padding:'5px'}}>#</th>
              <th style={{padding:'5px'}}>Date</th>
              <th style={{padding:'5px'}}>Time</th>
              <th style={{padding:'5px'}}>Pace</th>
            </tr>
          </thead>
          <tbody>
            {records.map((run, index) => (
              <tr
                key={run.activity_id}
                // クリックで詳細へ飛ぶ（run全体を渡すかIDを渡すか、handleChartClickの実装に合わせる）
                onClick={() => onSelect(run)}
                style={{ cursor: 'pointer', transition: 'background 0.2s' }}
                onMouseEnter={(e) => e.currentTarget.style.background = '#f4f6f7'}
                onMouseLeave={(e) => e.currentTarget.style.background = 'transparent'}
              >
                <td style={{
                  fontWeight: index === 0 ? 'bold' : 'normal',
                  color: index === 0 ? '#fff' : '#666',
                  backgroundColor: index === 0 ? '#f39c12' : 'transparent', // 1位は金メダル色背景
                  textAlign: 'center',
                  borderRadius: '50%',
                  width: '20px',
                  height: '20px',
                  display: 'inline-block',
                  lineHeight: '20px',
                  marginTop: '5px'
                }}>
                  {index + 1}
                </td>
                <td style={{padding:'8px 5px', color:'#555'}}>{run.date}</td>
                <td style={{ fontWeight: 'bold', color: '#2980b9', padding:'8px 5px' }}>
                  {run.pb_display_time}
                </td>
                <td style={{padding:'8px 5px', fontFamily:'monospace', color:'#555'}}>
                  {run.pb_pace}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>





  );





};

export default App;