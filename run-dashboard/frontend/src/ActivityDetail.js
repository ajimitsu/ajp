import React, { useEffect, useState, useMemo } from 'react';
import axios from 'axios';
import {
  LineChart,
  ComposedChart, // LineChartから格上げ
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  ReferenceArea, // 背景色用
  Legend
} from 'recharts';

// --- 1. 心拍ゾーンの定義 (自分の閾値に書き換えろ！) ---
// y1: 下限, y2: 上限, fill: 色, label: 表示名
const HR_ZONES = [
  { zone: 'Z0', y1: 0,   y2: 119, fill: '#e0e0e0', label: 'Z1: Recovery' }, // グレー
  { zone: 'Z1', y1: 120, y2: 132, fill: '#e0e0e0', label: 'Z1: Recovery' }, // グレー
  { zone: 'Z2', y1: 133, y2: 145, fill: '#add8e6', label: 'Z2: Aerobic' },  // 水色
  { zone: 'Z3', y1: 146, y2: 156, fill: '#90ee90', label: 'Z3: Tempo' },    // 薄緑
  { zone: 'Z4', y1: 157, y2: 169, fill: '#ffd700', label: 'Z4: Threshold'}, // 金色
  { zone: 'Z5', y1: 170, y2: 220, fill: '#ffcccb', label: 'Z5: Anaerobic'}  // 薄赤
];

const PACE_TICKS = [3.5, 4.0, 4.5, 5.0, 5.5, 6.0, 6.5, 7.0, 7.5, 8.0, 8.5, 9.0, 9.5, 10.0, 10.5, 11.0, 11.5, 12.0];



function ActivityDetail({ activityId, onClose }) {
  const [streams, setStreams] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const API_URL = process.env.REACT_APP_API_URL || "http://localhost:8002/api";

  useEffect(() => {
    setLoading(true);
    // 詳細データ取得APIを叩く
    axios.get(`${API_URL}/activity/${activityId}`)
      .then(response => {
        setStreams(response.data.streams);
        setLoading(false);
      })
      .catch(err => {
        console.error("Error fetching details:", err);
        setError("データの取得に失敗した。Garmin接続を確認しろ。");
        setLoading(false);
      });
  }, [activityId]);

  // 10進法のペースを「分:秒」に変換する関数
  const formatTime = (decimal) => {
    if (!decimal || decimal === 0 || !isFinite(decimal)) return "--:--";
    const totalSeconds = Math.round(decimal * 60);
    const min = Math.floor(totalSeconds / 60);
    const sec = totalSeconds % 60;
    return `${min}:${sec.toString().padStart(2, '0')}`;
  };

// ★ X軸の目盛りを「10分刻み」にするための計算
  const xAxisTicks = useMemo(() => {
    if (!streams || streams.length === 0) return [];
    const maxTime = Math.ceil(streams[streams.length - 1].time_min);
    const ticks = [];
    for (let i = 0; i <= maxTime; i += 5) {
      ticks.push(i);
    }
    return ticks;
  }, [streams]);

  // ツールチップのカスタマイズ（複数グラフで同期表示させるためシンプルに）
  const CustomTooltip = ({ active, payload, label }) => {
    if (active && payload && payload.length) {
      return (
        <div style={{ background: 'white', padding: '5px', border: '1px solid #ccc' }}>
          <p style={{margin:0}}>{`Time: ${label} min`}</p>
          {payload.map((p, index) => (
            <p key={index} style={{margin:0, color: p.color}}>{`${p.name}: ${p.value} ${p.unit || ''}`}</p>
          ))}
        </div>
      );
    }
    return null;
  };

  // 共通のチャート設定 (syncIdが重要！)
  const commonChartProps = {
    data: streams,
    syncId: "activityDetailSync", // これで全てのグラフのX軸が同期する
    margin: { top: 5, right: 30, left: 20, bottom: 5 }
  };

  return (
<div className="modal-overlay" onClick={onClose}>
      <div className="modal-content" onClick={e => e.stopPropagation()} style={{width: '90%', maxWidth: '1000px'}}>
        <button className="close-btn" onClick={onClose}>&times;</button>
        <h2 style={{borderBottom:'2px solid #333', paddingBottom:'10px'}}>Activity Analysis (ID: {activityId})</h2>

        {loading && <div className="loading">Loading detailed data...</div>}
        {error && <div className="error">{error}</div>}

        {streams && !loading && (
          <div>
            {/* ============================================================
                ★ メインチャート: Pace vs Heart Rate (Composite)
               ============================================================ */}
            <div className="chart-title" style={{marginTop:'20px', fontWeight:'bold'}}>
              Pace (Blue) vs Heart Rate (Red) with Zones
            </div>
            <div className="detail-chart-row" style={{height: '400px'}}>
              <ResponsiveContainer width="100%" height="100%">
                <ComposedChart data={streams} syncId="syncedCharts" margin={{ top: 20, right: 20, left: 20, bottom: 20 }}>
                  <CartesianGrid strokeDasharray="3 3" vertical={false} />

                  <XAxis
                    dataKey="time_min"
                    tickFormatter={formatTime}
                    ticks={xAxisTicks}
                    type="number"
                    domain={['dataMin', 'dataMax']}
                    label={{ value: 'Time (mm:ss)', position: 'insideBottomRight', offset: -10 }}
                  />

                  {/* --- 1. 背景の心拍ゾーン (必ずLineより先に書く！) --- */}
                  {HR_ZONES.map((zone) => (
                    <ReferenceArea
                      key={zone.zone}
                      yAxisId="y_hr" // 右軸(心拍)に合わせる
                      y1={zone.y1}
                      y2={zone.y2}
                      fill={zone.fill}
                      fillOpacity={0.3} // 薄くする
                      stroke="none"
                    />
                  ))}

                  {/* --- 2. 左軸: Pace (反転・固定範囲) --- */}
                  <YAxis
                    yAxisId="y_pace"
                    orientation="left"
                    reversed={true} // 速い(3:30)を上に
                    domain={[ min => Math.max(min, 3.5), max => Math.min(max, 12.0)]}
                    ticks={PACE_TICKS}
                    tickFormatter={formatTime}
                    label={{ value: 'Pace (min/km)', angle: -90, position: 'insideLeft' }}
                  />

                  {/* --- 3. 右軸: Heart Rate --- */}
                  <YAxis
                    yAxisId="y_hr"
                    orientation="right"
                    domain={[100, 200]} // 自分の最大心拍に合わせて調整
                    label={{ value: 'Heart Rate (bpm)', angle: 90, position: 'insideRight' }}
                  />

                  <Tooltip content={<CustomTooltip />} />
                  <Legend verticalAlign="top" height={36}/>

                  {/* --- 4. データライン --- */}
                  <Line
                    yAxisId="y_pace"
                    type="monotone"
                    dataKey={(data) => {
                      const val = data.pace_min_km;
                      if (val === null || val === undefined) return null;
                      // 3:30より速い(異常値) または 12:00より遅い(歩き) なら null
                      return Math.min(12.0, Math.max(3.5, val));
                    }}
                    stroke="#007bff" // 青
                    strokeWidth={2}
                    dot={false}
                    name="Pace"
                    unit="min/km"
                    isAnimationActive={false}
                    clipDot={true}
                    connectNulls={false}
                  />

                  <Line
                    yAxisId="y_hr"
                    type="monotone"
                    dataKey="hr"
                    stroke="#ff0000" // 赤
                    strokeWidth={2}
                    dot={false}
                    name="HR"
                    unit="bpm"
                  />
                </ComposedChart>
              </ResponsiveContainer>
            </div>

            {/* ============================================================
                サブチャート: Cadence & Stride (同期させる)
               ============================================================ */}
            <div style={{display:'flex', gap:'20px', marginTop:'20px'}}>

              {/* Cadence */}
              <div style={{flex:1, height:'200px'}}>
                 <div className="chart-title">Cadence (spm)</div>
                 <ResponsiveContainer width="100%" height="100%">
                  <LineChart data={streams} syncId="syncedCharts">
                    <CartesianGrid strokeDasharray="3 3" />
                    <XAxis dataKey="time_min" tickFormatter={formatTime} ticks={xAxisTicks} type="number" domain={['dataMin', 'dataMax']}/>
                    <YAxis domain={['auto', 'auto']} />
                    <Tooltip content={<CustomTooltip />} />
                    <Line type="monotone" dataKey="cadence" stroke="#8884d8" dot={false} name="Cadence" unit="spm" strokeWidth={2}/>
                  </LineChart>
                </ResponsiveContainer>
              </div>

              {/* Stride */}
              <div style={{flex:1, height:'200px'}}>
                 <div className="chart-title">Stride (m)</div>
                 <ResponsiveContainer width="100%" height="100%">
                  <LineChart data={streams} syncId="syncedCharts">
                    <CartesianGrid strokeDasharray="3 3" />
                    <XAxis dataKey="time_min" tickFormatter={formatTime} ticks={xAxisTicks} type="number" domain={['dataMin', 'dataMax']}/>
                    <YAxis domain={['auto', 'auto']} />
                    <Tooltip content={<CustomTooltip />} />
                    <Line type="monotone" dataKey="stride_m" stroke="#ffc658" dot={false} name="Stride" unit="m" strokeWidth={2}/>
                  </LineChart>
                </ResponsiveContainer>
              </div>

            </div>
          </div>
        )}
      </div>
    </div>
  );
}

export default ActivityDetail;
