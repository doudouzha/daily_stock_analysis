"""
Step 1: 定义10种投资组合，获取成分股，拉取3年日线数据
数据源：AkShare 新浪源（稳定）+ 中证指数成分股
"""
import akshare as ak
import pandas as pd
import numpy as np
import time
import pickle
import os
from datetime import datetime

# ============ 配置 ============
START_DATE = '20230801'
END_DATE = '20260801'
STOCKS_PER_POOL = 25  # 每组取25只，控制数据量
CACHE_DIR = '/tmp/mc_cache'
os.makedirs(CACHE_DIR, exist_ok=True)

def get_prefix(code):
    """判断沪深前缀"""
    code = str(code).zfill(6)
    if code.startswith('6'):
        return 'sh'
    elif code.startswith(('0', '3')):
        return 'sz'
    elif code.startswith('688'):
        return 'sh'
    return 'sh'

def fetch_daily(code, start=START_DATE, end=END_DATE):
    """获取单只股票日线（新浪源）"""
    prefix = get_prefix(code)
    symbol = f"{prefix}{code}"
    try:
        df = ak.stock_zh_a_daily(symbol=symbol, start_date=start, end_date=end, adjust='qfq')
        if df is None or df.empty:
            return None
        if not isinstance(df.index, pd.DatetimeIndex):
            if 'date' in df.columns:
                df['date'] = pd.to_datetime(df['date'])
                df = df.set_index('date')
            else:
                df.index = pd.to_datetime(df.index)
        return df
    except Exception as e:
        return None

# ============ 定义10种组合 ============
print("=" * 60)
print("定义10种投资组合")
print("=" * 60)

pools = {}

# 组合1: 沪深300（大盘蓝筹）
print("\n[1/10] 沪深300...")
try:
    df_hs300 = ak.index_stock_cons_csindex(symbol="000300")
    codes = df_hs300['成分券代码'].tolist()[:STOCKS_PER_POOL]
    pools['沪深300_大盘蓝筹'] = [str(c).zfill(6) for c in codes]
    print(f"  获取 {len(pools['沪深300_大盘蓝筹'])} 只")
except Exception as e:
    print(f"  失败: {e}, 使用备用")
    pools['沪深300_大盘蓝筹'] = ['600519','601318','600036','000858','600276',
        '601166','000333','600900','601888','600809','000568','002714',
        '600585','601012','300750','600030','601668','000002','600104',
        '601398','600887','000651','600031','601899','002415']

time.sleep(1)

# 组合2: 中证500（中盘成长）
print("[2/10] 中证500...")
try:
    df_zz500 = ak.index_stock_cons_csindex(symbol="000905")
    codes = df_zz500['成分券代码'].tolist()[:STOCKS_PER_POOL]
    pools['中证500_中盘成长'] = [str(c).zfill(6) for c in codes]
    print(f"  获取 {len(pools['中证500_中盘成长'])} 只")
except Exception as e:
    print(f"  失败: {e}")
    pools['中证500_中盘成长'] = ['002049','300014','002129','300124','002371',
        '300033','002460','300122','002241','300059','002032','300142',
        '002600','300070','002180','300136','002405','300088','002252',
        '300168','002093','300207','002500','300251','002340']

time.sleep(1)

# 组合3: 上证50（超大盘）
print("[3/10] 上证50...")
try:
    df_sz50 = ak.index_stock_cons_csindex(symbol="000016")
    codes = df_sz50['成分券代码'].tolist()[:STOCKS_PER_POOL]
    pools['上证50_超大盘'] = [str(c).zfill(6) for c in codes]
    print(f"  获取 {len(pools['上证50_超大盘'])} 只")
except Exception as e:
    print(f"  失败: {e}")
    pools['上证50_超大盘'] = ['600519','601318','600036','600276','601166',
        '600900','601888','600809','600585','601012','600030','601668',
        '600104','601398','600887','601899','600000','601288','600048',
        '601601','600050','601857','600196','601088','600309']

time.sleep(1)

# 组合4: TMT/科技
print("[4/10] TMT科技...")
try:
    df_tmt = ak.index_stock_cons_csindex(symbol="000998")
    codes = df_tmt['成分券代码'].tolist()[:STOCKS_PER_POOL]
    pools['TMT_科技'] = [str(c).zfill(6) for c in codes]
    print(f"  获取 {len(pools['TMT_科技'])} 只")
except Exception as e:
    print(f"  失败: {e}")
    pools['TMT_科技'] = ['002230','300059','002415','300033','002236',
        '300124','002049','300188','002405','300253','002241','300315',
        '002439','300369','002555','300418','002602','300433','002624',
        '300454','002714','300496','002841','300502','002920']

time.sleep(1)

# 组合5: 消费
print("[5/10] 消费...")
try:
    df_xf = ak.index_stock_cons_csindex(symbol="000932")
    codes = df_xf['成分券代码'].tolist()[:STOCKS_PER_POOL]
    pools['消费_内需'] = [str(c).zfill(6) for c in codes]
    print(f"  获取 {len(pools['消费_内需'])} 只")
except Exception as e:
    print(f"  失败: {e}")
    pools['消费_内需'] = ['600519','000858','600809','000568','600887',
        '002714','000895','603288','600600','002557','000876','600298',
        '002507','603027','600132','000729','600660','002568','600702',
        '000860','603345','600872','002695','603517','600419']

time.sleep(1)

# 组合6: 医药
print("[6/10] 医药...")
try:
    df_yy = ak.index_stock_cons_csindex(symbol="000933")
    codes = df_yy['成分券代码'].tolist()[:STOCKS_PER_POOL]
    pools['医药_健康'] = [str(c).zfill(6) for c in codes]
    print(f"  获取 {len(pools['医药_健康'])} 只")
except Exception as e:
    print(f"  失败: {e}")
    pools['医药_健康'] = ['600276','300760','000538','300122','002007',
        '300347','600196','300529','002001','300558','600436','300595',
        '002223','300601','600763','300628','002252','300676','600867',
        '300759','002422','300760','601607','300832','002821']

time.sleep(1)

# 组合7: 新能源
print("[7/10] 新能源...")
try:
    df_xny = ak.index_stock_cons_csindex(symbol="399808")
    codes = df_xny['成分券代码'].tolist()[:STOCKS_PER_POOL]
    pools['新能源_碳中和'] = [str(c).zfill(6) for c in codes]
    print(f"  获取 {len(pools['新能源_碳中和'])} 只")
except Exception as e:
    print(f"  失败: {e}")
    pools['新能源_碳中和'] = ['300750','002594','601012','300274','002459',
        '300014','600438','002129','300763','601865','002074','300316',
        '600905','002709','300450','601615','002812','300457','601877',
        '002850','300568','603659','002916','300618','603799']

time.sleep(1)

# 组合8: 金融
print("[8/10] 金融...")
try:
    df_jr = ak.index_stock_cons_csindex(symbol="000934")
    codes = df_jr['成分券代码'].tolist()[:STOCKS_PER_POOL]
    pools['金融_低估值'] = [str(c).zfill(6) for c in codes]
    print(f"  获取 {len(pools['金融_低估值'])} 只")
except Exception as e:
    print(f"  失败: {e}")
    pools['金融_低估值'] = ['601318','600036','601166','600030','601398',
        '601288','600000','601601','601857','601088','600016','601688',
        '600015','601211','600999','601377','600837','601878','600908',
        '601838','600919','601916','600926','601990','600958']

time.sleep(1)

# 组合9: 随机组合A（全市场随机抽样）
print("[9/10] 随机组合A...")
try:
    df_all = ak.stock_info_a_code_name()
    all_codes = df_all['code'].tolist()
    # 过滤ST和退市
    all_codes = [c for c in all_codes if not c.startswith('4') and not c.startswith('8')]
    np.random.seed(42)
    sampled = np.random.choice(all_codes, size=STOCKS_PER_POOL, replace=False).tolist()
    pools['随机组合A_seed42'] = [str(c).zfill(6) for c in sampled]
    print(f"  获取 {len(pools['随机组合A_seed42'])} 只")
except Exception as e:
    print(f"  失败: {e}")
    np.random.seed(42)
    pools['随机组合A_seed42'] = [str(c).zfill(6) for c in 
        np.random.choice([f'{i:06d}' for i in range(1, 3000)], 25, replace=False)]

time.sleep(1)

# 组合10: 随机组合B（另一组随机）
print("[10/10] 随机组合B...")
np.random.seed(2026)
try:
    sampled2 = np.random.choice(all_codes, size=STOCKS_PER_POOL, replace=False).tolist()
    pools['随机组合B_seed2026'] = [str(c).zfill(6) for c in sampled2]
    print(f"  获取 {len(pools['随机组合B_seed2026'])} 只")
except:
    pools['随机组合B_seed2026'] = [str(c).zfill(6) for c in 
        np.random.choice([f'{i:06d}' for i in range(1, 3000)], 25, replace=False)]

# ============ 汇总 ============
print("\n" + "=" * 60)
print("10种组合定义完成:")
for name, codes in pools.items():
    print(f"  {name}: {len(codes)} 只")
print("=" * 60)

# 保存组合定义
with open(f'{CACHE_DIR}/pools.pkl', 'wb') as f:
    pickle.dump(pools, f)

print("\n组合定义已保存到 /tmp/mc_cache/pools.pkl")
