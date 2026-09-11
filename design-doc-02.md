# Matrix One Global Demand Intelligence

## `market.matrix-one.tech`

本项目已经有第一版可运行系统。

现在请基于现有代码继续开发，**不要推倒重写，不要再按 Phase 1 / Phase 2 的产品思路组织架构。**

从现在开始，整个系统按照最终目标设计：

> **Global Demand Intelligence + China Supply Intelligence + Distribution Opportunity Engine**

长期要回答的不是：

> 某个国家进口了多少？

而是：

> **中国已有的某个商品，全球哪些市场存在真实需求，哪个国家、哪个渠道、以什么成本和风险最值得进入？**

最终系统需要形成：

```text
Global Data
    ↓
Demand Graph
    ↓
Market Opportunity
    ↓
China Supply Graph
    ↓
Supply Matching
    ↓
Economics
    ↓
Distribution Opportunity
    ↓
Decision
    ↓
ERP Execution
    ↓
Real Outcome
    ↓
Feedback
```

---

# 1. 整体系统边界

Matrix One 最终由以下系统组成：

```text
supplier.matrix-one.tech
=
What can China supply?
中国能提供什么

market.matrix-one.tech
=
What does the world demand?
世界需要什么

Matching Engine
=
Which supply fits which demand?
什么供给适合什么需求

ERP
=
Execute the match
执行分发、定价、订单、采购和交易
```

Market 系统不能重新变成 ERP，也不能直接修改 Supplier 数据。

系统之间通过 API / Event 交互。

---

# 2. Market 的最终定位

Market 不是：

```text
全球贸易统计网站
数据可视化网站
AI市场报告工具
```

而是：

# Global Distribution Intelligence

核心对象不是 Report。

核心对象是：

```text
DistributionOpportunity
```

最终粒度：

```text
Product
×
Country
×
Channel
×
Time
```

例如：

```text
Pressure Sensor
×
Turkey
×
B2B Distributor
×
2026-Q3
```

或者：

```text
AGV K6S
×
Russia
×
Ozon
×
2026-Q3
```

---

# 3. 全球需求必须拆成独立信号层

不能把所有数据揉成一个“AI Score”。

系统从架构上定义以下 Demand Layers：

```text
Structural Demand
Digital Demand
Marketplace Demand
Explicit Demand
Country Capacity
Market Access
```

再与：

```text
China Supply Fit
Economics
Risk
```

组合。

---

# 4. Structural Demand

回答：

> 一个国家长期真实买不买这类商品？

主要数据：

```text
UN Comtrade
ITC / Trade Map compatible sources
BACI compatible sources
```

核心指标：

```text
import_value
import_quantity
net_weight
unit_value

global_import_rank

yoy_growth
cagr_3y
cagr_5y

market_volatility

china_import_value
china_share
china_share_trend

supplier_country_count
supplier_concentration
top_supplier_share
HHI

trade_balance
```

这层属于：

```text
REPORTED
```

事实数据。

---

# 5. Market Access

回答：

> 中国货进入这个市场难不难？

数据源架构：

```text
WTO
UNCTAD TRAINS
WITS
future customs/tariff sources
```

核心指标：

```text
mfn_tariff
preferential_tariff
china_applicable_tariff
bound_tariff

duty_free_flag

anti_dumping_flag
countervailing_flag

ntm_count
ntm_categories

import_restriction_flag

market_access_score
```

如果数据无法确认：

```text
UNKNOWN
```

禁止 AI 补造。

---

# 6. Country Capacity

回答：

> 即使该产品有贸易量，这个国家整体是否值得进入？

主要：

```text
World Bank
IMF-compatible sources
```

只接与商业决策真正有关的数据。

核心字段：

```text
gdp_usd
gdp_growth
gdp_per_capita
gdp_per_capita_ppp

population

household_consumption

internet_penetration
mobile_penetration

imports_percent_gdp
trade_percent_gdp

logistics_performance_index

urbanization

currency_volatility
inflation

country_risk_score
```

不要用宏观指标直接替代商品需求。

---

# 7. Digital Demand

回答：

> 最近需求是否正在升温？

Provider 架构从现在建立：

```text
GoogleTrendsProvider
GoogleSearchProvider
SocialSignalProvider
NewsSignalProvider
```

当前没有稳定数据源的 Provider 可以：

```text
disabled
```

禁止返回伪数据。

核心模型：

```text
DigitalDemandSignal
```

字段：

```text
product_id nullable
hs_code nullable

country_iso3

keyword
keyword_language

source

period_start
period_end

interest_index
growth_rate
momentum
seasonality_score

signal_type

observed_type
confidence

retrieved_at
```

注意：

Google Trends 是：

```text
normalized interest
```

不是绝对搜索量。

禁止显示为：

```text
monthly_search_volume
```

除非数据源真的提供这个字段。

---

# 8. Marketplace Demand

回答：

> 目标渠道里到底有没有真实消费者和竞争环境？

必须从架构层支持：

```text
Amazon
Ozon
Wildberries
Mercado Libre
Shopee
TikTok Shop
其他Marketplace
```

但不要求现在全部接通。

定义统一：

```python
class MarketplaceProvider(Protocol):
    async def search_products(...)
    async def get_product(...)
    async def get_keyword_metrics(...)
    async def get_category_metrics(...)
```

实现：

```text
OzonMarketplaceProvider
WildberriesMarketplaceProvider
AmazonMarketplaceProvider
NullMarketplaceProvider
```

数据模型：

```text
MarketplaceSignal
```

至少：

```text
marketplace
country_iso3

keyword
product_ref nullable

observed_at

price
currency

rating
review_count
review_growth

rank
rank_change

seller_count

promotion_flag
stock_status

estimated_sales nullable

observed_type
source_reliability
confidence
```

严格区分：

```text
OBSERVED
ESTIMATED
INFERRED
```

例如：

```text
price = OBSERVED
review_count = OBSERVED
estimated_sales = ESTIMATED
market_demand_level = INFERRED
```

禁止混在一起。

---

# 9. Explicit Demand

回答：

> 有没有人明确正在采购？

最终支持：

```text
Government Tender
Corporate Tender
RFQ
BOM
Importer Inquiry
Distributor Inquiry
Buyer Request
```

统一模型：

```text
ExplicitDemand
```

字段：

```text
id

source_type
source_identifier

buyer_name nullable
buyer_country_iso3

title
description

hs_code nullable
product_id nullable

quantity nullable
quantity_unit nullable

budget_min nullable
budget_max nullable
currency nullable

deadline nullable

published_at

requirements JSONB

source_url nullable

status

observed_type
source_reliability

retrieved_at
```

---

# 10. China Supply Fit

Market 必须正式接：

```text
supplier.matrix-one.tech
```

但只能通过 API。

禁止：

```text
Market直接访问Supplier数据库
```

Supplier 需要通过授权接口提供聚合数据。

统一客户端：

```python
class SupplierNetworkClient(Protocol):
    async def get_supply_summary(...)
    async def get_products(...)
    async def get_offers(...)
    async def get_capability_summary(...)
```

核心返回维度：

```text
supplier_count

product_count

active_offer_count

min_price
median_price
price_distribution

moq_min
moq_median

stock_total

lead_time_min
lead_time_median

certified_supplier_count

dropship_supplier_count

historical_delivery_score nullable
quality_score nullable
```

生成：

```text
SupplyFit
```

不能只返回一个分数。

---

# 11. Economics Engine

长期最重要模块之一。

负责回答：

> 有需求，有供应，但到底赚不赚钱？

统一模型：

```text
DistributionEconomics
```

输入：

```text
supplier_offer
quantity

destination_country
channel

purchase_price

currency

domestic_shipping

international_shipping

tariff

tax

marketplace_commission

marketplace_logistics

payment_fee

advertising_estimate

return_cost_estimate

other_variable_cost
```

输出：

```text
landed_cost

channel_cost

total_variable_cost

target_sale_price

gross_profit

contribution_profit

gross_margin

contribution_margin

break_even_price
```

必须保留：

```text
input_source
calculation_version
calculated_at
```

无法取得真实费用时：

允许字段为空。

禁止用 AI 猜数字。

---

# 12. Risk Layer

建立统一：

```text
OpportunityRisk
```

维度：

```text
regulatory_risk

certification_risk

logistics_risk

payment_risk

currency_risk

political_risk

return_risk

after_sales_risk

marketplace_policy_risk

data_uncertainty_risk
```

每个风险：

```text
score
reason
evidence
status
```

允许：

```text
UNKNOWN
```

未知不能自动等同低风险。

---

# 13. 数据可信度体系

这是整个系统的核心能力。

所有外部和内部数据必须带：

```text
source_reliability
```

统一枚举：

```text
A_PLUS
A
A_MINUS
B_PLUS
B
C
D
```

默认原则：

```text
A_PLUS
=
Matrix One真实交易结果

A
=
政府/官方统计
官方关税
Supplier确认的正式报价/库存

A_MINUS
=
Marketplace官方API

B_PLUS
=
Google Trends等官方数字行为信号

B
=
公开Marketplace页面
高可信商业数据源

C
=
第三方销量估算
第三方推测数据

D
=
AI推断
弱来源
```

不要完全写死来源等级。

设计：

```text
data_sources
```

允许管理员调整。

---

# 14. Observed Type

所有指标必须标识：

```text
REPORTED
OBSERVED
ESTIMATED
INFERRED
AI_GENERATED
```

含义：

```text
REPORTED
=
政府、企业、供应商正式报告

OBSERVED
=
系统直接观察网页/API状态

ESTIMATED
=
统计模型估算

INFERRED
=
多个信号推导

AI_GENERATED
=
LLM生成的文本或结论
```

任何 AI 生成数据不得冒充：

```text
REPORTED
OBSERVED
```

---

# 15. Evidence Registry

正式升级成整个系统的基础设施。

统一模型：

```text
Evidence
```

字段：

```text
id

entity_type
entity_id

metric_key

value_numeric nullable
value_text nullable
value_json nullable

unit nullable
currency nullable

source_id
source_type

source_identifier
source_url nullable

source_reliability
observed_type

period_start nullable
period_end nullable

retrieved_at

raw_snapshot_id nullable

confidence nullable

notes nullable
```

所有 Opportunity 关键指标必须可以追溯。

---

# 16. Data Source Registry

新增：

```text
data_sources
```

字段：

```text
id
code
name

category

provider_type

base_url nullable

reliability

enabled

update_frequency

last_success_at
last_failure_at

status

terms_notes nullable

created_at
updated_at
```

category：

```text
TRADE
TARIFF
MACRO
SEARCH
MARKETPLACE
TENDER
RFQ
SUPPLY
LOGISTICS
RISK
```

---

# 17. Raw Snapshot 永远保留

现有：

```text
source_snapshots
```

继续强化。

禁止标准化结果覆盖 Raw。

Raw必须至少：

```text
source
request
response
checksum
retrieved_at
status
```

如果来源有 revision：

保存：

```text
source_revision
```

---

# 18. DemandSignal统一模型

不同来源的数据不要全部直接塞进 MarketOpportunity。

建立：

```text
DemandSignal
```

字段：

```text
id

signal_layer

product_id nullable
hs_code nullable

country_iso3

channel nullable

metric_key

value_numeric nullable
value_text nullable

normalized_value nullable

period_start
period_end

source_id
evidence_id

observed_type
source_reliability

confidence nullable

created_at
```

signal_layer：

```text
STRUCTURAL
DIGITAL
MARKETPLACE
EXPLICIT
MACRO
ACCESS
```

这样未来新数据源不会破坏 Opportunity 表结构。

---

# 19. Demand Graph

Graph 是业务概念。

当前继续用 PostgreSQL。

不要因为名字叫 Graph 就上 Neo4j。

核心关系：

```text
Product
↓
Country
↓
Channel
↓
Demand Signals
↓
Market Opportunity
```

后续再增加：

```text
Buyer
Supplier
Offer
Alternative Product
Equivalent Product
```

---

# 20. Product Mapping

HS Code 不等于真实 Product。

必须正式引入：

```text
ProductMarketIdentity
```

Market中的产品层最终要支持：

```text
Internal Product
Supplier Product
HS Code
Marketplace Product
Brand
Model
GTIN
MPN
EAN
UPC
```

建议模型：

```text
product_entities
product_identifiers
product_hs_mappings
product_relationships
```

product_relationship：

```text
EXACT
VARIANT
COMPATIBLE
REPLACEMENT
ACCESSORY
SIMILAR
```

HS Mapping：

```text
product_id
classification
hs_code

confidence

mapping_source

status

confirmed_by
confirmed_at
```

AI只能建议：

```text
PENDING
```

不能自动：

```text
CONFIRMED
```

---

# 21. MarketOpportunity重新定义

现有 MarketOpportunity 保留兼容，但向最终结构演进。

核心粒度：

```text
product_scope
×
country
×
channel nullable
×
period
```

其中 product_scope：

```text
HS
PRODUCT
CATEGORY
```

建议字段：

```text
id

product_scope_type
product_scope_id

hs_code nullable
product_id nullable

origin_iso3
destination_iso3

channel nullable

period_start
period_end

market_attractiveness_score nullable

structural_demand_score nullable
digital_demand_score nullable
marketplace_demand_score nullable
explicit_demand_score nullable

market_access_score nullable
country_capacity_score nullable

supply_fit_score nullable
economics_score nullable
competition_score nullable
risk_score nullable

distribution_opportunity_score nullable

data_coverage_score
confidence_score

score_version

status

calculated_at
```

---

# 22. Score Framework

不要现在硬凑所有分数。

各层独立计算。

允许：

```text
null
```

只有数据足够时才计算对应Score。

---

# 23. Structural Demand Score

继续保留当前：

```text
Market Size
Growth
Momentum
Stability
```

但增加：

```text
China Share
Supplier Concentration
```

建议长期权重：

```text
Market Size             30%
3Y Structural Growth    20%
Latest Momentum         15%
Stability               10%
China Share             15%
Competition Structure   10%
```

不要为了升级直接破坏当前结果。

增加：

```text
structural_demand_v2
```

版本。

旧版仍可重现。

---

# 24. Digital Demand Score

只有数据完整后计算。

建议框架：

```text
Search Interest      35%
Search Growth        35%
Momentum             20%
Seasonality Quality  10%
```

不要把缺失数据当0。

重新归一化。

同时输出 Coverage。

---

# 25. Marketplace Demand Score

长期框架：

```text
Observed Demand Signals     30%
Review Velocity             20%
Rank Momentum               20%
Competition                 15%
Seller Saturation           10%
Stock-out Signal             5%
```

如果只有第三方 estimated sales：

它不能成为唯一核心信号。

---

# 26. Explicit Demand Score

长期：

```text
RFQ Count
Tender Count
Purchase Value
Buyer Quality
Recency
Requirement Match
```

近期显性采购权重大于历史采购。

---

# 27. Supply Fit Score

建议：

```text
Supplier Coverage          20%
Active Offer Coverage      20%
Price Competitiveness      20%
MOQ                        10%
Lead Time                  10%
Stock Availability         10%
Capability / Quality       10%
```

没有真实履约数据前：

Quality Score保持null。

不要伪造供应商综合评分。

---

# 28. Economics Score

只有实际输入足够时计算。

重点：

```text
Contribution Margin
Break-even Safety
Price Headroom
Landed Cost Advantage
```

不要只看毛利率。

---

# 29. Risk Score

Risk建议统一含义：

```text
100 = Low Risk
0 = Very High Risk
```

不要有的字段高分代表高风险，有的代表低风险。

---

# 30. Distribution Opportunity Score

最终才组合：

```text
Demand
Supply Fit
Economics
Competition
Market Access
Risk
```

初始参考：

```text
Demand             30%
Supply Fit          25%
Economics           20%
Competition         10%
Market Access       10%
Risk                 5%
```

但是：

如果：

```text
Supply Fit
Economics
```

尚未有数据：

禁止生成完整 Distribution Opportunity Score。

显示：

```text
Not enough data
```

不能把 Market Attractiveness 当 Distribution Opportunity。

---

# 31. Confidence Score

Confidence不是商业评分。

它衡量：

```text
Data Coverage
Source Reliability
Data Freshness
Cross-source Consistency
Observed Type
```

建议计算：

```text
Coverage         35%
Reliability      30%
Freshness        20%
Consistency      15%
```

最终：

```text
0–100
```

同时映射：

```text
HIGH
MEDIUM
LOW
```

---

# 32. Freshness

所有指标定义：

```text
freshness_status
```

枚举：

```text
FRESH
AGING
STALE
UNKNOWN
```

不同数据源不同规则：

```text
Annual Trade
→ 365天级别

Monthly Trade
→ 45-90天

Marketplace
→ 小时/天

Supplier Price
→ 天

Tender
→ 小时/天
```

不能统一30天缓存。

---

# 33. Comtrade继续增强

现有年度数据之外增加：

```text
monthly data
```

如果来源可用。

模型不能假设：

```text
period = year
```

统一：

```text
period_type

YEAR
QUARTER
MONTH
WEEK
DAY
```

Trade Observation改为支持：

```text
period_start
period_end
```

保留旧年字段兼容迁移。

---

# 34. HS Classification

正式解决：

```text
HS2012
HS2017
HS2022
```

不得跨版本直接拼历史。

新增：

```text
hs_classifications
hs_correspondence
```

用于：

```text
HS2017 → HS2022
```

映射。

如果映射：

```text
1 → many
many → 1
```

不能强行当完全等价。

必须记录：

```text
mapping_type
confidence
```

---

# 35. Trade口径

分析目标国需求时：

默认：

```text
Importer-reported Imports
```

不要混用：

```text
China-reported Exports
```

作为主市场规模。

China Export可以作为交叉验证。

如果 bilateral discrepancy明显：

记录：

```text
trade_asymmetry
```

---

# 36. Unit Value

如果 Quantity数据可靠：

计算：

```text
trade_value / quantity
```

否则：

```text
trade_value / net_weight
```

字段叫：

```text
unit_value
```

禁止叫：

```text
product_price
retail_price
```

---

# 37. Tariff Provider

建立统一：

```python
class TariffProvider(Protocol):
    async def get_tariff(...)
    async def get_ntm(...)
```

实现：

```text
WtoTariffProvider
WitsTariffProvider
NullTariffProvider
```

业务代码不得直接依赖具体网站结构。

---

# 38. Macro Provider

统一：

```python
class MacroDataProvider(Protocol):
    async def get_country_metrics(...)
```

实现：

```text
WorldBankProvider
FixtureMacroProvider
```

---

# 39. Search Provider

统一：

```python
class SearchDemandProvider(Protocol):
    async def get_keyword_interest(...)
```

实现：

```text
GoogleTrendsProvider
NullSearchDemandProvider
```

关键词必须支持：

```text
country
language
```

不要用英文关键词直接代表所有国家需求。

未来需要：

```text
KeywordEntity
```

记录：

```text
concept
language
keyword
source
confidence
```

---

# 40. Tender / RFQ Provider

统一：

```python
class ExplicitDemandProvider(Protocol):
    async def search_demands(...)
```

实现：

```text
TenderProvider
RFQProvider
NullExplicitDemandProvider
```

---

# 41. Provider Registry

不要在业务代码里：

```python
if provider == "comtrade"
```

建立：

```text
ProviderRegistry
```

根据配置启停。

每个Provider必须提供：

```text
name
health
last_sync
capabilities
rate_limit
reliability
```

---

# 42. 数据同步模式

支持两种：

## On Demand

用户分析某个商品时：

```text
检查本地
↓
缺失/过期
↓
Provider Fetch
↓
Raw
↓
Normalize
↓
Signal
↓
Opportunity
```

## Scheduled

定时更新：

```text
重点HS
重点国家
重点Marketplace
重点Supplier Products
```

不要一开始试图每天抓全世界全部数据。

---

# 43. Watchlist

正式加入：

```text
Watchlist
```

用户可以监控：

```text
Product
HS
Country
Channel
```

例如：

```text
HS 902620
Russia
```

系统持续跟踪：

```text
Trade
Search
Marketplace
Tender
Supplier
Economics
```

---

# 44. Opportunity Event

当指标发生重要变化：

生成：

```text
OpportunityEvent
```

例如：

```text
DEMAND_SURGE
CHINA_SHARE_RISING
MARKET_IMPORT_DROP
TARIFF_CHANGED
NEW_TENDER
MARKETPLACE_PRICE_RISE
SUPPLY_COST_DROP
SUPPLIER_AVAILABLE
MARGIN_IMPROVED
RISK_INCREASED
```

字段：

```text
entity
event_type
severity
before
after
evidence
detected_at
```

---

# 45. Opportunity Feed

首页最终不应该只是一张地图。

增加：

# Opportunity Feed

例如：

```text
Russia · Pressure Sensor
Structural demand +18%
China share +7pp
28 active Chinese suppliers
→ Review Opportunity
```

或者：

```text
Turkey · Industrial Encoder
Import value +24%
Tariff unchanged
Supplier median cost -8%
→ Supply economics improving
```

---

# 46. Product → Country

保留现有核心入口。

用户输入：

```text
Supplier Product
Internal Product
HS
Keyword
```

输出：

```text
Global Ranking
```

---

# 47. Country → Product

增加第二入口：

用户选择：

```text
Russia
```

系统回答：

> 哪些商品需求增长最明显？

维度：

```text
HS
Import Growth
China Share
Momentum
Supply Availability
```

未来成为：

```text
Market Discovery
```

---

# 48. Supply → Market

这将是最重要入口之一。

从 Supplier Network 取得：

```text
supplier product
```

Market自动：

```text
Product → HS
↓
Global Demand
↓
Country Ranking
↓
Channel Ranking
↓
Economics
↓
Distribution Opportunity
```

回答：

> 这个中国商品应该卖到哪里？

---

# 49. Demand → Supply

反向：

```text
全球发现机会
↓
HS / Product Requirement
↓
Supplier Network
↓
找合适供应商
```

回答：

> 世界正在需要什么，而中国谁能供？

这两个方向必须共用同一数据模型。

---

# 50. Opportunity Detail 页面最终布局

顶部：

```text
Product
Country
Channel
Opportunity Status
Confidence
```

第一屏：

```text
Distribution Opportunity
Demand
Supply Fit
Economics
Risk
Confidence
```

如果完整Score暂无：

显示：

```text
Market Attractiveness
```

不要假装完整Opportunity存在。

---

第二块：

```text
Why this opportunity?
```

必须完全Evidence-driven。

例如：

```text
+ Import market top 8% globally
+ 3Y CAGR +21%
+ China share increased from 18% to 27%
+ Search momentum rising
+ 28 active suppliers available
- Tariff 12%
- Marketplace competition high
```

---

第三块：

```text
Demand
```

分别显示：

```text
Structural
Digital
Marketplace
Explicit
```

没有数据的层：

```text
No data connected
```

不要隐藏。

---

第四块：

```text
China Supply
```

显示：

```text
supplier_count
offers
cost
MOQ
stock
lead time
capabilities
```

---

第五块：

```text
Economics
```

---

第六块：

```text
Market Access & Risk
```

---

第七块：

```text
Evidence
```

全部来源和更新时间。

---

# 51. Data Quality 页面

新增：

```text
/admin/data-quality
```

显示：

```text
Provider Health

Data Coverage

Stale Sources

Failed Syncs

Missing HS mapping

Low Confidence Opportunities

Source Reliability

Recent Data Revisions
```

---

# 52. Methodology

现有 methodology 页面升级。

完整解释：

```text
Reported
Observed
Estimated
Inferred

Reliability

Coverage

Confidence

各Score公式

数据限制
```

这是产品的一部分，不是技术附录。

---

# 53. AI 的正确角色

现在正式预留：

```text
AI Research Layer
```

但是 AI 不拥有事实。

可以负责：

```text
解释
摘要
多语言
关键词生成
产品实体识别
HS候选
风险材料总结
Evidence synthesis
```

禁止负责：

```text
编市场规模
编关税
编销量
编供应商数量
编认证要求
```

---

# 54. AI Evidence Requirement

任何 AI结论必须：

```text
evidence_ids[]
```

没有 Evidence：

标记：

```text
HYPOTHESIS
```

不能显示成 Fact。

---

# 55. AI Research Output

统一：

```text
fact
interpretation
hypothesis
recommendation
```

不要混在一个自然语言段落中无法区分。

---

# 56. Decision Layer

未来 Opportunity 不能止步于：

```text
82分
```

建立：

```text
DecisionRecommendation
```

例如：

```text
TEST_MARKET
DEFER
REJECT
EXPAND
FIND_SUPPLIER
CONTACT_BUYER
LIST_ON_MARKETPLACE
REQUEST_SAMPLE
RUN_ECONOMICS
```

字段：

```text
recommendation
reason
evidence
confidence
human_status
```

---

# 57. ERP Integration

Market只生成：

```text
DistributionPlan
```

不直接上架。

例如：

```text
Product
Country
Channel
Supplier Offer
Target Price
Expected Cost
Opportunity
Evidence
```

用户点击：

```text
Create Distribution Plan
```

通过API发送ERP。

ERP负责：

```text
Listing
Pricing
Procurement
Stock
Advertising
Order
Transaction
```

---

# 58. Outcome Feedback

ERP未来回传：

```text
LISTED
PRICE_CHANGED
ORDER_CREATED
SALE
AD_SPEND
RETURN
PROFIT
STOCKOUT
```

Market建立：

```text
OpportunityOutcome
```

字段：

```text
opportunity_id

action

actual_gmv
actual_orders
actual_profit
actual_margin

conversion
return_rate

period

source
```

---

# 59. 最终壁垒

系统以后必须可以研究：

```text
某类Opportunity Score
↓
真实执行
↓
90天结果
```

从而回答：

> 哪些指标真的能够预测市场成功？

这是未来重新训练评分权重的依据。

不要现在用历史相关性不足的数据假装预测未来。

---

# 60. 数据源接入优先级

架构一次搭好。

实际数据按以下优先级接：

```text
1 UN Comtrade annual
2 UN Comtrade monthly
3 WTO / WITS tariff
4 World Bank
5 Google Trends
6 Ozon
7 Wildberries
8 Amazon
9 Tender / RFQ
10 Supplier Network
11 Logistics
12 Regulatory / certification
```

已经完成的数据不要重做。

---

# 61. 当前立即开发任务

请先检查现有代码。

生成：

```text
CURRENT_ARCHITECTURE_AUDIT.md
```

列出：

```text
已有模型
已有API
已有Provider
已有评分
已有页面
与本文档最终架构差异
数据库migration计划
兼容计划
```

不要直接删除现有模型。

---

# 62. 数据库演进

使用 Alembic migration。

不能：

```text
drop database and recreate
```

除非明确是本地测试环境。

现有：

```text
trade observations
market opportunities
evidence
analysis runs
```

尽量迁移扩展。

---

# 63. 第一轮应新增的核心实体

优先：

```text
data_sources

demand_signals

product_entities
product_identifiers
product_hs_mappings

market_access_metrics
country_metrics

supply_fit

distribution_economics

opportunity_risks

opportunity_events

watchlists

opportunity_outcomes
```

再根据当前代码实际情况调整。

---

# 64. Provider Framework

本轮必须搭好全部Provider接口。

即使：

```text
Google
Marketplace
Tender
Supplier
```

暂时无法连接，也必须有：

```text
Null Provider
Fixture Provider
```

这样未来增加数据源不修改业务核心。

---

# 65. 本轮真实数据接入

优先完成：

```text
UN Comtrade monthly
WTO / WITS tariff
World Bank
```

如果其中某个官方数据源因为授权、API限制无法稳定自动接：

不要阻塞整体开发。

建立：

```text
Provider
Fixture
Import CLI
Manual Dataset Ingestion
```

并文档说明。

---

# 66. 通用 Dataset Import

必须支持管理员导入：

```text
CSV
JSON
Parquet
```

进入：

```text
Raw
↓
Normalizer
↓
Canonical
```

不要让外部API成为唯一数据进入方式。

---

# 67. Provenance

所有数据进入系统必须知道：

```text
where
when
how
which version
```

即：

```text
provenance
```

这比多接几个API更重要。

---

# 68. Cache

从现在开始按数据类型配置：

```text
TRADE_ANNUAL
TRADE_MONTHLY
TARIFF
MACRO
SEARCH
MARKETPLACE
TENDER
SUPPLIER
```

不能继续一个统一TTL。

---

# 69. API最终结构

建议逐渐演进：

```text
/api/v1/products
/api/v1/countries

/api/v1/markets
/api/v1/opportunities

/api/v1/signals

/api/v1/trade
/api/v1/tariffs
/api/v1/macro

/api/v1/marketplaces
/api/v1/demands

/api/v1/supply

/api/v1/economics

/api/v1/watchlists
/api/v1/events

/api/v1/evidence

/api/v1/integrations
```

不要一次重命名破坏现有API。

保留兼容层。

---

# 70. Opportunity API

最终：

```http
GET /api/v1/opportunities/{id}
```

返回：

```json
{
  "market": {},
  "scores": {
    "market_attractiveness": null,
    "structural_demand": null,
    "digital_demand": null,
    "marketplace_demand": null,
    "explicit_demand": null,
    "supply_fit": null,
    "economics": null,
    "risk": null,
    "distribution_opportunity": null,
    "confidence": null
  },
  "signals": {},
  "supply": {},
  "economics": {},
  "risk": {},
  "evidence": [],
  "recommendations": []
}
```

没有数据：

```text
null
```

不要0。

---

# 71. 前端导航最终结构

建议：

```text
Overview

Discover
├─ Products
├─ Countries
├─ Opportunities
└─ Map

Demand
├─ Trade
├─ Search
├─ Marketplace
└─ Explicit Demand

Supply
├─ Supplier Match
└─ Supply Fit

Intelligence
├─ Watchlist
├─ Opportunity Feed
└─ Evidence

Admin
├─ Data Sources
├─ Data Quality
├─ Sync Jobs
└─ Methodology
```

ERP操作不要塞进这里。

---

# 72. 首页最终目标

首页不再只是搜索页。

包括：

```text
Global Opportunity Feed

Demand Movers

China Share Movers

New Explicit Demand

Supply-ready Opportunities

Watchlist Alerts
```

但只展示已有真实数据。

---

# 73. 数据库与分析技术

当前：

```text
PostgreSQL
```

继续使用。

允许使用：

```text
DuckDB
```

进行离线分析和批量处理。

暂时不要加入：

```text
ClickHouse
```

除非真实数据规模和查询性能证明需要。

---

# 74. Job系统

数据同步逐渐复杂后：

统一建立：

```text
DataJob
```

类型：

```text
INGEST
NORMALIZE
SCORE
REFRESH
BACKFILL
MATCH
```

状态：

```text
PENDING
RUNNING
COMPLETED
PARTIAL
FAILED
```

保留：

```text
attempt
error
started_at
finished_at
```

---

# 75. Idempotency

所有：

```text
sync
webhook
import
score calculation
```

必须尽可能幂等。

不要重复产生：

```text
trade observation
signal
opportunity event
```

---

# 76. Score Versioning

任何Score：

```text
structural_demand_v1
structural_demand_v2

distribution_opportunity_v1
```

不能在原版本下面静默修改公式。

---

# 77. Metric Registry

建议建立：

```text
metric_definitions
```

管理：

```text
metric_key
name
description
unit
higher_is_better
source_layer
normalization
```

避免大量魔法字符串散落代码。

---

# 78. Feature Flags

所有尚未稳定的数据源：

```text
ENABLE_GOOGLE_TRENDS
ENABLE_OZON
ENABLE_WILDBERRIES
ENABLE_AMAZON
ENABLE_TENDER
ENABLE_SUPPLIER
```

默认按实际环境配置。

---

# 79. 测试原则

测试必须覆盖：

```text
source reliability
observed type

missing data
stale data

provider failure
partial provider failure

score coverage
confidence

HS version

monthly trade

tariff
macro

signal normalization

opportunity calculation

duplicate import

provenance
```

---

# 80. Fixture

每个Provider必须有：

```text
fixture
```

CI不得依赖真实外网。

至少准备：

```text
Pressure Sensor / HS 902620
```

作为完整端到端案例。

---

# 81. E2E案例

目标：

```text
Pressure Sensor
↓
HS902620
↓
Global Structural Demand
↓
Turkey
↓
Tariff
↓
Country Capacity
↓
Digital Signal if available
↓
Marketplace if available
↓
Supplier Fit if available
↓
Economics if available
↓
Opportunity
↓
Evidence
```

任何层没有接入：

显示：

```text
Not connected / No data
```

---

# 82. UI可信度表达

每项核心指标可以展示：

```text
Source
Period
Updated
Reliability
Observed Type
```

例如：

```text
$183M
2025 Imports

UN Comtrade
REPORTED
Reliability A
```

---

# 83. 严禁行为

禁止：

```text
AI编造数据

缺失值自动填0

Estimated显示成Observed

HS6当SKU

Google Trends当搜索量

海关Unit Value当零售价

进口额当消费者销售额

平台管理员权限传给ERP

Market直接改Supplier

Market直接操作Marketplace

没有数据却生成完整Opportunity Score
```

---

# 84. 代码原则

核心业务必须：

```text
Provider-independent
Source-aware
Versioned
Auditable
Explainable
```

---

# 85. 文档

更新：

```text
ARCHITECTURE.md
DATA_MODEL.md
DATA_SOURCES.md
SCORING.md
DATA_RELIABILITY.md
PROVENANCE.md
SUPPLIER_INTEGRATION.md
ERP_INTEGRATION.md
ROADMAP.md
```

ROADMAP可以记录未接入数据源。

但系统架构不能按照 Roadmap 阶段拆成多个未来要重写的版本。

---

# 86. 最终业务模型

项目最终应该能够回答两个方向：

## Supply → Demand

```text
这个中国商品
↓
世界哪里最需要？
↓
哪个市场最值得进入？
↓
为什么？
```

## Demand → Supply

```text
全球哪里出现机会？
↓
需要什么？
↓
中国有哪些商品和供应商可以满足？
```

---

# 87. 最终飞轮

```text
Global Demand Data
        ↓
Demand Graph
        ↓
Opportunity Detection
        ↓
China Supply Match
        ↓
Economics
        ↓
Human Decision
        ↓
ERP Execution
        ↓
Real Transaction
        ↓
Outcome Data
        ↓
Scoring Improvement
```

---

# 88. Matrix One真正的核心资产

长期最有价值的不是：

```text
UN Comtrade数据
Google Trends
Marketplace数据
```

这些其他公司也可以买到。

真正资产是：

```text
Global External Data
+
China Supplier Network
+
Actual Supplier Offers
+
Real Marketplace Transactions
+
Real B2B RFQs
+
Decision History
+
Actual Outcome
```

最终形成：

```text
Demand Graph
×
Supply Graph
×
Transaction Graph
×
Decision / Outcome Graph
```

---

# 89. Codex现在的执行任务

请立即：

1. 阅读当前 market 项目全部代码和数据库migration；
2. 不重写当前V1；
3. 生成 `CURRENT_ARCHITECTURE_AUDIT.md`；
4. 对照本文档建立最终模型差异清单；
5. 设计兼容migration；
6. 建立 Data Source Registry；
7. 建立 Provider Registry；
8. 建立统一 DemandSignal；
9. 建立 Reliability / Observed Type / Freshness；
10. 强化 Evidence / Provenance；
11. 建立最终版 MarketOpportunity结构；
12. 建立 Tariff Provider；
13. 建立 Macro Provider；
14. 扩展 Comtrade Monthly Provider；
15. 建立 Marketplace / Search / Tender / Supplier Provider接口和 Null实现；
16. 接入可以可靠取得的 WTO/WITS、World Bank 和 Comtrade真实数据；
17. 建立 Data Quality后台；
18. 建立 Watchlist / OpportunityEvent；
19. 重构前端Opportunity Detail以支持多层数据；
20. 补齐所有测试和文档。

---

# 90. 实施约束

不要因为某个外部API无法立即使用而停止整个任务。

如果外部源存在：

```text
认证
限流
商业授权
网络限制
```

则：

```text
建立接口
建立fixture
建立导入能力
记录integration status
继续其他开发
```

不能用假数据伪装为已经接入。

---

# 91. Definition of Done

本轮架构升级完成的最低标准：

* [ ] 现有V1功能没有被破坏
* [ ] 数据库通过migration升级
* [ ] Data Source Registry存在
* [ ] Provider Registry存在
* [ ] Raw / Canonical / Signal / Intelligence层清晰
* [ ] DemandSignal统一模型存在
* [ ] Reliability体系存在
* [ ] Observed Type体系存在
* [ ] Freshness体系存在
* [ ] Evidence完整
* [ ] Provenance完整
* [ ] HS版本处理存在
* [ ] Comtrade月度架构存在
* [ ] Tariff Provider存在
* [ ] Macro Provider存在
* [ ] Search Provider接口存在
* [ ] Marketplace Provider接口存在
* [ ] Explicit Demand Provider接口存在
* [ ] Supplier Network Provider接口存在
* [ ] MarketOpportunity支持最终多维结构
* [ ] Confidence计算独立于Opportunity Score
* [ ] Watchlist可用
* [ ] Opportunity Event可用
* [ ] Data Quality后台可用
* [ ] 缺失数据不会生成伪结果
* [ ] Fixture下可以完整离线测试
* [ ] 所有测试通过
* [ ] Docker启动正常
* [ ] 文档完整

---

# 92. 最终设计原则

开发过程中始终用下面五句话判断架构是否正确：

> **官方数据负责证明需求真实存在。**

> **数字行为和Marketplace数据负责证明需求正在发生什么变化。**

> **RFQ/Tender负责证明谁现在就准备购买。**

> **Supplier Network负责证明中国真的能供。**

> **ERP真实交易结果负责证明我们的判断到底对不对。**

最终系统不是一个“分析工具”。

它应该逐渐成为：

# Matrix One Global Distribution Intelligence

核心能力：

> **发现全球需求 → 匹配中国供应 → 计算商业可行性 → 形成可执行决策 → 通过ERP完成交易 → 用真实结果继续优化判断。**

从现在开始所有代码和数据模型，都必须朝这个最终状态演进。
