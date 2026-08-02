"""
10组合 × 3年多因子回测 + 蒙特卡洛模拟
数据源：AkShare 新浪源（稳定）
因子：RSI_14 / Bollinger位置 / 5日动量 / 5日资金流
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
TOP_N = 5          # 每期持有Top5
REBALANCE = 5      # 每5个交易日调仓
WEIGHTS = {'rsi_14': 0.294, 'boll_pos': 0.289, 'mom_5d': 0.246, 'fund_flow_5d': 0.172}

# ============ 10种组合（硬编码，覆盖不同风格） ============
POOLS = {
    '沪深300_大盘蓝筹': ['600519','601318','600036','000858','600276','601166','000333',
        '600900','601888','600809','000568','002714','600585','601012','300750',
        '600030','601668','000002','600104','601398'],
    '中证500_中盘成长': ['002049','300014','002129','300124','002371','300033','002460',
        '300122','002241','300059','002032','300142','002600','300070','002180',
        '300136','002405','300088','002252','300168'],
    '上证50_超大盘': ['600519','601318','600036','600276','601166','600900','601888',
        '600809','600585','601012','600030','601668','600104','601398','600887',
        '601899','600000','601288','600048','601601'],
    'TMT_科技': ['002230','300059','002415','300033','002236','300124','002049','300188',
        '002405','300253','002241','300315','002439','300369','002555',
        '300418','002602','300433','002624','300454'],
    '消费_内需': ['600519','000858','600809','000568','600887','002714','000895','603288',
        '600600','002557','000876','600298','002507','603027','600132',
        '000729','600660','002568','600702','000860'],
    '医药_健康': ['600276','300760','000538','300122','002007','300347','600196','300529',
        '002001','300558','600436','300595','002223','300601','600763',
        '300628','002252','300676','600867','300759'],
    '新能源_碳中和': ['300750','002594','601012','300274','002459','300014','600438','002129',
        '300763','601865','002074','300316','600905','002709','300450',
        '601615','002812','300457','601877','002850'],
    '金融_低估值': ['601318','600036','601166','600030','601398','601288','600000','601601',
        '601857','601088','600016','601688','600015','601211','600999',
        '601377','600837','601878','600908','601838'],
    '随机组合A_seed42': ['000001','000063','000100','000157','000333','000425','000538',
        '000568','000596','000625','000651','000661','000703','000725',
        '000768','000776','000800','000807','000831','000858'],
    '随机组合B_seed2026': ['002001','002007','002008','002024','002027','002032','002044',
        '002049','002050','002056','002064','002065','002074','002078',
        '002080','002093','002120','002127','002129','002138'],
}

def get_prefix(code):
    code = str(code).zfill(6)
    if code.startswith('6'):
        return 'sh'
    return 'sz'

def fetch_daily(code):
    """获取单只股票3年日线（新浪源）"""
    prefix = get_prefix(code)
    symbol = f"{prefix}{code}"
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
        # 确保有基本列
        for col in ['open','high','low','close','volume']:
            if col not in df.columns:
                return None
        return df[['open','high','low','close','volume']].copy()
    except Exception as e:
        return None

def calc_factors(df):
    """计算四因子"""
    c, h, l, v = df['close'], df['high'], df['low'], df['volume']
    factors = pd.DataFrame(index=df.index)
    
    # RSI_14
    delta = c.diff()
    gain = delta.clip(lower=0).rolling(14).mean()
    loss = (-delta.clip(upper=0)).rolling(14).mean()
    rs = gain / loss.replace(0, np.nan)
    factors['rsi_14'] = 100 - (100 / (1 + rs))
    
    # Bollinger位置
    ma20 = c.rolling(20).mean()
    std20 = c.rolling(20).std()
    factors['boll_pos'] = (c - (ma20 - 2*std20)) / (4*std20)
    
    # 5日动量
    factors['mom_5d'] = c.pct_change(5)
    
    # 5日资金流（量价代理）
    hl_range = (h - l).replace(0, np.nan)
    net_flow = ((c - l) / hl_range - (h - c) / hl_range) * v
    factors['fund_flow_5d'] = net_flow.rolling(5).sum() / v.rolling(5).sum()
    
    return factors

def run_backtest(data_dict):
    """对一组股票执行多因子回测"""
    # 计算所有股票的因子
    all_factors = {}
    all_returns = {}
    
    for code, df in data_dict.items():
        if df is None or len(df) < 60:
            continue
        f = calc_factors(df)
        f = f.dropna()
        if len(f) < 30:
            continue
        all_factors[code] = f
        all_returns[code] = df['close'].pct_change()
    
    if len(all_factors) < 5:
        return None
    
    # 获取公共日期
    common_dates = None
    for code, f in all_factors.items():
        idx = set(f.index)
        if common_dates is None:
            common_dates = idx
        else:
            common_dates = common_dates & idx
    
    if common_dates is None or len(common_dates) < 60:
        return None
    
    common_dates = sorted(list(common_dates))
    
    # 每期调仓
    portfolio_returns = []
    rebalance_dates = common_dates[::REBALANCE]
    
    for i in range(len(rebalance_dates) - 1):
        reb_date = rebalance_dates[i]
        next_date = rebalance_dates[i + 1]
        
        # 在调仓日计算综合得分
        scores = {}
        for code, f in all_factors.items():
            if reb_date in f.index:
                row = f.loc[reb_date]
                score = 0
                for factor_name, weight in WEIGHTS.items():
                    val = row.get(factor_name, np.nan)
                    if not np.isnan(val):
                        # 截面标准化后加权
                        score += val * weight
                scores[code] = score
        
        if len(scores) < TOP_N:
            continue
        
        # 选Top N
        ranked = sorted(scores.items(), key=lambda x: x[1], reverse=True)
        selected = [code for code, _ in ranked[:TOP_N]]
        
        # 计算持有期收益
        period_dates = [d for d in common_dates if reb_date < d <= next_date]
        if not period_dates:
            continue
        
        period_ret = 0
        for code in selected:
            if code in all_returns:
                rets = all_returns[code]
                valid_rets = [rets[d] for d in period_dates if d in rets.index and not np.isnan(rets.get(d, np.nan))]
                if valid_rets:
                    period_ret += np.prod([1 + r for r in valid_rets]) - 1
        
        period_ret /= TOP_N  # 等权
        portfolio_returns.append({
            'date': next_date,
            'return': period_ret,
            'holdings': selected
        })
    
    if len(portfolio_returns) < 10:
        return None
    
    # 计算绩效指标
    rets = [r['return'] for r in portfolio_returns]
    rets = np.array(rets)
    
    total_return = np.prod(1 + rets) - 1
    n_periods = len(rets)
    years = n_periods * REBALANCE / 252
    annual_return = (1 + total_return) ** (1 / max(years, 0.1)) - 1 if years > 0 else 0
    
    # 胜率
    win_rate = np.sum(rets > 0) / len(rets)
    
    # 最大回撤
    cum = np.cumprod(1 + rets)
    peak = np.maximum.accumulate(cum)
    drawdown = (cum - peak) / peak
    max_dd = np.min(drawdown)
    
    # 夏普比率（年化）
    mean_ret = np.mean(rets)
    std_ret = np.std(rets)
    sharpe = (mean_ret / std_ret) * np.sqrt(252 / REBALANCE) if std_ret > 0 else 0
    
    # 日频收益序列（用于蒙特卡洛）
    daily_rets = []
    for r in portfolio_returns:
        period_dates_list = [d for d in common_dates if r['date'] == r['date']]
        daily_rets.extend([r['return'] / REBALANCE] * REBALANCE)
    
    return {
        'total_return': total_return,
        'annual_return': annual_return,
        'win_rate': win_rate,
        'max_drawdown': max_dd,
        'sharpe': sharpe,
        'n_periods': n_periods,
        'years': years,
        'period_returns': rets.tolist(),
        'portfolio_history': portfolio_returns
    }

# ============ 主流程 ============
print("=" * 70)
print("  10组合 × 3年多因子回测 + 蒙特卡洛模拟")
print("  回测区间: 2023-08-01 ~ 2026-08-01")
print("  因子: RSI_14 / Bollinger / 5日动量 / 5日资金流")
print("  调仓: 每5日 | 持仓: Top5等权")
print("=" * 70)

results = {}
all_period_returns = []  # 收集所有组合的期收益，用于蒙特卡洛

for pool_name, codes in POOLS.items():
    print(f"\n{'─' * 50}")
    print(f"▶ {pool_name} ({len(codes)} 只)")
    print(f"{'─' * 50}")
    
    # 拉取数据
    data_dict = {}
    success = 0
    for code in codes:
        df = fetch_daily(code)
        if df is not None and len(df) > 100:
            data_dict[code] = df
            success += 1
        time.sleep(0.3)
    
    print(f"  数据获取: {success}/{len(codes)} 只成功")
    
    if success < 8:
        print(f"  ⚠️ 数据不足，跳过")
        results[pool_name] = None
        continue
    
    # 回测
    bt = run_backtest(data_dict)
    if bt is None:
        print(f"  ⚠️ 回测失败")
        results[pool_name] = None
        continue
    
    results[pool_name] = bt
    all_period_returns.extend(bt['period_returns'])
    
    print(f"  年化收益: {bt['annual_return']*100:.2f}%")
    print(f"  胜率: {bt['win_rate']*100:.1f}%")
    print(f"  最大回撤: {bt['max_drawdown']*100:.2f}%")
    print(f"  夏普比率: {bt['sharpe']:.2f}")
    print(f"  调仓次数: {bt['n_periods']}")

# ============ 蒙特卡洛模拟 ============
print("\n" + "=" * 70)
print("  蒙特卡洛模拟 (10000次)")
print("=" * 70)

all_period_returns = np.array(all_period_returns)
print(f"\n  样本池: {len(all_period_returns)} 期收益")
print(f"  均值: {np.mean(all_period_returns)*100:.3f}%")
print(f"  标准差: {np.std(all_period_returns)*100:.3f}%")

# 模拟参数
N_SIM = 10000
PERIODS_PER_YEAR = int(252 / REBALANCE)  # ~50期/年
SIM_YEARS = 3
TOTAL_PERIODS = PERIODS_PER_YEAR * SIM_YEARS

np.random.seed(42)
mc_results = np.zeros((N_SIM, TOTAL_PERIODS))

for i in range(N_SIM):
    # 有放回抽样
    sampled = np.random.choice(all_period_returns, size=TOTAL_PERIODS, replace=True)
    mc_results[i] = np.cumprod(1 + sampled) - 1

# 统计
final_returns = mc_results[:, -1]
annual_returns_mc = (1 + final_returns) ** (1/SIM_YEARS) - 1

# 最大回撤分布
mc_max_dd = np.zeros(N_SIM)
for i in range(N_SIM):
    cum = 1 + mc_results[i]
    peak = np.maximum.accumulate(cum)
    dd = (cum - peak) / peak
    mc_max_dd[i] = np.min(dd)

# 胜率分布（年度正收益概率）
mc_yearly = mc_results[:, PERIODS_PER_YEAR-1::PERIODS_PER_YEAR]
mc_win_rates = np.mean(mc_yearly > np.concatenate([np.zeros((N_SIM,1)), mc_yearly[:,:-1]], axis=1), axis=1)

print(f"\n  === 3年期蒙特卡洛结果 ===")
print(f"  年化收益 P5:  {np.percentile(annual_returns_mc, 5)*100:.2f}%")
print(f"  年化收益 P25: {np.percentile(annual_returns_mc, 25)*100:.2f}%")
print(f"  年化收益 P50: {np.percentile(annual_returns_mc, 50)*100:.2f}%")
print(f"  年化收益 P75: {np.percentile(annual_returns_mc, 75)*100:.2f}%")
print(f"  年化收益 P95: {np.percentile(annual_returns_mc, 95)*100:.2f}%")
print(f"\n  最大回撤 P5:  {np.percentile(mc_max_dd, 5)*100:.2f}%")
print(f"  最大回撤 P50: {np.percentile(mc_max_dd, 50)*100:.2f}%")
print(f"  最大回撤 P95: {np.percentile(mc_max_dd, 95)*100:.2f}%")
print(f"\n  3年总收益 P5:  {np.percentile(final_returns, 5)*100:.2f}%")
print(f"  3年总收益 P50: {np.percentile(final_returns, 50)*100:.2f}%")
print(f"  3年总收益 P95: {np.percentile(final_returns, 95)*100:.2f}%")

# 亏损概率
loss_prob = np.mean(final_returns < 0)
print(f"\n  3年亏损概率: {loss_prob*100:.1f}%")
print(f"  年化>20%概率: {np.mean(annual_returns_mc > 0.20)*100:.1f}%")
print(f"  年化>50%概率: {np.mean(annual_returns_mc > 0.50)*100:.1f}%")

# ============ 保存结果 ============
output = {
    'results': results,
    'mc_annual_returns': annual_returns_mc.tolist(),
    'mc_max_dd': mc_max_dd.tolist(),
    'mc_final_returns': final_returns.tolist(),
    'mc_curves': mc_results[::100].tolist(),  # 每100条取一条用于画图
    'all_period_returns': all_period_returns.tolist(),
    'params': {
        'start': START_DATE, 'end': END_DATE,
        'top_n': TOP_N, 'rebalance': REBALANCE,
        'n_sim': N_SIM, 'sim_years': SIM_YEARS,
        'weights': WEIGHTS
    }
}

with open(f'{CACHE_DIR}/mc_results.pkl', 'wb') as f:
    pickle.dump(output, f)

print(f"\n✅ 结果已保存到 {CACHE_DIR}/mc_results.pkl")
