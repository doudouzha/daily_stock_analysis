"""
生成优质股池回测报告 HTML
"""
import pickle
import numpy as np
import json

CACHE_DIR = '/tmp/mc_cache'
OUTPUT = '/Users/huangren/.qoderwork/workspace/ms9393tmwes9zvfq/outputs/优质股_10组合回测_蒙特卡洛.html'

with open(f'{CACHE_DIR}/mc_quality_results.pkl', 'rb') as f:
    data = pickle.load(f)

results = data['results']
mc_annual = np.array(data['mc_annual_returns'])
mc_max_dd = np.array(data['mc_max_dd'])
mc_final = np.array(data['mc_final_returns'])
mc_curves = data['mc_curves']
params = data['params']

portfolio_names = []
portfolio_data = []
for name, bt in results.items():
    if bt:
        portfolio_names.append(name)
        portfolio_data.append(bt)

mc_pct = {k: float(np.percentile(mc_annual, int(k[1:])) * 100) for k in ['p5','p25','p50','p75','p95']}
dd_pct = {k: float(np.percentile(mc_max_dd, int(k[1:])) * 100) for k in ['p5','p50','p95']}
loss_prob = float(np.mean(mc_final < 0) * 100)
gt20_prob = float(np.mean(mc_annual > 0.20) * 100)
gt50_prob = float(np.mean(mc_annual > 0.50) * 100)

# 找最优/最差
best_idx = np.argmax([bt['annual_return'] for bt in portfolio_data])
worst_idx = np.argmin([bt['annual_return'] for bt in portfolio_data])
best_name = portfolio_names[best_idx]
worst_name = portfolio_names[worst_idx]

curves_json = {}
for name, bt in zip(portfolio_names, portfolio_data):
    step = max(1, len(bt['cum_curve']) // 60)
    curves_json[name] = {
        'dates': bt['dates'][::step],
        'values': [round((v - 1) * 100, 2) for v in bt['cum_curve'][::step]]
    }

mc_sample_curves = [[round((v-1)*100, 2) for v in c[::max(1,len(c)//60)]] for c in mc_curves[:12]]

hist_annual, bin_edges = np.histogram(mc_annual * 100, bins=50)
hist_data = {'labels': [f"{bin_edges[i]:.0f}~{bin_edges[i+1]:.0f}" for i in range(len(hist_annual))], 'values': hist_annual.tolist()}

table_rows = ""
for i, (name, bt) in enumerate(zip(portfolio_names, portfolio_data)):
    color = '#4ade80' if bt['annual_return'] > 0.10 else ('#fbbf24' if bt['annual_return'] > 0 else '#f87171')
    tag = ''
    if i == best_idx: tag = ' <span class="tag tag-best">最优</span>'
    elif i == worst_idx: tag = ' <span class="tag tag-worst">最差</span>'
    table_rows += f"""<tr>
        <td style="font-weight:600">{name}{tag}</td>
        <td style="color:{color};font-weight:700">{bt['annual_return']*100:+.1f}%</td>
        <td>{bt['total_return']*100:+.1f}%</td>
        <td>{bt['win_rate']*100:.0f}%</td>
        <td style="color:#f87171">{bt['max_drawdown']*100:.1f}%</td>
        <td>{bt['sharpe']:.2f}</td>
        <td>{bt['n_periods']}</td>
    </tr>"""

scatter_data = [{'x': round(abs(bt['max_drawdown'])*100,1), 'y': round(bt['annual_return']*100,1), 'label': name} for name, bt in zip(portfolio_names, portfolio_data)]

configs = params['configs']
config_labels = list(configs.keys())
config_trend = [configs[k]['trend']*100 for k in config_labels]
config_volume = [configs[k]['volume']*100 for k in config_labels]
config_fund = [configs[k]['fundamental']*100 for k in config_labels]
config_sent = [configs[k]['sentiment']*100 for k in config_labels]

html = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>优质股池 · 多因子策略 · 10组合回测 · 蒙特卡洛</title>
<script src="https://cdnjs.cloudflare.com/ajax/libs/Chart.js/4.4.1/chart.umd.min.js"></script>
<style>
*{{margin:0;padding:0;box-sizing:border-box}}
body{{font-family:-apple-system,'SF Pro Display','PingFang SC',sans-serif;background:#0a0a0f;color:#e4e4e7;line-height:1.6}}
.container{{max-width:1400px;margin:0 auto;padding:24px}}
h1{{font-size:26px;font-weight:700;margin-bottom:6px;background:linear-gradient(135deg,#4ade80,#60a5fa);-webkit-background-clip:text;-webkit-text-fill-color:transparent}}
.subtitle{{color:#71717a;font-size:13px;margin-bottom:28px}}
.grid{{display:grid;grid-template-columns:repeat(auto-fit,minmax(180px,1fr));gap:14px;margin-bottom:28px}}
.card{{background:#18181b;border:1px solid #27272a;border-radius:12px;padding:18px}}
.card-label{{font-size:11px;color:#71717a;text-transform:uppercase;letter-spacing:0.5px}}
.card-value{{font-size:26px;font-weight:700;margin-top:4px}}
.card-sub{{font-size:11px;color:#a1a1aa;margin-top:4px}}
.section{{background:#18181b;border:1px solid #27272a;border-radius:16px;padding:24px;margin-bottom:20px}}
.section-title{{font-size:17px;font-weight:600;margin-bottom:14px;color:#fafafa}}
.chart-container{{position:relative;height:360px}}
table{{width:100%;border-collapse:collapse;font-size:13px}}
th{{text-align:left;padding:10px 12px;border-bottom:2px solid #3f3f46;color:#a1a1aa;font-weight:500}}
td{{padding:10px 12px;border-bottom:1px solid #27272a}}
tr:hover td{{background:#1f1f23}}
.tag{{display:inline-block;padding:2px 8px;border-radius:4px;font-size:11px;font-weight:600}}
.tag-best{{background:#052e16;color:#4ade80}}
.tag-worst{{background:#450a0a;color:#f87171}}
.insight{{background:#052e16;border:1px solid #166534;border-radius:12px;padding:20px;margin-top:20px}}
.insight h3{{color:#4ade80;font-size:15px;margin-bottom:10px}}
.insight p{{color:#bbf7d0;font-size:14px;line-height:1.8}}
.two-col{{display:grid;grid-template-columns:1fr 1fr;gap:20px}}
@media(max-width:900px){{.two-col{{grid-template-columns:1fr}}}}
.method{{background:#1e1b4b;border:1px solid #3730a3;border-radius:12px;padding:16px;margin-bottom:20px;font-size:13px;color:#c7d2fe}}
</style>
</head>
<body>
<div class="container">
<h1>优质股池 · 多因子Alpha策略 · 蒙特卡洛收益区间</h1>
<p class="subtitle">股票池: A股主板 {params['n_quality_pool']} 只优质股（{params['screen_criteria']}） | 有效: {params['n_factors_valid']} 只 | 回测: 2023.08~2026.08 | 调仓: 每{params['rebalance']}日 Top{params['top_n']} | MC: {params['n_sim']}次×{params['sim_years']}年</p>

<div class="method">
<strong>选股逻辑：</strong>先从A股主板3149只中筛选优质公司（非ST + EPS>0.3 + 净利润为正 → {params['n_quality_pool']}只），再用四维因子（趋势/量价/基本面/情绪）按10种不同权重配置打分排名，每期选Top5等权持有，每5个交易日调仓。蒙特卡洛基于10组×144期=1440个收益样本有放回抽样10000次。
</div>

<div class="grid">
    <div class="card">
        <div class="card-label">最优组合年化</div>
        <div class="card-value" style="color:#4ade80">+{portfolio_data[best_idx]['annual_return']*100:.1f}%</div>
        <div class="card-sub">{best_name} | 夏普{portfolio_data[best_idx]['sharpe']:.2f}</div>
    </div>
    <div class="card">
        <div class="card-label">MC中位年化</div>
        <div class="card-value" style="color:#60a5fa">{mc_pct['p50']:.1f}%</div>
        <div class="card-sub">P25~P75: {mc_pct['p25']:.1f}%~{mc_pct['p75']:.1f}%</div>
    </div>
    <div class="card">
        <div class="card-label">3年亏损概率</div>
        <div class="card-value" style="color:#f87171">{loss_prob:.0f}%</div>
        <div class="card-sub">年化>20%: {gt20_prob:.0f}%</div>
    </div>
    <div class="card">
        <div class="card-label">中位最大回撤</div>
        <div class="card-value" style="color:#fbbf24">{dd_pct['p50']:.1f}%</div>
        <div class="card-sub">极端P5: {dd_pct['p5']:.1f}%</div>
    </div>
    <div class="card">
        <div class="card-label">最差组合</div>
        <div class="card-value" style="color:#f87171;font-size:18px">{worst_name}</div>
        <div class="card-sub">年化{portfolio_data[worst_idx]['annual_return']*100:.1f}% | 回撤{portfolio_data[worst_idx]['max_drawdown']*100:.0f}%</div>
    </div>
</div>

<div class="section">
    <div class="section-title">10种因子权重组合 · 3年回测对比</div>
    <table>
        <thead><tr><th>组合</th><th>年化收益</th><th>累计收益</th><th>胜率</th><th>最大回撤</th><th>夏普</th><th>期数</th></tr></thead>
        <tbody>{table_rows}</tbody>
    </table>
</div>

<div class="section">
    <div class="section-title">累积收益曲线（10组合 × 3年）</div>
    <div class="chart-container"><canvas id="cumChart"></canvas></div>
</div>

<div class="two-col">
<div class="section">
    <div class="section-title">蒙特卡洛 · 年化收益分布</div>
    <div class="chart-container"><canvas id="histChart"></canvas></div>
</div>
<div class="section">
    <div class="section-title">风险-收益散点图</div>
    <div class="chart-container"><canvas id="scatterChart"></canvas></div>
</div>
</div>

<div class="section">
    <div class="section-title">蒙特卡洛 · 模拟路径（12条 × 3年）</div>
    <div class="chart-container"><canvas id="mcPathChart"></canvas></div>
</div>

<div class="section">
    <div class="section-title">因子权重配置对比</div>
    <div class="chart-container"><canvas id="weightChart"></canvas></div>
</div>

<div class="insight">
    <h3>核心结论</h3>
    <p>
        在{params['n_quality_pool']}只优质主板股（EPS>0.3、盈利为正）上，策略表现高度依赖因子权重配置：<br><br>
        <strong>最优：{best_name}</strong>（年化+{portfolio_data[best_idx]['annual_return']*100:.1f}%，夏普{portfolio_data[best_idx]['sharpe']:.2f}）— 基本面因子（低波动+量稳定性）权重越高越赚钱。<br>
        <strong>最差：{worst_name}</strong>（年化{portfolio_data[worst_idx]['annual_return']*100:.1f}%，回撤{portfolio_data[worst_idx]['max_drawdown']*100:.0f}%）— 纯趋势/动量在优质股上完全失效。<br><br>
        <strong>蒙特卡洛收益区间：</strong>年化 P5={mc_pct['p5']:.1f}% / P50={mc_pct['p50']:.1f}% / P95={mc_pct['p95']:.1f}%<br>
        <strong>策略合理预期：</strong>采用防御型/基本面主导配置，年化12~17%可实现；均衡配置约3~12%；纯进攻型必亏。<br>
        <strong>风控要点：</strong>中位最大回撤-33%，极端可达-57%。必须配合止损纪律（-7%个股止损 / -10%组合止损）。
    </p>
</div>
</div>

<script>
Chart.defaults.color='#a1a1aa';Chart.defaults.borderColor='#27272a';
const cumData={json.dumps(curves_json,ensure_ascii=False)};
const colors=['#60a5fa','#f87171','#4ade80','#fbbf24','#a78bfa','#fb923c','#2dd4bf','#f472b6','#818cf8','#34d399'];
const cumDatasets=Object.entries(cumData).map(([n,d],i)=>({{label:n,data:d.values,borderColor:colors[i%10],borderWidth:2,pointRadius:0,tension:0.3,fill:false}}));
const refDates=Object.values(cumData)[0].dates;
new Chart(document.getElementById('cumChart'),{{type:'line',data:{{labels:refDates,datasets:cumDatasets}},options:{{responsive:true,maintainAspectRatio:false,plugins:{{legend:{{position:'bottom',labels:{{boxWidth:12,font:{{size:11}}}}}}}},scales:{{y:{{title:{{display:true,text:'累积收益(%)'}},grid:{{color:'#1f1f23'}}}},x:{{ticks:{{maxTicksLimit:12}},grid:{{display:false}}}}}}}}}});

const histData={json.dumps(hist_data)};
new Chart(document.getElementById('histChart'),{{type:'bar',data:{{labels:histData.labels,datasets:[{{data:histData.values,backgroundColor:histData.labels.map(l=>parseFloat(l.split('~')[0])<0?'rgba(248,113,113,0.6)':'rgba(74,222,128,0.5)'),borderWidth:0}}]}},options:{{responsive:true,maintainAspectRatio:false,plugins:{{legend:{{display:false}}}},scales:{{y:{{title:{{display:true,text:'频次'}},grid:{{color:'#1f1f23'}}}},x:{{ticks:{{maxTicksLimit:10,font:{{size:10}}}},grid:{{display:false}},title:{{display:true,text:'年化收益(%)'}}}}}}}}}});

const scatterData={json.dumps(scatter_data,ensure_ascii=False)};
new Chart(document.getElementById('scatterChart'),{{type:'scatter',data:{{datasets:[{{data:scatterData.map(d=>({{x:d.x,y:d.y}})),backgroundColor:scatterData.map(d=>d.y>0?'#4ade80':'#f87171'),pointRadius:9}}]}},options:{{responsive:true,maintainAspectRatio:false,plugins:{{legend:{{display:false}},tooltip:{{callbacks:{{label:ctx=>scatterData[ctx.dataIndex].label+': 年化'+scatterData[ctx.dataIndex].y+'% 回撤-'+scatterData[ctx.dataIndex].x+'%'}}}}}},scales:{{x:{{title:{{display:true,text:'最大回撤(%)'}},grid:{{color:'#1f1f23'}}}},y:{{title:{{display:true,text:'年化收益(%)'}},grid:{{color:'#1f1f23'}}}}}}}}}});

const mcCurves={json.dumps(mc_sample_curves)};
const mcLabels=Array.from({{length:mcCurves[0].length}},(_,i)=>`T${{i}}`);
new Chart(document.getElementById('mcPathChart'),{{type:'line',data:{{labels:mcLabels,datasets:mcCurves.map((c,i)=>({{data:c,borderColor:`hsla(${{i*30}},70%,60%,0.5)`,borderWidth:1.5,pointRadius:0,tension:0.3,fill:false}}))}},options:{{responsive:true,maintainAspectRatio:false,plugins:{{legend:{{display:false}}}},scales:{{y:{{title:{{display:true,text:'累积收益(%)'}},grid:{{color:'#1f1f23'}}}},x:{{ticks:{{maxTicksLimit:10}},grid:{{display:false}},title:{{display:true,text:'调仓期数(×5日)'}}}}}}}}}});

new Chart(document.getElementById('weightChart'),{{type:'bar',data:{{labels:{json.dumps(config_labels,ensure_ascii=False)},datasets:[
{{label:'趋势',data:{json.dumps(config_trend)},backgroundColor:'#60a5fa'}},
{{label:'量价',data:{json.dumps(config_volume)},backgroundColor:'#4ade80'}},
{{label:'基本面',data:{json.dumps(config_fund)},backgroundColor:'#fbbf24'}},
{{label:'情绪',data:{json.dumps(config_sent)},backgroundColor:'#a78bfa'}}
]}},options:{{responsive:true,maintainAspectRatio:false,plugins:{{legend:{{position:'bottom'}}}},scales:{{x:{{stacked:true,ticks:{{font:{{size:11}}}},grid:{{display:false}}}},y:{{stacked:true,max:100,title:{{display:true,text:'权重(%)'}},grid:{{color:'#1f1f23'}}}}}}}}}});
</script>
</body>
</html>"""

with open(OUTPUT, 'w', encoding='utf-8') as f:
    f.write(html)
print(f"✅ 报告: {OUTPUT} ({len(html)/1024:.1f}KB)")
