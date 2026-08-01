---
name: ashare_data_sources
display_name: A股数据接口选型
description: A股数据接口选型手册，覆盖新浪日线、指数成分股、同花顺资金流、东财千股千评舆情、涨停池、名称查询等十大板块，含不可用接口黑名单、批量拉取模板、缓存策略与稳定性评级表。
category: general
aliases: [数据源, 接口选型, A股数据, 拉数据, 数据接口]
default_active: false
user_invocable: true
default_priority: 90
---

> A股数据接口选型手册 — 覆盖日线、资金流、舆情、涨停池等核心场景，含可用性验证与稳定性评级

## 触发条件

当需要拉取 A 股市场数据时自动参照本 skill：
- 选择数据接口获取行情/K线/资金流/舆情等数据
- 判断某个接口是否可用、是否被列入黑名单
- 设计批量数据拉取方案
- 评估数据源稳定性并制定 fallback 策略

---

## 一、新浪日线（Sina Daily K-Line）

### 接口信息

| 项目 | 说明 |
|------|------|
| 端点 | `https://quotes.sina.cn/cn/api/jsonp_v2.php/var/CN_MarketDataService.getKLineData` |
| 方法 | GET |
| 频率限制 | 无明确限制，建议间隔 ≥ 0.5s |
| 数据范围 | 日K/周K/月K，最长约 1023 根 |
| 复权 | 不复权（原始价格） |

### 请求参数

```
symbol=sh600519       # 沪市 sh + 代码，深市 sz + 代码
scale=240             # 240=日K, 1200=周K, 7200=月K
ma=no                 # 是否返回均线
datalen=120           # 返回根数（最大1023）
```

### 响应格式

```json
[
  {"day":"2026-07-31","open":"5.40","high":"5.63","low":"5.40","close":"5.62","volume":"215768669"},
  ...
]
```

### 稳定性

- ✅ 长期可用，无需认证
- ✅ 沪深两市全覆盖
- ⚠️ 不支持前复权/后复权
- ⚠️ 高频调用可能触发临时封禁（建议 ≤ 2次/秒）

---

## 二、指数成分股（Index Constituents）

### 2.1 沪深300 / 上证50 / 中证500（东财接口）

| 项目 | 说明 |
|------|------|
| 端点 | `https://push2.eastmoney.com/api/qt/clist/get` |
| 方法 | GET |
| 认证 | 无需 |

**请求参数**：
```
pn=1&pz=500           # 分页
fs=b:BK0500           # BK0500=沪深300, BK0016=上证50, BK0900=中证500
fields=f12,f14,f2,f3  # 代码,名称,最新价,涨跌幅
```

### 2.2 备用方案（AkShare 封装）

```python
import akshare as ak
# 沪深300成分股
df = ak.index_stock_cons_csindex(symbol="000300")
# 上证50
df = ak.index_stock_cons_csindex(symbol="000016")
```

### 稳定性

- ⚠️ 东财 push2 接口在部分网络环境下频繁 RemoteDisconnected
- ✅ AkShare csindex 接口走中证指数官网，相对稳定
- 建议优先使用 AkShare 封装，东财作为 fallback

---

## 三、同花顺资金流（THS Capital Flow）

### 3.1 个股资金流（AkShare 封装）

```python
import akshare as ak
# 个股资金流向（同花顺源）
df = ak.stock_individual_fund_flow(stock="002027", market="sz")
# 返回：日期、主力净流入、超大单、大单、中单、小单
```

### 3.2 原始接口

| 项目 | 说明 |
|------|------|
| 端点 | `https://data.10jqka.com.cn/funds/ggzjl/` |
| 备用 | `http://data.10jqka.com.cn/funds/ggzjl/board/all/field/zdf/order/desc/page/1/ajax/1/` |
| 认证 | 需 Cookie（自动获取） |
| 频率 | 建议间隔 ≥ 2s |

### 3.3 实时资金流（东财）

```
https://push2.eastmoney.com/api/qt/stock/fflow/kline/get
secid=0.002027&fields1=f1,f2,f3,f7&fields2=f51,f52,f53,f54,f55,f56,f57,f58,f59,f60,f61,f62,f63,f64,f65
klt=1  # 1=分时, 101=日K
```

### 稳定性

- ⚠️ 同花顺有反爬机制，高频访问需处理 Cookie 和验证码
- ⚠️ 东财 push2 接口连接不稳定（RemoteDisconnected 频发）
- ✅ AkShare 封装有内置重试和 fallback
- 建议：AkShare 封装优先，失败后降级到腾讯财经

---

## 四、东财千股千评舆情（Eastmoney Stock Ratings）

### 4.1 可用接口

#### ✅ 接口 A：千股千评列表

| 项目 | 说明 |
|------|------|
| 端点 | `https://emappdata.eastmoney.com/stockcomment/api/XWEB/GetPraiseRate` |
| 方法 | POST |
| Content-Type | application/json |

**请求体**：
```json
{"code": "002027"}
```

**响应**：好评率、关注度、参与人数等

#### ✅ 接口 B：舆情详情（评论列表）

| 项目 | 说明 |
|------|------|
| 端点 | `https://emappdata.eastmoney.com/stockcomment/api/XWEB/GetCommentList` |
| 方法 | POST |

**请求体**：
```json
{"code": "002027", "ps": 20, "p": 1, "type": 0}
```

**响应**：用户评论列表、情绪标签、时间戳

#### ✅ 接口 C：综合评分/诊断

| 项目 | 说明 |
|------|------|
| 端点 | `https://emappdata.eastmoney.com/stockcomment/api/XWEB/GetStockComment` |
| 方法 | POST |

**请求体**：
```json
{"code": "002027"}
```

**响应**：综合评分、主力控盘、资金流向评分、短期/中期趋势评分

### 4.2 不可用接口

#### ❌ 接口 D：GetGPZYData（股权质押详情）

| 项目 | 说明 |
|------|------|
| 端点 | `https://emappdata.eastmoney.com/stockcomment/api/XWEB/GetGPZYData` |
| 状态 | **已下线 / 404** |
| 说明 | 该接口曾用于获取股权质押数据，目前已不存在，调用返回 404 或空响应 |

> ⚠️ 不要调用此接口，质押数据请使用 AkShare `ak.stock_gpzy_pledge_ratio_em()` 替代。

### 稳定性

- ✅ emappdata.eastmoney.com 域名比 push2.eastmoney.com 稳定得多
- ✅ 三个可用接口均无需认证，POST JSON 即可
- ⚠️ 频率限制：建议 ≤ 3次/秒
- 适合做舆情情绪因子的数据源

---

## 五、涨停池（Limit-Up Pool）

### 5.1 东财涨停板行情

| 项目 | 说明 |
|------|------|
| 端点 | `https://push2ex.eastmoney.com/getTopicZTPool` |
| 方法 | GET |
| 参数 | `ut=7eea3edcaed734bea9cbfc24409ed989&dpt=wz.ztzt&Pageindex=0&pagesize=200&sort=fbt%3Aasc&date=20260731` |

**响应字段**：代码、名称、涨停价、封板资金、首次封板时间、连板数、炸板次数

### 5.2 AkShare 封装

```python
import akshare as ak
# 涨停板行情（东财源）
df = ak.stock_zt_pool_em(date="20260731")
# 强势股池（昨日涨停今日未跌停）
df = ak.stock_zt_pool_strong_em(date="20260731")
# 次新股池
df = ak.stock_zt_pool_sub_new_em(date="20260731")
```

### 稳定性

- ⚠️ push2ex 与 push2 同域，存在 RemoteDisconnected 风险
- ✅ AkShare 有 fallback 处理
- 仅交易日有数据，非交易日返回空

---

## 六、名称查询（Stock Name Lookup）

### 6.1 腾讯实时行情（含名称）

```
https://qt.gtimg.cn/q=sh600519,sz002027
```

响应格式：`v_sh600519="1~贵州茅台~600519~1800.00~...";`
第2个字段即为股票名称。

### 6.2 东财搜索建议

```
https://searchapi.eastmoney.com/api/suggest/get
input=600519&type=14&token=D43BF722C8E33BDC906FB84D85E326E8&count=5
```

### 6.3 AkShare 全量列表

```python
import akshare as ak
# A股全部股票列表（代码+名称）
df = ak.stock_info_a_code_name()
```

### 稳定性

- ✅ 腾讯 qt.gtimg.cn 非常稳定（本项目实测 fallback 成功率最高）
- ✅ searchapi.eastmoney.com 稳定
- ✅ AkShare stock_info_a_code_name 走交易所官网，稳定

---

## 七、不可用接口黑名单

以下接口已验证**不可用**，禁止在代码中调用：

| 接口 | 域名 | 失败原因 | 替代方案 |
|------|------|----------|----------|
| GetGPZYData | emappdata.eastmoney.com | 404 已下线 | AkShare stock_gpzy_pledge_ratio_em |
| push2 实时行情 | push2.eastmoney.com | RemoteDisconnected 频发 | 腾讯 qt.gtimg.cn / AkShare 新浪源 |
| push2his 历史K线 | push2his.eastmoney.com | RemoteDisconnected 频发 | AkShare 新浪源 / Baostock |
| push2 板块排行 | push2.eastmoney.com | RemoteDisconnected 频发 | AkShare 新浪板块 ak.stock_sector_spot |
| searx.space 实例列表 | searx.space | 连接超时 | 配置 Tavily/SerpAPI/博查 等付费搜索 |
| efinance 东财系列 | push2/push2his | 底层依赖东财，同样不稳定 | AkShare + 腾讯 fallback |

### 黑名单规则

- 连续 3 次 RemoteDisconnected → 自动熔断 300s
- 熔断期内跳过该数据源，直接走下一优先级
- 黑名单每月复核一次，接口恢复后可移除

---

## 八、批量拉取模板

### 8.1 日线批量（新浪源）

```python
import requests, time

def batch_daily_kline(codes: list[str], days: int = 120) -> dict:
    """批量获取日K线（新浪源）
    codes: ['sh600519', 'sz002027', ...]
    """
    results = {}
    url = "https://quotes.sina.cn/cn/api/jsonp_v2.php/var/CN_MarketDataService.getKLineData"
    for code in codes:
        params = {"symbol": code, "scale": 240, "ma": "no", "datalen": days}
        try:
            resp = requests.get(url, params=params, timeout=10)
            # 解析 jsonp: var=([{...}])
            text = resp.text
            json_str = text[text.index("(") + 1 : text.rindex(")")]
            results[code] = json.loads(json_str)
        except Exception as e:
            results[code] = {"error": str(e)}
        time.sleep(0.5)  # 限速
    return results
```

### 8.2 实时行情批量（腾讯源）

```python
def batch_realtime(codes: list[str]) -> dict:
    """批量实时行情（腾讯源，单次最多60只）
    codes: ['sh600519', 'sz002027', ...]
    """
    results = {}
    # 腾讯支持逗号分隔批量查询
    for i in range(0, len(codes), 60):
        batch = codes[i:i+60]
        url = f"https://qt.gtimg.cn/q={','.join(batch)}"
        resp = requests.get(url, timeout=10)
        for line in resp.text.strip().split(";"):
            if "=" not in line:
                continue
            key, val = line.split("=", 1)
            code = key.replace("v_", "")
            fields = val.strip('"').split("~")
            if len(fields) > 40:
                results[code] = {
                    "name": fields[1],
                    "price": float(fields[3]),
                    "change_pct": float(fields[32]),
                    "volume": float(fields[6]),
                    "turnover_rate": float(fields[38]) if fields[38] else None,
                }
        time.sleep(0.3)
    return results
```

### 8.3 千股千评批量（东财舆情）

```python
def batch_stock_comment(codes: list[str]) -> dict:
    """批量获取千股千评综合评分
    codes: ['002027', '600519', ...]  # 纯6位代码
    """
    import requests, time
    results = {}
    url = "https://emappdata.eastmoney.com/stockcomment/api/XWEB/GetStockComment"
    for code in codes:
        try:
            resp = requests.post(url, json={"code": code}, timeout=10)
            results[code] = resp.json()
        except Exception as e:
            results[code] = {"error": str(e)}
        time.sleep(0.4)
    return results
```

---

## 九、缓存策略

### 9.1 缓存分级

| 数据类型 | 缓存时长 | 刷新时机 | 存储位置 |
|----------|----------|----------|----------|
| 日K线（历史） | 当日有效 | 每日收盘后刷新最新一根 | data/cache/daily/ |
| 实时行情 | 5-15 秒 | 盘中轮询 | 内存 |
| 指数成分股 | 30 天 | 每月调整日刷新 | data/cache/index/ |
| 千股千评/舆情 | 4 小时 | 盘中每4h刷新 | data/cache/comment/ |
| 涨停池 | 当日有效 | 仅交易日缓存 | data/cache/zt/ |
| 股票名称列表 | 7 天 | 有新股上市时刷新 | data/cache/names/ |
| 基本面（PE/PB） | 24 小时 | 每日刷新 | data/cache/fundamental/ |

### 9.2 缓存规则

- **断点续传**：当日已获取的数据不重复拉取（系统内置）
- **过期淘汰**：超过缓存时长的文件自动删除
- **降级读取**：接口全部失败时，读取最近一次有效缓存（标记 stale）
- **并发安全**：SQLite WAL 模式 + 文件锁，避免多进程写冲突

### 9.3 缓存键设计

```
{data_type}:{market}:{code}:{date}:{adjust}
示例：daily:cn:002027:20260731:qfq
```

---

## 十、稳定性评级表

| 数据源 | 接口/域名 | 评级 | 可用性 | 备注 |
|--------|-----------|:---:|:---:|------|
| 腾讯财经 | qt.gtimg.cn | ⭐⭐⭐⭐⭐ | 99%+ | 最稳定，实时行情首选 |
| 新浪日线 | quotes.sina.cn | ⭐⭐⭐⭐⭐ | 98%+ | 日K首选，无需认证 |
| 东财舆情 | emappdata.eastmoney.com | ⭐⭐⭐⭐ | 95% | 千股千评稳定 |
| 东财搜索 | searchapi.eastmoney.com | ⭐⭐⭐⭐ | 95% | 名称/代码搜索 |
| AkShare(新浪源) | ak.stock_zh_a_daily | ⭐⭐⭐⭐ | 93% | 封装好，有 fallback |
| AkShare(东财源) | ak.stock_zh_a_spot_em | ⭐⭐⭐ | 80% | 底层走 push2，不稳定 |
| 中证指数官网 | csindex.com.cn | ⭐⭐⭐⭐ | 92% | 成分股权威源 |
| 东财 push2 | push2.eastmoney.com | ⭐⭐ | 50-60% | RemoteDisconnected 频发 |
| 东财 push2his | push2his.eastmoney.com | ⭐⭐ | 50-60% | 同上，历史K线不可靠 |
| 同花顺 | data.10jqka.com.cn | ⭐⭐⭐ | 75% | 有反爬，需 Cookie |
| efinance | 底层东财 | ⭐⭐ | 50-60% | 完全依赖东财，同等不稳定 |
| Baostock | baostock.com | ⭐⭐⭐⭐ | 90% | 免费稳定，仅历史数据 |
| SearXNG 公共实例 | searx.space | ⭐ | <20% | 超时频发，基本不可用 |
| YFinance | query1.finance.yahoo.com | ⭐⭐⭐ | 85% | A股数据有限，美股首选 |

### 推荐优先级（A股场景）

```
实时行情：腾讯 > AkShare(新浪) > efinance > 东财push2
日K线：  新浪 > AkShare(新浪) > Baostock > 东财push2his
资金流：  AkShare(同花顺) > 东财fflow > 腾讯
舆情：   东财emappdata > AkShare新闻 > SearXNG(不推荐)
成分股：  AkShare(csindex) > 东财push2
涨停池：  AkShare(东财封装) > push2ex直连
名称：   腾讯qt > searchapi > AkShare列表
```

---

## 版本记录

| 版本 | 日期 | 变更 |
|------|------|------|
| v1.0 | 2026-08-01 | 初始版本：十板块完整覆盖 |

---

## 免责声明

本 skill 中涉及的接口均为公开数据源，仅供个人学习研究使用。接口可能随时变更或下线，请以实际测试结果为准。商业使用请遵守各数据平台的服务条款。
