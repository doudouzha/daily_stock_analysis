"""
多因子Alpha策略 × 10种因子权重组合 × 3年回测 + 蒙特卡洛
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
股票池: A股主板3149只（排除创业板300/科创板688）
方法: 随机抽取200只构建可操作池，用10种不同因子权重配置选股
因子: 趋势(RSI+动量) / 量价(资金流+量比) / 基本面(波动率+换手) / 情绪(乖离+超买超卖)
调仓: 每5个交易日 | 持仓: Top5等权
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
N_STOCKS = 200  # 从3149只中抽取的可操作池

# ============ 10种因子权重配置（对应策略中不同市场风格判断） ============
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

# ============ 工具函数 ============
def get_prefix(code):
    code = str(code).zfill(6)
    return 'sh' if code.startswith('6') else 'sz'

def fetch_daily(code):
    """获取单只股票3年日线（新浪源）"""
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
    """
    计算四维因子（对应策略SKILL.md中的四因子体系）
    - 趋势因子: RSI_14 + 5日动量 + 20日斜率
    - 量价因子: 5日资金流 + 量比
    - 基本面因子: 波动率(低波高分) + 换手稳定性
    - 情绪因子: 乖离率 + RSI超买超卖反转
    """
    c, h, l, v = df['close'], df['high'], df['low'], df['volume']
    factors = pd.DataFrame(index=df.index)
    
    # === 趋势因子 ===
    delta = c.diff()
    gain = delta.clip(lower=0).rolling(14).mean()
    loss = (-delta.clip(upper=0)).rolling(14).mean()
    rs = gain / loss.replace(0, np.nan)
    rsi = 100 - (100 / (1 + rs))
    mom_5d = c.pct_change(5)
    # 20日线性回归斜率（标准化）
    slope_20 = c.rolling(20).apply(lambda x: np.polyfit(range(len(x)), x, 1)[0] / x.mean() if len(x)==20 else np.nan, raw=False)
    factors['trend'] = (rsi / 100) * 0.4 + (mom_5d.rank(pct=True)) * 0.3 + (slope_20.rank(pct=True)) * 0.3
    
    # === 量价因子 ===
    hl_range = (h - l).replace(0, np.nan)
    net_flow = ((c - l) / hl_range - (h - c) / hl_range) * v
    fund_flow_5d = net_flow.rolling(5).sum() / v.rolling(5).sum()
    vol_ratio = v / v.rolling(5).mean()  # 量比
    factors['volume'] = (fund_flow_5d.rank(pct=True)) * 0.6 + (vol_ratio.clip(0, 3).rank(pct=True)) * 0.4
    
    # === 基本面因子（用波动率+换手稳定性代理） ===
    ret_20d = c.pct_change(20)
    volatility_20 = c.pct_change().rolling(20).std()
    # 低波动 = 高质量（取反）
    vol_score = 1 - volatility_20.rank(pct=True)
    # 成交量稳定性（变异系数取反）
    vol_cv = v.rolling(20).std() / v.rolling(20).mean().replace(0, np.nan)
    stability_score = 1 - vol_cv.rank(pct=True)
    factors['fundamental'] = vol_score * 0.5 + stability_score * 0.5
    
    # === 情绪因子 ===
    ma20 = c.rolling(20).mean()
    bias_20 = (c - ma20) / ma20  # 乖离率
    # 适度乖离(0-10%)得分高，极端乖离(>15%或<-10%)得分低
    bias_score = 1 - (bias_20.abs().rank(pct=True))
    # RSI超卖反转机会（RSI<30得分高）
    rsi_contrarian = (100 - rsi) / 100  # RSI越低，逆向得分越高
    factors['sentiment'] = bias_score * 0.5 + rsi_contrarian * 0.5
    
    return factors

def run_portfolio_backtest(all_factors, all_returns, weights, common_dates):
    """用指定权重配置执行回测"""
    rebalance_dates = common_dates[::REBALANCE]
    portfolio_returns = []
    
    for i in range(len(rebalance_dates) - 1):
        reb_date = rebalance_dates[i]
        next_date = rebalance_dates[i + 1]
        
        # 截面打分
        scores = {}
        for code, f in all_factors.items():
            if reb_date not in f.index:
                continue
            row = f.loc[reb_date]
            score = 0
            for dim, w in weights.items():
                val = row.get(dim, np.nan)
                if not np.isnan(val):
                    score += val * w
            if not np.isnan(score):
                scores[code] = score
        
        if len(scores) < TOP_N:
            continue
        
        # 选Top N
        ranked = sorted(scores.items(), key=lambda x: x[1], reverse=True)
        selected = [code for code, _ in ranked[:TOP_N]]
        
        # 持有期收益
        period_dates = [d for d in common_dates if reb_date < d <= next_date]
        if not period_dates:
            continue
        
        period_ret = 0
        valid_count = 0
        for code in selected:
            if code in all_returns:
                rets = all_returns[code]
                valid_rets = [rets[d] for d in period_dates if d in rets.index and not np.isnan(rets.get(d, np.nan))]
                if valid_rets:
                    period_ret += np.prod([1 + r for r in valid_rets]) - 1
                    valid_count += 1
        
        if valid_count > 0:
            period_ret /= valid_count
        else:
            period_ret = 0
            
        portfolio_returns.append({'date': next_date, 'return': period_ret, 'holdings': selected})
    
    if len(portfolio_returns) < 10:
        return None
    
    rets = np.array([r['return'] for r in portfolio_returns])
    total_return = np.prod(1 + rets) - 1
    n_periods = len(rets)
    years = n_periods * REBALANCE / 252
    annual_return = (1 + total_return) ** (1 / max(years, 0.1)) - 1 if years > 0 else 0
    win_rate = np.sum(rets > 0) / len(rets)
    
    cum = np.cumprod(1 + rets)
    peak = np.maximum.accumulate(cum)
    drawdown = (cum - peak) / peak
    max_dd = np.min(drawdown)
    
    mean_ret = np.mean(rets)
    std_ret = np.std(rets)
    sharpe = (mean_ret / std_ret) * np.sqrt(252 / REBALANCE) if std_ret > 0 else 0
    
    return {
        'total_return': float(total_return),
        'annual_return': float(annual_return),
        'win_rate': float(win_rate),
        'max_drawdown': float(max_dd),
        'sharpe': float(sharpe),
        'n_periods': n_periods,
        'years': float(years),
        'period_returns': rets.tolist(),
        'cum_curve': cum.tolist(),
        'dates': [str(r['date'])[:10] for r in portfolio_returns],
    }

# ============ 主流程 ============
print("=" * 70)
print("  多因子Alpha策略 × 10种组合 × 3年回测 + 蒙特卡洛")
print("  股票池: A股主板（排除创业板/科创板）")
print("  回测区间: 2023-08-01 ~ 2026-08-01")
print("=" * 70)

# Step 1: 加载股票池，随机抽取200只
print("\n[Step 1] 加载主板股票池...")
with open(f'{CACHE_DIR}/main_board_codes.pkl', 'rb') as f:
    all_codes = pickle.load(f)
print(f"  主板总量: {len(all_codes)} 只")

np.random.seed(2026)
sampled_codes = np.random.choice(all_codes, size=N_STOCKS, replace=False).tolist()
print(f"  抽样操作池: {N_STOCKS} 只")

# Step 2: 批量拉取3年数据
print(f"\n[Step 2] 拉取3年日线数据（{N_STOCKS}只）...")
data_dict = {}
failed = 0
for i, code in enumerate(sampled_codes):
    df = fetch_daily(code)
    if df is not None and len(df) > 200:
        data_dict[code] = df
    else:
        failed += 1
    if (i + 1) % 50 == 0:
        print(f"  进度: {i+1}/{N_STOCKS} | 成功: {len(data_dict)} | 失败: {failed}")
    time.sleep(0.25)

print(f"  最终获取: {len(data_dict)} 只有效数据")

if len(data_dict) < 30:
    print("❌ 数据不足，无法继续")
    exit(1)

# Step 3: 计算四因子
print(f"\n[Step 3] 计算四维因子...")
all_factors = {}
all_returns = {}
for code, df in data_dict.items():
    try:
        f = calc_four_factors(df)
        f = f.dropna()
        if len(f) > 60:
            all_factors[code] = f
            all_returns[code] = df['close'].pct_change()
    except:
        pass

print(f"  因子计算完成: {len(all_factors)} 只")

# 公共日期
common_dates = None
for code, f in all_factors.items():
    idx = set(f.index)
    common_dates = idx if common_dates is None else (common_dates & idx)
common_dates = sorted(list(common_dates))
print(f"  公共交易日: {len(common_dates)} 天 ({common_dates[0].strftime('%Y-%m-%d')} ~ {common_dates[-1].strftime('%Y-%m-%d')})")

# Step 4: 10种权重配置回测
print(f"\n[Step 4] 执行10种组合回测...")
results = {}
all_period_returns = []

for name, weights in PORTFOLIO_CONFIGS.items():
    bt = run_portfolio_backtest(all_factors, all_returns, weights, common_dates)
    if bt:
        results[name] = bt
        all_period_returns.extend(bt['period_returns'])
        print(f"  {name}: 年化{bt['annual_return']*100:+.1f}% | 胜率{bt['win_rate']*100:.0f}% | 回撤{bt['max_drawdown']*100:.1f}% | 夏普{bt['sharpe']:.2f}")
    else:
        results[name] = None
        print(f"  {name}: 回测失败")

# Step 5: 蒙特卡洛模拟
print(f"\n[Step 5] 蒙特卡洛模拟 (10000次 × 3年)...")
all_period_returns = np.array(all_period_returns)
print(f"  收益样本池: {len(all_period_returns)} 期")
print(f"  样本均值: {np.mean(all_period_returns)*100:.3f}%/期")
print(f"  样本标准差: {np.std(all_period_returns)*100:.3f}%/期")

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

# Step 6: 保存
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
        'configs': PORTFOLIO_CONFIGS
    }
}

with open(f'{CACHE_DIR}/mc_results_full.pkl', 'wb') as f:
    pickle.dump(output, f)

print(f"\n✅ 全部完成，结果已保存")
