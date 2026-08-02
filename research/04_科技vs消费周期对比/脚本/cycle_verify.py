import pickle, numpy as np, pandas as pd
with open('/tmp/mc_cache/cycle_compare.pkl','rb') as f:
    d = pickle.load(f)

cb = d['cons_basket']; tb = d['tech_basket']
ca = d['cons_aligned']; ta = d['tech_aligned']

print("=== 消费篮子关键时点 ===")
print(f"底部 {d['cons_bottom_date'].strftime('%Y-%m-%d')}: {cb.loc[d['cons_bottom_date']]:.1f}")
print(f"顶部 {d['cons_peak_date'].strftime('%Y-%m-%d')}: {cb.loc[d['cons_peak_date']]:.1f}")
print(f"当前 {cb.index[-1].strftime('%Y-%m-%d')}: {cb.iloc[-1]:.1f}")
peak = cb.loc[d['cons_peak_date']]
print(f"顶部→当前 回撤: {(cb.iloc[-1]/peak-1)*100:.1f}%")
print(f"顶部→最低 回撤: {(cb[cb.index>=d['cons_peak_date']].min()/peak-1)*100:.1f}%")

print("\n=== 科技篮子关键时点 ===")
print(f"底部 {d['tech_bottom_date'].strftime('%Y-%m-%d')}: {tb.loc[d['tech_bottom_date']]:.1f}")
print(f"当前 {tb.index[-1].strftime('%Y-%m-%d')}: {tb.iloc[-1]:.1f}")
print(f"底部→当前: +{(tb.iloc[-1]/tb.loc[d['tech_bottom_date']]-1)*100:.0f}%")

print("\n=== 对齐后 (底部=100) ===")
n = d['n_tech']
print(f"科技已走 {n} 交易日, 对齐值={ta.iloc[-1]:.1f} (+{ta.iloc[-1]-100:.0f}%)")
print(f"消费同期(第{n}日) 对齐值={ca.iloc[n-1]:.1f} (+{ca.iloc[n-1]-100:.0f}%)")
print(f"消费顶部 对齐值={ca.max():.1f}, 在第{int(np.argmax(ca.values))+1}个交易日")
print(f"消费当前 对齐值={ca.iloc[-1]:.1f}")

# 消费从第n日到顶部的涨幅 (这是科技若复刻的"剩余空间")
cons_at_n = ca.iloc[n-1]
cons_peak_v = ca.max()
print(f"\n消费从第{n}日({cons_at_n:.0f})到顶部({cons_peak_v:.0f}): +{(cons_peak_v/cons_at_n-1)*100:.0f}%")
print(f"消费从顶部到当前: {(ca.iloc[-1]/cons_peak_v-1)*100:.0f}%")

# 各成分股当前 vs 顶部
print("\n=== 各成分股 (当前/顶部) ===")
for name in d['cons_df'].columns:
    s = d['cons_df'][name].dropna()
    print(f"  消费-{name}: 当前{s.iloc[-1]:.0f} / 顶部{s.max():.0f} = {s.iloc[-1]/s.max()*100:.0f}%")
for name in d['tech_df'].columns:
    s = d['tech_df'][name].dropna()
    print(f"  科技-{name}: 当前{s.iloc[-1]:.0f} / 底部后最高{s[s.index>=d['tech_bottom_date']].max():.0f}")
