import pickle, pandas as pd, numpy as np

with open('/tmp/mc_cache/nari_results_v2.pkl', 'rb') as f:
    data = pickle.load(f)
with open('/tmp/mc_cache/nari_mc_v2.pkl', 'rb') as f:
    mc_df = pickle.load(f)

phase1 = data['phase1']
phase2 = data['phase2']
df = data['df']

out = '/Users/huangren/.qoderwork/workspace/ms9393tmwes9zvfq/outputs'

# CSV 1: Phase1 Top200 策略排名
rows = []
for i, r in enumerate(phase1[:200]):
    rows.append({
        '排名': i+1,
        '买入信号': r['buy_signal'],
        '卖出信号': r['sell_signal'],
        '交易次数': r['trades'],
        '年化收益率': f"{r['annual_return']*100:.1f}%",
        '总收益率': f"{r['total_return']*100:.1f}%",
        '胜率': f"{r['win_rate']*100:.0f}%",
        '最大回撤': f"{r['max_drawdown']*100:.1f}%",
        '平均持仓天数': f"{r['avg_hold']:.0f}",
        '平均每笔收益': f"{r['avg_return']*100:.2f}%",
    })
pd.DataFrame(rows).to_csv(f'{out}/国电南瑞_WilderRSI_Top200策略排名.csv', index=False, encoding='utf-8-sig')
print("✅ Top200策略排名 CSV")

# CSV 2: Phase2 参数优化 Top200
rows2 = []
for i, r in enumerate(phase2[:200]):
    rows2.append({
        '排名': i+1,
        '买入信号': r['buy_signal'],
        '卖出信号': r['sell_signal'],
        '止损': f"{r['sl']*100:.0f}%",
        '止盈': f"{r['tp']*100:.0f}%",
        '最长持仓': f"{r['max_hold']}日",
        '交易次数': r['trades'],
        '年化收益率': f"{r['annual_return']*100:.1f}%",
        '总收益率': f"{r['total_return']*100:.1f}%",
        '胜率': f"{r['win_rate']*100:.0f}%",
        '最大回撤': f"{r['max_drawdown']*100:.1f}%",
        '平均持仓天数': f"{r['avg_hold']:.0f}",
        '平均每笔收益': f"{r['avg_return']*100:.2f}%",
    })
pd.DataFrame(rows2).to_csv(f'{out}/国电南瑞_WilderRSI_参数优化Top200.csv', index=False, encoding='utf-8-sig')
print("✅ 参数优化Top200 CSV")

# CSV 3: 最优策略逐笔交易
best = phase2[0]
trade_rows = []
for i, t in enumerate(best['trade_list']):
    trade_rows.append({
        '序号': i+1,
        '买入日期': t['entry_date'].strftime('%Y-%m-%d'),
        '买入价': f"{t['entry_price']:.2f}",
        '卖出日期': t['exit_date'].strftime('%Y-%m-%d'),
        '卖出价': f"{t['exit_price']:.2f}",
        '收益率': f"{t['return']*100:.2f}%",
        '持仓天数': t['hold_days'],
        '卖出原因': t['exit_reason'],
    })
pd.DataFrame(trade_rows).to_csv(f'{out}/国电南瑞_WilderRSI_最优策略逐笔交易.csv', index=False, encoding='utf-8-sig')
print("✅ 最优策略逐笔交易 CSV")

# CSV 4: 蒙特卡洛1000路径(抽样)
mc_sample = mc_df.sample(1000, random_state=42).reset_index(drop=True)
mc_out = pd.DataFrame({
    '路径编号': range(1, 1001),
    '5年总收益率': (mc_sample['total_return']*100).round(1).astype(str) + '%',
    '年化收益率': (mc_sample['annual_return']*100).round(1).astype(str) + '%',
    '最大回撤': (mc_sample['max_drawdown']*100).round(1).astype(str) + '%',
    '20万终值(万)': (mc_sample['final_capital']/10000).round(1),
})
mc_out.to_csv(f'{out}/国电南瑞_WilderRSI_蒙特卡洛1000路径.csv', index=False, encoding='utf-8-sig')
print("✅ 蒙特卡洛1000路径 CSV")

# CSV 5: 回测汇总
summary = {
    '项目': [
        '股票代码', '股票名称', '回测区间', '交易日数',
        '最新收盘价', '最新RSI(14) Wilder',
        'Phase1有效策略数', 'Phase2有效策略数',
        '最优策略(Phase1)', '最优年化(Phase1)',
        '最优策略(Phase2)', '最优参数(Phase2)', '最优年化(Phase2)', '最优胜率(Phase2)', '最优回撤(Phase2)',
        'MC年化中位数', 'MC年化P5', 'MC年化P95',
        'MC 5年亏损概率', 'MC年化>10%概率',
        '20万→5年中位终值',
    ],
    '值': [
        '600406', '国电南瑞', 
        f"{df.index[0].strftime('%Y-%m-%d')} ~ {df.index[-1].strftime('%Y-%m-%d')}",
        str(len(df)),
        f"{data['latest_close']:.2f}",
        f"{data['latest_rsi']:.1f}",
        str(len(phase1)), str(len(phase2)),
        f"{phase1[0]['buy_signal']} → {phase1[0]['sell_signal']}",
        f"{phase1[0]['annual_return']*100:+.1f}%",
        f"{best['buy_signal']} → {best['sell_signal']}",
        f"SL{best['sl']*100:.0f}%/TP{best['tp']*100:.0f}%/{best['max_hold']}日",
        f"{best['annual_return']*100:+.1f}%",
        f"{best['win_rate']*100:.0f}%",
        f"{best['max_drawdown']*100:.1f}%",
        f"{mc_df['annual_return'].median()*100:+.1f}%",
        f"{mc_df['annual_return'].quantile(0.05)*100:+.1f}%",
        f"{mc_df['annual_return'].quantile(0.95)*100:+.1f}%",
        f"{(mc_df['total_return']<0).mean()*100:.1f}%",
        f"{(mc_df['annual_return']>0.10).mean()*100:.1f}%",
        f"{mc_df['final_capital'].median()/10000:.1f}万",
    ]
}
pd.DataFrame(summary).to_csv(f'{out}/国电南瑞_WilderRSI_回测汇总.csv', index=False, encoding='utf-8-sig')
print("✅ 回测汇总 CSV")

print("\n全部CSV导出完成!")
