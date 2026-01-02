import React, { useEffect, useState } from 'react';
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

// --- 2. ペース軸の目盛りを定義 (3:30 ～ 10:00) ---
// 0.5刻み (30秒刻み) で定義する
const PACE_TICKS = [3.5, 4.0, 4.5, 5.0, 5.5, 6.0, 6.5, 7.0, 7.5, 8.0, 8.5, 9.0, 9.5, 10.0];



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
  const formatPace = (decimal) => {
    if (!decimal || decimal === 0 || !isFinite(decimal)) return "--:--";
    const totalSeconds = Math.round(decimal * 60);
    const min = Math.floor(totalSeconds / 60);
    const sec = totalSeconds % 60;
    return `${min}:${sec.toString().padStart(2, '0')}`;
  };

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
      <div className="modal-content" onClick={e => e.stopPropagation()}>
        <button className="close-btn" onClick={onClose}>&times;</button>
        <h2>Activity Analysis (ID: {activityId})</h2>

        {loading && <div>Loading detailed data from Garmin/DB... 解析中...</div>}
        {error && <div style={{color:'red'}}>{error}</div>}

        {streams && !loading && (
          <div>
            {/* 1. ペースグラフ */}
            <div className="chart-title">Pace (min/km) - 低いほど速い</div>
            <div className="detail-chart-row">
              <ResponsiveContainer width="100%" height="100%">
                <LineChart {...commonChartProps}>
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis dataKey="time_min" type="number" domain={['dataMin', 'dataMax']} label={{ value: 'Time (min)', position: 'insideBottom', offset: -5 }} tickFormatter={formatPace} />
                  {/* ペースは反転させた方が直感的 */}
                  <YAxis yAxisId="right" domain={['auto', 'auto']} reversed={true} tickFormatter={formatPace} />
                      <Tooltip
                  // 横軸（時間）の表示も見やすくする
                  labelFormatter={(label) => `Time: ${formatPace(label)} min`}

                  // ★ ここがキモだ！値と名前を見て、ペースなら変換する
                  formatter={(value, name) => {
                    // <Line name="Pace" ...> と設定しているなら name は "Pace" になる
                    // 念のため "pace_min_km" も対象に入れておく（安全策）
                    if (name === 'Pace' || name === 'pace_min_km') {
                      // [変換後の値, ラベル名] を返す
                      return [formatPace(value), 'Pace (min/km)'];
                    }
                    // 心拍数などはそのまま返す
                    return [value, name];
                  }}

                  // ついでに見た目も少し整える（お好みで）
                  contentStyle={{ backgroundColor: '#fff', borderRadius: '5px', border: '1px solid #ccc' }}
                />
                  <Line type="monotone" yAxisId="right" dataKey="pace_min_km" stroke="#82ca9d" dot={false} name="Pace" unit="min/km" strokeWidth={2}/>
                </LineChart>
              </ResponsiveContainer>
            </div>

            {/* 2. 心拍数グラフ */}
            <div className="chart-title">Heart Rate (bpm)</div>
            <div className="detail-chart-row">
              <ResponsiveContainer width="100%" height="100%">
                <LineChart {...commonChartProps}>
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis dataKey="time_min" hide={true} tickFormatter={formatPace}/> {/* 中間のX軸は隠す */}
                  <YAxis domain={['auto', 'auto']} />
                  <Tooltip content={<CustomTooltip />} />
                  <Line type="monotone" dataKey="hr" stroke="#ff7300" dot={false} name="HR" unit="bpm" strokeWidth={2}/>
                </LineChart>
              </ResponsiveContainer>
            </div>

            {/* 3. ピッチ (Cadence) グラフ */}
            <div className="chart-title">Cadence (spm)</div>
            <div className="detail-chart-row">
              <ResponsiveContainer width="100%" height="100%">
                <LineChart {...commonChartProps}>
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis dataKey="time_min" hide={true} tickFormatter={formatPace} />
                  <YAxis domain={['auto', 'auto']} />
                  <Tooltip content={<CustomTooltip />} />
                  <Line type="monotone" dataKey="cadence" stroke="#8884d8" dot={false} name="Cadence" unit="spm" />
                </LineChart>
              </ResponsiveContainer>
            </div>

             {/* 4. ストライド (Stride Length) グラフ */}
            <div className="chart-title">Stride Length (m)</div>
            <div className="detail-chart-row">
              <ResponsiveContainer width="100%" height="100%">
                <LineChart {...commonChartProps}>
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis dataKey="time_min" hide={true} tickFormatter={formatPace} />
                  <YAxis domain={['auto', 'auto']} />
                  <Tooltip content={<CustomTooltip />} />
                  <Line type="monotone" dataKey="stride_m" stroke="#ffc658" dot={false} name="Stride" unit="m" />
                </LineChart>
              </ResponsiveContainer>
            </div>

          </div>
        )}
      </div>
    </div>
  );
}

export default ActivityDetail;
