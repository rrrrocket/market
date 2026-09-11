# Matrix One Global Demand Intelligence

## `market.matrix-one.tech`

> 本文档是可直接执行的开发规格。
> 请按本文档开始开发，不要先做概念 Demo，也不要为了“架构先进”引入不必要的微服务、Kafka、图数据库或多套数据库。
>
> 如遇不影响核心功能的细节缺失，请自行做合理工程决策，不要停下来等待确认。
>
> 当前第一目标：**做出一个可以真实分析全球市场需求，并为中国商品寻找最值得进入国家的可运行系统。**

---

# 0. 项目背景

Matrix One 的长期愿景：

> **中国供应能力的全球化分发。**

实现路径：

> **用软件、数据和 AI，把中国高度分散的供应能力，与海外高度分散的需求进行规模化匹配。**

现有供给端已经开始建设：

```text
supplier.matrix-one.tech
```

负责：

```text
Supplier
Product
Supplier Offer
MOQ
Stock
Lead Time
Capability
```

需求端现在开始建设：

```text
market.matrix-one.tech
```

负责回答：

> 世界哪里需要什么？

未来总体关系：

```text
              GLOBAL DEMAND
                    │
                    ↓
        market.matrix-one.tech
                    │
              Demand Graph
                    │
                    ↓
             Matching Engine
                    ↑
                    │
               Supply Graph
                    ↑
                    │
       supplier.matrix-one.tech
                    │
                    ↓
                  ERP
             Execution OS
                    │
         ┌──────────┴──────────┐
         ↓                     ↓
        ToC                   ToB
 Marketplace            RFQ / Trade
```

---

# 1. 产品定位

产品名暂定：

```text
Matrix One Market
```

内部名称：

```text
Global Demand Intelligence
```

它不是：

```text
全球贸易数据查询网站
```

也不是：

```text
AI自动生成市场报告
```

而是：

> **把全球市场数据转换为可执行的商业机会。**

核心问题：

```text
一个中国商品
↓
全球哪些国家存在真实需求？
↓
哪些市场正在增长？
↓
中国商品进入这些市场是否已经被验证？
↓
哪些国家最值得优先测试？
↓
为什么？
```

第一阶段聚焦：

# Product → Country

后续再扩展：

```text
Product
×
Country
×
Channel
×
Customer
```

---

# 2. 第一版必须完成的核心能力

用户输入：

```text
HS Code
或
商品关键词
```

例如：

```text
902620
Pressure sensors
```

系统输出：

```text
全球市场排名
```

例如：

| Rank | Country | Market Attractiveness | Confidence | Import Value | 3Y Growth | China Share |
| ---- | ------- | --------------------: | ---------: | -----------: | --------: | ----------: |
| 1    | Russia  |                    88 |         92 |        $XXXM |      +18% |         34% |
| 2    | Turkey  |                    84 |         95 |        $XXXM |      +21% |         29% |
| 3    | India   |                    79 |         90 |        $XXXM |      +32% |         18% |

点击某个国家后展示：

```text
市场规模
历史趋势
进口增长
主要供应国
中国份额
中国份额趋势
进口单价
数据覆盖度
评分解释
```

系统必须回答：

> **为什么这个市场排在这里？**

而不是只展示一个 AI 随机生成的分数。

---

# 3. V1产品原则

## 3.1 V1不做销量预测

禁止输出：

```text
预计一年销售 ¥3,721,493
```

没有充分数据支撑时禁止伪精确预测。

V1输出的是：

```text
Market Attractiveness Score
```

即：

> 市场吸引力。

后续接入 Supplier Network、Marketplace、关税、物流、认证、成本以后，才建立：

```text
Distribution Opportunity Score
```

两者不能混为一谈。

---

## 3.2 Score 和 Confidence 必须分开

示例：

```text
Market Attractiveness
88 / 100

Data Coverage
92%

Confidence
High
```

不能因为缺失数据就暗中降低商业评分。

缺失数据必须明确告诉用户。

---

## 3.3 所有分析必须有证据来源

任何指标必须能够追溯：

```text
source
source_url / source_identifier
retrieved_at
period
raw_value
processed_value
```

后续 AI 生成解释，也只能基于已有数据和 Evidence。

禁止 AI 补造：

```text
市场规模
法规
认证要求
关税
销量
供应商数量
```

---

# 4. 技术架构

创建独立项目：当前文件夹

# 5. 技术栈

后端：

```text
Python
FastAPI
SQLAlchemy 2
Pydantic
Alembic
PostgreSQL
httpx
```

数据处理：

```text
Python
Polars 或 Pandas
```

优先 Polars。

前端：

```text
Next.js
TypeScript
Tailwind CSS
ECharts
MapLibre GL
```

不要引入大型 UI Framework。

可以使用少量成熟 headless component。

数据库：

```text
PostgreSQL
```

暂时不要使用：

```text
MongoDB
Neo4j
Elasticsearch
Kafka
ClickHouse
```

数据量明显增长以后再考虑。

---

# 6. 推荐目录结构

```text
market/
├── apps/
│   ├── api/
│   │   ├── app/
│   │   │   ├── api/
│   │   │   ├── core/
│   │   │   ├── models/
│   │   │   ├── schemas/
│   │   │   ├── services/
│   │   │   ├── repositories/
│   │   │   ├── integrations/
│   │   │   │   ├── comtrade/
│   │   │   │   ├── world_bank/
│   │   │   │   └── supplier/
│   │   │   ├── scoring/
│   │   │   └── main.py
│   │   ├── migrations/
│   │   └── tests/
│   │
│   └── web/
│       ├── app/
│       ├── components/
│       ├── lib/
│       ├── types/
│       └── public/
│
├── data/
│   ├── fixtures/
│   └── seeds/
│
├── docs/
│   ├── ARCHITECTURE.md
│   ├── DATA_MODEL.md
│   ├── SCORING.md
│   ├── DATA_SOURCES.md
│   └── SUPPLIER_INTEGRATION.md
│
├── scripts/
├── docker-compose.yml
├── Makefile
├── .env.example
└── README.md
```

---

# 7. 数据分层

严格分成三层：

## Raw Layer

保存外部数据源原始响应。

```text
Comtrade JSON
World Bank response
未来 Marketplace response
未来 Tender/RFQ
```

原始数据禁止被加工结果覆盖。

---

## Canonical Layer

统一标准模型：

```text
Country
HsProduct
TradeObservation
DemandSignal
```

---

## Intelligence Layer

计算结果：

```text
MarketOpportunity
ScoreRun
Evidence
```

未来：

```text
SupplyFit
DistributionOpportunity
```

---

# 8. 核心数据库模型

## 8.1 countries

```text
id
iso2
iso3
numeric_code
name_en
name_zh nullable
region
subregion
is_active
created_at
updated_at
```

`iso3` 唯一。

---

## 8.2 hs_products

```text
id
classification
hs_code
level
parent_code nullable
name_en
name_zh nullable
description
is_active
created_at
updated_at
```

例如：

```text
HS2022
902620
6
Instruments and apparatus for measuring or checking pressure
```

唯一键：

```text
classification + hs_code
```

---

## 8.3 source_snapshots

保存外部数据原始响应。

```text
id
source_type
source_identifier
request_payload JSONB
response_payload JSONB
retrieved_at
checksum
status
error_message
```

source_type 示例：

```text
COMTRADE
WORLD_BANK
SUPPLIER
```

---

## 8.4 trade_observations

标准化贸易事实。

```text
id
classification
hs_code
period_year

reporter_iso3
partner_iso3

flow
trade_value_usd
net_weight_kg nullable
quantity nullable
quantity_unit nullable

source_snapshot_id
created_at
```

flow：

```text
IMPORT
EXPORT
```

唯一性应包含：

```text
classification
hs_code
period_year
reporter_iso3
partner_iso3
flow
```

---

## 8.5 market_metrics

某商品 × 国家 × 年度的衍生指标。

```text
id

hs_code
country_iso3
origin_iso3

period_year

import_value_usd
import_value_prev_year
import_value_3y_ago

yoy_growth
cagr_3y

china_import_value_usd
china_import_share

unit_value_usd nullable
market_volatility nullable

calculated_at
```

初期：

```text
origin_iso3 = CHN
```

但字段不能写死中国。

---

## 8.6 market_opportunities

核心业务对象。

```text
id

hs_code
origin_iso3
destination_iso3
period_year

market_attractiveness_score
data_coverage_score

size_score
growth_score
momentum_score
stability_score

rank_global

score_version

status
calculated_at
```

唯一键：

```text
hs_code
origin_iso3
destination_iso3
period_year
score_version
```

---

## 8.7 evidence

```text
id

entity_type
entity_id

metric_key
source_type
source_identifier

period
raw_value
display_value

retrieved_at
notes
```

例如：

```text
entity_type = MARKET_OPPORTUNITY
metric_key = IMPORT_VALUE
source_type = COMTRADE
```

---

## 8.8 analysis_runs

记录一次分析任务。

```text
id
hs_code
origin_iso3
requested_year

status

started_at
finished_at

countries_analyzed
countries_succeeded
countries_failed

score_version

error_message
```

状态：

```text
PENDING
RUNNING
COMPLETED
PARTIAL
FAILED
```

---

# 9. Supplier Network预留模型

V1暂时不读取 Supplier 数据，但从第一天预留：

## supply_product_links

```text
id

external_system
external_product_id

hs_code

mapping_confidence
mapping_source

status

confirmed_by nullable
confirmed_at nullable

created_at
updated_at
```

mapping_source：

```text
MANUAL
RULE
AI
SUPPLIER
```

status：

```text
PENDING
CONFIRMED
REJECTED
```

不能让 AI 自动确认 HS Code。

---

# 10. 第一数据源：UN Comtrade

第一版的核心外部数据源：

```text
UN Comtrade
```

优先使用官方：

```text
comtradeapicall
```

如果 SDK 无法满足要求：

通过独立 Adapter 封装 REST API。

必须满足：

```text
业务逻辑不能直接依赖 Comtrade SDK
```

定义接口：

```python
class TradeDataProvider(Protocol):

    async def get_imports(
        self,
        hs_code: str,
        year: int,
        reporter: str | None = None,
        partner: str | None = None,
    ) -> list[TradeRecord]:
        ...

    async def get_exports(...):
        ...
```

实现：

```text
ComtradeTradeDataProvider
FixtureTradeDataProvider
```

测试环境一律使用 Fixture。

测试不得依赖互联网。

---

# 11. 不要一次下载全世界全部Comtrade数据

V1采用：

# On-demand ingestion

用户分析：

```text
HS 902620
```

系统：

```text
检查数据库缓存
↓
如果数据存在且未过期
→ 直接计算

否则
↓
从Comtrade获取需要的数据
↓
Raw Snapshot
↓
Normalize
↓
TradeObservation
↓
Market Metrics
↓
Score
```

第一阶段每个 HS Code 获取：

```text
最近5个完整年度
```

不要默认分析当前尚不完整的自然年度。

需要实现：

```text
latest_complete_year
```

配置。

---

# 12. 第一版分析范围

默认 Origin：

```text
China
ISO3: CHN
```

目标国家：

全球有效经济体。

过滤：

```text
import_value_usd < 100,000
```

的市场可不进入主要排行榜，但仍允许查看。

阈值写入配置：

```text
MIN_MARKET_IMPORT_VALUE_USD
```

---

# 13. V1评分算法

## 13.1 Market Attractiveness Score

只评价：

> 市场本身是否值得进一步研究。

不评价：

```text
实际利润
物流
认证
Supplier能力
Marketplace竞争
```

公式：

```text
Market Attractiveness
=
45% Market Size
+
30% Structural Growth
+
15% Momentum
+
10% Stability
```

---

# 14. Market Size Score

使用：

```text
log(import_value_usd + 1)
```

然后在当前 HS Code 的所有目标国家之间计算 percentile rank：

```text
0–100
```

原因：

极少数超大进口国不能把其他国家全部压成接近0。

---

# 15. Structural Growth Score

使用：

```text
3-year CAGR
```

公式：

```text
CAGR =
(latest / value_3y_ago)^(1/3) - 1
```

对 CAGR 做 clipping：

```text
-25% ～ +50%
```

映射：

```text
-25% → 0
0% → 33
+25% → 67
+50% → 100
```

具体实现使用线性映射。

---

# 16. Momentum Score

使用最新完整年度：

```text
YoY
```

clip：

```text
-50% ～ +100%
```

线性映射：

```text
0–100
```

---

# 17. Stability Score

取最近4个完整年度市场进口额。

计算：

```text
CV = std / mean
```

映射：

```text
CV = 0
→ 100

CV >= 1.5
→ 0
```

中间线性。

如果历史数据不足：

该指标标记：

```text
MISSING
```

并影响 Data Coverage。

---

# 18. Data Coverage Score

每个指标有数据权重：

```text
Market Size       45
Growth            30
Momentum          15
Stability         10
```

有数据则计入。

例如：

```text
Size        ✅
Growth      ✅
Momentum    ✅
Stability   ❌
```

则：

```text
Data Coverage = 90%
```

评分计算时：

缺失指标不直接当0。

而是：

```text
对已存在指标重新归一化权重
```

同时明确显示：

```text
Coverage 90%
```

---

# 19. 不要在V1创建完整Opportunity Score

V1只显示：

```text
Market Attractiveness
```

后续接入：

```text
Supplier Network
Tariff
Logistics
Marketplace
Certification
```

以后再创建：

```text
Distribution Opportunity Score
```

未来目标：

```text
Distribution Opportunity
=
Demand
+
China Supply Fit
+
Economics
+
Competition
+
Entry Risk
```

现在只预留字段与接口，不实现虚假的综合评分。

---

# 20. REST API

Prefix：

```text
/api/v1
```

---

## Product Search

```http
GET /api/v1/products/search?q=pressure
```

返回：

```json
[
  {
    "hs_code": "902620",
    "name_en": "...",
    "level": 6
  }
]
```

---

## Countries

```http
GET /api/v1/countries
```

---

## Create Analysis

```http
POST /api/v1/analyses
```

Body：

```json
{
  "hs_code": "902620",
  "origin_iso3": "CHN"
}
```

返回：

```json
{
  "analysis_id": "...",
  "status": "PENDING"
}
```

---

## Analysis Status

```http
GET /api/v1/analyses/{analysis_id}
```

---

## Opportunity Ranking

```http
GET /api/v1/opportunities
  ?hs_code=902620
  &origin_iso3=CHN
```

支持：

```text
sort
limit
region
min_score
min_coverage
```

---

## Opportunity Detail

```http
GET /api/v1/opportunities/{id}
```

必须包含：

```text
score
score components
raw metrics
historical trend
China share
rank
coverage
evidence
```

---

## Country Trade History

```http
GET /api/v1/trade/history
?hs_code=902620
&country_iso3=RUS
```

---

## Competition / Supplier Countries

```http
GET /api/v1/trade/suppliers
?hs_code=902620
&country_iso3=TUR
&year=2025
```

输出：

```text
supplier country
trade value
share
rank
```

---

# 21. 前端页面

## `/`

首页。

目标：

用户马上理解：

> 找到中国商品最值得进入的全球市场。

Hero：

```text
发现全球需求
找到中国商品最值得进入的市场
```

搜索框：

```text
输入 HS Code 或商品关键词
```

示例：

```text
902620
Pressure Sensor
Motorcycle Helmet
```

下方简单展示：

```text
Global Demand
Market Ranking
Trade Trends
China Position
```

不要在首页堆几十张图。

---

# 22. `/explore`

核心分析页。

布局：

```text
┌──────────────────────────────────────┐
│ Product / HS Search                  │
├───────────────────┬──────────────────┤
│                   │                  │
│   Global Map      │ Market Ranking   │
│                   │                  │
│                   │ #1 Russia        │
│                   │ #2 Turkey        │
│                   │ #3 India         │
├───────────────────┴──────────────────┤
│ Trend / China Share / Summary        │
└──────────────────────────────────────┘
```

地图：

MapLibre。

国家颜色：

按：

```text
Market Attractiveness Score
```

渐变。

点击国家：

更新右侧详情。

---

# 23. `/product/[hs_code]`

商品全球市场页。

顶部：

```text
HS 902620
Pressure measurement instruments
```

显示：

```text
Global Import Value
Top Import Market
Fastest Growing Market
China Export Position
Countries Covered
Data Year
```

下方：

```text
世界地图
国家排名
历史趋势
```

---

# 24. `/product/[hs]/country/[iso3]`

国家详情。

结构：

## Market Overview

```text
Import Value
3Y CAGR
YoY
Global Rank
Market Score
Coverage
```

## Trade Trend

5年曲线。

## Supplier Countries

例如：

```text
China      32%
Germany    19%
USA        12%
Japan       8%
...
```

## China Position

```text
China import share
China share trend
China bilateral trade value
```

## Why this market?

不能调用AI瞎写。

基于规则生成：

```text
+ 市场规模位于全球前10%
+ 过去3年增长21%
+ 最新年度继续增长14%
+ 中国已经占进口额29%
- 市场波动高于同类国家
```

规则化生成。

后续AI只负责润色。

---

# 25. `/methodology`

必须公开说明：

```text
数据源
数据年份
评分公式
Coverage定义
限制
```

特别写明：

> Score代表市场吸引力，不代表未来销量预测。

---

# 26. `/admin/data`

内部数据管理页。

展示：

```text
Source Status
Last Sync
Analysis Runs
Failed Runs
Cached Products
Trade Records
```

提供：

```text
Retry
Refresh
View Error
```

V1不用复杂权限系统。

可以采用简单：

```text
ADMIN_EMAIL
ADMIN_PASSWORD
```

的Session登录。

以后再接统一身份。

---

# 27. 视觉设计

整体：

```text
Matrix One
Enterprise
Data Intelligence
Clean
Professional
```

不要：

```text
Web3风
霓虹AI
夸张渐变
大量玻璃拟态
```

颜色：

```text
白/浅灰背景
深蓝/黑灰文字
蓝色作为核心操作色
```

地图和数据可使用语义色，但不要滥用。

---

# 28. Supplier Network Integration

V1：

只创建 Adapter，不真实同步。

接口：

```python
class SupplierNetworkClient(Protocol):

    async def get_supply_summary(
        self,
        hs_code: str
    ) -> SupplySummary:
        ...
```

未来返回：

```json
{
  "hs_code": "902620",
  "supplier_count": 28,
  "product_count": 137,
  "active_offer_count": 93,
  "min_price_cny": 74.5,
  "median_price_cny": 118,
  "avg_lead_time_days": 5.2
}
```

实现：

```text
NullSupplierNetworkClient
HttpSupplierNetworkClient
```

V1默认：

```text
NullSupplierNetworkClient
```

不要让 Market 直接访问 Supplier 数据库。

---

# 29. 未来 Supply Fit

现在只写文档，不实现评分。

预留：

```text
SupplyFitScore

supplier_coverage
offer_coverage
price_competitiveness
lead_time
moq
quality_score
```

未来：

```text
Market Attractiveness
+
Supply Fit
=
Distribution Opportunity
```

---

# 30. Evidence Registry

所有计算指标都可以追溯。

例如：

```json
{
  "metric": "import_value_usd",
  "value": 183000000,
  "source": "UN_COMTRADE",
  "period": "2025",
  "retrieved_at": "...",
  "source_identifier": "..."
}
```

前端所有核心指标旁边允许：

```text
ⓘ
```

查看：

```text
数据来源
年份
更新时间
```

---

# 31. 缓存策略

贸易数据不是实时数据。

默认：

```text
COMTRADE_CACHE_TTL_DAYS=30
```

如果已有：

```text
同HS
同年份
同reporter
同partner
```

且未过期：

不重复请求。

Admin可以强制刷新。

---

# 32. External API失败策略

不能因为Comtrade暂时不可用导致整个页面500。

流程：

```text
API request failed
↓
如果本地存在旧数据
→ 使用旧数据
→ 标记 STALE

如果完全无数据
→ Analysis PARTIAL/FAILED
```

前端明确显示：

```text
Data updated: 2026-08-31
```

---

# 33. 环境变量

创建 `.env.example`：

```env
APP_ENV=development

DATABASE_URL=postgresql+psycopg://market:market@localhost:5432/market

COMTRADE_API_KEY=
COMTRADE_CACHE_TTL_DAYS=30

DEFAULT_ORIGIN_ISO3=CHN
MIN_MARKET_IMPORT_VALUE_USD=100000

LATEST_COMPLETE_TRADE_YEAR=

SUPPLIER_API_BASE_URL=
SUPPLIER_API_KEY=
SUPPLIER_INTEGRATION_ENABLED=false

ADMIN_EMAIL=admin@matrix-one.tech
ADMIN_PASSWORD=change-me

NEXT_PUBLIC_API_BASE_URL=http://localhost:8000
```

如果：

```text
LATEST_COMPLETE_TRADE_YEAR
```

为空：

系统必须计算合理的最近完整年度。

不要假设当前年度完整。

---

# 34. 开发数据

必须提供 Fixture：

```text
data/fixtures/comtrade/
```

至少包含：

```text
HS 902620
最近4-5年
至少10个目标国家
世界进口
中国→目标国家
```

数据可以从真实API抓取后保存。

如果开发环境没有互联网：

提供静态 fixture。

Fixture必须明确：

```text
TEST DATA
```

不得在生产数据库当成真实最新数据。

---

# 35. 测试

后端：

```text
pytest
```

必须覆盖：

### Scoring

```text
Market Size percentile
CAGR
YoY
Stability
Coverage
Missing data
Ranking
```

### API

```text
Product search
Create analysis
Analysis status
Opportunity ranking
Opportunity detail
Trade history
```

### Data Provider

```text
Fixture provider
Comtrade response normalization
API failure
Cache
```

### Persistence

```text
duplicate observations
score version
analysis rerun
```

---

# 36. Frontend测试

至少：

```text
TypeScript compile
ESLint
build
```

关键交互：

```text
Search product
Select HS
Render ranking
Render map
Select country
Render country detail
```

---

# 37. 必须通过的端到端验收

使用：

```text
HS 902620
Origin CHN
```

完整运行：

```text
Search
↓
Start Analysis
↓
Load/Fake Fixture Data
↓
Normalize
↓
Calculate Metrics
↓
Calculate Scores
↓
Rank Markets
↓
Store Evidence
↓
API
↓
Frontend
```

最终首页可以进入：

```text
/product/902620
```

并看到：

```text
Global Map
Country Ranking
Scores
Coverage
Trade Trends
China Share
Evidence
```

---

# 38. 数据正确性验收

必须保证：

### 历史数据不能被最新数据覆盖

不同：

```text
year
country
product
partner
```

独立保存。

### Score可复现

同样输入：

```text
数据
score_version
```

必须得到完全相同的Score。

### Score Version

第一版：

```text
market_attractiveness_v1
```

未来修改公式：

必须：

```text
market_attractiveness_v2
```

禁止悄悄修改历史评分定义。

---

# 39. 性能目标

V1：

```text
已缓存商品分析页面：
< 1s API

排行榜：
< 500ms

地图：
首次数据加载 < 2s
```

Comtrade首次分析允许较慢。

分析任务应异步执行。

初期可采用：

```text
数据库Job + Background Worker
```

不要先上Celery/RabbitMQ，除非确有必要。

---

# 40. Docker

提供：

```text
docker-compose.yml
```

至少：

```text
postgres
api
web
```

要求：

```bash
docker compose up --build
```

即可启动。

---

# 41. Makefile

提供：

```bash
make dev
make test
make lint
make migrate
make seed
make build
```

---

# 42. README

必须包含：

```text
项目定位
架构
本地启动
环境变量
数据库迁移
Comtrade配置
Fixture模式
测试
Docker
评分逻辑入口
Supplier Integration未来方向
```

---

# 43. 文档

生成：

```text
docs/ARCHITECTURE.md
docs/DATA_MODEL.md
docs/SCORING.md
docs/DATA_SOURCES.md
docs/SUPPLIER_INTEGRATION.md
```

---

# 44. 明确不做的东西

V1禁止扩散范围。

不要做：

```text
AI聊天助手
全球Marketplace爬虫
社交媒体分析
Amazon数据
Ozon数据
Tender
RFQ
物流报价
关税自动计算
认证数据库
客户CRM
自动报价
自动开发客户
AI销量预测
图数据库
复杂Agent
```

全部留到后续。

---

# 45. Phase 2规划

V1稳定以后，再接：

```text
Google Trends
Google Search
Amazon
Ozon
Wildberries
Marketplace Signals
```

建立：

```text
Digital Demand Score
Marketplace Demand Score
```

这时：

```text
Structural Demand
+
Digital Demand
+
Marketplace Demand
```

开始接近真实需求。

---

# 46. Phase 3规划

接入：

```text
supplier.matrix-one.tech
```

建立：

```text
Supply Fit
```

例如：

```text
中国内部供应商数
活跃Offer数
采购价格
MOQ
库存
交期
履约能力
```

再生成：

# Distribution Opportunity Score

这是产品真正开始形成壁垒的阶段。

---

# 47. Phase 4规划

接：

```text
Tender
RFQ
BOM
Importer
Distributor
Buyer
```

建立：

```text
Explicit Demand
```

最终：

```text
Structural Demand
+
Digital Demand
+
Marketplace Demand
+
Explicit Demand
+
China Supply Fit
=
Global Distribution Intelligence
```

---

# 48. 最终产品方向

长期系统不是：

```text
告诉用户某国进口多少
```

而应该变成：

```text
System detects:

Turkey
HS 902620

Demand ↑
Import +21%
Marketplace signal ↑
China suppliers available: 28
Active offers: 93
Cost advantage: strong

↓

Distribution Opportunity
86 / 100

↓

Recommended Action:

Test B2B distributor channel
Test marketplace channel
Contact selected suppliers
```

然后：

```text
[Match Supply]
```

进入：

```text
Supplier Network
```

再：

```text
[Create Distribution Plan]
```

进入：

```text
ERP
```

---

# 49. 最核心的系统边界

必须一直保持：

```text
Supplier
=
中国有什么

Market
=
世界需要什么

Matching
=
什么供给适合什么需求

ERP
=
把匹配结果真正执行
```

不要重新把所有功能塞进一个ERP。

---

# 50. Codex执行顺序

请严格按下面顺序开发：

## Step 1

创建项目骨架：

```text
market/
```

完成：

```text
FastAPI
Next.js
PostgreSQL
Docker
Alembic
```

---

## Step 2

建立：

```text
Country
HsProduct
SourceSnapshot
TradeObservation
AnalysisRun
MarketMetric
MarketOpportunity
Evidence
```

数据库模型与migration。

---

## Step 3

建立：

```text
FixtureTradeDataProvider
```

先用本地Fixture跑通完整分析。

---

## Step 4

实现：

```text
Scoring Engine
```

并完整单元测试。

---

## Step 5

实现API：

```text
search
analysis
ranking
detail
history
supplier countries
```

---

## Step 6

完成Web：

```text
Home
Explore
Product
Country Detail
Methodology
Admin Data
```

---

## Step 7

加入MapLibre世界地图与ECharts趋势图。

---

## Step 8

接入真实：

```text
UN Comtrade
```

但保留Fixture模式。

---

## Step 9

建立：

```text
SupplierNetworkClient
```

只做接口骨架，不接真实业务。

---

## Step 10

执行全部：

```text
tests
lint
build
migration
Docker startup
```

---

# 51. 完成定义 Definition of Done

项目只有满足以下条件才算V1完成：

* [ ] 全新环境可启动
* [ ] PostgreSQL migration正常
* [ ] HS商品可搜索
* [ ] 可以对一个HS商品发起全球分析
* [ ] 可以生成国家排名
* [ ] 可以查看世界地图
* [ ] 可以查看国家详情
* [ ] 可以查看至少4年趋势
* [ ] 可以查看中国进口份额
* [ ] 每个Score可解释
* [ ] 每个重要指标有Evidence
* [ ] Coverage正确显示
* [ ] 外部API失败不会造成数据损坏
* [ ] Fixture模式可完全离线测试
* [ ] 所有后端测试通过
* [ ] TypeScript build通过
* [ ] Docker启动通过
* [ ] README完整
* [ ] SCORING文档完整
* [ ] 不存在AI编造的商业数据

---

# 52. 最后的开发原则

这个项目的价值不在：

```text
图表漂亮
```

而在：

```text
Raw Global Data
       ↓
Normalized Demand
       ↓
Explainable Score
       ↓
Market Ranking
       ↓
China Supply Match
       ↓
Action
       ↓
Real Transaction
       ↓
Outcome
```

第一版只完成前四步。

但所有模型、接口和代码结构都必须保证未来能够自然进入：

```text
China Supply Match
```

而无需推翻重写。

开发时牢记最终问题：

> **中国已经有一个商品，我应该把它卖到世界哪里？**

第一版必须真实回答好这个问题。
