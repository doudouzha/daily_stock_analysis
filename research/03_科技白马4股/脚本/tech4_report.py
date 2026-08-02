import pickle, pandas as pd, numpy as np, json
import warnings; warnings.filterwarnings('ignore')

with open('/tmp/mc_cache/tech4_results.pkl','rb') as f:
    all_results = pickle.load(f)
with open('/tmp/mc_cache/tech4_mc.pkl','rb') as f:
    mc_all = pickle.load(f)

J = lambda x: json.dumps(x, ensure_ascii=False)

# 计算每只股票的当前买卖点位
stock_cards = []
compare_rows = []
chart_data = {}

for code, res in all_results.items():
    name = res['name']
    df = res['df']
    best = res['phase2'][0] if res['phase2'] else None
    mdf = mc_all.get(code)
    c = df['close'].astype(float)
    last = df.iloc[-1]
    price = float(c.iloc[-1])
    rsi = float(res['latest_rsi'])
    ma20 = float(last['ma20']); ma60 = float(last['ma60']); ma120 = float(last['ma120'])
    boll_l = float(last['boll_lower']); boll_u = float(last['boll_upper'])

    # 近1年走势
    recent = df[df.index >= '2025-08-01']
    chart_data[code] = {
        'dates': [d.strftime('%Y-%m-%d') for d in recent.index],
        'close': [round(float(x),2) for x in recent['close']],
        'rsi': [round(float(x),1) if not np.isnan(x) else None for x in recent['rsi_14']],
    }

    # 买卖点位逻辑
    # 买入参考: 基于最优策略的买入信号
    bsig = best['buy_signal']
    if 'RSI<30' in bsig: buy_rsi = 30
    elif 'RSI<35' in bsig: buy_rsi = 35
    elif 'RSI<40' in bsig: buy_rsi = 40
    elif 'RSI<45' in bsig: buy_rsi = 45
    elif 'RSI<50' in bsig: buy_rsi = 50
    else: buy_rsi = None

    # 用近60日 RSI-价格关系估算买入价
    r60 = df.tail(60)
    if buy_rsi is not None:
        # 找近60日RSI接近buy_rsi时的价格中位数作为参考
        mask = (r60['rsi_14'] >= buy_rsi-3) & (r60['rsi_14'] <= buy_rsi+3)
        if mask.sum() > 0:
            buy_price_est = float(r60.loc[mask,'close'].median())
        else:
            buy_price_est = price * 0.93
    else:
        buy_price_est = None

    # 止损/止盈价
    sl_price = price * (1 - best['sl'])
    tp_price = price * (1 + best['tp'])

    # RSI状态判断
    if rsi < 30: rsi_state = ('超卖区', '#4caf50', '强烈关注买入')
    elif rsi < 40: rsi_state = ('偏弱区', '#8bc34a', '接近买入区间')
    elif rsi < 60: rsi_state = ('中性区', '#ffc107', '观望等待')
    elif rsi < 70: rsi_state = ('偏强区', '#ff9800', '持有/谨慎追高')
    else: rsi_state = ('超买区', '#f44336', '考虑减仓')

    stock_cards.append({
        'code': code, 'name': name, 'price': price, 'rsi': rsi,
        'ma20': ma20, 'ma60': ma60, 'ma120': ma120,
        'boll_l': boll_l, 'boll_u': boll_u,
        'best': best, 'mdf': mdf,
        'buy_rsi': buy_rsi, 'buy_price_est': buy_price_est,
        'sl_price': sl_price, 'tp_price': tp_price,
        'rsi_state': rsi_state,
    })

    mc_med = mdf['annual_return'].median()*100 if mdf is not None else 0
    compare_rows.append({
        'name': name, 'code': code.replace('sz',''),
        'price': price, 'rsi': rsi,
        'strategy': f"{best['buy_signal']}→{best['sell_signal']}",
        'params': f"SL{best['sl']*100:.0f}%/TP{best['tp']*100:.0f}%/{best['max_hold']}日",
        'annual': best['annual_return']*100, 'win': best['win_rate']*100,
        'mdd': best['max_drawdown']*100, 'trades': best['trades'],
        'mc_med': mc_med, 'loss_prob': (mdf['total_return']<0).mean()*100 if mdf is not None else 0,
    })

# 排序: 按MC中位年化
compare_rows.sort(key=lambda x: x['mc_med'], reverse=True)

# 生成HTML
cards_html = ''
for sc in stock_cards:
    best = sc['best']; mdf = sc['mdf']
    state_txt, state_color, state_act = sc['rsi_state']
    mc_med = mdf['annual_return'].median()*100
    loss_prob = (mdf['total_return']<0).mean()*100

    # 买卖点建议
    if sc['buy_rsi'] is not None and sc['buy_price_est'] is not None:
        buy_txt = f"RSI跌至 <b>{sc['buy_rsi']}</b> 以下买入（参考价 <b>{sc['buy_price_est']:.2f}</b>）"
    else:
        buy_txt = f"等待 <b>{best['buy_signal']}</b> 信号触发买入"

    sell_txt = f"触发 <b>{best['sell_signal']}</b> 卖出；或止损 <b>{sc['sl_price']:.2f}</b>(-{best['sl']*100:.0f}%) / 止盈 <b>{sc['tp_price']:.2f}</b>(+{best['tp']*100:.0f}%)"

    params_str = f"SL{best['sl']*100:.0f}%/TP{best['tp']*100:.0f}%/{best['max_hold']}日"
    cards_html += f'''
<div class="card">
<h2>{sc['name']} ({sc['code'].replace('sz','')}) <span style="float:right;font-size:13px;padding:3px 10px;border-radius:12px;background:{state_color}22;color:{state_color}">{state_txt} · {state_act}</span></h2>
<div class="grid">
<div class="stat"><div class="label">现价</div><div class="value blue">{sc['price']:.2f}</div></div>
<div class="stat"><div class="label">RSI(14)</div><div class="value" style="color:{state_color}">{sc['rsi']:.1f}</div></div>
<div class="stat"><div class="label">最优年化</div><div class="value green">+{best['annual_return']*100:.1f}%</div></div>
<div class="stat"><div class="label">胜率</div><div class="value green">{best['win_rate']*100:.0f}%</div></div>
<div class="stat"><div class="label">最大回撤</div><div class="value red">{best['max_drawdown']*100:.1f}%</div></div>
<div class="stat"><div class="label">MC中位年化</div><div class="value green">+{mc_med:.1f}%</div></div>
</div>
<div class="note">
<b>最优策略</b>：{best['buy_signal']} → {best['sell_signal']}（{params_str}，{best['trades']}笔，均持{best['avg_hold']:.0f}日）<br><br>
<b>📍 买入点</b>：{buy_txt}<br>
<b>📍 卖出点</b>：{sell_txt}<br><br>
<b>关键价位</b>：MA20={sc['ma20']:.2f} | MA60={sc['ma60']:.2f} | MA120={sc['ma120']:.2f} | 布林下轨={sc['boll_l']:.2f} | 布林上轨={sc['boll_u']:.2f}<br>
<b>蒙特卡洛</b>：5年亏损概率 {loss_prob:.1f}% | MC年化P5={mdf['annual_return'].quantile(.05)*100:+.1f}% / P95={mdf['annual_return'].quantile(.95)*100:+.1f}%
</div>
<div id="chart_{sc['code']}" class="chart-sm"></div>
</div>'''

# 对比表
compare_html = '<tr><th>排名</th><th>股票</th><th>现价</th><th>RSI</th><th>最优策略</th><th>参数</th><th>年化</th><th>胜率</th><th>回撤</th><th>MC中位年化</th><th>亏损概率</th></tr>'
for i, r in enumerate(compare_rows):
    compare_html += f'<tr><td>{i+1}</td><td><b>{r["name"]}</b><br><span style="color:#666">{r["code"]}</span></td><td>{r["price"]:.2f}</td><td>{r["rsi"]:.1f}</td><td>{r["strategy"]}</td><td>{r["params"]}</td><td class="green">+{r["annual"]:.1f}%</td><td>{r["win"]:.0f}%</td><td class="red">{r["mdd"]:.1f}%</td><td class="green">+{r["mc_med"]:.1f}%</td><td>{r["loss_prob"]:.1f}%</td></tr>'

# JS图表
charts_js = ''
for sc in stock_cards:
    cd = chart_data[sc['code']]
    charts_js += f'''
var ch_{sc['code']} = echarts.init(document.getElementById('chart_{sc['code']}'));
ch_{sc['code']}.setOption({{
  backgroundColor:'transparent',
  tooltip:{{trigger:'axis',axisPointer:{{type:'cross'}}}},
  legend:{{data:['收盘价','RSI(14)'],textStyle:{{color:'#aaa'}},top:0}},
  grid:[{{left:55,right:55,top:30,height:'55%'}},{{left:55,right:55,top:'72%',height:'20%'}}],
  xAxis:[
    {{type:'category',data:{J(cd['dates'])},gridIndex:0,axisLabel:{{color:'#888',fontSize:9}},axisLine:{{lineStyle:{{color:'#333'}}}}}},
    {{type:'category',data:{J(cd['dates'])},gridIndex:1,axisLabel:{{show:false}},axisLine:{{lineStyle:{{color:'#333'}}}}}}
  ],
  yAxis:[
    {{type:'value',gridIndex:0,axisLabel:{{color:'#888'}},splitLine:{{lineStyle:{{color:'#222'}}}}}},
    {{type:'value',gridIndex:1,min:0,max:100,axisLabel:{{color:'#888'}},splitLine:{{lineStyle:{{color:'#222'}}}}}}
  ],
  series:[
    {{name:'收盘价',type:'line',data:{J(cd['close'])},xAxisIndex:0,yAxisIndex:0,lineStyle:{{color:'#42a5f5',width:1.5}},symbol:'none',
      areaStyle:{{color:new echarts.graphic.LinearGradient(0,0,0,1,[{{offset:0,color:'rgba(66,165,245,0.15)'}},{{offset:1,color:'rgba(66,165,245,0)'}}])}}}},
    {{name:'RSI(14)',type:'line',data:{J(cd['rsi'])},xAxisIndex:1,yAxisIndex:1,lineStyle:{{color:'#ffc107',width:1.2}},symbol:'none',
      markLine:{{silent:true,data:[{{yAxis:40,lineStyle:{{color:'#4caf50',type:'dashed'}},label:{{formatter:'40',color:'#4caf50',fontSize:9}}}},{{yAxis:70,lineStyle:{{color:'#f44336',type:'dashed'}},label:{{formatter:'70',color:'#f44336',fontSize:9}}}}]}}}}
  ]
}});'''

html = f'''<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>科技白马4股 Wilder RSI 策略对比报告</title>
<script src="https://registry.npmmirror.com/echarts/5.5.0/files/dist/echarts.min.js"></script>
<style>
*{{margin:0;padding:0;box-sizing:border-box}}
body{{font-family:-apple-system,"PingFang SC","Microsoft YaHei",sans-serif;background:#0f1117;color:#e0e0e0}}
.container{{max-width:1200px;margin:0 auto;padding:20px}}
h1{{text-align:center;font-size:24px;padding:30px 0 10px;color:#fff}}
.subtitle{{text-align:center;color:#888;font-size:14px;margin-bottom:30px}}
.card{{background:#1a1d29;border-radius:12px;padding:20px;margin-bottom:20px;border:1px solid #2a2d3a}}
.card h2{{font-size:16px;color:#7eb8ff;margin-bottom:15px;padding-bottom:8px;border-bottom:1px solid #2a2d3a}}
.grid{{display:grid;grid-template-columns:repeat(auto-fit,minmax(160px,1fr));gap:12px;margin-bottom:15px}}
.stat{{background:#22263a;border-radius:8px;padding:12px;text-align:center}}
.stat .label{{font-size:12px;color:#888;margin-bottom:4px}}
.stat .value{{font-size:19px;font-weight:700}}
.green{{color:#4caf50}}.red{{color:#f44336}}.yellow{{color:#ffc107}}.blue{{color:#42a5f5}}
.chart-sm{{width:100%;height:300px}}
table{{width:100%;border-collapse:collapse;font-size:13px}}
th{{background:#22263a;color:#7eb8ff;padding:8px 6px;text-align:left}}
td{{padding:8px 6px;border-bottom:1px solid #2a2d3a;vertical-align:top}}
tr:hover td{{background:#22263a}}
.note{{background:#1a237e;border-radius:8px;padding:14px;margin:12px 0;font-size:13px;color:#90caf9;line-height:1.7}}
</style>
</head>
<body>
<div class="container">
<h1>科技白马 4 股策略对比报告</h1>
<p class="subtitle">海康威视 · 立讯精密 · 京东方A · 中兴通讯 | Wilder RSI | 回测 2021-08 ~ 2026-07 | 生成于 2026-08-02</p>

<div class="card">
<h2>📊 综合对比排名（按蒙特卡洛中位年化）</h2>
<table>{compare_html}</table>
<div class="note">
<b>解读</b>：中兴通讯、立讯精密的策略弹性最大（MC中位年化95%+/60%+），但回撤也更深；海康威视最稳（回撤仅-13.9%）。
注意：MC是基于历史最优策略收益的<b>有放回重采样</b>，存在过拟合风险，实际收益大概率低于中位数，建议以P5（悲观情形）作为预期底线。
</div>
</div>

{cards_html}

<p style="text-align:center;color:#555;font-size:12px;padding:20px 0">
本报告由多因子Alpha策略系统生成 | Wilder RSI | 仅供研究参考，不构成投资建议
</p>
</div>
<script>
{charts_js}
window.addEventListener('resize',function(){{document.querySelectorAll('[id^=chart_]').forEach(function(el){{var c=echarts.getInstanceByDom(el);if(c)c.resize();}});}});
</script>
</body>
</html>'''

outpath = '/Users/huangren/.qoderwork/workspace/ms9393tmwes9zvfq/outputs/科技白马4股_策略对比_买卖点.html'
with open(outpath,'w',encoding='utf-8') as f:
    f.write(html)
print(f"✅ 报告已生成: {len(html)/1024:.1f} KB")

# 同时导出对比CSV
cdf = pd.DataFrame(compare_rows)
cdf.columns = ['股票','代码','现价','RSI','最优策略','参数','历史年化%','胜率%','最大回撤%','交易笔数','MC中位年化%','5年亏损概率%']
for col in ['历史年化%','胜率%','最大回撤%','MC中位年化%','5年亏损概率%']:
    cdf[col] = cdf[col].round(1)
cdf.to_csv('/Users/huangren/.qoderwork/workspace/ms9393tmwes9zvfq/outputs/科技白马4股_策略对比.csv', index=False, encoding='utf-8-sig')
print("✅ 对比CSV已导出")
