"""
打印10种因子组合最近一年的逐期持仓操作
"""
import akshare as ak
import pandas as pd
import numpy as np
import time
import pickle
import os
import warnings
warnings.filterwarnings('ignore')

CACHE_DIR = '/tmp/mc_cache'
START_DATE = '20230801'
END_DATE = '20260801'
TOP_N = 5
REBALANCE = 5

PORTFOLIO_CONFIGS = {
    'P01_趋势主导': {'trend': 0.40, 'volume': 0.25, 'fundamental': 0.20, 'sentiment': 0.15},
    'P02_量价主导': {'trend': 0.20, 'volume': 0.40, 'fundamental': 0.25, 'sentiment': 0.15},
    'P03_基本面主导': {'trend': 0.15, 'volume': 0.20, 'fundamental': 0.40, 'sentiment': 0.25},
    'P04_情绪主导': {'trend': 0.20, 'volume': 0.20, 'fundamental': 0.20, 'sentiment': 0.40},
    'P05_均衡配置': {'trend': 0.25, 'volume': 0.25, 'fundamental': 0.25, 'sentiment': 0.25},
    'P06_趋势量价': {'trend': 0.35, 'volume': 0.35, 'fundamental': 0.15, 'sentiment': 0.15},
    'P07_基本面情绪': {'trend': 0.15, 'volume': 0.15, 'fundamental': 0.35, 'sentiment': 0.35},
    'P08_进攻型': {'trend': 0.45, 'volume': 0.30, 'fundamental': 0.10, 'sentiment': 0.15},
    'P09_防御型': {'trend': 0.15, 'volume': 0.20, 'fundamental': 0.45, 'sentiment': 0.20},
    'P10_动量轮动': {'trend': 0.30, 'volume': 0.30, 'fundamental': 0.20, 'sentiment': 0.20},
}

def get_prefix(code):
    return 'sh' if str(code).startswith('6') else 'sz'

def fetch_daily(code):
    symbol = f"{get_prefix(code)}{code}"
    try:
        df = ak.stock_zh_a_daily(symbol=symbol, start_date=START_DATE, end_date=END_DATE, adjust='qfq')
        if df is None or df.empty:
            return None
        if not isinstance(df.index, pd.DatetimeIndex):
            if 'date' in df.columns:
                df['date'] = pd.to_datetime(df['date'])
                df = df.set_index('date')
            else:
                df.index = pd.to_datetime(df.index)
        for col in ['open','high','low','close','volume']:
            if col not in df.columns:
                return None
        return df[['open','high','low','close','volume']].astype(float)
    except:
        return None

def calc_four_factors(df):
    c, h, l, v = df['close'], df['high'], df['low'], df['volume']
    factors = pd.DataFrame(index=df.index)
    delta = c.diff()
    gain = delta.clip(lower=0).rolling(14).mean()
    loss = (-delta.clip(upper=0)).rolling(14).mean()
    rs = gain / loss.replace(0, np.nan)
    rsi = 100 - (100 / (1 + rs))
    mom_5d = c.pct_change(5)
    slope_20 = c.pct_change(20)
    factors['trend'] = (rsi / 100) * 0.4 + mom_5d.rank(pct=True) * 0.3 + slope_20.rank(pct=True) * 0.3
    hl_range = (h - l).replace(0, np.nan)
    net_flow = ((c - l) / hl_range - (h - c) / hl_range) * v
    fund_flow_5d = net_flow.rolling(5).sum() / v.rolling(5).sum()
    vol_ratio = v / v.rolling(5).mean()
    factors['volume'] = fund_flow_5d.rank(pct=True) * 0.6 + vol_ratio.clip(0, 3).rank(pct=True) * 0.4
    volatility_20 = c.pct_change().rolling(20).std()
    vol_score = 1 - volatility_20.rank(pct=True)
    vol_cv = v.rolling(20).std() / v.rolling(20).mean().replace(0, np.nan)
    stability_score = 1 - vol_cv.rank(pct=True)
    factors['fundamental'] = vol_score * 0.5 + stability_score * 0.5
    ma20 = c.rolling(20).mean()
    bias_20 = (c - ma20) / ma20
    bias_score = 1 - bias_20.abs().rank(pct=True)
    rsi_contrarian = (100 - rsi) / 100
    factors['sentiment'] = bias_score * 0.5 + rsi_contrarian * 0.5
    return factors

def run_backtest_with_holdings(all_factors, all_prices, weights, master_dates, start_filter=None):
    """回测并记录每期持仓"""
    rebalance_dates = master_dates[::REBALANCE]
    history = []
    
    for i in range(len(rebalance_dates) - 1):
        reb_date = rebalance_dates[i]
        next_date = rebalance_dates[i + 1]
        
        if start_filter and reb_date < start_filter:
            continue
        
        scores = {}
        for code, f in all_factors.items():
            if reb_date not in f.index:
                continue
            row = f.loc[reb_date]
            if row.isna().all():
                continue
            score = sum(row.get(dim, 0) * w for dim, w in weights.items() if not np.isnan(row.get(dim, np.nan)))
            if not np.isnan(score):
                scores[code] = score
        
        if len(scores) < TOP_N:
            continue
        
        ranked = sorted(scores.items(), key=lambda x: x[1], reverse=True)
        selected = [code for code, _ in ranked[:TOP_N]]
        
        # 计算收益
        period_ret = 0
        valid_count = 0
        stock_rets = {}
        for code in selected:
            if code not in all_prices:
                continue
            prices = all_prices[code]
            mask = (prices.index > reb_date) & (prices.index <= next_date)
            future_prices = prices[mask]
            if reb_date in prices.index and len(future_prices) > 0:
                entry = prices.loc[reb_date]
                exit_p = future_prices.iloc[-1]
                ret = (exit_p - entry) / entry
                if not np.isnan(ret):
                    period_ret += ret
                    stock_rets[code] = ret
                    valid_count += 1
        
        if valid_count > 0:
            period_ret /= valid_count
            history.append({
                'date': reb_date.strftime('%Y-%m-%d'),
                'next': next_date.strftime('%Y-%m-%d'),
                'holdings': selected,
                'stock_rets': stock_rets,
                'period_ret': period_ret
            })
    
    return history

# ============ 主流程 ============
print("加载数据...")
with open(f'{CACHE_DIR}/main_board_codes.pkl', 'rb') as f:
    all_codes = pickle.load(f)

# 加载名称映射
try:
    with open(f'{CACHE_DIR}/name_map.pkl', 'rb') as f:
        name_map = pickle.load(f)
except:
    name_map = {}

np.random.seed(2026)
sampled_codes = np.random.choice(all_codes, size=200, replace=False).tolist()

# 拉取数据
print(f"拉取{len(sampled_codes)}只股票3年数据...")
data_dict = {}
for i, code in enumerate(sampled_codes):
    df = fetch_daily(code)
    if df is not None and len(df) > 200:
        data_dict[code] = df
    if (i + 1) % 50 == 0:
        print(f"  {i+1}/200 | 成功: {len(data_dict)}")
    time.sleep(0.2)

print(f"有效: {len(data_dict)} 只")

# 计算因子
print("计算因子...")
all_factors = {}
all_prices = {}
for code, df in data_dict.items():
    try:
        f = calc_four_factors(df)
        f = f.dropna(how='all')
        if len(f) > 60:
            all_factors[code] = f
            all_prices[code] = df['close']
    except:
        pass

longest_code = max(all_prices.keys(), key=lambda c: len(all_prices[c]))
master_dates = sorted(all_prices[longest_code].index.tolist())

# 最近一年过滤
one_year_ago = pd.Timestamp('2025-08-01')
print(f"\n打印最近一年（2025-08-01起）的操作记录")
print("=" * 80)

for pname, weights in PORTFOLIO_CONFIGS.items():
    history = run_backtest_with_holdings(all_factors, all_prices, weights, master_dates, start_filter=one_year_ago)
    
    if not history:
        print(f"\n{'━' * 80}")
        print(f"  {pname} — 无有效记录")
        continue
    
    # 统计
    rets = [h['period_ret'] for h in history]
    total = np.prod([1+r for r in rets]) - 1
    win = sum(1 for r in rets if r > 0) / len(rets)
    
    print(f"\n{'━' * 80}")
    print(f"  {pname}")
    print(f"  权重: 趋势{weights['trend']:.0%} | 量价{weights['volume']:.0%} | 基本面{weights['fundamental']:.0%} | 情绪{weights['sentiment']:.0%}")
    print(f"  近一年: {len(history)}期 | 累计{total*100:+.1f}% | 胜率{win*100:.0f}%")
    print(f"{'━' * 80}")
    print(f"  {'调仓日':<12} {'持有→下期':<12} {'本期收益':>8}  持仓（代码 名称 收益）")
    print(f"  {'─'*72}")
    
    for h in history:
        ret_str = f"{h['period_ret']*100:+.2f}%"
        holdings_str = ""
        for code in h['holdings']:
            name = name_map.get(code, '')
            sr = h['stock_rets'].get(code, 0)
            holdings_str += f"{code}({name}){sr*100:+.1f}% "
        print(f"  {h['date']:<12} →{h['next']:<10} {ret_str:>8}  {holdings_str}")

print(f"\n{'=' * 80}")
print("完成")
