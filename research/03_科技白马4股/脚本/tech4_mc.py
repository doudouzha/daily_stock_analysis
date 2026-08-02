import pickle, numpy as np, pandas as pd
import warnings; warnings.filterwarnings('ignore')

with open('/tmp/mc_cache/tech4_results.pkl','rb') as f:
    all_results = pickle.load(f)

mc_all = {}
print("="*60)
print("蒙特卡洛验证 (10000路径 × 5年)")
print("="*60)

for code, res in all_results.items():
    name = res['name']
    if not res['phase2']:
        continue
    best = res['phase2'][0]
    trade_returns = [t['return'] for t in best['trade_list']]
    avg_hold = best['avg_hold']
    n_trades = int(250/avg_hold*5)
    np.random.seed(42)
    rows = []
    for _ in range(10000):
        s = np.random.choice(trade_returns, size=n_trades, replace=True)
        cum = np.cumprod(1+s)
        tr = cum[-1]-1
        ar = (1+tr)**(1/5)-1
        peak = np.maximum.accumulate(cum)
        mdd = ((cum-peak)/peak).min()
        rows.append({'total_return':tr,'annual_return':ar,'max_drawdown':mdd,'final_value':cum[-1]})
    mdf = pd.DataFrame(rows)
    mc_all[code] = mdf
    print(f"\n{name} | 最优: {best['buy_signal']}→{best['sell_signal']}")
    print(f"  历史: 年化{best['annual_return']*100:+.1f}% 胜率{best['win_rate']*100:.0f}% {best['trades']}笔")
    print(f"  MC年化: P5={mdf['annual_return'].quantile(.05)*100:+.1f}% 中位={mdf['annual_return'].median()*100:+.1f}% P95={mdf['annual_return'].quantile(.95)*100:+.1f}%")
    print(f"  5年亏损概率: {(mdf['total_return']<0).mean()*100:.1f}% | 年化>10%概率: {(mdf['annual_return']>0.10).mean()*100:.1f}%")

with open('/tmp/mc_cache/tech4_mc.pkl','wb') as f:
    pickle.dump(mc_all, f)
print("\n✅ MC完成")
