import React from 'react';
import {
  ComposedChart, Line, Area, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer, ReferenceLine, Brush
} from 'recharts';

const PerformanceChart = ({ data, onClick}) => {
  if (!data || data.length === 0) return null;

  // TSBがプラスかマイナスかで色を変えるためのグラデーション定義
  const gradientOffset = () => {
    const dataMax = Math.max(...data.map((i) => i.tsb));
    const dataMin = Math.min(...data.map((i) => i.tsb));

    if (dataMax <= 0) return 0;
    if (dataMin >= 0) return 1;

    return dataMax / (dataMax - dataMin);
  };

  const off = gradientOffset();

// --- 【追加】初期表示範囲の計算 ---
  // データが30件以上あるなら「全件数 - 30」を開始位置にする。
  // これで常に「直近30日」がデフォルト表示になる。
  const defaultStartIndex = data.length > 30 ? data.length - 30 : 0;

  return (
    <div className="chart-card">
      <h3>Performance Management Chart (PMC)</h3>
      <p className="chart-desc">
        <span style={{color:'#8884d8', fontWeight:'bold'}}>🟦 CTL (体力)</span>: 過去42日の積み上げ。高いほど強い。<br/>
        <span style={{color:'#ff7300', fontWeight:'bold'}}>🟥 ATL (疲労)</span>: 直近7日の負荷。急上昇は怪我のもと。<br/>
        <span style={{color:'#82ca9d', fontWeight:'bold'}}>🟨 TSB (調子)</span>: ゼロ以上なら好調。レース前はプラスにしろ。<br/>
      </p>

      <ResponsiveContainer width="100%" height={400}>
        <ComposedChart data={data} onClick={onClick} style={{cursor:'pointer'}} margin={{ top: 20, right: 20, bottom: 20, left: 20 }}>
          <CartesianGrid strokeDasharray="3 3" vertical={false} />

          <XAxis
            dataKey="date"
            tick={{fontSize: 12}}
            minTickGap={30}
            // 日付を短く表示
            tickFormatter={(str) => {
                const d = new Date(str);
                return `${d.getMonth()+1}/${d.getDate()}`;
            }}
          />

          {/* 左軸: Load (CTL, ATL, TRIMP用) */}
          <YAxis yAxisId="left" label={{ value: 'Load (TRIMP)', angle: -90, position: 'insideLeft' }} />

          {/* 右軸: TSB用 (範囲を固定して0を見やすくする) */}
          <YAxis yAxisId="right" orientation="right" label={{ value: 'TSB (Form)', angle: 90, position: 'insideRight' }} />

          <Tooltip
            labelFormatter={(label) => `Date: ${label}`}
            formatter={(value, name) => [Math.round(value), name]}
          />
          <Legend verticalAlign="top" height={36}/>

          {/* 0ラインの強調 */}
          <ReferenceLine y={0} yAxisId="right" stroke="#000" strokeOpacity={0.2} />

          {/* グラデーション定義 (TSB用) */}
          <defs>
            <linearGradient id="splitColor" x1="0" y1="0" x2="0" y2="1">
              <stop offset={off} stopColor="#82ca9d" stopOpacity={0.6}/>
              <stop offset={off} stopColor="#ff7300" stopOpacity={0.6}/>
            </linearGradient>
          </defs>

          {/* 1. TRIMP (日々の負荷) - 背景に薄く表示 */}
          <Bar yAxisId="left" dataKey="trimp" name="Daily TRIMP" fill="#e0e0e0" barSize={20} />

          {/* 2. TSB (調子) - エリアチャート */}
          <Area
            yAxisId="right"
            type="monotone"
            dataKey="tsb"
            name="TSB (Form)"
            stroke="#000"
            strokeOpacity={0.2}
            fill="url(#splitColor)"
          />

          {/* 3. ATL (疲労) */}
          <Line
            yAxisId="left"
            type="monotone"
            dataKey="atl"
            name="ATL (Fatigue)"
            stroke="#ff7300"
            strokeWidth={2}
            dot={false}
            strokeDasharray="5 5" // 点線にする
          />

          {/* 4. CTL (体力) - 一番目立たせる */}
          <Line
            yAxisId="left"
            type="monotone"
            dataKey="ctl"
            name="CTL (Fitness)"
            stroke="#8884d8"
            strokeWidth={3}
            dot={false}
          />

        <Brush
            dataKey="date"
            height={30}
            stroke="#8884d8"
            // これが「直近30日」を表示する魔法の設定だ
            startIndex={defaultStartIndex}
            endIndex={data.length - 1}

            // スライダー内の文字が見にくいならフォーマッターを入れる
            tickFormatter={(str) => {
                const d = new Date(str);
                return `${d.getMonth()+1}/${d.getDate()}`;
            }}
          />

        </ComposedChart>
      </ResponsiveContainer>
    </div>
  );
};

export default PerformanceChart;