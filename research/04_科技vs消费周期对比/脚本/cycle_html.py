import pickle, numpy as np, pandas as pd, json
import warnings; warnings.filterwarnings('ignore')

with open('/tmp/mc_cache/cycle_compare.pkl','rb') as f:
    d = pickle.load(f)

ca = d['cons_aligned'].values   # 消费对齐(底部=100), 完整路径
ta = d['tech_aligned'].values   # 科技对齐(底部=100), 到目前
n = d['n_tech']                 # 科技已走交易日
sim = d['similarity']

cons_peak_v = ca.max(); cons_peak_day = int(np.argmax(ca))+1
tech_now = ta[-1]
cons_at_n = ca[n-1]

# 复刻推演: 科技从当前按消费后续路径走
proj_len = len(ca) - n
proj = tech_now * ca[n:] / ca[n-1]   # ca[n-1]是第n日
proj_peak = proj.max(); proj_peak_idx = int(np.argmax(proj))
proj_end = proj[-1]

# 降采样以便绘图
def downsample(arr, maxn=600):
    if len(arr) <= maxn: return arr.tolist()
    step = len(arr)/maxn
    return [arr[int(i*step)] for i in range(maxn)] + [arr[-1]]

cons_path = [round(x,1) for x in downsample(ca)]
tech_path = [round(x,1) for x in downsample(ta)]
# 推演路径: 前面接上科技实际路径, 后面接推演
proj_full = np.concatenate([ta, proj[1:]])
proj_path = [round(x,1) for x in downsample(proj_full)]

# x轴: 交易日 -> 约多少月 (21交易日/月)
cons_x = [round(i*21/252*12/10*10/21*21/12,1) for i in range(len(cons_path))]  # 简化
# 直接用交易日序号(降采样后)
def xs(arr_len, maxn=600):
    if arr_len <= maxn: return list(range(arr_len))
    step = arr_len/maxn
    return [int(i*step) for i in range(maxn)] + [arr_len-1]
cons_x = xs(len(ca)); tech_x = xs(len(ta)); proj_x = xs(len(proj_full))

J = lambda x: json.dumps(x)

# 关键数字
tech_annual = (tech_now/100)**(252/n)-1
cons_annual_to_peak = (cons_peak_v/100)**(252/cons_peak_day)-1
pace_ratio = (tech_now-100)/(cons_at_n-100)  # 科技涨幅/消费同期涨幅

html = f'''<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>科技股 vs 消费股 周期对比 — 历史类比分析</title>
<script src="https://registry.npmmirror.com/echarts/5.5.0/files/dist/echarts.min.js"></script>
<style>
*{{margin:0;padding:0;box-sizing:border-box}}
body{{font-family:-apple-system,"PingFang SC","Microsoft YaHei",sans-serif;background:#0f1117;color:#e0e0e0}}
.container{{max-width:1200px;margin:0 auto;padding:20px}}
h1{{text-align:center;font-size:24px;padding:30px 0 8px;color:#fff}}
.subtitle{{text-align:center;color:#888;font-size:14px;margin-bottom:25px}}
.card{{background:#1a1d29;border-radius:12px;padding:20px;margin-bottom:20px;border:1px solid #2a2d3a}}
.card h2{{font-size:16px;color:#7eb8ff;margin-bottom:15px;padding-bottom:8px;border-bottom:1px solid #2a2d3a}}
.grid{{display:grid;grid-template-columns:repeat(auto-fit,minmax(170px,1fr));gap:12px;margin-bottom:15px}}
.stat{{background:#22263a;border-radius:8px;padding:13px;text-align:center}}
.stat .label{{font-size:12px;color:#888;margin-bottom:4px}}
.stat .value{{font-size:19px;font-weight:700}}
.green{{color:#4caf50}}.red{{color:#f44336}}.yellow{{color:#ffc107}}.blue{{color:#42a5f5}}.purple{{color:#b388ff}}
.chart{{width:100%;height:440px}}
.chart-sm{{width:100%;height:320px}}
.note{{background:#1a237e;border-radius:8px;padding:14px;margin:12px 0;font-size:13px;color:#90caf9;line-height:1.7}}
.warn{{background:#4a1a1a;border-radius:8px;padding:14px;margin:12px 0;font-size:13px;color:#ffab91;line-height:1.7}}
table{{width:100%;border-collapse:collapse;font-size:13px}}
th{{background:#22263a;color:#7eb8ff;padding:8px 6px;text-align:left}}
td{{padding:8px 6px;border-bottom:1px solid #2a2d3a}}
tr:hover td{{background:#22263a}}
.verdict{{background:linear-gradient(135deg,#1a3a1a,#1a2a3a);border:1px solid #2e7d32;border-radius:12px;padding:20px;margin:15px 0}}
.verdict h3{{color:#81c784;font-size:16px;margin-bottom:10px}}
.verdict p{{font-size:14px;line-height:1.8;color:#c8e6c9}}
</style>
</head>
<body>
<div class="container">
<h1>科技股 vs 消费股 · 周期位置对比</h1>
<p class="subtitle">历史类比法 | 消费篮子(茅台/五粮液/伊利/海天) vs 科技篮子(海康/立讯/京东方/中兴) | 生成于 2026-08-02</p>

<div class="note">
<b>方法</b>：将消费股(2015年底部→2021年顶部→至今)与科技股(2022年底部→至今)各自归一化为底部=100，
按"周期底部以来交易日数"对齐叠加，观察科技股当前处于消费股当年周期的哪个位置，并做路径复刻推演。
</div>

<div class="grid">
<div class="stat"><div class="label">消费本轮涨幅(底→顶)</div><div class="value green">+1168%</div></div>
<div class="stat"><div class="label">消费用时(底→顶)</div><div class="value blue">6.1年</div></div>
<div class="stat"><div class="label">消费顶部后回撤</div><div class="value red">-61.6%</div></div>
<div class="stat"><div class="label">科技当前涨幅(底→今)</div><div class="value green">+77%</div></div>
<div class="stat"><div class="label">科技已走时间</div><div class="value blue">3.8年</div></div>
<div class="stat"><div class="label">形态相似度(相关系数)</div><div class="value purple">0.79</div></div>
</div>

<div class="card">
<h2>📈 核心图：周期底部对齐叠加（底部=100）</h2>
<div id="chart_align" class="chart"></div>
<div class="note">
蓝线=消费股完整周期(底部→+1168%顶部→-56%至今)；绿线=科技股已走路径(+77%)；
虚线=若科技完全复刻消费路径的推演。关键观察：<b>科技走到消费周期63%的时间点时，涨幅只有消费同期的40%</b>
(消费当时已+193%，科技仅+77%)——科技的上涨节奏明显更温和。
</div>
</div>

<div class="card">
<h2>⚖️ 同阶段对比：科技 vs 消费（底部后第925个交易日）</h2>
<table>
<tr><th>维度</th><th>消费股(当年同期)</th><th>科技股(当前)</th><th>解读</th></tr>
<tr><td>累计涨幅</td><td class="green">+193%</td><td class="green">+77%</td><td>科技涨幅仅为消费的40%，远未到泡沫程度</td></tr>
<tr><td>年化涨速</td><td class="green">+{cons_annual_to_peak*100:.0f}%(至顶部)</td><td class="green">+{tech_annual*100:.0f}%</td><td>消费是疯牛，科技是慢牛</td></tr>
<tr><td>距周期顶部</td><td>还有+333%才见顶</td><td>—</td><td>若复刻，科技理论上还有大段上行空间</td></tr>
<tr><td>成分股状态</td><td>全部历史高位</td><td>多数未回前高</td><td>海康/京东方/中兴仍低于2022初水平</td></tr>
</table>
</div>

<div class="card">
<h2>🔮 路径复刻推演（若科技完全重走消费的路）</h2>
<div id="chart_proj" class="chart-sm"></div>
<div class="warn">
<b>推演结果（仅供参考，非预测）</b>：若科技股完全复刻消费股后续路径——<br>
① 再涨 <b>+333%</b> 至顶部（约555个交易日后，即~2028年底）<br>
② 见顶后暴跌 <b>-56%</b>（复刻消费顶部后的崩塌）<br>
③ 最终回落到约当前的 <b>{proj_end/tech_now*100:.0f}%</b> 水平<br><br>
<b>但这个推演的前提是"完全复刻"，实际大概率不会发生</b>——因为科技当前的涨速(+77%)远低于消费同期(+193%)，
节奏差异意味着这更可能是一轮"慢牛"而非"疯牛"，见顶时间和形态都会不同。
</div>
</div>

<div class="card">
<h2>🎯 结论：科技股未来走势判断</h2>
<div class="verdict">
<h3>核心判断：科技股处于周期中段偏早，远未见顶，但需警惕"复刻崩塌"的尾部风险</h3>
<p>
<b>1. 不是泡沫顶部，是中段。</b>消费股见顶时是"全成分股历史高位+6年+1168%+全民讨论白酒"。
当前科技股仅+77%、多数个股未回前高、涨速温和(年化+{tech_annual*100:.0f}% vs 消费年化+{cons_annual_to_peak*100:.0f}%)，
距离典型泡沫特征还很远。形态相似度0.79说明<b>节奏相似</b>，但<b>幅度远未到位</b>。<br><br>
<b>2. 上行空间：若复刻消费，理论上还有+333%。</b>但更现实的基准是：科技涨速约为消费的40%，
则"打折后"的剩余空间约为 +130%~150%（对应消费剩余空间+333%×40%），时间窗口约2-3年。<br><br>
<b>3. 最大的风险不是现在，是未来见顶后的崩塌。</b>消费顶部后-61.6%、至今(2026)仍-56%未收复。
科技股若也走出同样的"疯牛→崩塌"，杀伤力巨大。当前温和的涨速反而是好事——<b>慢牛比疯牛更持久、崩塌时也更温和</b>。<br><br>
<b>4. 操作含义：</b>现在不是离场的时候（周期未到顶部），但也别指望复制消费+1168%的神话。
建议<b>持有为主、分批建仓、严格止损</b>；重点监控两个见顶信号——
① 成分股全面创历史新高且加速赶顶；② RSI持续>80的极端超买。这两个信号同时出现才是减仓时点。
</p>
</div>
</div>

<p style="text-align:center;color:#555;font-size:12px;padding:20px 0">
历史类比分析 | 等权篮子·前复权 | 仅供研究参考，不构成投资建议
</p>
</div>

<script>
var consPath={J(cons_path)};
var techPath={J(tech_path)};
var projPath={J(proj_path)};
var consX={J(cons_x)};var techX={J(tech_x)};var projX={J(proj_x)};
var nTech={n};

// 对齐叠加图
var c1=echarts.init(document.getElementById('chart_align'));
var consData=consX.map(function(x,i){{return [x,consPath[i]];}});
var techData=techX.map(function(x,i){{return [x,techPath[i]];}});
c1.setOption({{
  backgroundColor:'transparent',
  tooltip:{{trigger:'axis'}},
  legend:{{data:['消费股周期(2015底起)','科技股周期(2022底起)'],textStyle:{{color:'#aaa'}},top:5}},
  xAxis:{{type:'value',name:'底部以来(交易日)',nameTextStyle:{{color:'#888'}},axisLabel:{{color:'#888'}},splitLine:{{lineStyle:{{color:'#222'}}}},
    max:{len(ca)} }},
  yAxis:{{type:'log',name:'净值(底部=100,对数轴)',nameTextStyle:{{color:'#888'}},axisLabel:{{color:'#888'}},splitLine:{{lineStyle:{{color:'#222'}}}},min:80}},
  series:[
    {{name:'消费股周期(2015底起)',type:'line',data:consData,lineStyle:{{color:'#42a5f5',width:2}},symbol:'none',
      markPoint:{{data:[{{coord:[{cons_peak_day},{round(cons_peak_v,1)}],value:'消费顶部+1168%',itemStyle:{{color:'#f44336'}},label:{{color:'#fff',fontSize:10}}}}]}}}},
    {{name:'科技股周期(2022底起)',type:'line',data:techData,lineStyle:{{color:'#4caf50',width:2.5}},symbol:'none',
      markLine:{{silent:true,data:[{{xAxis:nTech,lineStyle:{{color:'#ffc107',type:'dashed'}},label:{{formatter:'科技当前位置',color:'#ffc107',fontSize:10}}}}]}}}}
  ]
}});

// 推演图
var c2=echarts.init(document.getElementById('chart_proj'));
var projData=projX.map(function(x,i){{return [x,projPath[i]];}});
c2.setOption({{
  backgroundColor:'transparent',
  tooltip:{{trigger:'axis'}},
  legend:{{data:['科技实际+复刻推演'],textStyle:{{color:'#aaa'}},top:0}},
  xAxis:{{type:'value',name:'底部以来(交易日)',nameTextStyle:{{color:'#888'}},axisLabel:{{color:'#888'}},splitLine:{{lineStyle:{{color:'#222'}}}}}},
  yAxis:{{type:'log',name:'净值(对数轴)',nameTextStyle:{{color:'#888'}},axisLabel:{{color:'#888'}},splitLine:{{lineStyle:{{color:'#222'}}}},min:80}},
  series:[
    {{name:'科技实际+复刻推演',type:'line',data:projData,lineStyle:{{color:'#b388ff',width:2}},symbol:'none',
      areaStyle:{{color:new echarts.graphic.LinearGradient(0,0,0,1,[{{offset:0,color:'rgba(179,136,255,0.2)'}},{{offset:1,color:'rgba(179,136,255,0)'}}])}},
      markLine:{{silent:true,data:[
        {{xAxis:nTech,lineStyle:{{color:'#ffc107',type:'dashed'}},label:{{formatter:'现在',color:'#ffc107',fontSize:10}}}},
        {{xAxis:{n+proj_peak_idx},lineStyle:{{color:'#f44336',type:'dashed'}},label:{{formatter:'复刻顶部(+333%)',color:'#f44336',fontSize:10}}}}
      ]}}}}
  ]
}});
window.addEventListener('resize',function(){{[c1,c2].forEach(function(c){{c.resize();}});}});
</script>
</body>
</html>'''

outpath='/Users/huangren/.qoderwork/workspace/ms9393tmwes9zvfq/outputs/科技股vs消费股_周期对比_走势判断.html'
with open(outpath,'w',encoding='utf-8') as f:
    f.write(html)
print(f"✅ 报告已生成: {len(html)/1024:.1f} KB")
print(f"\n关键数字: 科技当前={tech_now:.1f}, 消费同期={cons_at_n:.1f}, 复刻顶部={proj_peak:.0f}(+{proj_peak/tech_now*100-100:.0f}%), 复刻终点={proj_end:.0f}")
