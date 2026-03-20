import React from 'react';

// --- メトリクス用語集コンポーネント ---
const MetricsGuide = () => {
  return (
    <div style={{ margin: '20px 20px', border: '1px solid #ddd', borderRadius: '8px', overflow: 'hidden' }}>
      <details style={{ background: '#fff' }}>
        <summary style={{
          padding: '15px',
          cursor: 'pointer',
          fontWeight: 'bold',
          background: '#f8f9fa',
          color: '#2c3e50',
          outline: 'none'
        }}>
          📚 Coach Ramos's Technical Guide (用語と適正値の目安)
        </summary>

        <div style={{ padding: '20px', display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))', gap: '20px' }}>

          {/* A:C Ratio */}
          <div className="guide-item">
            <h4 style={{ margin: '0 0 5px 0', color: '#e74c3c' }}>A:C Ratio (怪我リスク)</h4>
            <p style={{ fontSize: '0.9em', color: '#555', margin:0 }}>
              急激な負荷の増加率。「先週までの積み上げ(Chronic)」に対して「今週(Acute)」どれだけやったか。
            </p>
            <ul style={{ fontSize: '0.85em', marginTop: '5px', paddingLeft: '20px' }}>
              <li><strong>0.8 - 1.3</strong>: ✅ 最適 (Optimal)</li>
              <li><strong>1.5以上</strong>: ⚠️ 危険 (怪我のリスク激増)</li>
            </ul>
          </div>

          {/* Monotony */}
          <div className="guide-item">
            <h4 style={{ margin: '0 0 5px 0', color: '#d35400' }}>Monotony (単調さ)</h4>
            <p style={{ fontSize: '0.9em', color: '#555', margin:0 }}>
              トレーニングのバラつきの無さ。毎日同じ距離を同じペースで走ると高くなる。
            </p>
            <ul style={{ fontSize: '0.85em', marginTop: '5px', paddingLeft: '20px' }}>
              <li><strong>1.5以下</strong>: ✅ 良好 (メリハリがある)</li>
              <li><strong>2.0以上</strong>: ⚠️ 危険 (オーバートレーニング予備軍)</li>
            </ul>
          </div>

          {/* TRIMP */}
          <div className="guide-item">
            <h4 style={{ margin: '0 0 5px 0', color: '#2980b9' }}>TRIMP (トレーニング衝動)</h4>
            <p style={{ fontSize: '0.9em', color: '#555', margin:0 }}>
              心拍数に基づいた「その日の練習のキツさ」のスコア。時間(分) x 平均心拍数（Heart Rate Reserve） x 指数関数的重み付け
            </p>
            <ul style={{ fontSize: '0.85em', marginTop: '5px', paddingLeft: '20px' }}>
              <li><strong>50-100</strong>: つなぎの練習 (Recovery/Easy)</li>
              <li><strong>100-200</strong>: ポイント練習 (Threshold)</li>
              <li><strong>200以上</strong>: 高強度・ロング走 (Hard)</li>
            </ul>
          </div>

          {/* Strain */}
          <div className="guide-item">
            <h4 style={{ margin: '0 0 5px 0', color: '#8e44ad' }}>Training Strain (身体ダメージ)</h4>
            <p style={{ fontSize: '0.9em', color: '#555', margin:0 }}>
              「負荷(Load: 7 days total of TRIMP) × 単調さ(Monotony)」。単調でハードな練習ほどダメージがデカい。
            </p>
            <ul style={{ fontSize: '0.85em', marginTop: '5px', paddingLeft: '20px' }}>
              <li>高い数値が続いたら、完全休養か軽いJOGを入れろ。</li>
            </ul>
          </div>

        {/* CTL (Fitness) */}
          <div className="guide-item">
            <h4 style={{ margin: '0 0 5px 0', color: '#2980b9' }}>CTL (体力・Fitness)</h4>
            <p style={{ fontSize: '0.9em', color: '#555', margin:0 }}>
              Chronic Training Load。過去42日間の負荷の「積み上げ」。42日間のTRIMP指数加重平均。基礎体力を表す。
            </p>
            <ul style={{ fontSize: '0.85em', marginTop: '5px', paddingLeft: '20px' }}>
              <li><strong>右肩上がり ↗</strong>: ✅ トレーニングが順調に積めている。</li>
              <li><strong>維持・低下 ↘</strong>: 練習不足または調整期。</li>
              <li>マラソン完走ならまずは <strong>60-80</strong>、サブ3狙いなら <strong>100以上</strong> を目指せ。</li>
            </ul>
          </div>

          {/* ATL (Fatigue) */}
          <div className="guide-item">
            <h4 style={{ margin: '0 0 5px 0', color: '#e67e22' }}>ATL (疲労・Fatigue)</h4>
            <p style={{ fontSize: '0.9em', color: '#555', margin:0 }}>
              Acute Training Load。直近7日間の「急激な負荷」。7日間のTRIMP指数加重平均。今の疲れ具合を表す。
            </p>
            <ul style={{ fontSize: '0.85em', marginTop: '5px', paddingLeft: '20px' }}>
              <li><strong>CTLより高い</strong>: 負荷をかけている時期（強化期）。</li>
              <li><strong>急上昇 ⚠</strong>: 怪我のリスク大。休息が必要。</li>
              <li>レース1週間前はこれをガクンと落として、TSBをプラスにするんだ。</li>
            </ul>
          </div>

          {/* TSB */}
          <div className="guide-item">
            <h4 style={{ margin: '0 0 5px 0', color: '#f39c12' }}>TSB (好調さ・Form)</h4>
            <p style={{ fontSize: '0.9em', color: '#555', margin:0 }}>
              「体力(CTL) - 疲労(ATL)」。レース当日の元気さ。
            </p>
            <ul style={{ fontSize: '0.85em', marginTop: '5px', paddingLeft: '20px' }}>
              <li><strong>プラス (+)</strong>: 元気 (レース向き)</li>
              <li><strong>マイナス (-)</strong>: 疲労蓄積 (トレーニング期)</li>
              <li><strong>レース当日</strong>: +5 〜 +15 を狙ってテーパリングしろ。</li>
            </ul>
          </div>

          {/* Efficiency */}
          <div className="guide-item">
            <h4 style={{ margin: '0 0 5px 0', color: '#27ae60' }}>Efficiency (ランニングエコノミー)</h4>
            <p style={{ fontSize: '0.9em', color: '#555', margin:0 }}>
              燃費の良さ。Speed / HeartRate 等で算出。
            </p>
            <ul style={{ fontSize: '0.85em', marginTop: '5px', paddingLeft: '20px' }}>
              <li><strong>上昇傾向 ↗</strong>: ✅ 成長中 (同じ心拍で速く走れている)</li>
              <li><strong>下降傾向 ↘</strong>: ⚠️ 疲労 or フォームの乱れ</li>
              <li>目安: 1.3以上ならかなり優秀。</li>
            </ul>
          </div>

          {/* Marathon Shape */}
          <div className="guide-item">
            <h4 style={{ margin: '0 0 5px 0', color: '#27ae60' }}>Marathon Shape (マラソンシェイプ)</h4>
            <p style={{ fontSize: '0.9em', color: '#555', margin:0 }}>
              CTL CTL(基礎体力) + (過去10週間でのトップ3回のロング走20+km距離平均 × 2.5)で算出。
            </p>
            <ul style={{ fontSize: '0.85em', marginTop: '5px', paddingLeft: '20px' }}>
              <li><strong>80 〜 110</strong>: 完走 〜 サブ4.5レベル</li>
              <li><strong>115 〜 145</strong>: サブ4 レベル</li>
              <li><strong>150 〜 180</strong>: サブ3.5 レベル</li>
              <li><strong>190 〜 220+</strong>: サブ3 レベル</li>
            </ul>
          </div>

        </div>
      </details>
    </div>
  );
};

export default MetricsGuide;