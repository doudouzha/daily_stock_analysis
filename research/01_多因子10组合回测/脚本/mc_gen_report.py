"""
生成交互式HTML可视化报告
"""
import pickle
import numpy as np
import json

CACHE_DIR = '/tmp/mc_cache'
OUTPUT = '/Users/huangren/.qoderwork/workspace/ms9393tmwes9zvfq/outputs/多因子策略_10组合回测_蒙特卡洛.html'

with open(f'{CACHE_DIR}/mc_results_full.pkl', 'rb') as f:
    data = pickle.load(f)

results = data['results']
mc_annual = np.array(data['mc_annual_returns'])
mc_max_dd = np.array(data['mc_max_dd'])
mc_final = np.array(data['mc_final_returns'])
mc_curves = data['mc_curves']
params = data['params']

# 准备数据
portfolio_names = []
portfolio_data = []
for name, bt in results.items():
    if bt:
        portfolio_names.append(name)
        portfolio_data.append(bt)

# 蒙特卡洛分位数
mc_pct = {
    'p5': float(np.percentile(mc_annual, 5) * 100),
    'p25': float(np.percentile(mc_annual, 25) * 100),
    'p50': float(np.percentile(mc_annual, 50) * 100),
    'p75': float(np.percentile(mc_annual, 75) * 100),
    'p95': float(np.percentile(mc_annual, 95) * 100),
}
dd_pct = {
    'p5': float(np.percentile(mc_max_dd, 5) * 100),
    'p50': float(np.percentile(mc_max_dd, 50) * 100),
    'p95': float(np.percentile(mc_max_dd, 95) * 100),
}
loss_prob = float(np.mean(mc_final < 0) * 100)
gt20_prob = float(np.mean(mc_annual > 0.20) * 100)
gt50_prob = float(np.mean(mc_annual > 0.50) * 100)

# 累积曲线数据（降采样）
curves_json = {}
for i, (name, bt) in enumerate(zip(portfolio_names, portfolio_data)):
    curve = bt['cum_curve']
    dates = bt['dates']
    # 降采样到最多50点
    step = max(1, len(curve) // 50)
    curves_json[name] = {
        'dates': dates[::step],
        'values': [round((v - 1) * 100, 2) for v in curve[::step]]
    }

# MC曲线（取10条代表线）
mc_sample_curves = []
for curve in mc_curves[:10]:
    step = max(1, len(curve) // 50)
    mc_sample_curves.append([round((v - 1) * 100, 2) for v in curve[::step]])

# 蒙特卡洛直方图数据
hist_annual, bin_edges = np.histogram(mc_annual * 100, bins=50)
hist_data = {
    'labels': [f"{bin_edges[i]:.0f}~{bin_edges[i+1]:.0f}" for i in range(len(hist_annual))],
    'values': hist_annual.tolist()
}

# 表格数据
table_rows = ""
for name, bt in zip(portfolio_names, portfolio_data):
    color = '#22c55e' if bt['annual_return'] > 0 else '#ef4444'
    table_rows += f"""<tr>
        <td style="font-weight:600">{name}</td>
        <td style="color:{color};font-weight:700">{bt['annual_return']*100:+.1f}%</td>
        <td>{bt['total_return']*100:+.1f}%</td>
        <td>{bt['win_rate']*100:.0f}%</td>
        <td style="color:#ef4444">{bt['max_drawdown']*100:.1f}%</td>
        <td>{bt['sharpe']:.2f}</td>
        <td>{bt['n_periods']}</td>
    </tr>"""

# 散点图数据
scatter_data = []
for name, bt in zip(portfolio_names, portfolio_data):
    scatter_data.append({
        'x': round(abs(bt['max_drawdown']) * 100, 1),
        'y': round(bt['annual_return'] * 100, 1),
        'label': name
    })

# 权重配置
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
<title>多因子Alpha策略 · 10组合回测 · 蒙特卡洛模拟</title>
<script src="https://cdnjs.cloudflare.com/ajax/libs/Chart.js/4.4.1/chart.umd.min.js"></script>
<style>
* {{ margin:0; padding:0; box-sizing:border-box; }}
body {{ font-family: -apple-system, 'SF Pro Display', 'Helvetica Neue', sans-serif; background:#0a0a0f; color:#e4e4e7; line-height:1.6; }}
.container {{ max-width:1400px; margin:0 auto; padding:24px; }}
h1 {{ font-size:28px; font-weight:700; margin-bottom:8px; background:linear-gradient(135deg,#60a5fa,#a78bfa); -webkit-background-clip:text; -webkit-text-fill-color:transparent; }}
.subtitle {{ color:#71717a; font-size:14px; margin-bottom:32px; }}
.grid {{ display:grid; grid-template-columns:repeat(auto-fit, minmax(200px, 1fr)); gap:16px; margin-bottom:32px; }}
.card {{ background:#18181b; border:1px solid #27272a; border-radius:12px; padding:20px; }}
.card-label {{ font-size:12px; color:#71717a; text-transform:uppercase; letter-spacing:0.5px; }}
.card-value {{ font-size:28px; font-weight:700; margin-top:4px; }}
.card-sub {{ font-size:12px; color:#a1a1aa; margin-top:4px; }}
.section {{ background:#18181b; border:1px solid #27272a; border-radius:16px; padding:24px; margin-bottom:24px; }}
.section-title {{ font-size:18px; font-weight:600; margin-bottom:16px; color:#fafafa; }}
.chart-container {{ position:relative; height:380px; }}
table {{ width:100%; border-collapse:collapse; font-size:13px; }}
th {{ text-align:left; padding:10px 12px; border-bottom:2px solid #3f3f46; color:#a1a1aa; font-weight:500; }}
td {{ padding:10px 12px; border-bottom:1px solid #27272a; }}
tr:hover td {{ background:#1f1f23; }}
.tag {{ display:inline-block; padding:2px 8px; border-radius:4px; font-size:11px; font-weight:600; }}
.tag-best {{ background:#052e16; color:#4ade80; }}
.tag-worst {{ background:#450a0a; color:#f87171; }}
.insight {{ background:#1e1b4b; border:1px solid #3730a3; border-radius:12px; padding:20px; margin-top:24px; }}
.insight h3 {{ color:#a5b4fc; font-size:15px; margin-bottom:12px; }}
.insight p {{ color:#c7d2fe; font-size:14px; line-height:1.8; }}
.two-col {{ display:grid; grid-template-columns:1fr 1fr; gap:24px; }}
@media (max-width:900px) {{ .two-col {{ grid-template-columns:1fr; }} }}
</style>
</head>
<body>
<div class="container">
<h1>多因子Alpha策略 · 10组合回测 · 蒙特卡洛模拟</h1>
<p class="subtitle">股票池: A股主板 {params['n_stocks_pool']} 只（排除创业板/科创板） | 回测: {params['start'][:4]}-{params['start'][4:6]} ~ {params['end'][:4]}-{params['end'][4:6]} | 调仓: 每{params['rebalance']}日 Top{params['top_n']} | 模拟: {params['n_sim']}次×{params['sim_years']}年</p>

<!-- 核心指标卡片 -->
<div class="grid">
    <div class="card">
        <div class="card-label">策略中位年化</div>
        <div class="card-value" style="color:#60a5fa">{mc_pct['p50']:.1f}%</div>
        <div class="card-sub">P25~P75: {mc_pct['p25']:.1f}% ~ {mc_pct['p75']:.1f}%</div>
    </div>
    <div class="card">
        <div class="card-label">3年亏损概率</div>
        <div class="card-value" style="color:#f87171">{loss_prob:.0f}%</div>
        <div class="card-sub">10000次模拟中</div>
    </div>
    <div class="card">
        <div class="card-label">中位最大回撤</div>
        <div class="card-value" style="color:#fbbf24">{dd_pct['p50']:.1f}%</div>
        <div class="card-sub">P5极端: {dd_pct['p5']:.1f}%</div>
    </div>
    <div class="card">
        <div class="card-label">年化>20%概率</div>
        <div class="card-value" style="color:#4ade80">{gt20_prob:.0f}%</div>
        <div class="card-sub">年化>50%: {gt50_prob:.1f}%</div>
    </div>
    <div class="card">
        <div class="card-label">最优组合</div>
        <div class="card-value" style="color:#4ade80;font-size:20px">P09防御型</div>
        <div class="card-sub">年化+31.1% | 夏普1.17</div>
    </div>
</div>

<!-- 10组合对比表 -->
<div class="section">
    <div class="section-title">10种因子权重组合 · 回测对比</div>
    <table>
        <thead><tr><th>组合</th><th>年化收益</th><th>累计收益</th><th>胜率</th><th>最大回撤</th><th>夏普</th><th>调仓次数</th></tr></thead>
        <tbody>{table_rows}</tbody>
    </table>
</div>

<!-- 累积收益曲线 -->
<div class="section">
    <div class="section-title">10组合累积收益曲线</div>
    <div class="chart-container"><canvas id="cumChart"></canvas></div>
</div>

<div class="two-col">
<!-- 蒙特卡洛分布 -->
<div class="section">
    <div class="section-title">蒙特卡洛 · 年化收益分布 (10000次)</div>
    <div class="chart-container"><canvas id="histChart"></canvas></div>
</div>

<!-- 风险收益散点 -->
<div class="section">
    <div class="section-title">风险-收益散点图</div>
    <div class="chart-container"><canvas id="scatterChart"></canvas></div>
</div>
</div>

<!-- 蒙特卡洛路径 -->
<div class="section">
    <div class="section-title">蒙特卡洛 · 模拟路径（10条样本 × 3年）</div>
    <div class="chart-container"><canvas id="mcPathChart"></canvas></div>
</div>

<!-- 因子权重堆叠图 -->
<div class="section">
    <div class="section-title">10组合因子权重配置</div>
    <div class="chart-container"><canvas id="weightChart"></canvas></div>
</div>

<!-- 策略洞察 -->
<div class="insight">
    <h3>策略收益区间结论（蒙特卡洛）</h3>
    <p>
        基于A股主板 {params['n_stocks_pool']} 只股票、3年回测数据（{params['start'][:4]}.{params['start'][4:6]}~{params['end'][:4]}.{params['end'][4:6]}），
        通过10种不同因子权重配置的回测结果构建收益分布，再进行10000次蒙特卡洛抽样模拟：<br><br>
        <strong>收益区间：</strong>年化 P5={mc_pct['p5']:.1f}% / P25={mc_pct['p25']:.1f}% / P50={mc_pct['p50']:.1f}% / P75={mc_pct['p75']:.1f}% / P95={mc_pct['p95']:.1f}%<br>
        <strong>回撤区间：</strong>最大回撤 P5={dd_pct['p5']:.1f}% / P50={dd_pct['p50']:.1f}% / P95={dd_pct['p95']:.1f}%<br>
        <strong>亏损概率：</strong>3年持有亏损概率 {loss_prob:.0f}%，年化>20%概率 {gt20_prob:.0f}%<br><br>
        <strong>核心发现：</strong>防御型配置（基本面权重45%）在主板股票上表现最优（年化+31%，夏普1.17），
        而进攻型配置（趋势权重45%）表现最差（年化-28%）。这说明在排除创业板/科创板的主板池中，
        低波动+量稳定性因子比纯动量因子更有效。策略的合理预期为年化6~18%（P50~P75区间），
        极端乐观情况下可达38%（P95），但需承受-35%的中位最大回撤。
    </p>
</div>

</div>

<script>
Chart.defaults.color = '#a1a1aa';
Chart.defaults.borderColor = '#27272a';

// 累积收益曲线
const cumData = {json.dumps(curves_json, ensure_ascii=False)};
const colors = ['#60a5fa','#f87171','#4ade80','#fbbf24','#a78bfa','#fb923c','#2dd4bf','#f472b6','#818cf8','#34d399'];
const cumDatasets = Object.entries(cumData).map(([name, d], i) => ({{
    label: name,
    data: d.values,
    borderColor: colors[i % 10],
    borderWidth: 2,
    pointRadius: 0,
    tension: 0.3,
    fill: false
}}));
const maxLen = Math.max(...Object.values(cumData).map(d => d.dates.length));
const refDates = Object.values(cumData)[0].dates;

new Chart(document.getElementById('cumChart'), {{
    type: 'line',
    data: {{ labels: refDates, datasets: cumDatasets }},
    options: {{
        responsive: true, maintainAspectRatio: false,
        plugins: {{ legend: {{ position:'bottom', labels:{{boxWidth:12, font:{{size:11}}}} }} }},
        scales: {{
            y: {{ title:{{display:true, text:'累积收益(%)'}}, grid:{{color:'#1f1f23'}} }},
            x: {{ ticks:{{maxTicksLimit:12}}, grid:{{display:false}} }}
        }}
    }}
}});

// 蒙特卡洛直方图
const histData = {json.dumps(hist_data)};
new Chart(document.getElementById('histChart'), {{
    type: 'bar',
    data: {{
        labels: histData.labels,
        datasets: [{{ data: histData.values, backgroundColor: histData.labels.map(l => {{
            const v = parseFloat(l.split('~')[0]);
            return v < 0 ? 'rgba(248,113,113,0.6)' : 'rgba(96,165,250,0.6)';
        }}), borderWidth: 0 }}]
    }},
    options: {{
        responsive: true, maintainAspectRatio: false,
        plugins: {{ legend:{{display:false}} }},
        scales: {{
            y: {{ title:{{display:true, text:'频次'}}, grid:{{color:'#1f1f23'}} }},
            x: {{ ticks:{{maxTicksLimit:10, font:{{size:10}}}}, grid:{{display:false}}, title:{{display:true, text:'年化收益(%)'}} }}
        }}
    }}
}});

// 散点图
const scatterData = {json.dumps(scatter_data, ensure_ascii=False)};
new Chart(document.getElementById('scatterChart'), {{
    type: 'scatter',
    data: {{
        datasets: [{{
            data: scatterData.map(d => ({{x: d.x, y: d.y}})),
            backgroundColor: scatterData.map(d => d.y > 0 ? '#4ade80' : '#f87171'),
            pointRadius: 8
        }}]
    }},
    options: {{
        responsive: true, maintainAspectRatio: false,
        plugins: {{
            legend:{{display:false}},
            tooltip: {{ callbacks: {{ label: (ctx) => scatterData[ctx.dataIndex].label + ': 年化' + scatterData[ctx.dataIndex].y + '% 回撤-' + scatterData[ctx.dataIndex].x + '%' }} }}
        }},
        scales: {{
            x: {{ title:{{display:true, text:'最大回撤(%)'}}, grid:{{color:'#1f1f23'}} }},
            y: {{ title:{{display:true, text:'年化收益(%)'}}, grid:{{color:'#1f1f23'}} }}
        }}
    }}
}});

// MC路径
const mcCurves = {json.dumps(mc_sample_curves)};
const mcLabels = Array.from({{length: mcCurves[0].length}}, (_, i) => `T${{i}}`);
new Chart(document.getElementById('mcPathChart'), {{
    type: 'line',
    data: {{
        labels: mcLabels,
        datasets: mcCurves.map((c, i) => ({{
            data: c,
            borderColor: `hsla(${{i*36}}, 70%, 60%, 0.5)`,
            borderWidth: 1.5,
            pointRadius: 0,
            tension: 0.3,
            fill: false
        }}))
    }},
    options: {{
        responsive: true, maintainAspectRatio: false,
        plugins: {{ legend:{{display:false}} }},
        scales: {{
            y: {{ title:{{display:true, text:'累积收益(%)'}}, grid:{{color:'#1f1f23'}} }},
            x: {{ ticks:{{maxTicksLimit:10}}, grid:{{display:false}}, title:{{display:true, text:'调仓期数(×5日)'}} }}
        }}
    }}
}});

// 权重堆叠图
new Chart(document.getElementById('weightChart'), {{
    type: 'bar',
    data: {{
        labels: {json.dumps(config_labels, ensure_ascii=False)},
        datasets: [
            {{ label:'趋势', data:{json.dumps(config_trend)}, backgroundColor:'#60a5fa' }},
            {{ label:'量价', data:{json.dumps(config_volume)}, backgroundColor:'#4ade80' }},
            {{ label:'基本面', data:{json.dumps(config_fund)}, backgroundColor:'#fbbf24' }},
            {{ label:'情绪', data:{json.dumps(config_sent)}, backgroundColor:'#a78bfa' }}
        ]
    }},
    options: {{
        responsive: true, maintainAspectRatio: false,
        plugins: {{ legend:{{position:'bottom'}} }},
        scales: {{
            x: {{ stacked:true, ticks:{{font:{{size:11}}}}, grid:{{display:false}} }},
            y: {{ stacked:true, max:100, title:{{display:true, text:'权重(%)'}}, grid:{{color:'#1f1f23'}} }}
        }}
    }}
}});
</script>
</body>
</html>"""

with open(OUTPUT, 'w', encoding='utf-8') as f:
    f.write(html)

print(f"✅ 报告已生成: {OUTPUT}")
print(f"   文件大小: {len(html)/1024:.1f} KB")
