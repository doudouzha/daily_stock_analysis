import akshare as ak
import pandas as pd
import numpy as np
import pickle, warnings
warnings.filterwarnings('ignore')

STOCKS = {
    'sz002415': '海康威视',
    'sz002475': '立讯精密',
    'sz000725': '京东方A',
    'sz000063': '中兴通讯',
}

def calc_indicators(df):
    c = df['close'].astype(float)
    h = df['high'].astype(float)
    l = df['low'].astype(float)
    v = df['volume'].astype(float)
    # Wilder RSI
    delta = c.diff()
    gain = delta.clip(lower=0)
    loss = (-delta.clip(upper=0))
    ag = gain.ewm(alpha=1/14, min_periods=14, adjust=False).mean()
    al = loss.ewm(alpha=1/14, min_periods=14, adjust=False).mean()
    rs = ag / al.replace(0, np.nan)
    df['rsi_14'] = 100 - (100 / (1 + rs))
    df['ma5'] = c.rolling(5).mean()
    df['ma10'] = c.rolling(10).mean()
    df['ma20'] = c.rolling(20).mean()
    df['ma60'] = c.rolling(60).mean()
    df['ma120'] = c.rolling(120).mean()
    ema12 = c.ewm(span=12, adjust=False).mean()
    ema26 = c.ewm(span=26, adjust=False).mean()
    df['dif'] = ema12 - ema26
    df['dea'] = df['dif'].ewm(span=9, adjust=False).mean()
    df['boll_mid'] = c.rolling(20).mean()
    bstd = c.rolling(20).std()
    df['boll_upper'] = df['boll_mid'] + 2*bstd
    df['boll_lower'] = df['boll_mid'] - 2*bstd
    df['vol_ratio'] = v / v.rolling(5).mean()
    df['mom_5'] = c.pct_change(5)
    df['mom_10'] = c.pct_change(10)
    low9 = l.rolling(9).min(); high9 = h.rolling(9).max()
    rsv = (c - low9) / (high9 - low9).replace(0, np.nan) * 100
    df['k'] = rsv.ewm(com=2, adjust=False).mean()
    df['d'] = df['k'].ewm(com=2, adjust=False).mean()
    df['j'] = 3*df['k'] - 2*df['d']
    return df

BUY_SIGNALS = {
    'RSI<30': lambda d,i: d['rsi_14'].iloc[i] < 30,
    'RSI<35': lambda d,i: d['rsi_14'].iloc[i] < 35,
    'RSI<40': lambda d,i: d['rsi_14'].iloc[i] < 40,
    'RSI<45': lambda d,i: d['rsi_14'].iloc[i] < 45,
    'RSI<50': lambda d,i: d['rsi_14'].iloc[i] < 50,
    'KDJ金叉': lambda d,i: i>0 and d['k'].iloc[i-1]<d['d'].iloc[i-1] and d['k'].iloc[i]>d['d'].iloc[i] and d['k'].iloc[i]<50,
    'KDJ_J<20': lambda d,i: d['j'].iloc[i] < 20,
    'MACD金叉': lambda d,i: i>0 and d['dif'].iloc[i-1]<d['dea'].iloc[i-1] and d['dif'].iloc[i]>d['dea'].iloc[i],
    'MACD零上金叉': lambda d,i: i>0 and d['dif'].iloc[i-1]<d['dea'].iloc[i-1] and d['dif'].iloc[i]>d['dea'].iloc[i] and d['dif'].iloc[i]>0,
    'MA5上穿MA20': lambda d,i: i>0 and d['ma5'].iloc[i-1]<d['ma20'].iloc[i-1] and d['ma5'].iloc[i]>d['ma20'].iloc[i],
    'MA5上穿MA60': lambda d,i: i>0 and d['ma5'].iloc[i-1]<d['ma60'].iloc[i-1] and d['ma5'].iloc[i]>d['ma60'].iloc[i],
    'MA20上穿MA60': lambda d,i: i>0 and d['ma20'].iloc[i-1]<d['ma60'].iloc[i-1] and d['ma20'].iloc[i]>d['ma60'].iloc[i],
    '触布林下轨': lambda d,i: d['close'].iloc[i] <= d['boll_lower'].iloc[i],
    '触布林中轨': lambda d,i: abs(d['close'].iloc[i]-d['boll_mid'].iloc[i])/d['boll_mid'].iloc[i] < 0.01,
    '缩量回调': lambda d,i: d['vol_ratio'].iloc[i]<0.7 and d['close'].iloc[i]>d['ma20'].iloc[i],
    '放量突破': lambda d,i: d['vol_ratio'].iloc[i]>2 and d['close'].iloc[i]>d['ma20'].iloc[i],
    '5日动量转正': lambda d,i: i>0 and d['mom_5'].iloc[i-1]<0 and d['mom_5'].iloc[i]>0,
    '10日动量转正': lambda d,i: i>0 and d['mom_10'].iloc[i-1]<0 and d['mom_10'].iloc[i]>0,
    '站上MA120': lambda d,i: i>0 and d['close'].iloc[i-1]<d['ma120'].iloc[i-1] and d['close'].iloc[i]>d['ma120'].iloc[i],
    'RSI<35+MACD金叉': lambda d,i: d['rsi_14'].iloc[i]<35 and i>0 and d['dif'].iloc[i-1]<d['dea'].iloc[i-1] and d['dif'].iloc[i]>d['dea'].iloc[i],
    'KDJ金叉+RSI<50': lambda d,i: i>0 and d['k'].iloc[i-1]<d['d'].iloc[i-1] and d['k'].iloc[i]>d['d'].iloc[i] and d['rsi_14'].iloc[i]<50,
    '布林下轨+RSI<40': lambda d,i: d['close'].iloc[i]<=d['boll_lower'].iloc[i] and d['rsi_14'].iloc[i]<40,
    'MA多头初成': lambda d,i: i>0 and not(d['ma5'].iloc[i-1]>d['ma10'].iloc[i-1]>d['ma20'].iloc[i-1]) and (d['ma5'].iloc[i]>d['ma10'].iloc[i]>d['ma20'].iloc[i]),
}

SELL_SIGNALS = {
    'RSI>70': lambda d,i: d['rsi_14'].iloc[i] > 70,
    'RSI>65': lambda d,i: d['rsi_14'].iloc[i] > 65,
    'RSI>60': lambda d,i: d['rsi_14'].iloc[i] > 60,
    'RSI>75': lambda d,i: d['rsi_14'].iloc[i] > 75,
    'RSI>80': lambda d,i: d['rsi_14'].iloc[i] > 80,
    'KDJ死叉': lambda d,i: i>0 and d['k'].iloc[i-1]>d['d'].iloc[i-1] and d['k'].iloc[i]<d['d'].iloc[i] and d['k'].iloc[i]>50,
    'KDJ_J>80': lambda d,i: d['j'].iloc[i] > 80,
    'MACD死叉': lambda d,i: i>0 and d['dif'].iloc[i-1]>d['dea'].iloc[i-1] and d['dif'].iloc[i]<d['dea'].iloc[i],
    'MACD零下死叉': lambda d,i: i>0 and d['dif'].iloc[i-1]>d['dea'].iloc[i-1] and d['dif'].iloc[i]<d['dea'].iloc[i] and d['dif'].iloc[i]<0,
    'MA5下穿MA20': lambda d,i: i>0 and d['ma5'].iloc[i-1]>d['ma20'].iloc[i-1] and d['ma5'].iloc[i]<d['ma20'].iloc[i],
    'MA5下穿MA60': lambda d,i: i>0 and d['ma5'].iloc[i-1]>d['ma60'].iloc[i-1] and d['ma5'].iloc[i]<d['ma60'].iloc[i],
    '跌破MA20': lambda d,i: i>0 and d['close'].iloc[i-1]>d['ma20'].iloc[i-1] and d['close'].iloc[i]<d['ma20'].iloc[i],
    '跌破MA60': lambda d,i: i>0 and d['close'].iloc[i-1]>d['ma60'].iloc[i-1] and d['close'].iloc[i]<d['ma60'].iloc[i],
    '触布林上轨': lambda d,i: d['close'].iloc[i] >= d['boll_upper'].iloc[i],
    '放量滞涨': lambda d,i: d['vol_ratio'].iloc[i]>2 and abs(d['close'].pct_change().iloc[i])<0.01,
    '5日动量转负': lambda d,i: i>0 and d['mom_5'].iloc[i-1]>0 and d['mom_5'].iloc[i]<0,
    'RSI>70+MACD死叉': lambda d,i: d['rsi_14'].iloc[i]>70 and i>0 and d['dif'].iloc[i-1]>d['dea'].iloc[i-1] and d['dif'].iloc[i]<d['dea'].iloc[i],
    'KDJ死叉+RSI>60': lambda d,i: i>0 and d['k'].iloc[i-1]>d['d'].iloc[i-1] and d['k'].iloc[i]<d['d'].iloc[i] and d['rsi_14'].iloc[i]>60,
    '布林上轨+RSI>65': lambda d,i: d['close'].iloc[i]>=d['boll_upper'].iloc[i] and d['rsi_14'].iloc[i]>65,
    'MA空头初成': lambda d,i: i>0 and not(d['ma5'].iloc[i-1]<d['ma10'].iloc[i-1]<d['ma20'].iloc[i-1]) and (d['ma5'].iloc[i]<d['ma10'].iloc[i]<d['ma20'].iloc[i]),
    '跌破MA120': lambda d,i: i>0 and d['close'].iloc[i-1]>d['ma120'].iloc[i-1] and d['close'].iloc[i]<d['ma120'].iloc[i],
    'RSI顶背离': lambda d,i: i>=20 and d['rsi_14'].iloc[i]<d['rsi_14'].iloc[i-10] and d['close'].iloc[i]>d['close'].iloc[i-10] and d['rsi_14'].iloc[i]>60,
    '连续3阴': lambda d,i: i>=2 and d['close'].iloc[i]<d['close'].iloc[i-1]<d['close'].iloc[i-2],
}

def run_backtest(df, sl, tp, mh, bfunc, sfunc):
    c = df['close'].astype(float)
    trades = []
    i = 120
    while i < len(df) - 1:
        try:
            if not bfunc(df, i):
                i += 1; continue
        except:
            i += 1; continue
        ep = c.iloc[i]; ed = df.index[i]
        xi = None; reason = ''
        for j in range(i+1, min(i+1+mh, len(df))):
            r = (c.iloc[j]-ep)/ep
            if r <= -sl: xi=j; reason=f'止损{r*100:.1f}%'; break
            if r >= tp: xi=j; reason=f'止盈{r*100:.1f}%'; break
            try:
                if sfunc(df, j): xi=j; reason='signal'; break
            except: pass
        if xi is None:
            xi = min(i+mh, len(df)-1); reason='到期'
        xp = c.iloc[xi]
        trades.append({'entry_date':ed,'exit_date':df.index[xi],'entry_price':ep,'exit_price':xp,
                       'return':(xp-ep)/ep,'hold_days':xi-i,'exit_reason':reason})
        i = xi + 1
    return trades

def summarize(trades, df):
    if len(trades) < 3: return None
    tdf = pd.DataFrame(trades)
    tr = (1+tdf['return']).prod()-1
    years = (df.index[-1]-df.index[0]).days/365.25
    ar = (1+tr)**(1/years)-1 if years>0 else 0
    wr = (tdf['return']>0).mean()
    cum=1; peak=1; mdd=0
    for r in tdf['return']:
        cum*=(1+r); peak=max(peak,cum); mdd=min(mdd,(cum-peak)/peak)
    return {'trades':len(trades),'total_return':tr,'annual_return':ar,'win_rate':wr,
            'max_drawdown':mdd,'avg_hold':tdf['hold_days'].mean(),'avg_return':tdf['return'].mean(),'trade_list':trades}

PARAM_GRID = [
    (0.05,0.10,15),(0.05,0.15,20),(0.05,0.20,25),
    (0.07,0.10,15),(0.07,0.15,20),(0.07,0.20,25),(0.07,0.25,30),
    (0.10,0.15,20),(0.10,0.20,25),(0.10,0.25,30),(0.10,0.30,30),
]

all_results = {}
for code, name in STOCKS.items():
    print(f"\n{'='*55}\n处理 {name}({code})...\n{'='*55}")
    df = ak.stock_zh_a_daily(symbol=code, adjust="qfq")
    df['date'] = pd.to_datetime(df['date'])
    df = df.set_index('date').sort_index()
    df = df[df.index >= '2021-08-01']
    df = calc_indicators(df)
    c = df['close'].astype(float)
    print(f"  数据: {df.index[0].strftime('%Y-%m-%d')}~{df.index[-1].strftime('%Y-%m-%d')} {len(df)}日 | 收盘{c.iloc[-1]:.2f} | RSI {df['rsi_14'].iloc[-1]:.1f}")

    # Phase 1
    p1 = []
    for bn, bf in BUY_SIGNALS.items():
        for sn, sf in SELL_SIGNALS.items():
            tr = run_backtest(df, 0.07, 0.15, 20, bf, sf)
            s = summarize(tr, df)
            if s:
                s['buy_signal']=bn; s['sell_signal']=sn; p1.append(s)
    p1.sort(key=lambda x:x['annual_return'], reverse=True)
    print(f"  Phase1有效组合: {len(p1)}")

    # Phase 2: Top40 × grid
    p2 = []
    for strat in p1[:40]:
        bf = BUY_SIGNALS[strat['buy_signal']]; sf = SELL_SIGNALS[strat['sell_signal']]
        for sl,tp,mh in PARAM_GRID:
            tr = run_backtest(df, sl, tp, mh, bf, sf)
            s = summarize(tr, df)
            if s:
                s.update({'buy_signal':strat['buy_signal'],'sell_signal':strat['sell_signal'],'sl':sl,'tp':tp,'max_hold':mh})
                p2.append(s)
    p2.sort(key=lambda x:x['annual_return'], reverse=True)
    print(f"  Phase2有效组合: {len(p2)}")
    if p2:
        b = p2[0]
        print(f"  ★最优: {b['buy_signal']}→{b['sell_signal']} [SL{b['sl']*100:.0f}%/TP{b['tp']*100:.0f}%/{b['max_hold']}日] 年化{b['annual_return']*100:+.1f}% 胜率{b['win_rate']*100:.0f}% 回撤{b['max_drawdown']*100:.1f}% {b['trades']}笔")

    all_results[code] = {'name':name,'df':df,'phase1':p1,'phase2':p2,
                         'latest_rsi':df['rsi_14'].iloc[-1],'latest_close':c.iloc[-1]}

with open('/tmp/mc_cache/tech4_results.pkl','wb') as f:
    pickle.dump(all_results, f)
print("\n✅ 全部完成，已保存 /tmp/mc_cache/tech4_results.pkl")
