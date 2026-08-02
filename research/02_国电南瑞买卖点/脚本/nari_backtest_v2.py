import akshare as ak
import pandas as pd
import numpy as np
import pickle, time, warnings
warnings.filterwarnings('ignore')

print("=" * 60)
print("国电南瑞(600406) 买卖点回测 v2 — Wilder RSI")
print("=" * 60)

# 1. 拉取5年日线数据
print("\n[1/5] 拉取日线数据...")
df = ak.stock_zh_a_daily(symbol="sh600406", adjust="qfq")
df['date'] = pd.to_datetime(df['date'])
df = df.set_index('date').sort_index()
df = df[df.index >= '2021-08-01']  # 近5年
print(f"  数据范围: {df.index[0].strftime('%Y-%m-%d')} ~ {df.index[-1].strftime('%Y-%m-%d')}, 共{len(df)}个交易日")

# 2. 计算技术指标 — 使用 Wilder RSI
print("\n[2/5] 计算技术指标 (Wilder RSI)...")
c = df['close'].astype(float)
h = df['high'].astype(float)
l = df['low'].astype(float)
v = df['volume'].astype(float)

# Wilder RSI (标准方法，与同花顺/东财一致)
delta = c.diff()
gain = delta.clip(lower=0)
loss = (-delta.clip(upper=0))
avg_gain = gain.ewm(alpha=1/14, min_periods=14, adjust=False).mean()
avg_loss = loss.ewm(alpha=1/14, min_periods=14, adjust=False).mean()
rs = avg_gain / avg_loss.replace(0, np.nan)
df['rsi_14'] = 100 - (100 / (1 + rs))

# 其他指标
df['ma5'] = c.rolling(5).mean()
df['ma10'] = c.rolling(10).mean()
df['ma20'] = c.rolling(20).mean()
df['ma60'] = c.rolling(60).mean()
df['ma120'] = c.rolling(120).mean()

# MACD
ema12 = c.ewm(span=12, adjust=False).mean()
ema26 = c.ewm(span=26, adjust=False).mean()
df['dif'] = ema12 - ema26
df['dea'] = df['dif'].ewm(span=9, adjust=False).mean()
df['macd'] = 2 * (df['dif'] - df['dea'])

# 布林带
df['boll_mid'] = c.rolling(20).mean()
df['boll_std'] = c.rolling(20).std()
df['boll_upper'] = df['boll_mid'] + 2 * df['boll_std']
df['boll_lower'] = df['boll_mid'] - 2 * df['boll_std']

# 量比
df['vol_ratio'] = v / v.rolling(5).mean()

# ATR
tr = pd.concat([h-l, (h-c.shift()).abs(), (l-c.shift()).abs()], axis=1).max(axis=1)
df['atr_14'] = tr.rolling(14).mean()

# 动量
df['mom_5'] = c.pct_change(5)
df['mom_10'] = c.pct_change(10)
df['mom_20'] = c.pct_change(20)

# KDJ
low_9 = l.rolling(9).min()
high_9 = h.rolling(9).max()
rsv = (c - low_9) / (high_9 - low_9).replace(0, np.nan) * 100
df['k'] = rsv.ewm(com=2, adjust=False).mean()
df['d'] = df['k'].ewm(com=2, adjust=False).mean()
df['j'] = 3 * df['k'] - 2 * df['d']

print(f"  最新RSI(14) Wilder: {df['rsi_14'].iloc[-1]:.1f}")
print(f"  最新收盘价: {c.iloc[-1]:.2f}")

# 3. 定义买卖信号
print("\n[3/5] 定义买卖信号矩阵...")

buy_signals = {
    'RSI<30': lambda d, i: d['rsi_14'].iloc[i] < 30,
    'RSI<35': lambda d, i: d['rsi_14'].iloc[i] < 35,
    'RSI<40': lambda d, i: d['rsi_14'].iloc[i] < 40,
    'RSI<45': lambda d, i: d['rsi_14'].iloc[i] < 45,
    'RSI<50': lambda d, i: d['rsi_14'].iloc[i] < 50,
    'KDJ金叉': lambda d, i: i > 0 and d['k'].iloc[i-1] < d['d'].iloc[i-1] and d['k'].iloc[i] > d['d'].iloc[i] and d['k'].iloc[i] < 50,
    'KDJ_J<20': lambda d, i: d['j'].iloc[i] < 20,
    'MACD金叉': lambda d, i: i > 0 and d['dif'].iloc[i-1] < d['dea'].iloc[i-1] and d['dif'].iloc[i] > d['dea'].iloc[i],
    'MACD零轴上金叉': lambda d, i: i > 0 and d['dif'].iloc[i-1] < d['dea'].iloc[i-1] and d['dif'].iloc[i] > d['dea'].iloc[i] and d['dif'].iloc[i] > 0,
    'MA5上穿MA20': lambda d, i: i > 0 and d['ma5'].iloc[i-1] < d['ma20'].iloc[i-1] and d['ma5'].iloc[i] > d['ma20'].iloc[i],
    'MA5上穿MA60': lambda d, i: i > 0 and d['ma5'].iloc[i-1] < d['ma60'].iloc[i-1] and d['ma5'].iloc[i] > d['ma60'].iloc[i],
    'MA20上穿MA60': lambda d, i: i > 0 and d['ma20'].iloc[i-1] < d['ma60'].iloc[i-1] and d['ma20'].iloc[i] > d['ma60'].iloc[i],
    '价格触布林下轨': lambda d, i: d['close'].iloc[i] <= d['boll_lower'].iloc[i],
    '价格触布林中轨': lambda d, i: abs(d['close'].iloc[i] - d['boll_mid'].iloc[i]) / d['boll_mid'].iloc[i] < 0.01,
    '缩量回调(量比<0.7)': lambda d, i: d['vol_ratio'].iloc[i] < 0.7 and d['close'].iloc[i] > d['ma20'].iloc[i],
    '放量突破(量比>2)': lambda d, i: d['vol_ratio'].iloc[i] > 2 and d['close'].iloc[i] > d['ma20'].iloc[i],
    '5日动量转正': lambda d, i: i > 0 and d['mom_5'].iloc[i-1] < 0 and d['mom_5'].iloc[i] > 0,
    '10日动量转正': lambda d, i: i > 0 and d['mom_10'].iloc[i-1] < 0 and d['mom_10'].iloc[i] > 0,
    '站上MA120': lambda d, i: i > 0 and d['close'].iloc[i-1] < d['ma120'].iloc[i-1] and d['close'].iloc[i] > d['ma120'].iloc[i],
    'RSI<30+MA20上': lambda d, i: d['rsi_14'].iloc[i] < 30 and d['close'].iloc[i] > d['ma20'].iloc[i],
    'RSI<35+MACD金叉': lambda d, i: d['rsi_14'].iloc[i] < 35 and i > 0 and d['dif'].iloc[i-1] < d['dea'].iloc[i-1] and d['dif'].iloc[i] > d['dea'].iloc[i],
    'KDJ金叉+RSI<50': lambda d, i: i > 0 and d['k'].iloc[i-1] < d['d'].iloc[i-1] and d['k'].iloc[i] > d['d'].iloc[i] and d['rsi_14'].iloc[i] < 50,
    '布林下轨+RSI<40': lambda d, i: d['close'].iloc[i] <= d['boll_lower'].iloc[i] and d['rsi_14'].iloc[i] < 40,
    'MA多头排列初成': lambda d, i: i > 0 and not (d['ma5'].iloc[i-1] > d['ma10'].iloc[i-1] > d['ma20'].iloc[i-1]) and (d['ma5'].iloc[i] > d['ma10'].iloc[i] > d['ma20'].iloc[i]),
}

sell_signals = {
    'RSI>70': lambda d, i: d['rsi_14'].iloc[i] > 70,
    'RSI>65': lambda d, i: d['rsi_14'].iloc[i] > 65,
    'RSI>60': lambda d, i: d['rsi_14'].iloc[i] > 60,
    'RSI>75': lambda d, i: d['rsi_14'].iloc[i] > 75,
    'RSI>80': lambda d, i: d['rsi_14'].iloc[i] > 80,
    'KDJ死叉': lambda d, i: i > 0 and d['k'].iloc[i-1] > d['d'].iloc[i-1] and d['k'].iloc[i] < d['d'].iloc[i] and d['k'].iloc[i] > 50,
    'KDJ_J>80': lambda d, i: d['j'].iloc[i] > 80,
    'MACD死叉': lambda d, i: i > 0 and d['dif'].iloc[i-1] > d['dea'].iloc[i-1] and d['dif'].iloc[i] < d['dea'].iloc[i],
    'MACD零轴下死叉': lambda d, i: i > 0 and d['dif'].iloc[i-1] > d['dea'].iloc[i-1] and d['dif'].iloc[i] < d['dea'].iloc[i] and d['dif'].iloc[i] < 0,
    'MA5下穿MA20': lambda d, i: i > 0 and d['ma5'].iloc[i-1] > d['ma20'].iloc[i-1] and d['ma5'].iloc[i] < d['ma20'].iloc[i],
    'MA5下穿MA60': lambda d, i: i > 0 and d['ma5'].iloc[i-1] > d['ma60'].iloc[i-1] and d['ma5'].iloc[i] < d['ma60'].iloc[i],
    '跌破MA20': lambda d, i: i > 0 and d['close'].iloc[i-1] > d['ma20'].iloc[i-1] and d['close'].iloc[i] < d['ma20'].iloc[i],
    '跌破MA60': lambda d, i: i > 0 and d['close'].iloc[i-1] > d['ma60'].iloc[i-1] and d['close'].iloc[i] < d['ma60'].iloc[i],
    '触布林上轨': lambda d, i: d['close'].iloc[i] >= d['boll_upper'].iloc[i],
    '放量滞涨': lambda d, i: d['vol_ratio'].iloc[i] > 2 and abs(d['close'].pct_change().iloc[i]) < 0.01,
    '5日动量转负': lambda d, i: i > 0 and d['mom_5'].iloc[i-1] > 0 and d['mom_5'].iloc[i] < 0,
    'RSI>70+MACD死叉': lambda d, i: d['rsi_14'].iloc[i] > 70 and i > 0 and d['dif'].iloc[i-1] > d['dea'].iloc[i-1] and d['dif'].iloc[i] < d['dea'].iloc[i],
    'KDJ死叉+RSI>60': lambda d, i: i > 0 and d['k'].iloc[i-1] > d['d'].iloc[i-1] and d['k'].iloc[i] < d['d'].iloc[i] and d['rsi_14'].iloc[i] > 60,
    '布林上轨+RSI>65': lambda d, i: d['close'].iloc[i] >= d['boll_upper'].iloc[i] and d['rsi_14'].iloc[i] > 65,
    'MA空头排列初成': lambda d, i: i > 0 and not (d['ma5'].iloc[i-1] < d['ma10'].iloc[i-1] < d['ma20'].iloc[i-1]) and (d['ma5'].iloc[i] < d['ma10'].iloc[i] < d['ma20'].iloc[i]),
    '跌破MA120': lambda d, i: i > 0 and d['close'].iloc[i-1] > d['ma120'].iloc[i-1] and d['close'].iloc[i] < d['ma120'].iloc[i],
    'RSI顶背离': lambda d, i: i >= 20 and d['rsi_14'].iloc[i] < d['rsi_14'].iloc[i-10] and d['close'].iloc[i] > d['close'].iloc[i-10] and d['rsi_14'].iloc[i] > 60,
    '连续3阴': lambda d, i: i >= 2 and d['close'].iloc[i] < d['close'].iloc[i-1] < d['close'].iloc[i-2] and d['close'].iloc[i-1] < d['close'].iloc[i-2],
}

print(f"  买入信号: {len(buy_signals)}种, 卖出信号: {len(sell_signals)}种")

# 4. Phase 1: 固定参数跑所有信号组合
print("\n[4/5] Phase 1: 遍历信号组合...")
sl_pct = 0.07   # 止损7%
tp_pct = 0.15   # 止盈15%
max_hold = 20   # 最长持有20天

results = []
total = len(buy_signals) * len(sell_signals)
count = 0

for bname, bfunc in buy_signals.items():
    for sname, sfunc in sell_signals.items():
        count += 1
        if count % 100 == 0:
            print(f"  进度: {count}/{total} ({count/total*100:.0f}%)")
        
        trades = []
        i = 120  # 跳过前120天(指标预热)
        while i < len(df) - 1:
            # 检查买入信号
            try:
                if not bfunc(df, i):
                    i += 1
                    continue
            except:
                i += 1
                continue
            
            entry_price = c.iloc[i]
            entry_date = df.index[i]
            exit_i = None
            exit_reason = ''
            
            # 持仓期检查
            for j in range(i+1, min(i+1+max_hold, len(df))):
                cur_price = c.iloc[j]
                ret = (cur_price - entry_price) / entry_price
                
                # 止损
                if ret <= -sl_pct:
                    exit_i = j
                    exit_reason = f'止损{ret*100:.1f}%'
                    break
                # 止盈
                if ret >= tp_pct:
                    exit_i = j
                    exit_reason = f'止盈{ret*100:.1f}%'
                    break
                # 卖出信号
                try:
                    if sfunc(df, j):
                        exit_i = j
                        exit_reason = sname
                        break
                except:
                    pass
            
            # 到期未触发
            if exit_i is None:
                exit_i = min(i + max_hold, len(df) - 1)
                exit_reason = '到期'
            
            exit_price = c.iloc[exit_i]
            trade_ret = (exit_price - entry_price) / entry_price
            hold_days = exit_i - i
            
            trades.append({
                'entry_date': entry_date,
                'exit_date': df.index[exit_i],
                'entry_price': entry_price,
                'exit_price': exit_price,
                'return': trade_ret,
                'hold_days': hold_days,
                'exit_reason': exit_reason,
            })
            
            i = exit_i + 1  # 卖出后次日才能再买
        
        if len(trades) >= 3:  # 至少3笔交易才有统计意义
            tdf = pd.DataFrame(trades)
            total_ret = (1 + tdf['return']).prod() - 1
            years = (df.index[-1] - df.index[0]).days / 365.25
            annual_ret = (1 + total_ret) ** (1/years) - 1 if years > 0 else 0
            win_rate = (tdf['return'] > 0).mean()
            max_dd = 0
            cum = 1
            peak = 1
            for r in tdf['return']:
                cum *= (1 + r)
                peak = max(peak, cum)
                dd = (cum - peak) / peak
                max_dd = min(max_dd, dd)
            
            results.append({
                'buy_signal': bname,
                'sell_signal': sname,
                'trades': len(trades),
                'total_return': total_ret,
                'annual_return': annual_ret,
                'win_rate': win_rate,
                'max_drawdown': max_dd,
                'avg_hold': tdf['hold_days'].mean(),
                'avg_return': tdf['return'].mean(),
                'trade_list': trades,
            })

print(f"\n  有效策略组合: {len(results)}个 (至少3笔交易)")

# 排序
results.sort(key=lambda x: x['annual_return'], reverse=True)

# 5. Phase 2: Top50策略 × 参数网格
print("\n[5/5] Phase 2: Top50 × 参数网格...")
top50 = results[:50]
param_grid = [
    (0.05, 0.10, 15),
    (0.05, 0.15, 20),
    (0.05, 0.20, 25),
    (0.07, 0.10, 15),
    (0.07, 0.15, 20),
    (0.07, 0.20, 25),
    (0.07, 0.25, 30),
    (0.10, 0.15, 20),
    (0.10, 0.20, 25),
    (0.10, 0.25, 30),
    (0.10, 0.30, 30),
]

grid_results = []
for strat in top50:
    bname = strat['buy_signal']
    sname = strat['sell_signal']
    bfunc = buy_signals[bname]
    sfunc = sell_signals[sname]
    
    for sl, tp, mh in param_grid:
        trades = []
        i = 120
        while i < len(df) - 1:
            try:
                if not bfunc(df, i):
                    i += 1
                    continue
            except:
                i += 1
                continue
            
            entry_price = c.iloc[i]
            entry_date = df.index[i]
            exit_i = None
            exit_reason = ''
            
            for j in range(i+1, min(i+1+mh, len(df))):
                cur_price = c.iloc[j]
                ret = (cur_price - entry_price) / entry_price
                if ret <= -sl:
                    exit_i = j; exit_reason = f'止损{ret*100:.1f}%'; break
                if ret >= tp:
                    exit_i = j; exit_reason = f'止盈{ret*100:.1f}%'; break
                try:
                    if sfunc(df, j):
                        exit_i = j; exit_reason = sname; break
                except:
                    pass
            
            if exit_i is None:
                exit_i = min(i + mh, len(df) - 1)
                exit_reason = '到期'
            
            exit_price = c.iloc[exit_i]
            trade_ret = (exit_price - entry_price) / entry_price
            trades.append({
                'entry_date': entry_date,
                'exit_date': df.index[exit_i],
                'entry_price': entry_price,
                'exit_price': exit_price,
                'return': trade_ret,
                'hold_days': exit_i - i,
                'exit_reason': exit_reason,
            })
            i = exit_i + 1
        
        if len(trades) >= 3:
            tdf = pd.DataFrame(trades)
            total_ret = (1 + tdf['return']).prod() - 1
            years = (df.index[-1] - df.index[0]).days / 365.25
            annual_ret = (1 + total_ret) ** (1/years) - 1 if years > 0 else 0
            win_rate = (tdf['return'] > 0).mean()
            max_dd = 0
            cum = 1; peak = 1
            for r in tdf['return']:
                cum *= (1 + r)
                peak = max(peak, cum)
                max_dd = min(max_dd, (cum - peak) / peak)
            
            grid_results.append({
                'buy_signal': bname,
                'sell_signal': sname,
                'sl': sl, 'tp': tp, 'max_hold': mh,
                'trades': len(trades),
                'total_return': total_ret,
                'annual_return': annual_ret,
                'win_rate': win_rate,
                'max_drawdown': max_dd,
                'avg_hold': tdf['hold_days'].mean(),
                'avg_return': tdf['return'].mean(),
                'trade_list': trades,
            })

grid_results.sort(key=lambda x: x['annual_return'], reverse=True)
print(f"  参数网格结果: {len(grid_results)}个有效组合")

# 保存
with open('/tmp/mc_cache/nari_results_v2.pkl', 'wb') as f:
    pickle.dump({
        'phase1': results,
        'phase2': grid_results,
        'df': df,
        'latest_rsi': df['rsi_14'].iloc[-1],
        'latest_close': c.iloc[-1],
    }, f)

print("\n" + "=" * 60)
print("Phase 1 Top 10 (固定参数 SL7%/TP15%/20日):")
print("=" * 60)
for i, r in enumerate(results[:10]):
    print(f"  #{i+1} {r['buy_signal']} → {r['sell_signal']}")
    print(f"      年化{r['annual_return']*100:+.1f}% | 胜率{r['win_rate']*100:.0f}% | 回撤{r['max_drawdown']*100:.1f}% | {r['trades']}笔 | 均持{r['avg_hold']:.0f}日")

print("\n" + "=" * 60)
print("Phase 2 Top 10 (参数优化后):")
print("=" * 60)
for i, r in enumerate(grid_results[:10]):
    print(f"  #{i+1} {r['buy_signal']} → {r['sell_signal']} [SL{r['sl']*100:.0f}%/TP{r['tp']*100:.0f}%/{r['max_hold']}日]")
    print(f"      年化{r['annual_return']*100:+.1f}% | 胜率{r['win_rate']*100:.0f}% | 回撤{r['max_drawdown']*100:.1f}% | {r['trades']}笔 | 均持{r['avg_hold']:.0f}日")

print("\n✅ 完成! 结果已保存到 /tmp/mc_cache/nari_results_v2.pkl")
