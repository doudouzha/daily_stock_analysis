import pickle, numpy as np, pandas as pd
import warnings
warnings.filterwarnings('ignore')

# 加载数据
with open('/tmp/mc_cache/nari_results_v2.pkl', 'rb') as f:
    data = pickle.load(f)

phase1 = data['phase1']
phase2 = data['phase2']
df = data['df']
latest_rsi = data['latest_rsi']
latest_close = data['latest_close']

print("=" * 60)
print("蒙特卡洛模拟 — 基于 Wilder RSI 最优策略")
print("=" * 60)

# 取Phase2最优策略的交易收益序列
best = phase2[0]
print(f"\n最优策略: {best['buy_signal']} → {best['sell_signal']}")
print(f"参数: SL{best['sl']*100:.0f}%/TP{best['tp']*100:.0f}%/{best['max_hold']}日")
print(f"历史: {best['trades']}笔 | 年化{best['annual_return']*100:+.1f}% | 胜率{best['win_rate']*100:.0f}%")

trade_returns = [t['return'] for t in best['trade_list']]
print(f"单笔收益分布: 均值{np.mean(trade_returns)*100:+.2f}% | 中位{np.median(trade_returns)*100:+.2f}% | 标准差{np.std(trade_returns)*100:.2f}%")

# 蒙特卡洛: 10000路径 × 5年
# 平均每年约 250/avg_hold 笔交易
avg_hold = best['avg_hold']
trades_per_year = 250 / avg_hold
n_years = 5
n_trades_total = int(trades_per_year * n_years)
n_paths = 10000

print(f"\n模拟参数: {n_paths}路径 × {n_years}年 × ~{trades_per_year:.0f}笔/年 = {n_trades_total}笔")

np.random.seed(42)
mc_results = []
for _ in range(n_paths):
    sampled = np.random.choice(trade_returns, size=n_trades_total, replace=True)
    cum = np.cumprod(1 + sampled)
    total_ret = cum[-1] - 1
    annual_ret = (1 + total_ret) ** (1/n_years) - 1
    # 最大回撤
    peak = np.maximum.accumulate(cum)
    dd = (cum - peak) / peak
    max_dd = dd.min()
    mc_results.append({
        'total_return': total_ret,
        'annual_return': annual_ret,
        'max_drawdown': max_dd,
        'final_value': cum[-1],  # 1元变多少
    })

mc_df = pd.DataFrame(mc_results)

print(f"\n蒙特卡洛结果 (10000路径, 5年):")
print(f"  年化收益: P5={mc_df['annual_return'].quantile(0.05)*100:+.1f}% | P25={mc_df['annual_return'].quantile(0.25)*100:+.1f}% | 中位={mc_df['annual_return'].median()*100:+.1f}% | P75={mc_df['annual_return'].quantile(0.75)*100:+.1f}% | P95={mc_df['annual_return'].quantile(0.95)*100:+.1f}%")
print(f"  5年总收益: P5={mc_df['total_return'].quantile(0.05)*100:+.1f}% | 中位={mc_df['total_return'].median()*100:+.1f}% | P95={mc_df['total_return'].quantile(0.95)*100:+.1f}%")
print(f"  最大回撤: P5={mc_df['max_drawdown'].quantile(0.05)*100:.1f}% | 中位={mc_df['max_drawdown'].median()*100:.1f}% | P95={mc_df['max_drawdown'].quantile(0.95)*100:.1f}%")
print(f"  亏损概率: {(mc_df['total_return'] < 0).mean()*100:.1f}%")
print(f"  年化>10%概率: {(mc_df['annual_return'] > 0.10).mean()*100:.1f}%")
print(f"  年化>20%概率: {(mc_df['annual_return'] > 0.20).mean()*100:.1f}%")

# 20万资金模拟
capital = 200000
mc_df['final_capital'] = mc_df['final_value'] * capital
print(f"\n  20万本金 → 5年后:")
print(f"    P5: {mc_df['final_capital'].quantile(0.05)/10000:.1f}万")
print(f"    中位: {mc_df['final_capital'].median()/10000:.1f}万")
print(f"    P95: {mc_df['final_capital'].quantile(0.95)/10000:.1f}万")

# 保存MC结果
with open('/tmp/mc_cache/nari_mc_v2.pkl', 'wb') as f:
    pickle.dump(mc_df, f)

print("\n✅ 蒙特卡洛完成")
