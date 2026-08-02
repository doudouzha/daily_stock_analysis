import akshare as ak
import pandas as pd
import numpy as np
import pickle, warnings
warnings.filterwarnings('ignore')

STOCKS = {'sh600487':'亨通光电','sh601138':'工业富联','sz002281':'光迅科技'}

def analyze(code, name):
    df = ak.stock_zh_a_daily(symbol=code, adjust="qfq")
    df['date'] = pd.to_datetime(df['date'])
    df = df.set_index('date').sort_index()
    df = df[df.index >= '2024-01-01']
    c = df['close'].astype(float); h = df['high'].astype(float)
    l = df['low'].astype(float); v = df['volume'].astype(float)

    r = {'name':name,'code':code}
    last = df.iloc[-1]; prev = df.iloc[-2]

    # ===== Step1 行情概览 =====
    r['close'] = float(c.iloc[-1]); r['prev_close'] = float(c.iloc[-2])
    r['chg_pct'] = (c.iloc[-1]/c.iloc[-2]-1)*100
    r['high'] = float(h.iloc[-1]); r['low'] = float(l.iloc[-1])
    r['amount'] = float((df['amount'].astype(float).iloc[-1])/1e8)  # 亿元
    r['week_chg'] = (c.iloc[-1]/c.iloc[-6]-1)*100 if len(c)>6 else np.nan
    r['month_chg'] = (c.iloc[-1]/c.iloc[-22]-1)*100 if len(c)>22 else np.nan
    r['last_date'] = df.index[-1].strftime('%Y-%m-%d')

    # ===== Step2 趋势: 均线 + MACD =====
    for n in [5,10,20,60,120]:
        r[f'ma{n}'] = float(c.rolling(n).mean().iloc[-1])
    # 均线排列
    mas = [r['ma5'],r['ma10'],r['ma20'],r['ma60']]
    r['bull_align'] = mas[0]>mas[1]>mas[2]>mas[3]
    r['bear_align'] = mas[0]<mas[1]<mas[2]<mas[3]
    # MACD
    e12 = c.ewm(span=12,adjust=False).mean(); e26 = c.ewm(span=26,adjust=False).mean()
    dif = e12-e26; dea = dif.ewm(span=9,adjust=False).mean(); macd = 2*(dif-dea)
    r['dif'] = float(dif.iloc[-1]); r['dea'] = float(dea.iloc[-1]); r['macd'] = float(macd.iloc[-1])
    r['macd_prev'] = float(macd.iloc[-2])
    r['dif_above_dea'] = dif.iloc[-1] > dea.iloc[-1]
    r['golden_cross'] = (dif.iloc[-2]<dea.iloc[-2]) and (dif.iloc[-1]>dea.iloc[-1])
    r['death_cross'] = (dif.iloc[-2]>dea.iloc[-2]) and (dif.iloc[-1]<dea.iloc[-1])
    r['macd_expanding'] = abs(macd.iloc[-1]) > abs(macd.iloc[-2])

    # ===== Step3 位置: 布林带 + RSI + 52周位置 =====
    mid = c.rolling(20).mean(); std = c.rolling(20).std()
    r['boll_up'] = float((mid+2*std).iloc[-1]); r['boll_mid'] = float(mid.iloc[-1]); r['boll_low'] = float((mid-2*std).iloc[-1])
    price = r['close']
    r['boll_pos'] = (price - r['boll_low'])/(r['boll_up']-r['boll_low'])*100  # 0=下轨 100=上轨
    # Wilder RSI
    delta = c.diff(); gain = delta.clip(lower=0); loss = -delta.clip(upper=0)
    ag = gain.ewm(alpha=1/14,min_periods=14,adjust=False).mean()
    al = loss.ewm(alpha=1/14,min_periods=14,adjust=False).mean()
    rsi = 100 - 100/(1+ag/al.replace(0,np.nan))
    r['rsi'] = float(rsi.iloc[-1])
    # KDJ
    low9=l.rolling(9).min(); high9=h.rolling(9).max()
    rsv=(c-low9)/(high9-low9).replace(0,np.nan)*100
    k=rsv.ewm(com=2,adjust=False).mean(); dd=k.ewm(com=2,adjust=False).mean(); j=3*k-2*dd
    r['k']=float(k.iloc[-1]); r['d']=float(dd.iloc[-1]); r['j']=float(j.iloc[-1])
    # 52周高低
    yr = df[df.index >= df.index[-1]-pd.Timedelta(days=365)]
    r['high_52w'] = float(yr['high'].astype(float).max()); r['low_52w'] = float(yr['low'].astype(float).min())
    r['pos_52w'] = (price - r['low_52w'])/(r['high_52w']-r['low_52w'])*100
    r['dist_high'] = (price/r['high_52w']-1)*100

    # ===== Step4 支撑压力: 近期高低点 + 枢轴 =====
    r20 = df.tail(20)
    r['resist_20d'] = float(r20['high'].astype(float).max())   # 近20日高点=压力
    r['support_20d'] = float(r20['low'].astype(float).min())   # 近20日低点=支撑
    r60 = df.tail(60)
    r['resist_60d'] = float(r60['high'].astype(float).max())
    r['support_60d'] = float(r60['low'].astype(float).min())
    # 经典枢轴点
    H,L,C = r['high'],r['low'],r['close']
    P = (H+L+C)/3
    r['pivot'] = P; r['r1'] = 2*P-L; r['s1'] = 2*P-H

    # ===== Step5 量能: 量比 + OBV + MFI + WVAD =====
    r['vol_ratio'] = float(v.iloc[-1]/v.rolling(5).mean().iloc[-1])
    # OBV
    obv = (np.sign(c.diff())*v).fillna(0).cumsum()
    r['obv_up'] = obv.iloc[-1] > obv.iloc[-6]  # 5日OBV是否抬升
    r['obv_slope5'] = float((obv.iloc[-1]-obv.iloc[-6])/abs(obv.iloc[-6])*100) if obv.iloc[-6]!=0 else 0
    # MFI(14)
    tp = (h+l+c)/3; mf = tp*v
    pos_mf = mf.where(tp>tp.shift(),0).rolling(14).sum()
    neg_mf = mf.where(tp<tp.shift(),0).rolling(14).sum()
    mfi = 100 - 100/(1+pos_mf/neg_mf.replace(0,np.nan))
    r['mfi'] = float(mfi.iloc[-1])
    # WVAD
    wvad = ((c-h)+(c-l))/(h-l).replace(0,np.nan)*v
    r['wvad5'] = float(wvad.rolling(5).mean().iloc[-1])
    # 近5日量能 vs 近20日
    r['vol_5v20'] = float(v.rolling(5).mean().iloc[-1]/v.rolling(20).mean().iloc[-1])

    return r

results = {}
for code,name in STOCKS.items():
    print(f"分析 {name}({code})...")
    results[code] = analyze(code,name)

with open('/tmp/mc_cache/tech3_ind.pkl','wb') as f:
    pickle.dump(results,f)

# 打印摘要
for code,r in results.items():
    print(f"\n{'='*50}\n{r['name']} ({code}) @ {r['last_date']}")
    print(f"  收盘 {r['close']:.2f} ({r['chg_pct']:+.2f}%) | 日高{r['high']:.2f}/低{r['low']:.2f} | 成交{r['amount']:.1f}亿")
    print(f"  周涨跌 {r['week_chg']:+.1f}% | 月涨跌 {r['month_chg']:+.1f}% | 52周位置 {r['pos_52w']:.0f}% (距高点{r['dist_high']:+.1f}%)")
    print(f"  均线: MA5={r['ma5']:.2f} MA10={r['ma10']:.2f} MA20={r['ma20']:.2f} MA60={r['ma60']:.2f} | 多头排列={r['bull_align']} 空头={r['bear_align']}")
    print(f"  MACD: DIF={r['dif']:.3f} DEA={r['dea']:.3f} 柱={r['macd']:.3f} | DIF>DEA={r['dif_above_dea']} 金叉={r['golden_cross']} 死叉={r['death_cross']} 柱放大={r['macd_expanding']}")
    print(f"  布林: 上{r['boll_up']:.2f}/中{r['boll_mid']:.2f}/下{r['boll_low']:.2f} | 带内位置{r['boll_pos']:.0f}% | RSI={r['rsi']:.1f} KDJ J={r['j']:.0f}")
    print(f"  支撑压力: 20日[{r['support_20d']:.2f}~{r['resist_20d']:.2f}] 60日[{r['support_60d']:.2f}~{r['resist_60d']:.2f}] 枢轴P={r['pivot']:.2f}")
    print(f"  量能: 量比{r['vol_ratio']:.2f} 5/20日量比{r['vol_5v20']:.2f} | OBV5日抬升={r['obv_up']} MFI={r['mfi']:.0f} WVAD5={r['wvad5']:.0f}")
print("\n✅ 完成")
