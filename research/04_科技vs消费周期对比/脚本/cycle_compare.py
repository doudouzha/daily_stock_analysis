import akshare as ak
import pandas as pd
import numpy as np
import pickle, warnings
warnings.filterwarnings('ignore')

# 消费股篮子(核心资产代表) & 科技股篮子
CONSUMER = {'sh600519':'贵州茅台','sz000858':'五粮液','sh600887':'伊利股份','sh603288':'海天味业'}
TECH = {'sz002415':'海康威视','sz002475':'立讯精密','sz000725':'京东方A','sz000063':'中兴通讯'}

def fetch(code):
    df = ak.stock_zh_a_daily(symbol=code, adjust="qfq")
    df['date'] = pd.to_datetime(df['date'])
    return df.set_index('date').sort_index()['close'].astype(float)

def build_basket(stocks, ref_date):
    """等权篮子: 每只股票在ref_date归一化为100, 逐日取均值"""
    series = {}
    for code, name in stocks.items():
        s = fetch(code)
        # 找ref_date当天或之前最近的交易日
        ref_val = s[s.index <= ref_date].iloc[-1]
        series[name] = s / ref_val * 100
        print(f"  {name}({code}): {s.index[0].strftime('%Y-%m-%d')}~{s.index[-1].strftime('%Y-%m-%d')}")
    df = pd.DataFrame(series)
    basket = df.mean(axis=1)  # 等权
    return basket, df

print("="*60)
print("构建消费股篮子 (参考日 2015-01-05)")
print("="*60)
cons_basket, cons_df = build_basket(CONSUMER, '2015-01-05')
cons_basket = cons_basket[cons_basket.index >= '2015-01-01'].dropna()

print("\n" + "="*60)
print("构建科技股篮子 (参考日 2022-01-04)")
print("="*60)
tech_basket, tech_df = build_basket(TECH, '2022-01-04')
tech_basket = tech_basket[tech_basket.index >= '2022-01-01'].dropna()

# ---- 识别周期底部 ----
# 消费: 2015-2016年间的底部(核心资产牛市起点)
cons_window = cons_basket[(cons_basket.index >= '2015-01-01') & (cons_basket.index <= '2016-12-31')]
cons_bottom_date = cons_window.idxmin()
cons_bottom_val = cons_window.min()
# 消费的顶部
cons_peak_date = cons_basket[cons_basket.index >= cons_bottom_date].idxmax()
cons_peak_val = cons_basket.loc[cons_peak_date]

# 科技: 2022-2024年间的底部(本轮AI行情起点)
tech_window = tech_basket[(tech_basket.index >= '2022-01-01') & (tech_basket.index <= '2024-12-31')]
tech_bottom_date = tech_window.idxmin()
tech_bottom_val = tech_window.min()
tech_now_val = tech_basket.iloc[-1]
tech_now_date = tech_basket.index[-1]

print("\n" + "="*60)
print("周期定位")
print("="*60)
print(f"消费篮子: 底部 {cons_bottom_date.strftime('%Y-%m-%d')} ({cons_bottom_val:.1f}) → 顶部 {cons_peak_date.strftime('%Y-%m-%d')} ({cons_peak_val:.1f})")
print(f"  底部到顶部: {(cons_peak_date-cons_bottom_date).days}天 | 涨幅 +{(cons_peak_val/cons_bottom_val-1)*100:.0f}%")
cons_after_peak = cons_basket[cons_basket.index >= cons_peak_date]
cons_trough_after = cons_after_peak.min()
cons_trough_date = cons_after_peak.idxmin()
print(f"  顶部后最大回撤: {(cons_trough_after/cons_peak_val-1)*100:.1f}% (至 {cons_trough_date.strftime('%Y-%m-%d')})")

print(f"\n科技篮子: 底部 {tech_bottom_date.strftime('%Y-%m-%d')} ({tech_bottom_val:.1f}) → 当前 {tech_now_date.strftime('%Y-%m-%d')} ({tech_now_val:.1f})")
print(f"  底部到当前: {(tech_now_date-tech_bottom_date).days}天 | 涨幅 +{(tech_now_val/tech_bottom_val-1)*100:.0f}%")

# ---- 周期对齐: 从各自底部归一化为100 ----
cons_aligned = cons_basket[cons_basket.index >= cons_bottom_date] / cons_bottom_val * 100
tech_aligned = tech_basket[tech_basket.index >= tech_bottom_date] / tech_bottom_val * 100

# 用交易日序号对齐
cons_aligned = cons_aligned.reset_index(drop=True)  # index=交易日序号
tech_aligned = tech_aligned.reset_index(drop=True)

# ---- 形态相似度: 科技当前路径 vs 消费同阶段路径 ----
n_tech = len(tech_aligned)
cons_same_len = cons_aligned.iloc[:n_tech]
# 对数收益序列的相关性(形态相似度)
tech_logret = np.log(tech_aligned.values[1:])
cons_logret = np.log(cons_same_len.values[1:])
similarity = np.corrcoef(tech_logret, cons_logret)[0,1]

# 累计涨幅对比
tech_gain_now = tech_aligned.iloc[-1] - 100
cons_gain_same_stage = cons_same_len.iloc[-1] - 100

print("\n" + "="*60)
print("形态相似度分析")
print("="*60)
print(f"科技已走交易日数: {n_tech}")
print(f"消费同期(底部后{n_tech}个交易日)累计涨幅: +{cons_gain_same_stage:.0f}%")
print(f"科技当前累计涨幅: +{tech_gain_now:.0f}%")
print(f"日收益率序列相关系数(形态相似度): {similarity:.3f}")

# ---- 推演: 如果科技完全复刻消费的路径 ----
cons_full = cons_aligned.values
# 消费从底部到顶部用了多少交易日
cons_days_to_peak = int(np.argmax(cons_full))
print(f"\n消费从底部到顶部用了 {cons_days_to_peak} 个交易日")
print(f"科技目前已走 {n_tech} 个交易日 = 消费周期的 {n_tech/cons_days_to_peak*100:.0f}%")

# 如果科技复刻消费: 未来路径 = 消费路径从n_tech开始
if n_tech < len(cons_full):
    cons_future = cons_full[n_tech:]
    # 按比例映射到科技当前水平
    proj = tech_aligned.iloc[-1] * (cons_future / cons_full[n_tech])
    proj_peak = proj.max()
    proj_peak_idx = int(np.argmax(proj))
    proj_trough = proj.min()
    print(f"\n[复刻推演] 若科技完全复刻消费后续路径:")
    print(f"  未来最高点: {proj_peak:.1f} (较当前 {(proj_peak/tech_aligned.iloc[-1]-1)*100:+.0f}%), 约{proj_peak_idx}个交易日后")
    print(f"  之后最低点: {proj_trough:.1f} (较当前 {(proj_trough/tech_aligned.iloc[-1]-1)*100:+.0f}%)")

# 保存
with open('/tmp/mc_cache/cycle_compare.pkl','wb') as f:
    pickle.dump({
        'cons_basket':cons_basket,'tech_basket':tech_basket,
        'cons_df':cons_df,'tech_df':tech_df,
        'cons_aligned':cons_aligned,'tech_aligned':tech_aligned,
        'cons_bottom_date':cons_bottom_date,'cons_peak_date':cons_peak_date,
        'tech_bottom_date':tech_bottom_date,
        'similarity':similarity,'n_tech':n_tech,
        'cons_days_to_peak':cons_days_to_peak,
        'tech_gain_now':tech_gain_now,'cons_gain_same_stage':cons_gain_same_stage,
    }, f)
print("\n✅ 已保存 /tmp/mc_cache/cycle_compare.pkl")
