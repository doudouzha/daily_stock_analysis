"""
Step 1: 用财务数据筛选A股主板优质公司
筛选条件：ROE>10%、净利润为正、营收正增长、非ST、流动性充足
"""
import akshare as ak
import pandas as pd
import numpy as np
import pickle
import os
import time
import warnings
warnings.filterwarnings('ignore')

CACHE_DIR = '/tmp/mc_cache'
os.makedirs(CACHE_DIR, exist_ok=True)

# 加载主板股票池
with open(f'{CACHE_DIR}/main_board_codes.pkl', 'rb') as f:
    main_board = pickle.load(f)
with open(f'{CACHE_DIR}/name_map.pkl', 'rb') as f:
    name_map = pickle.load(f)

print(f"主板股票池: {len(main_board)} 只")

# ============ 方法1: 业绩报表（东财，一次拉全量） ============
print("\n[尝试] 获取最新业绩报表...")
yjbb = None
for date in ['20260331', '20251231', '20250930']:
    try:
        df = ak.stock_yjbb_em(date=date)
        if df is not None and len(df) > 100:
            yjbb = df
            print(f"  成功: {date} | {len(df)} 条记录")
            print(f"  列名: {df.columns.tolist()[:15]}")
            break
    except Exception as e:
        print(f"  {date} 失败: {e}")
    time.sleep(1)

if yjbb is not None:
    # 筛选主板
    yjbb['股票代码'] = yjbb['股票代码'].astype(str).str.zfill(6)
    yjbb_main = yjbb[yjbb['股票代码'].isin(main_board)].copy()
    print(f"\n  主板匹配: {len(yjbb_main)} 只")
    
    # 查看可用列
    print(f"  所有列: {yjbb_main.columns.tolist()}")
    
    # 筛选条件
    quality = yjbb_main.copy()
    
    # 1. 排除ST
    if '股票简称' in quality.columns:
        quality = quality[~quality['股票简称'].str.contains('ST|退', na=False)]
        print(f"  排除ST后: {len(quality)}")
    
    # 2. ROE > 10%
    roe_col = None
    for col in ['净资产收益率(%)', '加权净资产收益率(%)', 'roe']:
        if col in quality.columns:
            roe_col = col
            break
    if roe_col:
        quality[roe_col] = pd.to_numeric(quality[roe_col], errors='coerce')
        quality = quality[quality[roe_col] > 10]
        print(f"  ROE>10%: {len(quality)} (列: {roe_col})")
    
    # 3. 净利润为正
    profit_col = None
    for col in ['净利润(元)', '净利润', '归母净利润(元)']:
        if col in quality.columns:
            profit_col = col
            break
    if profit_col:
        quality[profit_col] = pd.to_numeric(quality[profit_col], errors='coerce')
        quality = quality[quality[profit_col] > 0]
        print(f"  净利润>0: {len(quality)} (列: {profit_col})")
    
    # 4. 营收正增长
    rev_col = None
    for col in ['营业收入同比增长(%)', '营业收入-同比增长(%)', '营收同比']:
        if col in quality.columns:
            rev_col = col
            break
    if rev_col:
        quality[rev_col] = pd.to_numeric(quality[rev_col], errors='coerce')
        quality = quality[quality[rev_col] > 0]
        print(f"  营收正增长: {len(quality)} (列: {rev_col})")
    
    # 5. 每股收益 > 0.3
    eps_col = None
    for col in ['基本每股收益(元)', '每股收益']:
        if col in quality.columns:
            eps_col = col
            break
    if eps_col:
        quality[eps_col] = pd.to_numeric(quality[eps_col], errors='coerce')
        quality = quality[quality[eps_col] > 0.3]
        print(f"  EPS>0.3: {len(quality)} (列: {eps_col})")
    
    quality_codes = quality['股票代码'].tolist()
    print(f"\n✅ 业绩筛选后优质股: {len(quality_codes)} 只")
    
    # 保存
    with open(f'{CACHE_DIR}/quality_codes.pkl', 'wb') as f:
        pickle.dump(quality_codes, f)
    
    # 打印前20只
    if '股票简称' in quality.columns:
        print("\n  前20只:")
        for _, row in quality.head(20).iterrows():
            code = row['股票代码']
            name = row.get('股票简称', name_map.get(code, ''))
            roe_val = row.get(roe_col, '') if roe_col else ''
            print(f"    {code} {name} ROE={roe_val}")

else:
    print("\n[备选] 业绩报表接口不可用，用名称+价格筛选...")
    # 备选：排除ST，后续用价格数据做流动性筛选
    quality_codes = [c for c in main_board if 'ST' not in name_map.get(c, '') and '退' not in name_map.get(c, '')]
    print(f"  排除ST后: {len(quality_codes)} 只")
    with open(f'{CACHE_DIR}/quality_codes.pkl', 'wb') as f:
        pickle.dump(quality_codes, f)

print(f"\n最终优质池: {len(quality_codes)} 只，已保存")
