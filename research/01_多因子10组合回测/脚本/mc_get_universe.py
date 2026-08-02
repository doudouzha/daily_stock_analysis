"""
Step 1: 获取A股全量主板股票（排除创业板300/科创板688）
"""
import akshare as ak
import pandas as pd
import pickle
import os

CACHE_DIR = '/tmp/mc_cache'
os.makedirs(CACHE_DIR, exist_ok=True)

print("获取A股全量股票列表...")
df = ak.stock_info_a_code_name()
print(f"全量: {len(df)} 只")
print(f"列名: {df.columns.tolist()}")
print(df.head())

# 过滤：只保留主板
# 沪市主板: 600xxx, 601xxx, 603xxx, 605xxx
# 深市主板: 000xxx, 001xxx, 002xxx
# 排除: 300xxx(创业板), 688xxx(科创板), 4xx/8xx(北交所)
codes = df['code'].astype(str).str.zfill(6).tolist()

main_board = []
for c in codes:
    if c.startswith(('600', '601', '603', '605')):  # 沪市主板
        main_board.append(c)
    elif c.startswith(('000', '001', '002')):  # 深市主板
        main_board.append(c)
    # 排除 300(创业板), 688(科创板), 4/8(北交所)

print(f"\n主板股票（排除创业板+科创板）: {len(main_board)} 只")
print(f"  沪市主板: {sum(1 for c in main_board if c.startswith('6'))} 只")
print(f"  深市主板: {sum(1 for c in main_board if c.startswith('0'))} 只")

# 保存
with open(f'{CACHE_DIR}/main_board_codes.pkl', 'wb') as f:
    pickle.dump(main_board, f)

# 也保存名称映射
name_map = dict(zip(df['code'].astype(str).str.zfill(6), df['name']))
with open(f'{CACHE_DIR}/name_map.pkl', 'wb') as f:
    pickle.dump(name_map, f)

print(f"\n✅ 已保存 {len(main_board)} 只主板股票代码")
print(f"示例: {main_board[:10]}")
