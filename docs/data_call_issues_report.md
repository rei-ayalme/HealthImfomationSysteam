# 数据调用问题专项报告

**报告日期**: 2026-04-16  
**检查范围**: `frontend/`、`utils/`、`modules/`、`data/`  
**报告版本**: v1.0

---

## 一、执行摘要

本次检查针对中台系统数据层（data）和模块层（modules）的数据源调用情况进行了全面审查，识别出**6项主要问题**，涵盖数据源调用冗余、数据格式不匹配、数据处理逻辑错误、缓存一致性问题、Mock/硬编码数据使用以及前端直接硬编码数据等方面。

**关键发现**:
- 最严重问题：DEA效率计算使用人口数作为产出指标，导致结果失真
- 中等问题：数据格式硬编码、缓存缺乏版本控制
- 轻微问题：前端硬编码数据、Mock数据标识不清晰

---

## 二、问题总览

| 序号 | 问题类别 | 严重程度 | 涉及模块 | 优先级 |
|------|---------|---------|---------|--------|
| 1 | 数据源调用冗余 | 中 | `integrated_pipeline.py` | P1 |
| 2 | 数据格式不匹配 | 中 | `integrated_pipeline.py` | P1 |
| 3 | 数据处理逻辑错误 | **高** | `integrated_pipeline.py`, `loader.py` | **P0** |
| 4 | 缓存一致性问题 | 中 | `loader.py` | P2 |
| 5 | Mock/硬编码数据使用 | 中 | `frontend/`, `utils/` | P2 |
| 6 | 前端直接硬编码数据 | 低 | `macro-analysis.html` | P3 |

---

## 三、六项问题的四维分析

### 问题 1：数据源调用冗余

#### 表现
- `integrated_pipeline.py` 第87-88行重复实例化 `processor` 和 `loader`
- `run_global_burden_analysis()` 中多次读取同一GBD/WDI文件

#### 原因
- 代码重构时未清理重复逻辑
- 缺乏数据加载缓存机制

#### 影响
- 增加I/O开销，降低处理效率
- 重复内存占用

#### 建议
1. 复用已创建的实例，避免重复初始化
2. 实现文件级缓存，避免重复读取相同文件
3. 使用上下文管理器管理资源生命周期

**代码位置**: `modules/integrated_pipeline.py` L87-88

---

### 问题 2：数据格式不匹配

#### 表现
- GBD/WDI列名映射硬编码（`integrated_pipeline.py` L164-226）
- WDI年份列动态查找仅支持2019年

#### 原因
- 数据源Schema变更频繁
- 缺乏统一的列名映射配置

#### 影响
- 数据源更新时需修改代码
- 不同年份数据无法兼容

#### 建议
1. 提取列名映射到 `config/data_mappings.json`
2. 实现Schema版本控制
3. 增加多年份支持，使用通配符匹配年份列

**代码位置**: `modules/integrated_pipeline.py` L164-226

---

### 问题 3：数据处理逻辑错误 ⚠️ **最严重**

#### 表现
- DEA产出指标使用`population`代替真实诊疗数据
- E2SFCA默认容量值固定为1000

#### 原因
- 真实产出数据（诊疗/出院人数）缺失
- POI数据未包含床位数信息

#### 影响
- DEA效率计算结果失真，无法准确评估医疗资源配置效率
- 空间可及性评估不准确，影响资源配置决策

#### 建议
1. 从WDI或本地年鉴获取真实诊疗/出院人数作为DEA产出指标
2. 高德API返回数据增加床位数字段
3. 建立医院等级-容量映射表，根据医院类型设置合理容量

**代码位置**:
- `modules/integrated_pipeline.py` L300
- `modules/data/loader.py` L609

---

### 问题 4：缓存一致性问题 ✅ 已修复

#### 表现
- Redis缓存无版本控制
- 内存缓存无持久化机制

#### 原因
- 缓存设计未考虑数据更新场景
- 缺乏缓存失效策略

#### 影响
- 数据源更新后可能读取过期缓存
- 服务重启后内存缓存丢失

#### 修复方案 (2026-04-17)
已在 `modules/data/loader_v2.py` 中实现完整的缓存版本控制机制：

1. **缓存键版本控制**
   - 缓存键格式：`loader:v{version}:{source}:{indicator}:{params_hash}`
   - 版本号 `current_version` 作为类级别常量，升级时修改即可
   - 版本不匹配时自动视为缓存失效

2. **缓存过期策略**
   - 支持 TTL（Time To Live）设置，默认 86400 秒（1天）
   - 缓存元数据记录创建时间和过期时间
   - 自动清理过期缓存

3. **多级缓存架构**
   - 内存缓存（LRU策略）+ Redis 缓存
   - 内存缓存定期同步到 Redis
   - 支持缓存预热和手动失效

4. **缓存监控**
   - 详细的缓存操作日志（命中/未命中/失效）
   - 缓存统计信息（版本分布、缓存项数量）
   - 缓存命中率追踪

**关键代码**:
```python
class CacheManager:
    def _generate_cache_key(self, source, indicator, ...):
        # 缓存键包含版本号
        return f"loader:v{self.current_version}:{source}:{indicator}:..."
    
    def _is_cache_valid(self, metadata):
        # 检查版本号和过期时间
        if metadata.version != self.current_version:
            return False
        if metadata.expires_at and datetime.now() > expires:
            return False
        return True
```

**代码位置**: `modules/data/loader_v2.py` L155-400

---

### 问题 5：Mock/硬编码数据使用 ✅ 已修复

#### 表现
- `data-service.js` 引用 `/assets/data/simulation_data.json`
- `global_life_expectancy.py` 使用UN历史趋势外推法生成fallback数据
- 多个utils模块使用fallback/mock数据

#### 原因
- API失败时的降级策略
- 真实数据获取失败时的兜底方案

#### 影响
- 用户可能看到非真实数据而不自知
- 数据血缘不清晰，难以追溯

#### 修复方案 (2026-04-17)
已在 `modules/data/loader_v2.py` 中实现统一的 Mock 数据标识机制：

1. **标准 Mock 数据结构**
   - 所有 Mock 数据通过 `VersionedDataFrame` 包装
   - 元数据包含 `is_mock: True` 标识
   - 记录 Mock 数据生成原因和来源

2. **统一元数据格式**
   ```python
   @dataclass
   class DataMeta:
       is_mock: bool = False          # Mock 数据标识
       data_source: str = ""           # 数据来源
       version: str = "1.0.0"          # 数据版本
       fetched_at: str = ""            # 获取时间
       notes: str = ""                 # 备注（包含Mock原因）
   ```

3. **自动降级机制**
   - API 调用失败时自动返回带标识的 Mock 数据
   - 详细日志记录降级原因
   - 支持自定义 Mock 数据 Schema

4. **Mock 数据识别**
   - 通过 `VersionedDataFrame.is_mock` 属性快速识别
   - 数据框包含 `_meta` 列存储完整元数据
   - 支持元数据序列化/反序列化

**关键代码**:
```python
class DataLoaderV2:
    def _create_mock_data(self, source, indicator, schema=None, reason=""):
        """创建标准格式的 Mock 数据"""
        self.logger.warning(f"🎭 生成 Mock 数据 [{source}:{indicator}] - 原因: {reason}")
        
        if schema:
            df = pd.DataFrame({col: pd.Series(dtype=object) for col in schema.keys()})
        else:
            df = pd.DataFrame(columns=['region', 'year', 'value', 'indicator'])
        
        meta = DataMeta(
            is_mock=True,
            data_source=source,
            version=self.CURRENT_VERSION,
            notes=f"Mock数据: {reason}"
        )
        
        return VersionedDataFrame(df, meta)
```

**使用示例**:
```python
loader = DataLoaderV2()
result = loader.fetch_owid_data("life_expectancy")

if result.is_mock:
    print(f"警告：正在使用 Mock 数据 - {result.meta.notes}")
else:
    print(f"数据加载成功，来源: {result.meta.data_source}")
```

**代码位置**: `modules/data/loader_v2.py` L400-500

**涉及文件**:
- `modules/data/loader_v2.py` (新增)
- `tests/test_loader_v2.py` (单元测试)

---

### 问题 6：前端直接硬编码数据

#### 表现
- `macro-analysis.html` 包含硬编码的世界地图指标数据
- 预期寿命、DALYs率、死亡率等数据直接写在前端

#### 原因
- 减少API调用，提升页面加载速度
- 数据相对稳定

#### 影响
- 数据更新需修改前端代码
- 前后端数据可能不一致

#### 建议
1. 将硬编码数据迁移到后端API
2. 前端增加数据更新时间戳显示
3. 建立数据版本同步机制
4. 使用Service Worker缓存API响应

**代码位置**: `frontend/use/macro-analysis.html` L1419-1491

---

## 四、问题优先级矩阵

```
                    影响程度
    高 │                    │
       │     问题3          │
       │   (DEA逻辑错误)     │
       │                    │
    中 │  问题1    问题2    │  问题5
       │ (冗余)   (格式)    │ (Mock数据)
       │                    │
    低 │  问题4    问题6    │
       │ (缓存)   (前端)    │
       └────────────────────┘
         低        中        高
                  修复难度
```

---

## 五、整改建议汇总

| 优先级 | 问题 | 整改措施 | 预计工作量 | 负责人 |
|--------|------|---------|-----------|--------|
| **P0** | 问题3 | 修复DEA产出指标和E2SFCA容量计算逻辑 | 2-3天 | 数据团队 |
| P1 | 问题2 | 配置化列名映射，支持多版本Schema | 1-2天 | 后端开发 |
| P1 | 问题1 | 清理重复实例化，实现文件级缓存 | 1天 | 后端开发 |
| P2 | 问题4 | 增加缓存版本控制和持久化机制 | 2-3天 | 后端开发 |
| P2 | 问题5 | 完善Mock数据标识和验证机制 | 1天 | 前端+后端 |
| P3 | 问题6 | 将前端硬编码数据迁移到后端API | 2-3天 | 前端开发 |

---

## 六、数据调用规范检查清单

为确保数据调用符合规范，建议建立以下检查清单：

### 6.1 数据源验证
- [ ] 所有文件路径通过 `os.path.exists()` 验证
- [ ] 文件格式在白名单内（`.csv`, `.xlsx`, `.json`, `.geojson`）
- [ ] 文件大小在合理范围内
- [ ] 文件编码正确（UTF-8）

### 6.2 数据格式校验
- [ ] 使用Schema字典进行强类型校验
- [ ] 必填列存在性检查
- [ ] 数值范围合理性检查
- [ ] 日期格式统一性检查

### 6.3 缓存策略
- [ ] 实现带版本控制的缓存机制
- [ ] 缓存过期时间合理设置
- [ ] 缓存命中率监控
- [ ] 缓存失效策略明确

### 6.4 降级方案
- [ ] API失败时有明确的降级策略
- [ ] 降级数据来源清晰标识
- [ ] 用户界面显示数据状态（真实/模拟）
- [ ] 优先尝试其他数据源

### 6.5 血缘追踪
- [ ] 记录数据来源（文件/API/数据库）
- [ ] 记录数据处理过程（清洗/转换/计算）
- [ ] 记录数据更新时间
- [ ] 记录数据版本号

### 6.6 安全审计
- [ ] API密钥不硬编码在代码中
- [ ] 路径拼接使用 `os.path.join()`
- [ ] 用户输入参数化查询
- [ ] 敏感数据加密存储

### 6.7 性能监控
- [ ] 记录数据加载时间
- [ ] 监控缓存命中率
- [ ] 监控API响应时间
- [ ] 监控数据处理吞吐量

### 6.8 一致性检查
- [ ] 定期对比前后端数据一致性
- [ ] 定期验证Mock数据与真实数据偏差
- [ ] 建立数据质量评分机制
- [ ] 建立数据异常告警机制

---

## 七、附录

### 7.1 相关配置文件

| 配置文件 | 用途 | 位置 |
|---------|------|------|
| `schema_dictionary.json` | 数据字典，定义数据格式规范 | `config/schema_dictionary.json` |
| `column_mapping.json` | 列名映射，统一方言差异 | `config/column_mapping.json` |
| `settings.py` | 系统配置，包含数据路径 | `config/settings.py` |

### 7.2 关键代码文件

| 文件 | 职责 | 位置 |
|------|------|------|
| `loader.py` | 数据加载，I/O操作 | `modules/data/loader.py` |
| `processor.py` | 数据处理，清洗转换 | `modules/data/processor.py` |
| `integrated_pipeline.py` | 数据管道，流程编排 | `modules/integrated_pipeline.py` |
| `evaluator.py` | 算法引擎，DEA/E2SFCA | `modules/core/evaluator.py` |
| `data-service.js` | 前端数据服务 | `frontend/assets/js/data-service.js` |

### 7.3 术语说明

| 术语 | 说明 |
|------|------|
| DEA | 数据包络分析（Data Envelopment Analysis），用于评估资源配置效率 |
| E2SFCA | 增强型两步移动搜索法（Enhanced Two-Step Floating Catchment Area），用于计算空间可及性 |
| GBD | 全球疾病负担（Global Burden of Disease） |
| WDI | 世界发展指标（World Development Indicators） |
| POI | 兴趣点（Point of Interest），如医院、社区等地理位置信息 |
| Mock数据 | 模拟数据，用于测试或API失败时的降级方案 |

---

## 八、报告总结

本次检查发现6项数据调用相关问题，其中**问题3（数据处理逻辑错误）**最为严重，需优先修复。DEA效率计算使用人口数作为产出指标，会导致医疗资源配置效率评估结果失真，直接影响决策准确性。

建议按照优先级矩阵逐步整改：
1. **立即修复**（P0）：DEA产出指标和E2SFCA容量计算逻辑
2. **短期优化**（P1）：配置化列名映射、清理重复实例化
3. **中期改进**（P2）：缓存版本控制、Mock数据标识
4. **长期规划**（P3）：前端数据迁移到后端API

同时，建议建立数据调用规范检查清单，纳入代码审查流程，确保新增代码符合数据质量要求。

---

**报告编制**: AI Assistant  
**审核状态**: 待审核  
**下次复查**: 建议1个月后复查整改进度
