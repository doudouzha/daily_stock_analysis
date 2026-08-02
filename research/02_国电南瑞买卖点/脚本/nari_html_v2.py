import pickle, pandas as pd, numpy as np

with open('/tmp/mc_cache/nari_results_v2.pkl', 'rb') as f:
    data = pickle.load(f)
with open('/tmp/mc_cache/nari_mc_v2.pkl', 'rb') as f:
    mc_df = pickle.load(f)

phase1 = data['phase1']
phase2 = data['phase2']
df = data['df']
best = phase2[0]
c = df['close'].astype(float)

# 准备图表数据
# 1. 股价 + RSI走势(近1年)
recent = df[df.index >= '2025-08-01']
dates_str = [d.strftime('%Y-%m-%d') for d in recent.index]
close_list = [round(float(x), 2) for x in recent['close']]
rsi_list = [round(float(x), 1) if not np.isnan(x) else None for x in recent['rsi_14']]

# 2. 最优策略买卖点标注
buy_points = []
sell_points = []
for t in best['trade_list']:
    ed = t['entry_date'].strftime('%Y-%m-%d')
    xd = t['exit_date'].strftime('%Y-%m-%d')
    if ed in dates_str:
        buy_points.append({'x': ed, 'y': round(t['entry_price'], 2)})
    if xd in dates_str:
        sell_points.append({'x': xd, 'y': round(t['exit_price'], 2)})

# 3. MC年化收益分布
mc_annual = (mc_df['annual_return'] * 100).values
mc_hist, mc_edges = np.histogram(mc_annual, bins=50)
mc_hist = mc_hist.tolist()
mc_centers = [round((mc_edges[i]+mc_edges[i+1])/2, 1) for i in range(len(mc_hist))]

# 4. MC路径(取100条)
np.random.seed(123)
sample_idx = np.random.choice(len(mc_df), 100, replace=False)
# 重新模拟路径曲线
trade_returns = [t['return'] for t in best['trade_list']]
avg_hold = best['avg_hold']
trades_per_year = 250 / avg_hold
n_trades_total = int(trades_per_year * 5)

mc_paths_data = []
np.random.seed(99)
for p in range(100):
    sampled = np.random.choice(trade_returns, size=n_trades_total, replace=True)
    cum = np.cumprod(1 + sampled)
    # 降采样到50个点
    step = max(1, len(cum) // 50)
    path = cum[::step].tolist()
    if len(path) > 50:
        path = path[:50]
    mc_paths_data.append([round(x, 3) for x in path])

# 5. Phase1 Top15 年化收益柱状图
p1_names = [f"{r['buy_signal']}→{r['sell_signal']}" for r in phase1[:15]]
p1_annual = [round(r['annual_return']*100, 1) for r in phase1[:15]]

# 6. 逐笔收益散点
trade_dates = [t['entry_date'].strftime('%Y-%m-%d') for t in best['trade_list']]
trade_rets = [round(t['return']*100, 2) for t in best['trade_list']]

# 7. 回撤曲线
cum_val = 1
peak_val = 1
dd_list = []
for t in best['trade_list']:
    cum_val *= (1 + t['return'])
    peak_val = max(peak_val, cum_val)
    dd_list.append(round((cum_val - peak_val) / peak_val * 100, 2))

html = f'''<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>国电南瑞(600406) Wilder RSI 买卖点回测报告 v2</title>
<script src="https://cdnjs.cloudflare.com/ajax/libs/echarts/5.5.0/echarts.min.js"></script>
<style>
* {{ margin:0; padding:0; box-sizing:border-box; }}
body {{ font-family: -apple-system, "PingFang SC", "Microsoft YaHei", sans-serif; background:#0f1117; color:#e0e0e0; }}
.container {{ max-width:1200px; margin:0 auto; padding:20px; }}
h1 {{ text-align:center; font-size:24px; padding:30px 0 10px; color:#fff; }}
.subtitle {{ text-align:center; color:#888; font-size:14px; margin-bottom:30px; }}
.card {{ background:#1a1d29; border-radius:12px; padding:20px; margin-bottom:20px; border:1px solid #2a2d3a; }}
.card h2 {{ font-size:16px; color:#7eb8ff; margin-bottom:15px; padding-bottom:8px; border-bottom:1px solid #2a2d3a; }}
.grid {{ display:grid; grid-template-columns:repeat(auto-fit, minmax(180px, 1fr)); gap:12px; margin-bottom:20px; }}
.stat {{ background:#22263a; border-radius:8px; padding:14px; text-align:center; }}
.stat .label {{ font-size:12px; color:#888; margin-bottom:4px; }}
.stat .value {{ font-size:20px; font-weight:700; }}
.green {{ color:#4caf50; }}
.red {{ color:#f44336; }}
.yellow {{ color:#ffc107; }}
.blue {{ color:#42a5f5; }}
.chart {{ width:100%; height:400px; }}
.chart-sm {{ width:100%; height:300px; }}
table {{ width:100%; border-collapse:collapse; font-size:13px; }}
th {{ background:#22263a; color:#7eb8ff; padding:8px 6px; text-align:left; }}
td {{ padding:7px 6px; border-bottom:1px solid #2a2d3a; }}
tr:hover td {{ background:#22263a; }}
.tag {{ display:inline-block; padding:2px 8px; border-radius:4px; font-size:11px; }}
.tag-buy {{ background:#1b5e20; color:#a5d6a7; }}
.tag-sell {{ background:#b71c1c; color:#ef9a9a; }}
.note {{ background:#1a237e; border-radius:8px; padding:14px; margin:15px 0; font-size:13px; color:#90caf9; line-height:1.6; }}
.compare {{ display:grid; grid-template-columns:1fr 1fr; gap:15px; }}
.compare .old {{ border-left:3px solid #f44336; padding-left:12px; }}
.compare .new {{ border-left:3px solid #4caf50; padding-left:12px; }}
.compare h3 {{ font-size:14px; margin-bottom:8px; }}
</style>
</head>
<body>
<div class="container">
<h1>国电南瑞(600406) 买卖点回测报告</h1>
<p class="subtitle">Wilder RSI 修正版 | 回测区间 {df.index[0].strftime('%Y-%m-%d')} ~ {df.index[-1].strftime('%Y-%m-%d')} | {len(df)}个交易日 | 生成于 2026-08-02</p>

<div class="note">
⚠️ <b>RSI 修正说明</b>：本报告使用 <b>Wilder 平滑法</b>（ewm alpha=1/14）计算 RSI，与同花顺/东财等主流平台一致。
此前版本误用 SMA（rolling mean），导致 RSI 偏高约 15 点、回测信号失真。修正后最优策略从 "RSI&lt;30买/RSI&gt;70卖" 变为 "RSI&lt;40买 + 跌破MA60卖"。
</div>

<!-- 核心指标 -->
<div class="grid">
<div class="stat"><div class="label">最新收盘价</div><div class="value blue">{data['latest_close']:.2f}</div></div>
<div class="stat"><div class="label">RSI(14) Wilder</div><div class="value yellow">{data['latest_rsi']:.1f}</div></div>
<div class="stat"><div class="label">最优策略年化</div><div class="value green">+{best['annual_return']*100:.1f}%</div></div>
<div class="stat"><div class="label">最优策略胜率</div><div class="value green">{best['win_rate']*100:.0f}%</div></div>
<div class="stat"><div class="label">最大回撤</div><div class="value red">{best['max_drawdown']*100:.1f}%</div></div>
<div class="stat"><div class="label">MC中位年化</div><div class="value green">+{mc_df['annual_return'].median()*100:.1f}%</div></div>
<div class="stat"><div class="label">5年亏损概率</div><div class="value green">{(mc_df['total_return']<0).mean()*100:.1f}%</div></div>
<div class="stat"><div class="label">20万→5年中位</div><div class="value green">{mc_df['final_capital'].median()/10000:.1f}万</div></div>
</div>

<!-- 最优策略详情 -->
<div class="card">
<h2>🏆 最优策略详情（Phase 2 参数优化）</h2>
<div class="grid">
<div class="stat"><div class="label">买入信号</div><div class="value" style="font-size:15px"><span class="tag tag-buy">{best['buy_signal']}</span></div></div>
<div class="stat"><div class="label">卖出信号</div><div class="value" style="font-size:15px"><span class="tag tag-sell">{best['sell_signal']}</span></div></div>
<div class="stat"><div class="label">止损/止盈</div><div class="value" style="font-size:15px">{best['sl']*100:.0f}% / {best['tp']*100:.0f}%</div></div>
<div class="stat"><div class="label">最长持仓</div><div class="value" style="font-size:15px">{best['max_hold']}日</div></div>
<div class="stat"><div class="label">交易笔数</div><div class="value" style="font-size:15px">{best['trades']}笔</div></div>
<div class="stat"><div class="label">平均持仓</div><div class="value" style="font-size:15px">{best['avg_hold']:.0f}日</div></div>
</div>
<div class="note">
<b>策略逻辑</b>：当 Wilder RSI(14) 跌破 40（超卖区）时买入，持有期间若收盘价跌破 MA60 则卖出止损/止盈。
同时设置 {best['sl']*100:.0f}% 硬止损和 {best['tp']*100:.0f}% 硬止盈，最长持有 {best['max_hold']} 个交易日。
该策略本质是<b>均值回归</b>：在国电南瑞这类大盘蓝筹股上，RSI 超卖后大概率反弹，而 MA60 是中期趋势的生命线。
</div>
</div>

<!-- 股价+RSI+买卖点 -->
<div class="card">
<h2>📈 近一年股价走势 + RSI + 买卖点</h2>
<div id="chart_price" class="chart"></div>
</div>

<!-- 逐笔收益 -->
<div class="card">
<h2>📊 最优策略逐笔收益</h2>
<div id="chart_trades" class="chart-sm"></div>
</div>

<!-- 回撤曲线 -->
<div class="card">
<h2>📉 最优策略资金曲线与回撤</h2>
<div id="chart_dd" class="chart-sm"></div>
</div>

<!-- MC分布 -->
<div class="card">
<h2>🎲 蒙特卡洛年化收益分布（10000路径 × 5年）</h2>
<div id="chart_mc_hist" class="chart-sm"></div>
</div>

<!-- MC路径 -->
<div class="card">
<h2>🔀 蒙特卡洛资金增长路径（100条抽样）</h2>
<div id="chart_mc_paths" class="chart"></div>
</div>

<!-- Phase1 Top15 -->
<div class="card">
<h2>📋 Phase 1 信号组合 Top 15（固定参数）</h2>
<div id="chart_p1" class="chart-sm"></div>
</div>

<!-- 新旧对比 -->
<div class="card">
<h2>🔄 SMA vs Wilder RSI 对比</h2>
<div class="compare">
<div class="old">
<h3 style="color:#f44336">❌ 旧版（SMA RSI）</h3>
<p style="font-size:13px;line-height:1.8">
RSI计算方法: rolling(14).mean()<br>
最新RSI: 75.8（误判为超买）<br>
最优策略: RSI&lt;30买 / RSI&gt;70卖<br>
年化: +28.9% | 胜率: 88%<br>
<b>问题</b>: SMA RSI偏高15点，信号触发频率和时机均失真
</p>
</div>
<div class="new">
<h3 style="color:#4caf50">✅ 新版（Wilder RSI）</h3>
<p style="font-size:13px;line-height:1.8">
RSI计算方法: ewm(alpha=1/14)<br>
最新RSI: 60.7（中性区间）<br>
最优策略: RSI&lt;40买 / 跌破MA60卖<br>
年化: +18.5% | 胜率: 83%<br>
<b>优势</b>: 与同花顺/东财一致，信号更真实可靠
</p>
</div>
</div>
<div class="note" style="margin-top:15px">
<b>解读</b>：修正后年化从 28.9% 降至 18.5%，看似"变差"，实则更可信。旧版 SMA RSI 偏高导致 RSI&lt;30 极少触发（只在真正暴跌时才买入），
恰好避开了所有震荡，但这种"完美"在实盘中不可复制。Wilder 版本更接近实盘体验，18.5% 年化 + 83% 胜率对大盘蓝筹而言已属优秀。
</div>
</div>

<!-- 逐笔交易表 -->
<div class="card">
<h2>📝 最优策略逐笔交易清单</h2>
<table>
<tr><th>#</th><th>买入日</th><th>买价</th><th>卖出日</th><th>卖价</th><th>收益</th><th>持仓</th><th>原因</th></tr>
'''

for i, t in enumerate(best['trade_list']):
    ret_color = 'green' if t['return'] > 0 else 'red'
    html += f'''<tr>
<td>{i+1}</td>
<td>{t['entry_date'].strftime('%Y-%m-%d')}</td>
<td>{t['entry_price']:.2f}</td>
<td>{t['exit_date'].strftime('%Y-%m-%d')}</td>
<td>{t['exit_price']:.2f}</td>
<td class="{ret_color}">{t['return']*100:+.2f}%</td>
<td>{t['hold_days']}日</td>
<td>{t['exit_reason']}</td>
</tr>'''

html += f'''</table>
</div>

<!-- 操作建议 -->
<div class="card">
<h2>💡 当前操作建议</h2>
<div class="note">
<b>当前状态</b>：RSI(14) = {data['latest_rsi']:.1f}，处于中性区间（40-60），无明确买入/卖出信号。<br><br>
<b>操作方案</b>：<br>
① <b>等待买入</b>：RSI 跌至 40 以下时分批建仓（第一笔 1/3 仓位）<br>
② <b>加仓条件</b>：RSI 继续跌至 35 以下 + 股价仍在 MA120 之上，加至 2/3 仓位<br>
③ <b>止损</b>：买入后亏损达 10% 或收盘跌破 MA60，无条件离场<br>
④ <b>止盈</b>：盈利达 20% 减半仓，剩余跟踪 MA20<br>
⑤ <b>时间止损</b>：持仓超 25 个交易日仍未盈利，重新评估<br><br>
<b>条件单设置</b>（以当前价 {data['latest_close']:.2f} 为参考）：<br>
• 买入条件单: 收盘价 ≤ {data['latest_close']*0.92:.2f}（约-8%，对应RSI~40）<br>
• 止损条件单: 收盘价 ≤ 买入价 × 0.90<br>
• 止盈条件单: 收盘价 ≥ 买入价 × 1.20
</div>
</div>

<p style="text-align:center;color:#555;font-size:12px;padding:20px 0">
本报告由多因子Alpha策略系统生成 | Wilder RSI修正版 | 仅供研究参考，不构成投资建议
</p>
</div>

<script>
// 股价+RSI+买卖点
var chart1 = echarts.init(document.getElementById('chart_price'));
chart1.setOption({{
  backgroundColor: 'transparent',
  tooltip: {{ trigger:'axis', axisPointer:{{type:'cross'}} }},
  legend: {{ data:['收盘价','RSI(14)','买入','卖出'], textStyle:{{color:'#aaa'}}, top:5 }},
  grid: [
    {{ left:60, right:60, top:40, height:'55%' }},
    {{ left:60, right:60, top:'72%', height:'20%' }}
  ],
  xAxis: [
    {{ type:'category', data:{dates_str}, gridIndex:0, axisLabel:{{color:'#888',fontSize:10}}, axisLine:{{lineStyle:{{color:'#333'}}}} }},
    {{ type:'category', data:{dates_str}, gridIndex:1, axisLabel:{{show:false}}, axisLine:{{lineStyle:{{color:'#333'}}}} }}
  ],
  yAxis: [
    {{ type:'value', gridIndex:0, name:'价格', nameTextStyle:{{color:'#888'}}, axisLabel:{{color:'#888'}}, splitLine:{{lineStyle:{{color:'#222'}}}} }},
    {{ type:'value', gridIndex:1, name:'RSI', min:0, max:100, nameTextStyle:{{color:'#888'}}, axisLabel:{{color:'#888'}}, splitLine:{{lineStyle:{{color:'#222'}}}} }}
  ],
  series: [
    {{ name:'收盘价', type:'line', data:{close_list}, xAxisIndex:0, yAxisIndex:0, lineStyle:{{color:'#42a5f5',width:1.5}}, symbol:'none', areaStyle:{{color:new echarts.graphic.LinearGradient(0,0,0,1,[{{offset:0,color:'rgba(66,165,245,0.15)'}},{{offset:1,color:'rgba(66,165,245,0)'}}])}} }},
    {{ name:'RSI(14)', type:'line', data:{rsi_list}, xAxisIndex:1, yAxisIndex:1, lineStyle:{{color:'#ffc107',width:1.2}}, symbol:'none',
      markLine:{{ silent:true, data:[{{yAxis:40,lineStyle:{{color:'#4caf50',type:'dashed'}},label:{{formatter:'RSI 40',color:'#4caf50',fontSize:10}}}},{{yAxis:70,lineStyle:{{color:'#f44336',type:'dashed'}},label:{{formatter:'RSI 70',color:'#f44336',fontSize:10}}}}] }} }},
    {{ name:'买入', type:'scatter', data:{buy_points}, xAxisIndex:0, yAxisIndex:0, symbol:'triangle', symbolSize:12, itemStyle:{{color:'#4caf50'}} }},
    {{ name:'卖出', type:'scatter', data:{sell_points}, xAxisIndex:0, yAxisIndex:0, symbol:'pin', symbolSize:12, itemStyle:{{color:'#f44336'}} }}
  ]
}});

// 逐笔收益
var chart2 = echarts.init(document.getElementById('chart_trades'));
chart2.setOption({{
  backgroundColor:'transparent',
  tooltip: {{ trigger:'axis' }},
  xAxis: {{ type:'category', data:{trade_dates}, axisLabel:{{color:'#888',fontSize:10,rotate:45}}, axisLine:{{lineStyle:{{color:'#333'}}}} }},
  yAxis: {{ type:'value', name:'收益率%', nameTextStyle:{{color:'#888'}}, axisLabel:{{color:'#888',formatter:'{{value}}%'}}, splitLine:{{lineStyle:{{color:'#222'}}}} }},
  series: [{{
    type:'bar', data:{trade_rets},
    itemStyle: {{ color: function(p) {{ return p.value >= 0 ? '#4caf50' : '#f44336'; }} }},
    label: {{ show:true, position:'top', formatter:'{{c}}%', fontSize:10, color:'#aaa' }}
  }}]
}});

// 资金曲线+回撤
var chart3 = echarts.init(document.getElementById('chart_dd'));
var cumData = [];
var cv = 1;
var rets = {trade_rets};
for (var i=0; i<rets.length; i++) {{ cv *= (1+rets[i]/100); cumData.push(Math.round(cv*1000)/1000); }}
chart3.setOption({{
  backgroundColor:'transparent',
  tooltip: {{ trigger:'axis' }},
  legend: {{ data:['净值','回撤%'], textStyle:{{color:'#aaa'}}, top:0 }},
  xAxis: {{ type:'category', data:{trade_dates}, axisLabel:{{color:'#888',fontSize:10,rotate:45}}, axisLine:{{lineStyle:{{color:'#333'}}}} }},
  yAxis: [
    {{ type:'value', name:'净值', nameTextStyle:{{color:'#888'}}, axisLabel:{{color:'#888'}}, splitLine:{{lineStyle:{{color:'#222'}}}} }},
    {{ type:'value', name:'回撤%', nameTextStyle:{{color:'#888'}}, axisLabel:{{color:'#888',formatter:'{{value}}%'}}, splitLine:{{show:false}} }}
  ],
  series: [
    {{ name:'净值', type:'line', data:cumData, lineStyle:{{color:'#42a5f5',width:2}}, symbol:'circle', symbolSize:5, areaStyle:{{color:new echarts.graphic.LinearGradient(0,0,0,1,[{{offset:0,color:'rgba(66,165,245,0.2)'}},{{offset:1,color:'rgba(66,165,245,0)'}}])}} }},
    {{ name:'回撤%', type:'bar', yAxisIndex:1, data:{dd_list}, itemStyle:{{color:'rgba(244,67,54,0.5)'}} }}
  ]
}});

// MC直方图
var chart4 = echarts.init(document.getElementById('chart_mc_hist'));
chart4.setOption({{
  backgroundColor:'transparent',
  tooltip: {{ trigger:'axis' }},
  xAxis: {{ type:'category', data:{mc_centers}, name:'年化收益率%', nameTextStyle:{{color:'#888'}}, axisLabel:{{color:'#888',fontSize:10}}, axisLine:{{lineStyle:{{color:'#333'}}}} }},
  yAxis: {{ type:'value', name:'路径数', nameTextStyle:{{color:'#888'}}, axisLabel:{{color:'#888'}}, splitLine:{{lineStyle:{{color:'#222'}}}} }},
  series: [{{
    type:'bar', data:{mc_hist},
    itemStyle: {{ color: new echarts.graphic.LinearGradient(0,0,0,1,[{{offset:0,color:'#7eb8ff'}},{{offset:1,color:'#1a5276'}}]) }},
    markLine: {{ data:[{{xAxis:{round(mc_df['annual_return'].median()*100,1)},lineStyle:{{color:'#ffc107'}},label:{{formatter:'中位{round(mc_df['annual_return'].median()*100,1)}%',color:'#ffc107'}}}}] }}
  }}]
}});

// MC路径
var chart5 = echarts.init(document.getElementById('chart_mc_paths'));
var pathSeries = [];
var pathsData = {mc_paths_data};
for (var i=0; i<pathsData.length; i++) {{
  pathSeries.push({{
    type:'line', data:pathsData[i], symbol:'none',
    lineStyle: {{ width:0.8, opacity:0.3, color: i<50 ? '#42a5f5' : '#4caf50' }}
  }});
}}
chart5.setOption({{
  backgroundColor:'transparent',
  tooltip: {{ trigger:'axis' }},
  xAxis: {{ type:'category', data:Array.from({{length:{len(mc_paths_data[0])}}}, function(_,i){{ return 'T'+(i+1); }}), name:'交易序号', nameTextStyle:{{color:'#888'}}, axisLabel:{{color:'#888',fontSize:10}}, axisLine:{{lineStyle:{{color:'#333'}}}} }},
  yAxis: {{ type:'value', name:'净值倍数', nameTextStyle:{{color:'#888'}}, axisLabel:{{color:'#888'}}, splitLine:{{lineStyle:{{color:'#222'}}}} }},
  series: pathSeries
}});

// Phase1 Top15
var chart6 = echarts.init(document.getElementById('chart_p1'));
chart6.setOption({{
  backgroundColor:'transparent',
  tooltip: {{ trigger:'axis' }},
  xAxis: {{ type:'value', name:'年化收益率%', nameTextStyle:{{color:'#888'}}, axisLabel:{{color:'#888',formatter:'{{value}}%'}}, splitLine:{{lineStyle:{{color:'#222'}}}} }},
  yAxis: {{ type:'category', data:{p1_names[::-1]}, axisLabel:{{color:'#ccc',fontSize:11}}, axisLine:{{lineStyle:{{color:'#333'}}}} }},
  grid: {{ left:220, right:40, top:10, bottom:30 }},
  series: [{{
    type:'bar', data:{p1_annual[::-1]},
    itemStyle: {{ color: new echarts.graphic.LinearGradient(0,0,1,0,[{{offset:0,color:'#1a5276'}},{{offset:1,color:'#7eb8ff'}}]) }},
    label: {{ show:true, position:'right', formatter:'{{c}}%', fontSize:11, color:'#aaa' }}
  }}]
}});

window.addEventListener('resize', function() {{
  [chart1,chart2,chart3,chart4,chart5,chart6].forEach(function(c){{ c.resize(); }});
}});
</script>
</body>
</html>'''

outpath = '/Users/huangren/.qoderwork/workspace/ms9393tmwes9zvfq/outputs/国电南瑞_WilderRSI_买卖点回测_蒙特卡洛.html'
with open(outpath, 'w', encoding='utf-8') as f:
    f.write(html)
print(f"✅ 报告已生成: {outpath}")
print(f"   文件大小: {len(html)/1024:.1f} KB")
