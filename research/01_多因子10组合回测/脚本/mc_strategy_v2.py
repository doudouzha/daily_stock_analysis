"""
多因子Alpha策略 × 10种因子权重组合 × 3年回测 + 蒙特卡洛（修复版）
修复：不取公共日期交集，每期独立对有效股票打分
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
os.makedirs(CACHE_DIR, exist_ok=True)

START_DATE = '20230801'
END_DATE = '20260801'
TOP_N = 5
REBALANCE = 5

# 10种因子权重配置
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
    """四维因子计算"""
    c, h, l, v = df['close'], df['high'], df['low'], df['volume']
    factors = pd.DataFrame(index=df.index)
    
    # 趋势因子: RSI + 动量 + 斜率
    delta = c.diff()
    gain = delta.clip(lower=0).rolling(14).mean()
    loss = (-delta.clip(upper=0)).rolling(14).mean()
    rs = gain / loss.replace(0, np.nan)
    rsi = 100 - (100 / (1 + rs))
    mom_5d = c.pct_change(5)
    # 简化斜率：用20日收益率代替polyfit（避免rolling apply太慢）
    slope_20 = c.pct_change(20)
    factors['trend'] = (rsi / 100) * 0.4 + mom_5d.rank(pct=True) * 0.3 + slope_20.rank(pct=True) * 0.3
    
    # 量价因子: 资金流 + 量比
    hl_range = (h - l).replace(0, np.nan)
    net_flow = ((c - l) / hl_range - (h - c) / hl_range) * v
    fund_flow_5d = net_flow.rolling(5).sum() / v.rolling(5).sum()
    vol_ratio = v / v.rolling(5).mean()
    factors['volume'] = fund_flow_5d.rank(pct=True) * 0.6 + vol_ratio.clip(0, 3).rank(pct=True) * 0.4
    
    # 基本面因子: 低波动 + 量稳定性
    volatility_20 = c.pct_change().rolling(20).std()
    vol_score = 1 - volatility_20.rank(pct=True)
    vol_cv = v.rolling(20).std() / v.rolling(20).mean().replace(0, np.nan)
    stability_score = 1 - vol_cv.rank(pct=True)
    factors['fundamental'] = vol_score * 0.5 + stability_score * 0.5
    
    # 情绪因子: 乖离率 + RSI逆向
    ma20 = c.rolling(20).mean()
    bias_20 = (c - ma20) / ma20
    bias_score = 1 - bias_20.abs().rank(pct=True)
    rsi_contrarian = (100 - rsi) / 100
    factors['sentiment'] = bias_score * 0.5 + rsi_contrarian * 0.5
    
    return factors

def run_backtest(all_factors, all_prices, weights, master_dates):
    """
    回测：每期对所有有效股票打分，选Top N，计算下期收益
    不要求所有股票在同一天有数据
    """
    rebalance_dates = master_dates[::REBALANCE]
    portfolio_returns = []
    
    for i in range(len(rebalance_dates) - 1):
        reb_date = rebalance_dates[i]
        next_date = rebalance_dates[i + 1]
        
        # 截面打分：只选在reb_date有因子数据的股票
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
        
        # 选Top N
        ranked = sorted(scores.items(), key=lambda x: x[1], reverse=True)
        selected = [code for code, _ in ranked[:TOP_N]]
        
        # 计算持有期收益：从reb_date到next_date
        period_ret = 0
        valid_count = 0
        for code in selected:
            if code not in all_prices:
                continue
            prices = all_prices[code]
            # 找reb_date和next_date对应的价格
            mask = (prices.index > reb_date) & (prices.index <= next_date)
            future_prices = prices[mask]
            if reb_date in prices.index and len(future_prices) > 0:
                entry_price = prices.loc[reb_date]
                exit_price = future_prices.iloc[-1]
                ret = (exit_price - entry_price) / entry_price
                if not np.isnan(ret):
                    period_ret += ret
                    valid_count += 1
        
        if valid_count > 0:
            period_ret /= valid_count
            portfolio_returns.append({
                'date': next_date,
                'return': float(period_ret),
                'holdings': selected
            })
    
    if len(portfolio_returns) < 10:
        return None
    
    rets = np.array([r['return'] for r in portfolio_returns])
    total_return = float(np.prod(1 + rets) - 1)
    n_periods = len(rets)
    years = n_periods * REBALANCE / 252
    annual_return = float((1 + total_return) ** (1 / max(years, 0.1)) - 1)
    win_rate = float(np.sum(rets > 0) / len(rets))
    
    cum = np.cumprod(1 + rets)
    peak = np.maximum.accumulate(cum)
    drawdown = (cum - peak) / peak
    max_dd = float(np.min(drawdown))
    
    std_ret = np.std(rets)
    sharpe = float((np.mean(rets) / std_ret) * np.sqrt(252 / REBALANCE)) if std_ret > 0 else 0
    
    return {
        'total_return': total_return,
        'annual_return': annual_return,
        'win_rate': win_rate,
        'max_drawdown': max_dd,
        'sharpe': sharpe,
        'n_periods': n_periods,
        'years': years,
        'period_returns': rets.tolist(),
        'cum_curve': cum.tolist(),
        'dates': [str(r['date'])[:10] for r in portfolio_returns],
    }

# ============ 主流程 ============
print("=" * 70)
print("  多因子Alpha策略 × 10种组合 × 3年回测 + 蒙特卡洛")
print("  股票池: A股主板3149只（排除创业板/科创板）")
print("  回测区间: 2023-08-01 ~ 2026-08-01")
print("=" * 70)

# Step 1: 加载股票池
print("\n[Step 1] 加载主板股票池...")
with open(f'{CACHE_DIR}/main_board_codes.pkl', 'rb') as f:
    all_codes = pickle.load(f)

np.random.seed(2026)
sampled_codes = np.random.choice(all_codes, size=200, replace=False).tolist()
print(f"  主板总量: {len(all_codes)} | 抽样: 200 只")

# Step 2: 拉取数据
print(f"\n[Step 2] 拉取3年日线数据...")
data_dict = {}
for i, code in enumerate(sampled_codes):
    df = fetch_daily(code)
    if df is not None and len(df) > 200:
        data_dict[code] = df
    if (i + 1) % 50 == 0:
        print(f"  进度: {i+1}/200 | 成功: {len(data_dict)}")
    time.sleep(0.25)

print(f"  有效数据: {len(data_dict)} 只")

# Step 3: 计算因子
print(f"\n[Step 3] 计算四维因子...")
all_factors = {}
all_prices = {}  # 收盘价序列
for code, df in data_dict.items():
    try:
        f = calc_four_factors(df)
        f = f.dropna(how='all')
        if len(f) > 60:
            all_factors[code] = f
            all_prices[code] = df['close']
    except:
        pass
print(f"  因子有效: {len(all_factors)} 只")

# 构建主日期序列（取数据最多的股票的日期作为基准）
longest_code = max(all_prices.keys(), key=lambda c: len(all_prices[c]))
master_dates = sorted(all_prices[longest_code].index.tolist())
print(f"  主日期序列: {len(master_dates)} 天 ({master_dates[0].strftime('%Y-%m-%d')} ~ {master_dates[-1].strftime('%Y-%m-%d')})")

# Step 4: 10种组合回测
print(f"\n[Step 4] 10种因子权重组合回测...")
print(f"{'组合':<16} {'年化':>8} {'胜率':>6} {'最大回撤':>8} {'夏普':>6} {'期数':>4}")
print("─" * 56)

results = {}
all_period_returns = []

for name, weights in PORTFOLIO_CONFIGS.items():
    bt = run_backtest(all_factors, all_prices, weights, master_dates)
    if bt:
        results[name] = bt
        all_period_returns.extend(bt['period_returns'])
        print(f"{name:<16} {bt['annual_return']*100:>+7.1f}% {bt['win_rate']*100:>5.0f}% {bt['max_drawdown']*100:>7.1f}% {bt['sharpe']:>5.2f} {bt['n_periods']:>4}")
    else:
        results[name] = None
        print(f"{name:<16} {'回测失败':>8}")

# Step 5: 蒙特卡洛
print(f"\n[Step 5] 蒙特卡洛模拟 (10000次 × 3年)...")
all_period_returns = np.array(all_period_returns)
if len(all_period_returns) == 0:
    print("❌ 无有效收益样本")
    exit(1)

print(f"  样本池: {len(all_period_returns)} 期")
print(f"  均值: {np.mean(all_period_returns)*100:.3f}%/期 | 标准差: {np.std(all_period_returns)*100:.3f}%/期")

N_SIM = 10000
PERIODS_PER_YEAR = int(252 / REBALANCE)
SIM_YEARS = 3
TOTAL_PERIODS = PERIODS_PER_YEAR * SIM_YEARS

np.random.seed(42)
mc_final = np.zeros(N_SIM)
mc_max_dd = np.zeros(N_SIM)
mc_curves = []

for i in range(N_SIM):
    sampled = np.random.choice(all_period_returns, size=TOTAL_PERIODS, replace=True)
    cum = np.cumprod(1 + sampled)
    mc_final[i] = cum[-1] - 1
    peak = np.maximum.accumulate(cum)
    dd = (cum - peak) / peak
    mc_max_dd[i] = np.min(dd)
    if i % 100 == 0:
        mc_curves.append(cum.tolist())

annual_returns_mc = (1 + mc_final) ** (1/SIM_YEARS) - 1

print(f"\n  ═══ 蒙特卡洛结果（3年期） ═══")
print(f"  年化收益 P5:  {np.percentile(annual_returns_mc, 5)*100:.2f}%")
print(f"  年化收益 P25: {np.percentile(annual_returns_mc, 25)*100:.2f}%")
print(f"  年化收益 P50: {np.percentile(annual_returns_mc, 50)*100:.2f}%")
print(f"  年化收益 P75: {np.percentile(annual_returns_mc, 75)*100:.2f}%")
print(f"  年化收益 P95: {np.percentile(annual_returns_mc, 95)*100:.2f}%")
print(f"  最大回撤 P5:  {np.percentile(mc_max_dd, 5)*100:.2f}%")
print(f"  最大回撤 P50: {np.percentile(mc_max_dd, 50)*100:.2f}%")
print(f"  最大回撤 P95: {np.percentile(mc_max_dd, 95)*100:.2f}%")
print(f"  3年亏损概率:  {np.mean(mc_final < 0)*100:.1f}%")
print(f"  年化>20%概率: {np.mean(annual_returns_mc > 0.20)*100:.1f}%")
print(f"  年化>50%概率: {np.mean(annual_returns_mc > 0.50)*100:.1f}%")

# 保存
output = {
    'results': results,
    'mc_annual_returns': annual_returns_mc.tolist(),
    'mc_max_dd': mc_max_dd.tolist(),
    'mc_final_returns': mc_final.tolist(),
    'mc_curves': mc_curves,
    'all_period_returns': all_period_returns.tolist(),
    'params': {
        'start': START_DATE, 'end': END_DATE,
        'top_n': TOP_N, 'rebalance': REBALANCE,
        'n_sim': N_SIM, 'sim_years': SIM_YEARS,
        'n_stocks_pool': len(data_dict),
        'n_factors_valid': len(all_factors),
        'master_dates_len': len(master_dates),
        'configs': PORTFOLIO_CONFIGS
    }
}

with open(f'{CACHE_DIR}/mc_results_full.pkl', 'wb') as f:
    pickle.dump(output, f)

print(f"\n✅ 全部完成")
