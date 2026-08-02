"""
国电南瑞 · 可视化报告生成
"""
import pickle
import numpy as np
import json

CACHE_DIR = '/tmp/mc_cache'
OUTPUT = '/Users/huangren/.qoderwork/workspace/ms9393tmwes9zvfq/outputs/国电南瑞_买卖点回测_蒙特卡洛.html'

with open(f'{CACHE_DIR}/nari_results.pkl', 'rb') as f:
    data = pickle.load(f)

all_results = data['all_results']
mc_annual = np.array(data['mc_annual'])
mc_max_dd = np.array(data['mc_max_dd'])
mc_final = np.array(data['mc_final'])
best = data['best']
info = data['stock_info']

# Top20表格
table_rows = ""
for i, r in enumerate(all_results[:20]):
    color = '#4ade80' if r['annual_return'] > 0.20 else ('#fbbf24' if r['annual_return'] > 0.10 else '#f87171')
    tag = ' <span class="tag tag-best">最优</span>' if i == 0 else ''
    table_rows += f"""<tr>
        <td>{i+1}</td>
        <td style="font-weight:600">{r['buy']}{tag}</td>
        <td>{r['sell']}</td>
        <td>{r['sl']:.0%}</td><td>{r['tp']:.0%}</td><td>{r['ts']}天</td>
        <td style="color:{color};font-weight:700">{r['annual_return']*100:+.1f}%</td>
        <td>{r['win_rate']*100:.0f}%</td>
        <td>{r['n_trades']}</td>
        <td>{r['avg_hold_days']:.0f}天</td>
        <td style="color:#f87171">{r['max_drawdown']*100:.1f}%</td>
    </tr>"""

# MC直方图
hist, edges = np.histogram(mc_annual * 100, bins=40)
hist_data = {'labels': [f"{edges[i]:.0f}~{edges[i+1]:.0f}" for i in range(len(hist))], 'values': hist.tolist()}

# 最优策略交易明细
best_trades = best['trades']
trade_labels = [t['entry_date'].strftime('%m/%d') for t in best_trades]
trade_rets = [round(t['return']*100, 2) for t in best_trades]
trade_cum = np.cumprod([1+t['return'] for t in best_trades])
trade_cum_pct = [round((v-1)*100, 2) for v in trade_cum]

# 年化收益散点（所有组合）
scatter_annual = [round(r['annual_return']*100, 1) for r in all_results[:200]]
scatter_winrate = [round(r['win_rate']*100, 1) for r in all_results[:200]]
scatter_dd = [round(abs(r['max_drawdown'])*100, 1) for r in all_results[:200]]

# 买入信号分布
buy_names = list(set(r['buy'] for r in all_results[:50]))
buy_counts = [sum(1 for r in all_results[:50] if r['buy'] == bn) for bn in buy_names]

mc_pct = {f'p{p}': float(np.percentile(mc_annual, p)*100) for p in [5,25,50,75,95]}
dd_pct = {f'p{p}': float(np.percentile(mc_max_dd, p)*100) for p in [5,50,95]}

html = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>国电南瑞(600406) · 买卖点挖掘 · 蒙特卡洛</title>
<script src="https://cdnjs.cloudflare.com/ajax/libs/Chart.js/4.4.1/chart.umd.min.js"></script>
<style>
*{{margin:0;padding:0;box-sizing:border-box}}
body{{font-family:-apple-system,'SF Pro Display','PingFang SC',sans-serif;background:#0a0a0f;color:#e4e4e7;line-height:1.6}}
.container{{max-width:1400px;margin:0 auto;padding:24px}}
h1{{font-size:26px;font-weight:700;margin-bottom:6px;background:linear-gradient(135deg,#fbbf24,#f87171);-webkit-background-clip:text;-webkit-text-fill-color:transparent}}
.subtitle{{color:#71717a;font-size:13px;margin-bottom:28px}}
.grid{{display:grid;grid-template-columns:repeat(auto-fit,minmax(170px,1fr));gap:14px;margin-bottom:28px}}
.card{{background:#18181b;border:1px solid #27272a;border-radius:12px;padding:18px}}
.card-label{{font-size:11px;color:#71717a;text-transform:uppercase;letter-spacing:0.5px}}
.card-value{{font-size:24px;font-weight:700;margin-top:4px}}
.card-sub{{font-size:11px;color:#a1a1aa;margin-top:4px}}
.section{{background:#18181b;border:1px solid #27272a;border-radius:16px;padding:24px;margin-bottom:20px}}
.section-title{{font-size:17px;font-weight:600;margin-bottom:14px;color:#fafafa}}
.chart-container{{position:relative;height:340px}}
table{{width:100%;border-collapse:collapse;font-size:12px}}
th{{text-align:left;padding:8px 10px;border-bottom:2px solid #3f3f46;color:#a1a1aa;font-weight:500}}
td{{padding:8px 10px;border-bottom:1px solid #27272a}}
tr:hover td{{background:#1f1f23}}
.tag{{display:inline-block;padding:2px 8px;border-radius:4px;font-size:10px;font-weight:600}}
.tag-best{{background:#052e16;color:#4ade80}}
.best-box{{background:#052e16;border:1px solid #166534;border-radius:12px;padding:20px;margin-bottom:20px}}
.best-box h3{{color:#4ade80;font-size:16px;margin-bottom:12px}}
.best-box .params{{display:grid;grid-template-columns:repeat(auto-fit,minmax(140px,1fr));gap:12px}}
.best-box .param{{background:#0a2e16;border-radius:8px;padding:12px;text-align:center}}
.best-box .param-label{{font-size:11px;color:#6ee7b7}}
.best-box .param-value{{font-size:18px;font-weight:700;color:#4ade80;margin-top:2px}}
.two-col{{display:grid;grid-template-columns:1fr 1fr;gap:20px}}
@media(max-width:900px){{.two-col{{grid-template-columns:1fr}}}}
.insight{{background:#1e1b4b;border:1px solid #3730a3;border-radius:12px;padding:20px;margin-top:20px}}
.insight h3{{color:#a5b4fc;font-size:15px;margin-bottom:10px}}
.insight p{{color:#c7d2fe;font-size:14px;line-height:1.8}}
</style>
</head>
<body>
<div class="container">
<h1>国电南瑞(600406) · 5552种买卖点组合 · 蒙特卡洛最优</h1>
<p class="subtitle">回测: {info['start']} ~ {info['end']} ({info['n_days']}天) | 股价: {info['price_start']:.2f} → {info['price_end']:.2f} | 信号: 24买×23卖 + 参数网格 | MC: 1000路径×5年</p>

<!-- 最优策略 -->
<div class="best-box">
    <h3>最优买卖策略（年化+{best['annual_return']*100:.1f}%）</h3>
    <div class="params">
        <div class="param"><div class="param-label">买入信号</div><div class="param-value">{best['buy']}</div></div>
        <div class="param"><div class="param-label">卖出信号</div><div class="param-value">{best['sell']}</div></div>
        <div class="param"><div class="param-label">止损</div><div class="param-value">{best['sl']:.0%}</div></div>
        <div class="param"><div class="param-label">止盈</div><div class="param-value">{best['tp']:.0%}</div></div>
        <div class="param"><div class="param-label">时间止损</div><div class="param-value">{best['ts']}天</div></div>
        <div class="param"><div class="param-label">胜率</div><div class="param-value">{best['win_rate']*100:.0f}%</div></div>
        <div class="param"><div class="param-label">交易次数</div><div class="param-value">{best['n_trades']}笔</div></div>
        <div class="param"><div class="param-label">平均持有</div><div class="param-value">{best['avg_hold_days']:.0f}天</div></div>
        <div class="param"><div class="param-label">平均收益/笔</div><div class="param-value">{best['avg_return']*100:.1f}%</div></div>
        <div class="param"><div class="param-label">最大回撤</div><div class="param-value">{best['max_drawdown']*100:.1f}%</div></div>
    </div>
</div>

<!-- 指标卡片 -->
<div class="grid">
    <div class="card"><div class="card-label">最优年化</div><div class="card-value" style="color:#4ade80">+{best['annual_return']*100:.1f}%</div><div class="card-sub">RSI<30买 / RSI>70卖</div></div>
    <div class="card"><div class="card-label">MC中位年化</div><div class="card-value" style="color:#60a5fa">{mc_pct['p50']:.1f}%</div><div class="card-sub">P25~P75: {mc_pct['p25']:.1f}%~{mc_pct['p75']:.1f}%</div></div>
    <div class="card"><div class="card-label">MC P95年化</div><div class="card-value" style="color:#fbbf24">{mc_pct['p95']:.1f}%</div><div class="card-sub">极端乐观</div></div>
    <div class="card"><div class="card-label">5年亏损概率</div><div class="card-value" style="color:#4ade80">{np.mean(mc_final<0)*100:.0f}%</div><div class="card-sub">1000路径中</div></div>
    <div class="card"><div class="card-label">中位最大回撤</div><div class="card-value" style="color:#f87171">{dd_pct['p50']:.1f}%</div><div class="card-sub">P5极端: {dd_pct['p5']:.1f}%</div></div>
    <div class="card"><div class="card-label">有效组合</div><div class="card-value" style="color:#a78bfa">5552</div><div class="card-sub">24买×23卖×参数</div></div>
</div>

<!-- 最优策略交易明细 -->
<div class="section">
    <div class="section-title">最优策略 · 逐笔交易收益（{best['n_trades']}笔）</div>
    <div class="chart-container"><canvas id="tradeChart"></canvas></div>
</div>

<div class="two-col">
<div class="section">
    <div class="section-title">蒙特卡洛 · 年化收益分布（1000路径）</div>
    <div class="chart-container"><canvas id="histChart"></canvas></div>
</div>
<div class="section">
    <div class="section-title">Top200组合 · 年化 vs 胜率</div>
    <div class="chart-container"><canvas id="scatterChart"></canvas></div>
</div>
</div>

<!-- Top20表格 -->
<div class="section">
    <div class="section-title">Top 20 买卖策略排名</div>
    <table>
        <thead><tr><th>#</th><th>买入</th><th>卖出</th><th>止损</th><th>止盈</th><th>时限</th><th>年化</th><th>胜率</th><th>交易</th><th>持有</th><th>回撤</th></tr></thead>
        <tbody>{table_rows}</tbody>
    </table>
</div>

<!-- 买入信号分布 -->
<div class="section">
    <div class="section-title">Top50策略中 · 买入信号出现频率</div>
    <div class="chart-container"><canvas id="buyChart"></canvas></div>
</div>

<div class="insight">
    <h3>收益最大化结论</h3>
    <p>
        对国电南瑞5年数据遍历5552种买卖组合后，最优策略非常清晰：<br><br>
        <strong>买入：RSI(14) < 30</strong>（超卖区间入场）<br>
        <strong>卖出：RSI(14) > 70</strong>（超买区间离场）<br>
        <strong>风控：止损7% + 止盈10% + 30天时间止损</strong><br><br>
        该策略5年24笔交易，胜率88%，年化+28.9%，最大回撤仅-7.2%，平均每笔+5.03%、持有20天。<br><br>
        <strong>为什么有效：</strong>国电南瑞是典型的大盘蓝筹（电力设备龙头），股价围绕均值波动，RSI均值回归效应极强。
        在RSI<30时买入相当于"恐慌打折时入场"，RSI>70时卖出相当于"过热时兑现"。
        10%的止盈比20%/30%更优，因为蓝筹股单次波段幅度有限，快进快出复利更高。<br><br>
        <strong>蒙特卡洛验证：</strong>1000条随机路径中位年化+28%，P5=+9.7%，P95=+49.5%，5年亏损概率0%。
        即使随机组合买卖点，国电南瑞也能正收益——说明这只股票本身质地优良，任何合理策略都能赚钱。
    </p>
</div>
</div>

<script>
Chart.defaults.color='#a1a1aa';Chart.defaults.borderColor='#27272a';

// 交易明细
const tradeLabels={json.dumps(trade_labels)};
const tradeRets={json.dumps(trade_rets)};
const tradeCum={json.dumps(trade_cum_pct)};
new Chart(document.getElementById('tradeChart'),{{
    type:'bar',
    data:{{labels:tradeLabels,datasets:[
        {{type:'bar',label:'单笔收益(%)',data:tradeRets,backgroundColor:tradeRets.map(v=>v>0?'rgba(74,222,128,0.6)':'rgba(248,113,113,0.6)'),yAxisID:'y'}},
        {{type:'line',label:'累积(%)',data:tradeCum,borderColor:'#60a5fa',borderWidth:2,pointRadius:2,tension:0.3,yAxisID:'y1'}}
    ]}},
    options:{{responsive:true,maintainAspectRatio:false,plugins:{{legend:{{position:'bottom'}}}},
    scales:{{y:{{position:'left',title:{{display:true,text:'单笔(%)'}},grid:{{color:'#1f1f23'}}}},
    y1:{{position:'right',title:{{display:true,text:'累积(%)'}},grid:{{display:false}}}},
    x:{{ticks:{{font:{{size:10}}}},grid:{{display:false}}}}}}}}
}});

// MC直方图
const histData={json.dumps(hist_data)};
new Chart(document.getElementById('histChart'),{{
    type:'bar',
    data:{{labels:histData.labels,datasets:[{{data:histData.values,backgroundColor:'rgba(96,165,250,0.5)',borderWidth:0}}]}},
    options:{{responsive:true,maintainAspectRatio:false,plugins:{{legend:{{display:false}}}},
    scales:{{y:{{title:{{display:true,text:'频次'}},grid:{{color:'#1f1f23'}}}},x:{{ticks:{{maxTicksLimit:10,font:{{size:10}}}},grid:{{display:false}},title:{{display:true,text:'年化(%)'}}}}}}}}
}});

// 散点图
const scatterAnnual={json.dumps(scatter_annual)};
const scatterWin={json.dumps(scatter_winrate)};
new Chart(document.getElementById('scatterChart'),{{
    type:'scatter',
    data:{{datasets:[{{data:scatterAnnual.map((a,i)=>({{x:scatterWin[i],y:a}})),backgroundColor:scatterAnnual.map(a=>a>20?'#4ade80':a>10?'#fbbf24':'#f87171'),pointRadius:5}}]}},
    options:{{responsive:true,maintainAspectRatio:false,plugins:{{legend:{{display:false}}}},
    scales:{{x:{{title:{{display:true,text:'胜率(%)'}},grid:{{color:'#1f1f23'}}}},y:{{title:{{display:true,text:'年化(%)'}},grid:{{color:'#1f1f23'}}}}}}}}
}});

// 买入信号频率
new Chart(document.getElementById('buyChart'),{{
    type:'bar',
    data:{{labels:{json.dumps(buy_names,ensure_ascii=False)},datasets:[{{data:{json.dumps(buy_counts)},backgroundColor:'rgba(251,191,36,0.6)',borderWidth:0}}]}},
    options:{{responsive:true,maintainAspectRatio:false,indexAxis:'y',plugins:{{legend:{{display:false}}}},
    scales:{{x:{{title:{{display:true,text:'出现次数(Top50中)'}},grid:{{color:'#1f1f23'}}}},y:{{ticks:{{font:{{size:11}}}},grid:{{display:false}}}}}}}}
}});
</script>
</body>
</html>"""

with open(OUTPUT, 'w', encoding='utf-8') as f:
    f.write(html)
print(f"✅ {OUTPUT} ({len(html)/1024:.1f}KB)")
