import akshare as ak, pandas as pd, numpy as np, pickle, json
import warnings; warnings.filterwarnings('ignore')

with open('/tmp/mc_cache/tech3_ind.pkl','rb') as f:
    R = pickle.load(f)

J = lambda x: json.dumps(x, ensure_ascii=False)

def get_chart(code):
    df = ak.stock_zh_a_daily(symbol=code, adjust="qfq")
    df['date']=pd.to_datetime(df['date']); df=df.set_index('date').sort_index()
    df = df.tail(130)
    c=df['close'].astype(float)
    delta=c.diff(); g=delta.clip(lower=0); lo=-delta.clip(upper=0)
    rsi=100-100/(1+g.ewm(alpha=1/14,min_periods=14,adjust=False).mean()/lo.ewm(alpha=1/14,min_periods=14,adjust=False).mean().replace(0,np.nan))
    e12=c.ewm(span=12,adjust=False).mean(); e26=c.ewm(span=26,adjust=False).mean()
    dif=e12-e26; dea=dif.ewm(span=9,adjust=False).mean(); macd=2*(dif-dea)
    mid=c.rolling(20).mean(); std=c.rolling(20).std()
    return {
        'dates':[d.strftime('%m-%d') for d in df.index],
        'close':[round(float(x),2) for x in c],
        'ma5':[round(float(x),2) if not np.isnan(x) else None for x in c.rolling(5).mean()],
        'ma20':[round(float(x),2) if not np.isnan(x) else None for x in c.rolling(20).mean()],
        'ma60':[round(float(x),2) if not np.isnan(x) else None for x in c.rolling(60).mean()],
        'bu':[round(float(x),2) if not np.isnan(x) else None for x in mid+2*std],
        'bl':[round(float(x),2) if not np.isnan(x) else None for x in mid-2*std],
        'rsi':[round(float(x),1) if not np.isnan(x) else None for x in rsi],
        'dif':[round(float(x),2) for x in dif], 'dea':[round(float(x),2) for x in dea],
        'macd':[round(float(x),2) for x in macd],
    }

charts = {code:get_chart(code) for code in R}

# 每只股票的趋势/位置/量能标签
def tags(r):
    trend = '空头排列·下降趋势' if r['bear_align'] else ('多头排列·上升趋势' if r['bull_align'] else '均线纠缠·震荡')
    trend_c = '#f44336' if r['bear_align'] else ('#4caf50' if r['bull_align'] else '#ffc107')
    if r['rsi']<30: pos,posc='深度超卖','#4caf50'
    elif r['rsi']<40: pos,posc='偏弱超卖','#8bc34a'
    elif r['rsi']<60: pos,posc='中性','#ffc107'
    else: pos,posc='偏强','#ff9800'
    vol = '放量' if r['vol_ratio']>1.2 else ('缩量' if r['vol_ratio']<0.8 else '平量')
    return trend,trend_c,pos,posc,vol

# 分析文案
ANALYSIS = {
'sh600487': {
 'summary':'三个月内从124.85高点崩塌至47.61，20个交易日暴跌-46.8%（7月13日曾跌停），是三只中跌得最惨的。当前RSI 27.9、KDJ J值13均处深度超卖区，短线随时可能技术性反弹，但均线全面空头排列、MACD深绿柱未收敛，趋势尚未扭转——典型的"接飞刀"位置，超卖≠见底。',
 'trend':'MA5(50.0) < MA10(53.0) < MA20(63.4) < MA60(81.8)，标准空头排列，价格被所有均线压制。MACD DIF(-11.2) < DEA(-10.1)，绿柱-2.25但已不再放大，说明杀跌动能边际减弱。趋势判定：<b>下降趋势，但跌速放缓</b>。',
 'position':'股价47.61位于布林带18%分位（下轨38.65/中轨63.44），距中轨还有+33%空间。RSI 27.9 < 30进入超卖区，KDJ J值13严重超卖。52周位置仅29%。位置判定：<b>深度超卖、严重偏离均线</b>，乖离率过大有回归需求，但回归方式可能是横盘修复而非V型反转。',
 'sr':'下方支撑：45.60（20日低点，已两次触及未破）→ 38.65（布林下轨）。上方压力：48.8（枢轴P）→ 50.0（MA5）→ 53.0（MA10）。当前价47.61夹在20日低点与枢轴之间，<b>45.60是生命线，跌破则打开下行空间</b>。',
 'volume':'量比1.21、今日成交107.7亿，但5/20日量比0.87（整体量能萎缩），OBV 5日仍在下行、MFI 30偏弱、WVAD为负。量能判定：<b>下跌放量、反弹缩量，资金仍在流出</b>，尚未看到底部放量吸筹特征。',
 'watch':'① 45.60支撑能否守住；② RSI能否底背离（价格新低但RSI不创新低）；③ 是否出现放量长阳收复MA5(50.0)。三者满足2个以上才考虑超跌反弹，否则继续观望。',
},
'sh601138': {
 'summary':'三只中跌得最温和（月跌-11.4%），今日放量大涨+5.39%（成交84.3亿），是三只中反弹信号最明确的。但股价56.70仍在所有均线下方，空头排列未破坏，反弹能否持续需看能否收复MA5(57.6)和MA20(61.6)。',
 'trend':'MA5(57.6) < MA10(58.9) < MA20(61.6) < MA60(68.1)，空头排列但均线间距收窄（MA5与MA10仅差1.3），说明跌势趋缓。MACD DIF(-3.2) < DEA(-2.8)，绿柱-0.80较浅。趋势判定：<b>下降趋势末段，今日放量长阳是首个修复信号</b>。',
 'position':'股价56.70位于布林带19%分位（下轨53.67/中轨61.56）。RSI 40.4中性偏弱（三只中最高，说明最抗跌），KDJ J值20低位。52周位置47%，距高点-33%。位置判定：<b>偏低位但非极端超卖</b>，今日+5.39%已从低点53.22反弹+6.5%。',
 'sr':'下方支撑：53.67（布林下轨）→ 53.22（20日低点）。上方压力：56.86（枢轴P，当前价几乎贴合）→ 57.58（MA5）→ 61.56（MA20/布林中轨）。当前价56.70正好压在枢轴点上，<b>站稳枢轴并收复MA5(57.6)则反弹确认</b>。',
 'volume':'量比1.19，今日+5.39%伴随84.3亿成交（明显放量），但OBV 5日仍下行、MFI 48中性。量能判定：<b>单日放量反弹是积极信号，但需连续2-3日放量确认</b>，若明日缩量回落则反弹夭折。',
 'watch':'① 能否放量收复MA5(57.6)并站稳；② 明日是否延续放量（量比>1.5）；③ MACD绿柱能否转红。这是三只中最值得跟踪反弹机会的标的。',
},
'sz002281': {
 'summary':'月跌-25.9%，从279高点回落至161.65（-42%），今日放量大涨+6.12%（量比1.30三只中最高）。KDJ J值仅9（极度超卖），布林带14%分位贴近下轨，超卖程度仅次于亨通。但MACD绿柱-9.48是三只中最深的，下跌动能仍强，属于"高波动高弹性"的超跌反弹博弈品种。',
 'trend':'MA5(169.9) < MA10(177.6) < MA20(198.0) < MA60(214.5)，空头排列且均线间距大（MA5与MA20差28元），说明前期跌势猛烈。MACD DIF(-15.5) < DEA(-10.8)，绿柱-9.48三只中最深。趋势判定：<b>下降趋势，下跌动能仍强，但今日+6.12%放量长阳显示超卖反弹启动</b>。',
 'position':'股价161.65位于布林带14%分位（下轨147.83/中轨197.98），距中轨有+22%空间。RSI 37.4偏弱，KDJ J值9极度超卖（三只中最低）。52周位置49%。位置判定：<b>极度超卖、贴近布林下轨</b>，技术性反弹一触即发，今日+6.12%已打响第一枪。',
 'sr':'下方支撑：152.33（20日低点）→ 147.83（布林下轨）。上方压力：163.4（枢轴P）→ 169.9（MA5）→ 177.6（MA10）。当前价161.65已突破枢轴163.4附近，<b>若站稳MA5(169.9)则超跌反弹空间打开至MA10(177.6)</b>。',
 'volume':'量比1.30三只中最高，今日+6.12%伴随87.5亿放量，但OBV 5日下行、MFI 32偏弱。量能判定：<b>放量反弹启动，量价配合初步成立</b>，但MFI仍低说明资金回流尚不充分，需持续放量验证。',
 'watch':'① 能否放量站上MA5(169.9)；② KDJ能否金叉（J值从9回升）；③ 152.33支撑是否二次探底。弹性最大但波动也最大，适合风险偏好高的超跌博弈。',
},
}

# 构建卡片
cards = ''
chart_js = ''
order = ['sh600487','sh601138','sz002281']
for code in order:
    r = R[code]; a = ANALYSIS[code]; ch = charts[code]
    trend,trend_c,pos,posc,vol = tags(r)
    cards += f'''
<div class="card">
<h2>{r['name']} ({code.replace('sh','').replace('sz','')}) 
<span class="pill" style="background:{trend_c}22;color:{trend_c}">{trend}</span>
<span class="pill" style="background:{posc}22;color:{posc}">{pos}</span>
<span class="pill" style="background:#42a5f522;color:#42a5f5">{vol}</span></h2>
<div class="grid">
<div class="stat"><div class="label">收盘价({r['last_date']})</div><div class="value blue">{r['close']:.2f}</div></div>
<div class="stat"><div class="label">当日涨跌</div><div class="value {'green' if r['chg_pct']>0 else 'red'}">{r['chg_pct']:+.2f}%</div></div>
<div class="stat"><div class="label">周涨跌</div><div class="value {'green' if r['week_chg']>0 else 'red'}">{r['week_chg']:+.1f}%</div></div>
<div class="stat"><div class="label">月涨跌</div><div class="value {'green' if r['month_chg']>0 else 'red'}">{r['month_chg']:+.1f}%</div></div>
<div class="stat"><div class="label">RSI(14)</div><div class="value" style="color:{posc}">{r['rsi']:.1f}</div></div>
<div class="stat"><div class="label">52周位置</div><div class="value yellow">{r['pos_52w']:.0f}%</div></div>
</div>
<div class="sec"><b>① 行情概览</b>：收盘{r['close']:.2f}元({r['chg_pct']:+.2f}%)，日内{r['low']:.2f}~{r['high']:.2f}，成交{r['amount']:.0f}亿。近一周{r['week_chg']:+.1f}%、近一月{r['month_chg']:+.1f}%，距52周高点{r['dist_high']:+.1f}%。</div>
<div class="sec"><b>② 趋势判断</b>：{a['trend']}</div>
<div class="sec"><b>③ 位置高低</b>：{a['position']}</div>
<div class="sec"><b>④ 支撑压力</b>：{a['sr']}</div>
<div class="sec"><b>⑤ 量能确认</b>：{a['volume']}</div>
<div class="sec watch"><b>👁 后续观察信号</b>：{a['watch']}</div>
<div class="sec summary"><b>📌 一句话总结</b>：{a['summary']}</div>
<div id="chart_{code}" class="chart"></div>
</div>'''

    chart_js += f'''
var ch_{code.replace('sh','').replace('sz','')}=echarts.init(document.getElementById('chart_{code}'));
ch_{code.replace('sh','').replace('sz','')}.setOption({{
  backgroundColor:'transparent',
  tooltip:{{trigger:'axis',axisPointer:{{type:'cross'}}}},
  legend:{{data:['收盘','MA5','MA20','MA60','布林上轨','布林下轨','RSI','MACD'],textStyle:{{color:'#aaa',fontSize:10}},top:0}},
  grid:[{{left:55,right:55,top:35,height:'42%'}},{{left:55,right:55,top:'56%',height:'16%'}},{{left:55,right:55,top:'78%',height:'16%'}}],
  xAxis:[
    {{type:'category',data:{J(ch['dates'])},gridIndex:0,axisLabel:{{show:false}},axisLine:{{lineStyle:{{color:'#333'}}}}}},
    {{type:'category',data:{J(ch['dates'])},gridIndex:1,axisLabel:{{show:false}},axisLine:{{lineStyle:{{color:'#333'}}}}}},
    {{type:'category',data:{J(ch['dates'])},gridIndex:2,axisLabel:{{color:'#888',fontSize:9}},axisLine:{{lineStyle:{{color:'#333'}}}}}}
  ],
  yAxis:[
    {{type:'value',gridIndex:0,axisLabel:{{color:'#888'}},splitLine:{{lineStyle:{{color:'#222'}}}}}},
    {{type:'value',gridIndex:1,min:0,max:100,axisLabel:{{color:'#888',fontSize:9}},splitLine:{{lineStyle:{{color:'#222'}}}}}},
    {{type:'value',gridIndex:2,axisLabel:{{color:'#888',fontSize:9}},splitLine:{{lineStyle:{{color:'#222'}}}}}}
  ],
  series:[
    {{name:'收盘',type:'line',data:{J(ch['close'])},xAxisIndex:0,yAxisIndex:0,lineStyle:{{color:'#42a5f5',width:1.8}},symbol:'none'}},
    {{name:'MA5',type:'line',data:{J(ch['ma5'])},xAxisIndex:0,yAxisIndex:0,lineStyle:{{color:'#ffc107',width:1}},symbol:'none'}},
    {{name:'MA20',type:'line',data:{J(ch['ma20'])},xAxisIndex:0,yAxisIndex:0,lineStyle:{{color:'#e91e63',width:1}},symbol:'none'}},
    {{name:'MA60',type:'line',data:{J(ch['ma60'])},xAxisIndex:0,yAxisIndex:0,lineStyle:{{color:'#9c27b0',width:1}},symbol:'none'}},
    {{name:'布林上轨',type:'line',data:{J(ch['bu'])},xAxisIndex:0,yAxisIndex:0,lineStyle:{{color:'#555',width:1,type:'dashed'}},symbol:'none'}},
    {{name:'布林下轨',type:'line',data:{J(ch['bl'])},xAxisIndex:0,yAxisIndex:0,lineStyle:{{color:'#555',width:1,type:'dashed'}},symbol:'none'}},
    {{name:'RSI',type:'line',data:{J(ch['rsi'])},xAxisIndex:1,yAxisIndex:1,lineStyle:{{color:'#ffc107',width:1.2}},symbol:'none',
      markLine:{{silent:true,data:[{{yAxis:30,lineStyle:{{color:'#4caf50',type:'dashed'}},label:{{show:false}}}},{{yAxis:70,lineStyle:{{color:'#f44336',type:'dashed'}},label:{{show:false}}}}]}}}},
    {{name:'MACD',type:'bar',data:{J(ch['macd'])},xAxisIndex:2,yAxisIndex:2,itemStyle:{{color:function(p){{return p.value>=0?'#f44336':'#4caf50';}}}}}},
    {{name:'DIF',type:'line',data:{J(ch['dif'])},xAxisIndex:2,yAxisIndex:2,lineStyle:{{color:'#42a5f5',width:1}},symbol:'none'}},
    {{name:'DEA',type:'line',data:{J(ch['dea'])},xAxisIndex:2,yAxisIndex:2,lineStyle:{{color:'#ffc107',width:1}},symbol:'none'}}
  ]
}});'''

html = f'''<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>光通信AI链3股技术分析报告</title>
<script src="https://registry.npmmirror.com/echarts/5.5.0/files/dist/echarts.min.js"></script>
<style>
*{{margin:0;padding:0;box-sizing:border-box}}
body{{font-family:-apple-system,"PingFang SC","Microsoft YaHei",sans-serif;background:#0f1117;color:#e0e0e0}}
.container{{max-width:1200px;margin:0 auto;padding:20px}}
h1{{text-align:center;font-size:24px;padding:28px 0 8px;color:#fff}}
.subtitle{{text-align:center;color:#888;font-size:14px;margin-bottom:22px}}
.card{{background:#1a1d29;border-radius:12px;padding:20px;margin-bottom:20px;border:1px solid #2a2d3a}}
.card h2{{font-size:17px;color:#7eb8ff;margin-bottom:14px;padding-bottom:8px;border-bottom:1px solid #2a2d3a}}
.pill{{font-size:12px;padding:3px 10px;border-radius:12px;margin-left:6px;font-weight:normal}}
.grid{{display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:10px;margin-bottom:14px}}
.stat{{background:#22263a;border-radius:8px;padding:11px;text-align:center}}
.stat .label{{font-size:11px;color:#888;margin-bottom:3px}}
.stat .value{{font-size:18px;font-weight:700}}
.green{{color:#4caf50}}.red{{color:#f44336}}.yellow{{color:#ffc107}}.blue{{color:#42a5f5}}
.sec{{font-size:13px;line-height:1.75;color:#c5cbe0;margin:10px 0;padding:10px 12px;background:#161a28;border-radius:8px;border-left:3px solid #3a4a6a}}
.sec b{{color:#90caf9}}
.sec.watch{{border-left-color:#ffc107}}
.sec.summary{{border-left-color:#4caf50;background:#16241a}}
.chart{{width:100%;height:480px;margin-top:12px}}
.note{{background:#1a237e;border-radius:8px;padding:14px;margin:12px 0;font-size:13px;color:#90caf9;line-height:1.7}}
.warn{{background:#4a1a1a;border-radius:8px;padding:14px;margin:12px 0;font-size:13px;color:#ffab91;line-height:1.7}}
table{{width:100%;border-collapse:collapse;font-size:13px}}
th{{background:#22263a;color:#7eb8ff;padding:8px 6px;text-align:left}}
td{{padding:8px 6px;border-bottom:1px solid #2a2d3a;vertical-align:top}}
</style></head>
<body><div class="container">
<h1>光通信·AI算力链 3股技术分析报告</h1>
<p class="subtitle">亨通光电 · 工业富联 · 光迅科技 | 数据截至 2026-07-31 | 基于AkShare日线(前复权)</p>

<div class="warn">
<b>⚠️ 板块背景</b>：这三只同属AI光通信/算力主题，近一个月集体大幅回调——亨通光电月跌-49%、光迅科技-26%、工业富联-11%。
这是典型的<b>主题炒作退潮</b>，三只均线全部空头排列。当前共同特征是"深度超卖+今日放量反弹"，
属于<b>超跌反弹博弈</b>窗口，但趋势尚未扭转，切勿当作趋势反转来重仓。
</div>

<div class="card">
<h2>📊 三股横向对比</h2>
<table>
<tr><th>维度</th><th>亨通光电</th><th>工业富联</th><th>光迅科技</th></tr>
<tr><td>收盘/当日</td><td>47.61 / +0.87%</td><td>56.70 / <b class="green">+5.39%</b></td><td>161.65 / <b class="green">+6.12%</b></td></tr>
<tr><td>月跌幅</td><td class="red">-49.3%</td><td class="red">-11.4%</td><td class="red">-25.9%</td></tr>
<tr><td>RSI(14)</td><td class="green">27.9(超卖)</td><td>40.4</td><td>37.4</td></tr>
<tr><td>KDJ J值</td><td class="green">13</td><td>20</td><td class="green">9(最低)</td></tr>
<tr><td>均线结构</td><td class="red">空头排列</td><td class="red">空头排列(收窄)</td><td class="red">空头排列(间距大)</td></tr>
<tr><td>MACD绿柱</td><td>-2.25(收敛)</td><td>-0.80(最浅)</td><td class="red">-9.48(最深)</td></tr>
<tr><td>布林分位</td><td>18%</td><td>19%</td><td class="green">14%(最低)</td></tr>
<tr><td>今日量比</td><td>1.21</td><td>1.19</td><td class="green">1.30(最高)</td></tr>
<tr><td>关键支撑</td><td>45.60</td><td>53.22</td><td>152.33</td></tr>
<tr><td>反弹第一压力</td><td>MA5=50.0</td><td>MA5=57.6</td><td>MA5=169.9</td></tr>
<tr><td>反弹弹性/风险</td><td>中/高</td><td class="green">低/低(最稳)</td><td class="yellow">高/高(最弹性)</td></tr>
</table>
<div class="note">
<b>排序建议</b>：<b>工业富联 &gt; 光迅科技 &gt; 亨通光电</b>。
工业富联跌得最浅、MACD绿柱最浅、均线间距收窄、今日放量反弹，是"超跌反弹"确定性最高的；
光迅科技超卖最极端(J=9)、弹性最大，适合激进博弈；
亨通光电跌得最惨、趋势破坏最严重，虽然RSI最低但"飞刀"风险最大，建议等右侧信号。
</div>
</div>

{cards}

<div class="card">
<h2>🎯 综合结论与操作纪律</h2>
<div class="sec summary"><b>共同结论</b>：三只均为<b>空头排列下的深度超卖反弹</b>，不是趋势反转。今日(7-31)集体放量反弹是主题崩塌后的首次修复，性质是"超跌反弹"，空间有限、需快进快出。</div>
<div class="sec"><b>① 趋势</b>：三只均线全部空头排列，MACD均在零轴下方，中期趋势向下。任何买入都只能是"抢反弹"，不能当作"抄底做趋势"。</div>
<div class="sec"><b>② 位置</b>：三只RSI均&lt;41、KDJ J值均&lt;21、布林分位均&lt;20%，全部处于超卖区，技术性反弹条件充分。亨通RSI 27.9、光迅J值9最极端。</div>
<div class="sec"><b>③ 量能</b>：今日三只均放量反弹(量比1.19~1.30)，量价初步配合，但OBV均未转正、MFI仍偏弱，资金回流尚不充分，需连续放量确认。</div>
<div class="sec watch"><b>④ 操作纪律</b>：抢反弹仓位控制在2-3成；买入后若跌破各自20日低点(亨通45.6/富联53.2/光迅152.3)无条件止损；反弹至MA5-Ma10区间(各自第一压力位)分批止盈；若明日缩量回落则反弹夭折，立即离场。</div>
</div>

<p style="text-align:center;color:#555;font-size:12px;padding:20px 0">技术分析报告 | 数据截至2026-07-31 | 仅供研究参考，不构成投资建议</p>
</div>
<script>
{chart_js}
window.addEventListener('resize',function(){{document.querySelectorAll('[id^=chart_]').forEach(function(el){{var c=echarts.getInstanceByDom(el);if(c)c.resize();}});}});
</script>
</body></html>'''

out='/Users/huangren/.qoderwork/workspace/ms9393tmwes9zvfq/outputs/光通信AI链3股_技术分析报告.html'
with open(out,'w',encoding='utf-8') as f: f.write(html)
print(f"✅ 报告已生成: {len(html)/1024:.1f} KB")
