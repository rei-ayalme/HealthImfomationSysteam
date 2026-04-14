# 数据格式规范文档

> 文档版本: 1.0.0  
> 最后更新: 2026-04-12  
> 适用范围: Health_Imformation_Systeam 项目全量数据资产

---

## 1. 数据资产概览

### 1.1 数据分层架构

```
data/
├── raw/                    # 原始数据层 (RAW)
│   ├── 卫生年鉴表/         # 中国卫生健康统计年鉴 (2001-2020)
│   ├── GBD.csv            # 全球疾病负担数据
│   ├── DBD.csv            # 疾病负担备份数据
│   ├── NBS.csv            # 国家统计局宽表
│   ├── WDI.csv            # 世界发展指标
│   └── WB_HNP.csv         # 世界银行健康营养人口数据 (2.6GB)
├── processed/             # 清洗后数据层 (PROCESSED)
│   ├── cleaned_health_data.xlsx
│   ├── cleaned_gbd_disease.csv
│   ├── cleaned_gbd_risk.csv
│   ├── cleaned_wdi_resources.csv
│   └── spatial_cache_*.json
├── china/                 # 参考数据层 (REF)
│   └── 全国省份经纬度坐标.csv
├── osmnx_cache/           # 缓存数据层 (CACHE)
│   └── *.json             # OpenStreetMap路网缓存
└── missing_data/          # 报告数据层 (REPORT)
    └── missing_report_*.json
```

### 1.2 数据量级统计

| 数据层级 | 文件数量 | 总大小 | 主要格式 |
|---------|---------|--------|---------|
| RAW | 25+ | ~2.7GB | CSV, XLSX, XLS |
| PROCESSED | 5+ | ~40MB | CSV, XLSX, JSON |
| REF | 1 | 2KB | CSV |
| CACHE | 16+ | ~20MB | JSON |
| FRONTEND | 3 | ~8MB | JSON |

---

## 2. 原始数据层 (RAW) 格式规范

### 2.1 中国卫生健康统计年鉴数据

#### 2.1.1 面板数据文件

**文件**: `中国卫生健康统计年鉴数据（2001-2020年）.xlsx`

| 属性 | 说明 |
|-----|------|
| 格式 | XLSX |
| 大小 | 3,886 KB |
| 时间跨度 | 2001-2020年 |
| 空间粒度 | 省级 (31省/市/区) |
| 安全级别 | 机密 |

**实际表头结构** (从 `audit/field_lineage.csv` 提取):

| 序号 | 中文字段名 | 英文字段名 | 数据类型 | 长度 | 是否必填 | 采样例值 | 单位 |
|-----|----------|-----------|---------|------|---------|---------|------|
| 1 | 地区/省份 | region_name | STRING | 50 | 是 | 北京/四川/广东 | 无 |
| 2 | 年份 | year | INT | 4 | 是 | 2019 | 年 |
| 3 | 执业(助理)医师数 | physicians | FLOAT | 12 | 否 | 2341560.0 | 人 |
| 4 | 注册护士数 | nurses | FLOAT | 12 | 否 | 3000000.0 | 人 |
| 5 | 医疗机构床位数 | hospital_beds | FLOAT | 12 | 否 | 6000000.0 | 张 |
| 6 | 总人口 | population | FLOAT | 12 | 否 | 14033.0 | 万人 |
| 7 | 每千人医师数 | physicians_per_1000 | FLOAT | 10,4 | 否 | 2.8 | 人/千人 |
| 8 | 每千人护士数 | nurses_per_1000 | FLOAT | 10,4 | 否 | 3.2 | 人/千人 |
| 9 | 每千人床位数 | hospital_beds_per_1000 | FLOAT | 10,4 | 否 | 6.0 | 张/千人 |
| 10 | 综合供给指数 | actual_supply_index | FLOAT | 10,4 | 否 | 3.15 | 指数 |
| 11 | 理论需求指数 | theoretical_demand_index | FLOAT | 10,4 | 否 | 3.50 | 指数 |
| 12 | 相对缺口率 | relative_gap_rate | FLOAT | 10,4 | 否 | 0.1 | 比率 |
| 13 | 缺口严重程度 | gap_severity | ENUM | 20 | 否 | 轻度短缺 | 无 |

**说明**:
- 原始年鉴数据单位：医师/护士/床位数为"万人"，需×10000转换为"人"
- 计算字段：physicians_per_1000 = physicians / (population × 10)
- 缺口严重程度分类：配置充足/合理/轻度/严重

**异构列名映射** (参见 `config/column_mapping.json`):

| 标准字段 | 数据类型 | 单位 | 单位转换 | 主要列名变体 |
|---------|---------|------|---------|-------------|
| region_code | STRING | 无 | - | 地区编码, 行政区划代码, 区划代码, code, region_id, adcode |
| region_name | STRING | 无 | - | 地区, 省份, 省市, 省/市, province, city, area, location |
| year | INT | 年 | - | 年份, 时间, 年度, year, 统计年份, data_year, period |
| physicians | FLOAT | 人 | ×10000 | 执业（助理）医师（人）, 执业医师（人）, 医生数, 医师总量, 执业医生数, doctors |
| nurses | FLOAT | 人 | ×10000 | 注册护士（人）, 护士数, 护士总量, 护理人员, 护理人员数, registered_nurses |
| hospital_beds | FLOAT | 张 | ×10000 | 医疗卫生机构床位数（张）, 床位数, 病床数, 床位, 医院床位数, beds |
| population | FLOAT | 万人 | ×1 | 总人口（万人）, 人口（万人）, 人口数, 年末常住人口, 常住人口, total_population |
| hospitals | FLOAT | 个 | - | 医院数, 医院数量, 医院个数, 医疗卫生机构数_医院, hospital_count |
| primary_institutions | FLOAT | 个 | - | 基层医疗卫生机构, 社区卫生服务中心, 乡镇卫生院, 村卫生室, 诊所 |
| medical_expenditure | FLOAT | 亿元 | - | 卫生总费用, 卫生费用, 卫生支出, 医疗卫生支出, health_expenditure |
| life_expectancy | FLOAT | 岁 | - | 预期寿命, 平均预期寿命, 人均预期寿命, 期望寿命, 平均寿命 |
| mortality_rate | FLOAT | ‰ | - | 死亡率, 人口死亡率, death_rate, 粗死亡率 |
| birth_rate | FLOAT | ‰ | - | 出生率, 人口出生率, fertility_rate, 粗出生率 |
| gdp | FLOAT | 亿元 | - | 地区生产总值, GDP, 国内生产总值, gross_domestic_product, 经济总量 |
| gdp_per_capita | FLOAT | 元 | - | 人均地区生产总值, 人均GDP, 人均国内生产总值, per_capita_gdp |
| urbanization_rate | FLOAT | % | - | 城镇化率, 城镇化水平, 城市化率, urban_rate, 城镇人口比重 |
| elderly_ratio | FLOAT | % | - | 老龄化比例, 老年人口比例, 65岁及以上人口比例, 老龄化率, aging_rate |
| location_name | STRING | 无 | - | location, country, nation, 地区, 国家, 国家/地区 |
| cause_name | STRING | 无 | - | cause, disease, 疾病, 疾病名称, 病种, 疾病类型, disease_name |
| val | FLOAT | - | - | value, 指标值, 数值, measure, measure_value |
| rei_name | STRING | 无 | - | rei, risk_factor, 风险因素, 危险因素, 暴露因素, risk_factor_name |
| paf | FLOAT | 无量纲 | - | PAF, 人群归因分数, population_attributable_fraction, attributable_fraction |
| indicator | STRING | 无 | - | indicator_name, 指标, 指标名称, 变量, 变量名 |
| longitude | FLOAT | 度 | - | 经度, lon, lng, x, long, 经度坐标 |
| latitude | FLOAT | 度 | - | 纬度, lat, y, 纬度坐标 |

**映射规则说明**:
1. **单位转换**: 部分字段原始数据单位为"万人"，需根据 `unit_conversion` 字段进行转换
2. **大小写不敏感**: 列名匹配时不区分大小写
3. **空格处理**: 自动去除列名前后空格，统一处理全角/半角空格
4. **模糊匹配**: 支持子串匹配和相似度匹配（可选）

#### 2.1.2 分年数据文件

**文件命名**: `{年份}.xlsx` (如 2005.xlsx, 2006.xlsx 等)

| 年份 | 格式 | 大小 | 特点 |
|-----|------|------|------|
| 2005-2020 | XLSX | 16-556 KB | 标准Excel格式 |
| 2006, 2007, 2008, 2009, 2012 | XLS | 混合 | 多子表格式 (VxxC命名) |

**历史年鉴特殊格式**:
- 2006年: p3~p405 共约130张分表
- 2007年: 13大类含人员/设施/服务等
- 2008-2012年: VxxC格式，省级数据

### 2.2 全球疾病负担数据 (GBD)

#### 2.2.1 GBD主数据文件

**文件**: `GBD.csv`

| 属性 | 说明 |
|-----|------|
| 格式 | CSV |
| 大小 | 908 KB |
| 记录数 | ~10,000行 |
| 来源 | IHME/GBD |

**实际表头结构**:

| 序号 | 中文字段名 | 英文字段名 | 数据类型 | 长度 | 取值范围 | 是否必填 | 采样例值 | 单位 |
|-----|----------|-----------|---------|------|---------|---------|---------|------|
| 1 | 国家/地区名称 | location_name | STRING | 100 | ISO国家/省名 | 是 | China | 无 |
| 2 | 年份 | year | INT | 4 | 1990-2025 | 是 | 2019 | 年 |
| 3 | 疾病名称 | cause_name | STRING | 200 | GBD疾病分类 | 是 | Cardiovascular diseases | 无 |
| 4 | 疾病大类 | disease_category | ENUM | 50 | 传染/非传染/伤害 | 否 | - | 无 |
| 5 | 疾病负担绝对值 | val | FLOAT | 15,4 | ≥0 | 否 | - | DALYs |
| 6 | 风险因素名称 | rei_name | STRING | 200 | GBD风险分类 | 否 | PM2.5 | 无 |
| 7 | 风险类别 | risk_category | ENUM | 50 | behavioral/environmental/metabolic | 否 | - | 无 |
| 8 | 人群归因分数 | paf | FLOAT | 10,4 | 0-1 | 否 | - | 无量纲 |
| 9 | 流行病学转型指数 | eti | FLOAT | 10,4 | 0-1 | 否 | - | 指数 |
| 10 | 转型阶段 | transition_stage | STRING | 50 | - | 否 | - | 无 |
| 11 | 纬度 | latitude | FLOAT | 9,6 | -90至90 | 否 | - | 度 |
| 12 | 经度 | longitude | FLOAT | 9,6 | -180至180 | 否 | - | 度 |
| 13 | 城市区划类型 | urban_zone_type | ENUM | 50 | 老城区/新开发区/边缘区 | 否 | - | 无 |
| 14 | 老龄化比例 | elderly_ratio | FLOAT | 10,4 | 0-1 | 否 | - | 比例 |
| 15 | 暴露等级语言变量 | exposure_category | ENUM | 50 | 高/中/低 | 否 | - | 无 |
| 16 | 云模型期望 | cloud_ex | FLOAT | 10,4 | - | 否 | - | - |
| 17 | 云模型熵 | cloud_en | FLOAT | 10,4 | - | 否 | - | - |
| 18 | 云模型超熵 | cloud_he | FLOAT | 10,4 | - | 否 | - | - |

#### 2.2.2 DBD备份文件

**文件**: `DBD.csv`

- 格式与GBD.csv相似
- 疑似重复数据，用于备份

### 2.3 世界银行数据

#### 2.3.1 WDI精选指标

**文件**: `WDI.csv`

| 属性 | 说明 |
|-----|------|
| 格式 | CSV |
| 大小 | 142 KB |
| 记录数 | ~2,000行 |
| 来源 | World Bank |

**实际表头结构**:

| 序号 | 中文字段名 | 英文字段名 | 数据类型 | 长度 | 取值范围 | 是否必填 | 说明 |
|-----|----------|-----------|---------|------|---------|---------|------|
| 1 | 指标名称 | indicator | STRING | 200 | 自由文本 | 是 | 原始OWID/WHO指标名 |
| 2 | 指标数值 | value | FLOAT | 15,4 | 依指标而定 | 否 | 指标具体数值 |
| 3 | 单位 | unit | STRING | 50 | 自由文本 | 否 | 指标单位 |
| 4 | 国家/地区名称 | location_name | STRING | 100 | ISO国家/省名 | 是 | 数据所属地区 |
| 5 | 年份 | year | INT | 4 | 1990-2025 | 是 | 统计年份 |
| 6 | 数据来源 | source | ENUM | 20 | WHO/Local/OWID/GBD/SEARCH | 否 | 数据来源标识 |

#### 2.3.2 WB_HNP大数据文件

**文件**: `WB_HNP.csv`

| 属性 | 说明 |
|-----|------|
| 格式 | CSV |
| 大小 | 2,753,909 KB (2.6GB) |
| 记录数 | >1000万行 |
| 处理建议 | 需分批处理 |

**说明**: 世界银行Health Nutrition and Population统计数据，包含全球各国健康指标时间序列。

### 2.4 国家统计局数据

**文件**: `NBS.csv`

| 属性 | 说明 |
|-----|------|
| 格式 | CSV |
| 大小 | 4 KB |
| 记录数 | ~30行 |
| 说明 | 国家统计局省份指标宽表 |
| 安全级别 | 内部 |

**实际表头结构**:

| 序号 | 中文字段名 | 英文字段名 | 数据类型 | 长度 | 是否必填 | 说明 |
|-----|----------|-----------|---------|------|---------|------|
| 1 | 地区/省份 | region_name | STRING | 50 | 是 | 省份名称 |
| 2 | 年份 | year | INT | 4 | 是 | 统计年份 |
| 3 | 总人口 | population | FLOAT | 12 | 否 | 年末常住人口(万人) |
| 4 | 执业(助理)医师数 | physicians | FLOAT | 12 | 否 | 医师数量 |
| 5 | 注册护士数 | nurses | FLOAT | 12 | 否 | 护士数量 |
| 6 | 医疗机构床位数 | hospital_beds | FLOAT | 12 | 否 | 床位数量 |

---

## 3. 清洗后数据层 (PROCESSED) 格式规范

### 3.1 清洗后健康数据

**文件**: `cleaned_health_data.xlsx`

| 属性 | 说明 |
|-----|------|
| 格式 | XLSX |
| 大小 | 39,825 KB (~40MB) |
| 记录数 | ~数万行 |
| 生成方式 | 系统自动 (预处理器输出) |

**实际表头结构**:

| 序号 | 中文字段名 | 英文字段名 | 数据类型 | 长度 | 是否必填 | 说明 |
|-----|----------|-----------|---------|------|---------|------|
| 1 | 地区编码 | region_code | STRING | 50 | 是 | 地区编码，如510100 |
| 2 | 地区名称 | region_name | STRING | 50 | 是 | 地区名称，如成都市 |
| 3 | 年份 | year | INT | 4 | 是 | 统计年份 |
| 4 | 执业(助理)医师数 | physicians | FLOAT | 12 | 否 | 医师数量(人) |
| 5 | 注册护士数 | nurses | FLOAT | 12 | 否 | 护士数量(人) |
| 6 | 医疗机构床位数 | hospital_beds | FLOAT | 12 | 否 | 床位数量(张) |
| 7 | 医院数量 | hospitals | FLOAT | 12 | 否 | 医院数量(个) |
| 8 | 年末常住人口 | population | FLOAT | 12 | 否 | 人口数量(万人) |
| 9 | 每千人医师数 | physicians_per_1000 | FLOAT | 10,4 | 否 | 计算字段 |
| 10 | 每千人护士数 | nurses_per_1000 | FLOAT | 10,4 | 否 | 计算字段 |
| 11 | 每千人床位数 | hospital_beds_per_1000 | FLOAT | 10,4 | 否 | 计算字段 |
| 12 | 综合供给指数 | actual_supply_index | FLOAT | 10,4 | 否 | 计算字段 |
| 13 | 理论需求指数 | theoretical_demand_index | FLOAT | 10,4 | 否 | 计算字段 |
| 14 | 相对缺口率 | relative_gap_rate | FLOAT | 10,4 | 否 | 计算字段 |
| 15 | 缺口严重程度 | gap_severity | STRING | 20 | 否 | 分类字段 |

### 3.2 清洗后GBD数据

**文件**: `cleaned_gbd_disease.csv`

| 属性 | 说明 |
|-----|------|
| 格式 | CSV |
| 大小 | 1,225 KB |
| 记录数 | ~8,000行 |

### 3.3 空间分析缓存

**文件**: `spatial_cache_*.json`

| 属性 | 说明 |
|-----|------|
| 格式 | JSON |
| 大小 | 2-3 KB/文件 |
| 内容 | 成都市各区E2SFCA可及性结果 |
| 生成方式 | 系统自动缓存 |

**JSON结构**:

```json
{
  "region_code": "510107",
  "region_name": "武侯区",
  "accessibility_index": 2.35,
  "method": "e2sfca",
  "threshold_km": 5.0,
  "physician_ratio": 3.2,
  "bed_ratio": 5.8,
  "timestamp": "2025-03-20T10:30:00Z"
}
```

---

## 4. 前端数据层 (FRONTEND) 格式规范

### 4.1 中国省级健康数据

**文件**: `frontend/assets/data/cn_health.json`

| 属性 | 说明 |
|-----|------|
| 格式 | JSON |
| 大小 | 924 KB |
| 用途 | 宏观分析页渲染 |

**数据结构**: 二维数组格式

```json
[
  ["", "2000", "2001", ...],  // 表头行
  ["北京市", "75.2", "76.1", ...],
  ["上海市", "78.5", "79.2", ...],
  ...
]
```

### 4.2 清洗后健康数据 (JSON版)

**文件**: `frontend/assets/data/cleaned_health_data.json`

| 属性 | 说明 |
|-----|------|
| 格式 | JSON |
| 大小 | 2,308 KB |
| 用途 | 前端图表渲染 |

### 4.3 微观仿真数据

**文件**: `frontend/assets/data/simulation_data.json`

| 属性 | 说明 |
|-----|------|
| 格式 | JSON |
| 大小 | 4,762 KB |
| 记录数 | ~百万代理 |
| 用途 | IPF微观仿真人口结果 |

**数据结构**:

```json
{
  "2024": [
    [103.9945, 31.0400, 0.0],   // [经度, 纬度, 属性标记]
    [104.2851, 30.4618, 0.0],
    [104.3067, 30.6914, 1.0],   // 1.0 表示特殊标记点
    ...
  ]
}
```

---

## 5. 参考数据层 (REF) 格式规范

### 5.1 省份坐标参考

**文件**: `data/china/全国省份经纬度坐标.csv`

| 属性 | 说明 |
|-----|------|
| 格式 | CSV |
| 大小 | 2 KB |
| 记录数 | 31行 (31省) |
| 安全级别 | 公开 |

**实际表头结构**:

| 序号 | 中文字段名 | 英文字段名 | 数据类型 | 长度 | 取值范围 | 是否必填 | 采样例值 | 单位 |
|-----|----------|-----------|---------|------|---------|---------|---------|------|
| 1 | 省份 | province | STRING | 50 | 全国31省 | 是 | 四川省 | 无 |
| 2 | 经度 | longitude | FLOAT | 9,6 | 73-135 | 是 | 104.0665 | 度 |
| 3 | 纬度 | latitude | FLOAT | 9,6 | 18-54 | 是 | 30.6667 | 度 |

**说明**: 存储全国31个省级行政区的地理中心坐标，用于地图可视化。

---

## 6. 数据模式定义 (Schema Dictionary)

### 6.1 医疗资源数据模式

```yaml
medical_resource:
  description: "医疗资源数据模式"
  fields:
    region_code:          {type: string, required: true, example: "510100"}
    region_name:          {type: string, required: true, example: "成都市"}
    year:                 {type: integer, required: true, example: 2023}
    physicians:           {type: number, required: true, example: 85000}
    nurses:               {type: number, required: true, example: 92000}
    hospital_beds:        {type: number, required: true, example: 120000}
    hospitals:            {type: number, required: false, example: 450}
    primary_institutions: {type: number, required: false, example: 5200}
```

### 6.2 人口统计数据模式

```yaml
population:
  description: "人口统计数据模式"
  fields:
    region_code:      {type: string, required: true}
    region_name:      {type: string, required: true}
    year:             {type: integer, required: true}
    total_population: {type: number, required: true, example: 2140.3}
    urban_population: {type: number, required: false, example: 1684.0}
    rural_population: {type: number, required: false, example: 456.3}
    elderly_population: {type: number, required: false, example: 285.6}
    elderly_ratio:    {type: number, required: false, example: 13.34}
    birth_rate:       {type: number, required: false, example: 8.5}
    mortality_rate:   {type: number, required: false, example: 6.2}
```

### 6.3 医疗设施位置数据模式

```yaml
facility_location:
  description: "医疗设施位置数据模式"
  fields:
    facility_id:      {type: string, required: true, example: "HOSP_001"}
    facility_name:    {type: string, required: true, example: "华西医院"}
    facility_type:    {type: string, required: true, enum: ["三级甲等", "三级乙等", "二级甲等", "二级乙等", "社区卫生服务中心", "乡镇卫生院"]}
    address:          {type: string, required: false}
    longitude:        {type: number, required: true, example: 104.0665}
    latitude:         {type: number, required: true, example: 30.6431}
    bed_capacity:     {type: integer, required: false, example: 4300}
    department_count: {type: integer, required: false, example: 45}
    is_emergency:     {type: boolean, required: false, example: true}
    phone:            {type: string, required: false}
```

### 6.4 社区需求点数据模式

```yaml
community_demand:
  description: "社区需求点数据模式"
  fields:
    community_id:   {type: string, required: true, example: "COMM_001"}
    community_name: {type: string, required: true, example: "玉林社区"}
    district:       {type: string, required: true, example: "武侯区"}
    longitude:      {type: number, required: true, example: 104.0565}
    latitude:       {type: number, required: true, example: 30.6331}
    population:     {type: number, required: true, example: 15000}
    elderly_ratio:  {type: number, required: false, example: 0.18}
    households:     {type: integer, required: false, example: 5200}
    avg_income:     {type: number, required: false, example: 48500}
```

### 6.5 可达性分析结果数据模式

```yaml
accessibility_result:
  description: "可达性分析结果数据模式"
  fields:
    region_code:       {type: string, required: true, example: "510107"}
    region_name:       {type: string, required: true, example: "武侯区"}
    accessibility_index: {type: number, required: true, example: 2.35}
    method:            {type: string, required: true, enum: ["e2sfca", "gravity", "2sfca"]}
    threshold_km:      {type: number, required: true, example: 5.0}
    physician_ratio:   {type: number, required: false, example: 3.2}
    bed_ratio:         {type: number, required: false, example: 5.8}
    nearest_hospital_km: {type: number, required: false, example: 1.5}
    avg_travel_time_min: {type: number, required: false, example: 12.5}
```

---

## 7. 全量字段汇总表

### 7.1 核心字段速查表

| 英文字段名 | 中文字段名 | 数据类型 | 长度 | 取值范围 | 单位 | 来源文件 |
|-----------|-----------|---------|------|---------|------|---------|
| region_code | 地区编码 | STRING | 50 | - | 无 | 年鉴表、清洗后数据 |
| region_name | 地区/省份 | STRING | 50 | 全国31省 | 无 | 年鉴表、NBS、WDI |
| year | 年份 | INT | 4 | 1990-2025 | 年 | 全部 |
| physicians | 执业(助理)医师数 | FLOAT | 12 | ≥0 | 人 | 年鉴表、NBS、清洗后数据 |
| nurses | 注册护士数 | FLOAT | 12 | ≥0 | 人 | 年鉴表、NBS、清洗后数据 |
| hospital_beds | 医疗机构床位数 | FLOAT | 12 | ≥0 | 张 | 年鉴表、NBS、清洗后数据 |
| population | 总人口 | FLOAT | 12 | ≥0 | 万人 | 年鉴表、NBS |
| physicians_per_1000 | 每千人医师数 | FLOAT | 10,4 | 0-50 | 人/千人 | 清洗后数据(计算) |
| nurses_per_1000 | 每千人护士数 | FLOAT | 10,4 | 0-50 | 人/千人 | 清洗后数据(计算) |
| hospital_beds_per_1000 | 每千人床位数 | FLOAT | 10,4 | 0-100 | 张/千人 | 清洗后数据(计算) |
| location_name | 国家/地区名称 | STRING | 100 | ISO国家/省名 | 无 | GBD、WDI |
| cause_name | 疾病名称 | STRING | 200 | GBD疾病分类 | 无 | GBD |
| val | 疾病负担绝对值 | FLOAT | 15,4 | ≥0 | DALYs | GBD |
| rei_name | 风险因素名称 | STRING | 200 | GBD风险分类 | 无 | GBD |
| paf | 人群归因分数 | FLOAT | 10,4 | 0-1 | 无量纲 | GBD |
| indicator | 指标名称 | STRING | 200 | 自由文本 | 无 | WDI |
| value | 指标数值 | FLOAT | 15,4 | 依指标而定 | 依指标 | WDI |
| longitude | 经度 | FLOAT | 9,6 | -180至180 | 度 | 省份坐标、GBD |
| latitude | 纬度 | FLOAT | 9,6 | -90至90 | 度 | 省份坐标、GBD |
| province | 省份 | STRING | 50 | 全国31省 | 无 | 省份坐标 |

### 7.2 计算字段说明

| 计算字段名 | 计算公式 | 说明 |
|-----------|---------|------|
| physicians_per_1000 | physicians / (population × 10) | 每千人医师数 |
| nurses_per_1000 | nurses / (population × 10) | 每千人护士数 |
| hospital_beds_per_1000 | hospital_beds / (population × 10) | 每千人床位数 |
| actual_supply_index | physician×0.4 + nurse×0.35 + beds×0.25 | 综合供给指数 |
| relative_gap_rate | (需求-供给) / 需求 | 相对缺口率 |

---

## 8. 数据关联关系

### 7.1 核心数据流

```
┌─────────────────────────────────────────────────────────────────┐
│                        原始数据层 (RAW)                          │
├─────────────────────────────────────────────────────────────────┤
│  卫生年鉴表 ──┐                                                  │
│  GBD.csv     ─┼──→ 清洗/标准化 ──→ 清洗后数据层 (PROCESSED)      │
│  WDI.csv     ─┤                       ↓                          │
│  WB_HNP.csv  ─┘                  前端数据层 (FRONTEND)           │
│                                       ↓                          │
│                                  可视化展示                      │
└─────────────────────────────────────────────────────────────────┘
```

### 7.2 关键关联字段

| 关联类型 | 主表 | 关联字段 | 从表 | 说明 |
|---------|------|---------|------|------|
| 空间关联 | 医疗设施 | (longitude, latitude) | 社区需求点 | 地理坐标匹配 |
| 时间关联 | 卫生年鉴 | year | GBD数据 | 年度对齐 |
| 地区关联 | 卫生年鉴 | region_name | 省份坐标 | 省份名称匹配 |
| 设施关联 | 可达性结果 | region_code | 医疗资源 | 地区编码匹配 |

---

## 8. 数据质量与约束

### 8.1 必填字段约束

| 数据类型 | 必填字段 |
|---------|---------|
| medical_resource | region_code, region_name, year, physicians, nurses, hospital_beds |
| population | region_code, region_name, year, total_population |
| facility_location | facility_id, facility_name, facility_type, longitude, latitude |
| community_demand | community_id, community_name, district, longitude, latitude, population |
| accessibility_result | region_code, region_name, accessibility_index, method, threshold_km |

### 8.2 数值范围约束

| 字段 | 最小值 | 最大值 | 说明 |
|-----|-------|-------|------|
| year | 2000 | 2030 | 统计年份 |
| paf | 0.0 | 1.0 | 人群归因分数 |
| elderly_ratio | 0.0 | 1.0 | 老龄化率 |
| longitude | 73.0 | 135.0 | 中国经度范围 |
| latitude | 18.0 | 54.0 | 中国纬度范围 |

### 8.3 枚举值约束

| 字段 | 允许值 |
|-----|-------|
| facility_type | "三级甲等", "三级乙等", "二级甲等", "二级乙等", "社区卫生服务中心", "乡镇卫生院" |
| method | "e2sfca", "gravity", "2sfca" |

---

## 9. 附录

### 9.1 相关配置文件

| 文件路径 | 用途 |
|---------|------|
| `config/schema_dictionary.json` | 数据模式定义 |
| `config/column_mapping.json` | 异构列名映射 |
| `audit/data_asset_inventory.csv` | 数据资产清单 |
| `audit/field_lineage.csv` | 字段血缘关系 |

### 9.2 数据安全分级

| 级别 | 说明 | 适用数据 |
|-----|------|---------|
| 公开 | 可公开访问 | 省份坐标、OSM路网 |
| 一般 | 内部使用 | GBD数据、WDI数据、清洗后数据 |
| 内部 | 限制访问 | NBS数据、处理中间数据 |
| 机密 | 严格管控 | 卫生年鉴原始数据 |

### 9.3 版本历史

| 版本 | 日期 | 变更说明 |
|-----|------|---------|
| 1.0.0 | 2026-04-12 | 初始版本，整合全量数据资产 |
