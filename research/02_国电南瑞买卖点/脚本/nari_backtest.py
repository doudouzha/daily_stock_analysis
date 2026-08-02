"""
国电南瑞(600406) · 1000种买卖点组合回测 + 蒙特卡洛最优策略
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
5年日线 | ~32种买入信号 × ~32种卖出信号 ≈ 1024组合
"""
import akshare as ak
import pandas as pd
import numpy as np
import time
import pickle
import os
import warnings
from itertools import product
warnings.filterwarnings('ignore')

CACHE_DIR = '/tmp/mc_cache'
os.makedirs(CACHE_DIR, exist_ok=True)
OUTPUT_DIR = '/Users/huangren/.qoderwork/workspace/ms9393tmwes9zvfq/outputs'

# ============ Step 1: 拉取5年数据 ============
print("=" * 70)
print("  国电南瑞(600406) · 1000种买卖点 · 蒙特卡洛最优")
print("=" * 70)

print("\n[Step 1] 拉取5年日线数据...")
df = ak.stock_zh_a_daily(symbol='sh600406', start_date='20210801', end_date='20260801', adjust='qfq')
if not isinstance(df.index, pd.DatetimeIndex):
    if 'date' in df.columns:
        df['date'] = pd.to_datetime(df['date'])
        df = df.set_index('date')
for col in ['open','high','low','close','volume']:
    df[col] = df[col].astype(float)

print(f"  数据: {len(df)} 天 ({df.index[0].strftime('%Y-%m-%d')} ~ {df.index[-1].strftime('%Y-%m-%d')})")
print(f"  价格: {df['close'].iloc[0]:.2f} → {df['close'].iloc[-1]:.2f}")

# ============ Step 2: 计算技术指标 ============
print("\n[Step 2] 计算技术指标...")
c, h, l, v = df['close'], df['high'], df['low'], df['volume']

# RSI
delta = c.diff()
gain = delta.clip(lower=0).rolling(14).mean()
loss = (-delta.clip(upper=0)).rolling(14).mean()
rs = gain / loss.replace(0, np.nan)
df['rsi'] = 100 - (100 / (1 + rs))

# MA
for period in [5, 10, 20, 60, 120]:
    df[f'ma{period}'] = c.rolling(period).mean()

# Bollinger
df['boll_mid'] = c.rolling(20).mean()
df['boll_std'] = c.rolling(20).std()
df['boll_upper'] = df['boll_mid'] + 2 * df['boll_std']
df['boll_lower'] = df['boll_mid'] - 2 * df['boll_std']
df['boll_pos'] = (c - df['boll_lower']) / (df['boll_upper'] - df['boll_lower'])

# MACD
ema12 = c.ewm(span=12).mean()
ema26 = c.ewm(span=26).mean()
df['macd_dif'] = ema12 - ema26
df['macd_dea'] = df['macd_dif'].ewm(span=9).mean()
df['macd_hist'] = df['macd_dif'] - df['macd_dea']

# 动量
df['mom_5'] = c.pct_change(5)
df['mom_10'] = c.pct_change(10)
df['mom_20'] = c.pct_change(20)

# 量比
df['vol_ratio'] = v / v.rolling(5).mean()
df['vol_ma5'] = v.rolling(5).mean()
df['vol_ma20'] = v.rolling(20).mean()

# N日最低/最高
for n in [5, 10, 20, 60]:
    df[f'low_{n}'] = l.rolling(n).min()
    df[f'high_{n}'] = h.rolling(n).max()

# 乖离率
df['bias_20'] = (c - df['ma20']) / df['ma20']
df['bias_60'] = (c - df['ma60']) / df['ma60']

# ATR
tr = pd.concat([h-l, (h-c.shift()).abs(), (l-c.shift()).abs()], axis=1).max(axis=1)
df['atr_14'] = tr.rolling(14).mean()

print(f"  指标计算完成，有效行数: {df.dropna().shape[0]}")

# ============ Step 3: 定义买卖信号 ============
print("\n[Step 3] 定义买卖信号矩阵...")

# 买入信号（返回布尔Series）
def buy_signals(df):
    signals = {}
    # RSI超卖
    for th in [20, 25, 30, 35, 40]:
        signals[f'RSI<{th}'] = df['rsi'] < th
    # 布林带位置
    for th in [0.0, 0.1, 0.2]:
        signals[f'BOLL<{th}'] = df['boll_pos'] < th
    # 价格触及N日低点
    for n in [10, 20, 60]:
        signals[f'触{n}日低'] = df['close'] <= df[f'low_{n}'] * 1.01
    # 均线支撑反弹（价格从下方穿越MA）
    for ma in [20, 60, 120]:
        signals[f'穿MA{ma}'] = (df['close'] > df[f'ma{ma}']) & (df['close'].shift(1) <= df[f'ma{ma}'].shift(1))
    # MACD金叉
    signals['MACD金叉'] = (df['macd_dif'] > df['macd_dea']) & (df['macd_dif'].shift(1) <= df['macd_dea'].shift(1))
    # 动量反转（5日动量从负转正）
    signals['动量反转5'] = (df['mom_5'] > 0) & (df['mom_5'].shift(1) <= 0)
    signals['动量反转10'] = (df['mom_10'] > 0) & (df['mom_10'].shift(1) <= 0)
    # 缩量后放量（量比>1.5且前一日<0.8）
    signals['缩量放量'] = (df['vol_ratio'] > 1.5) & (df['vol_ratio'].shift(1) < 0.8)
    # 乖离率超跌
    for th in [-0.08, -0.05, -0.03]:
        signals[f'乖离20<{th}'] = df['bias_20'] < th
    # 连续下跌后企稳（连跌3天后收阳）
    signals['连跌3后阳'] = (df['close'] > df['open']) & (df['close'].shift(1) < df['open'].shift(1)) & (df['close'].shift(2) < df['open'].shift(2)) & (df['close'].shift(3) < df['open'].shift(3))
    # 价格回踩MA20不破
    signals['回踩MA20'] = (df['low'] <= df['ma20'] * 1.01) & (df['close'] > df['ma20'])
    # 放量突破MA60
    signals['放量穿MA60'] = (df['close'] > df['ma60']) & (df['close'].shift(1) <= df['ma60'].shift(1)) & (df['vol_ratio'] > 1.3)
    return signals

# 卖出信号
def sell_signals(df):
    signals = {}
    # RSI超买
    for th in [60, 65, 70, 75, 80]:
        signals[f'RSI>{th}'] = df['rsi'] > th
    # 布林带高位
    for th in [0.8, 0.9, 1.0]:
        signals[f'BOLL>{th}'] = df['boll_pos'] > th
    # 价格触及N日高点
    for n in [10, 20, 60]:
        signals[f'触{n}日高'] = df['close'] >= df[f'high_{n}'] * 0.99
    # 均线破位
    for ma in [5, 10, 20]:
        signals[f'破MA{ma}'] = (df['close'] < df[f'ma{ma}']) & (df['close'].shift(1) >= df[f'ma{ma}'].shift(1))
    # MACD死叉
    signals['MACD死叉'] = (df['macd_dif'] < df['macd_dea']) & (df['macd_dif'].shift(1) >= df['macd_dea'].shift(1))
    # 动量转负
    signals['动量转负5'] = (df['mom_5'] < 0) & (df['mom_5'].shift(1) >= 0)
    signals['动量转负10'] = (df['mom_10'] < 0) & (df['mom_10'].shift(1) >= 0)
    # 乖离率超涨
    for th in [0.05, 0.08, 0.12]:
        signals[f'乖离20>{th}'] = df['bias_20'] > th
    # 放量滞涨（量比>2但涨幅<1%）
    signals['放量滞涨'] = (df['vol_ratio'] > 2) & (df['close'].pct_change() < 0.01)
    # 长上影线
    signals['长上影'] = (df['high'] - df[['open','close']].max(axis=1)) > 2 * (df['close'] - df['open']).abs()
    # 连续上涨后收阴
    signals['连涨3后阴'] = (df['close'] < df['open']) & (df['close'].shift(1) > df['open'].shift(1)) & (df['close'].shift(2) > df['open'].shift(2)) & (df['close'].shift(3) > df['open'].shift(3))
    return signals

buy_sigs = buy_signals(df)
sell_sigs = sell_signals(df)
print(f"  买入信号: {len(buy_sigs)} 种")
print(f"  卖出信号: {len(sell_sigs)} 种")
print(f"  组合总数: {len(buy_sigs) * len(sell_sigs)} 种")

# 固定止损/止盈/时间止损（附加卖出条件）
STOP_LOSSES = [0.05, 0.07, 0.10, 0.15]  # 止损比例
TAKE_PROFITS = [0.10, 0.15, 0.20, 0.30, 0.50]  # 止盈比例
TIME_STOPS = [5, 10, 15, 20, 30]  # 最大持有天数

# ============ Step 4: 回测引擎 ============
print("\n[Step 4] 遍历回测...")

# 预处理：去掉前120天（指标预热）
valid_df = df.iloc[120:].copy()
dates = valid_df.index.tolist()
closes = valid_df['close'].values
n_days = len(dates)

def backtest_combo(buy_mask, sell_mask, stop_loss, take_profit, time_stop):
    """回测单个买卖组合"""
    trades = []
    in_position = False
    entry_idx = 0
    entry_price = 0
    
    for i in range(n_days):
        if not in_position:
            if buy_mask[i]:
                in_position = True
                entry_idx = i
                entry_price = closes[i]
        else:
            hold_days = i - entry_idx
            current_ret = (closes[i] - entry_price) / entry_price
            
            # 检查卖出条件
            sell = False
            sell_reason = ''
            
            # 止损
            if current_ret <= -stop_loss:
                sell = True
                sell_reason = 'stop_loss'
            # 止盈
            elif current_ret >= take_profit:
                sell = True
                sell_reason = 'take_profit'
            # 时间止损
            elif hold_days >= time_stop:
                sell = True
                sell_reason = 'time_stop'
            # 信号卖出
            elif sell_mask[i]:
                sell = True
                sell_reason = 'signal'
            
            if sell:
                trades.append({
                    'entry_date': dates[entry_idx],
                    'exit_date': dates[i],
                    'entry_price': entry_price,
                    'exit_price': closes[i],
                    'return': current_ret,
                    'hold_days': hold_days,
                    'reason': sell_reason
                })
                in_position = False
    
    if len(trades) < 3:
        return None
    
    rets = [t['return'] for t in trades]
    total_ret = np.prod([1+r for r in rets]) - 1
    years = (dates[-1] - dates[0]).days / 365
    annual_ret = (1 + total_ret) ** (1/years) - 1 if years > 0 else 0
    win_rate = np.mean([r > 0 for r in rets])
    avg_ret = np.mean(rets)
    avg_hold = np.mean([t['hold_days'] for t in trades])
    
    # 最大回撤（基于交易序列）
    cum = np.cumprod([1+r for r in rets])
    peak = np.maximum.accumulate(cum)
    max_dd = np.min((cum - peak) / peak)
    
    return {
        'n_trades': len(trades),
        'total_return': total_ret,
        'annual_return': annual_ret,
        'win_rate': win_rate,
        'avg_return': avg_ret,
        'avg_hold_days': avg_hold,
        'max_drawdown': max_dd,
        'trades': trades
    }

# 遍历所有组合
results = []
combo_count = 0
total_combos = len(buy_sigs) * len(sell_sigs) * len(STOP_LOSSES) * len(TAKE_PROFITS) * len(TIME_STOPS)

# 为了控制在合理范围，采样组合
# 全量: 32 × 30 × 4 × 5 × 5 = 96000 太多
# 策略：固定止损0.07/止盈0.20/时间20，先跑信号组合 32×30=960
# 然后对Top50跑不同止损止盈参数

print(f"  Phase 1: 信号组合回测 (固定SL=7%/TP=20%/T=20天)...")
phase1_results = []
for buy_name, buy_mask in buy_sigs.items():
    buy_arr = buy_mask.iloc[120:].values.astype(bool)
    for sell_name, sell_mask in sell_sigs.items():
        sell_arr = sell_mask.iloc[120:].values.astype(bool)
        bt = backtest_combo(buy_arr, sell_arr, 0.07, 0.20, 20)
        if bt:
            phase1_results.append({
                'buy': buy_name, 'sell': sell_name,
                'sl': 0.07, 'tp': 0.20, 'ts': 20,
                **bt
            })
        combo_count += 1

print(f"  Phase 1 完成: {len(phase1_results)} 有效组合")

# Phase 2: Top50组合 × 不同参数
phase1_results.sort(key=lambda x: x['annual_return'], reverse=True)
top50 = phase1_results[:50]

print(f"  Phase 2: Top50 × 参数网格...")
phase2_results = []
for item in top50:
    buy_arr = buy_sigs[item['buy']].iloc[120:].values.astype(bool)
    sell_arr = sell_sigs[item['sell']].iloc[120:].values.astype(bool)
    for sl in STOP_LOSSES:
        for tp in TAKE_PROFITS:
            for ts in TIME_STOPS:
                bt = backtest_combo(buy_arr, sell_arr, sl, tp, ts)
                if bt:
                    phase2_results.append({
                        'buy': item['buy'], 'sell': item['sell'],
                        'sl': sl, 'tp': tp, 'ts': ts,
                        **bt
                    })

print(f"  Phase 2 完成: {len(phase2_results)} 有效组合")

# 合并所有结果
all_results = phase1_results + phase2_results
all_results.sort(key=lambda x: x['annual_return'], reverse=True)
print(f"\n  总有效组合: {len(all_results)}")

# ============ Step 5: 蒙特卡洛 ============
print(f"\n[Step 5] 蒙特卡洛模拟...")

# 用所有组合的交易收益作为样本池
all_trade_returns = []
for r in all_results:
    all_trade_returns.extend([t['return'] for t in r['trades']])
all_trade_returns = np.array(all_trade_returns)
print(f"  交易样本池: {len(all_trade_returns)} 笔")
print(f"  均值: {np.mean(all_trade_returns)*100:.3f}% | 标准差: {np.std(all_trade_returns)*100:.3f}%")

# MC模拟：模拟1000种随机策略路径
N_MC = 1000
TRADES_PER_YEAR = 15  # 平均每年交易次数
SIM_YEARS = 5
TOTAL_TRADES = TRADES_PER_YEAR * SIM_YEARS

np.random.seed(42)
mc_final = np.zeros(N_MC)
mc_max_dd = np.zeros(N_MC)
mc_win_rates = np.zeros(N_MC)

for i in range(N_MC):
    sampled = np.random.choice(all_trade_returns, size=TOTAL_TRADES, replace=True)
    cum = np.cumprod(1 + sampled)
    mc_final[i] = cum[-1] - 1
    peak = np.maximum.accumulate(cum)
    dd = (cum - peak) / peak
    mc_max_dd[i] = np.min(dd)
    mc_win_rates[i] = np.mean(sampled > 0)

mc_annual = (1 + mc_final) ** (1/SIM_YEARS) - 1

print(f"\n  ═══ 蒙特卡洛（1000路径 × 5年） ═══")
print(f"  年化 P5:  {np.percentile(mc_annual, 5)*100:.2f}%")
print(f"  年化 P25: {np.percentile(mc_annual, 25)*100:.2f}%")
print(f"  年化 P50: {np.percentile(mc_annual, 50)*100:.2f}%")
print(f"  年化 P75: {np.percentile(mc_annual, 75)*100:.2f}%")
print(f"  年化 P95: {np.percentile(mc_annual, 95)*100:.2f}%")
print(f"  最大回撤 P50: {np.percentile(mc_max_dd, 50)*100:.2f}%")
print(f"  5年亏损概率: {np.mean(mc_final < 0)*100:.1f}%")

# ============ Step 6: 输出Top20最优策略 ============
print(f"\n[Step 6] Top 20 最优买卖策略:")
print(f"{'排名':<4}{'买入信号':<14}{'卖出信号':<14}{'SL':>5}{'TP':>5}{'T':>4}{'年化':>8}{'胜率':>6}{'交易':>4}{'回撤':>8}")
print("─" * 76)
for i, r in enumerate(all_results[:20]):
    print(f"{i+1:<4}{r['buy']:<14}{r['sell']:<14}{r['sl']:>4.0%}{r['tp']:>5.0%}{r['ts']:>4}{r['annual_return']*100:>+7.1f}%{r['win_rate']*100:>5.0f}%{r['n_trades']:>4}{r['max_drawdown']*100:>7.1f}%")

# 最优策略详情
best = all_results[0]
print(f"\n  ═══ 最优策略 ═══")
print(f"  买入: {best['buy']}")
print(f"  卖出: {best['sell']}")
print(f"  止损: {best['sl']:.0%} | 止盈: {best['tp']:.0%} | 时间止损: {best['ts']}天")
print(f"  年化: {best['annual_return']*100:+.1f}% | 胜率: {best['win_rate']*100:.0f}% | 交易: {best['n_trades']}笔")
print(f"  平均持有: {best['avg_hold_days']:.1f}天 | 平均收益: {best['avg_return']*100:.2f}%/笔")
print(f"  最大回撤: {best['max_drawdown']*100:.1f}%")

# 保存
output = {
    'all_results': all_results[:200],  # Top200
    'mc_annual': mc_annual.tolist(),
    'mc_max_dd': mc_max_dd.tolist(),
    'mc_final': mc_final.tolist(),
    'all_trade_returns': all_trade_returns.tolist(),
    'best': best,
    'stock_info': {
        'code': '600406', 'name': '国电南瑞',
        'start': str(dates[0])[:10], 'end': str(dates[-1])[:10],
        'n_days': n_days, 'price_start': float(closes[0]), 'price_end': float(closes[-1])
    }
}
with open(f'{CACHE_DIR}/nari_results.pkl', 'wb') as f:
    pickle.dump(output, f)

print(f"\n✅ 完成，结果已保存")
