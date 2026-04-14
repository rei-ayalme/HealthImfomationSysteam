"""
数据质量检查模块
执行数据完整性、准确性、一致性检查
"""
import pandas as pd
import numpy as np
import os
import json
from datetime import datetime
from typing import Dict, List, Tuple, Any, Optional
from pathlib import Path
from utils.logger import logger


class DataQualityChecker:
    """数据质量检查器"""
    
    def __init__(self, base_dir: str):
        self.base_dir = Path(base_dir)
        self.data_dir = self.base_dir / "data"
        self.raw_dir = self.data_dir / "raw"
        self.processed_dir = self.data_dir / "processed"
        self.results = {
            "check_time": datetime.now().isoformat(),
            "completeness": {},
            "accuracy": {},
            "consistency": {},
            "issues": [],
            "recommendations": []
        }
    
    def check_all(self) -> Dict:
        """执行全部数据质量检查"""
        self._check_data_completeness()
        self._check_data_accuracy()
        self._check_data_consistency()
        self._generate_recommendations()
        return self.results
    
    def _check_data_completeness(self):
        """检查数据完整性"""
        completeness_results = {}
        
        raw_files = list(self.raw_dir.glob("*.csv")) if self.raw_dir.exists() else []
        raw_files.extend(list(self.raw_dir.glob("*.xlsx")) if self.raw_dir.exists() else [])
        
        processed_files = list(self.processed_dir.glob("*.csv")) if self.processed_dir.exists() else []
        processed_files.extend(list(self.processed_dir.glob("*.json")) if self.processed_dir.exists() else [])
        
        expected_files = [
            "GBD.csv", "NBS.csv", "WDI.csv", "WB_HNP.csv",
            "cleaned_health_data.xlsx", "cleaned_gbd_disease.csv",
            "cleaned_gbd_risk.csv"
        ]
        
        existing_files = [f.name for f in raw_files + processed_files]
        
        for expected in expected_files:
            found = any(expected in existing for existing in existing_files)
            completeness_results[expected] = {
                "exists": found,
                "status": "pass" if found else "missing"
            }
            if not found:
                self.results["issues"].append({
                    "type": "completeness",
                    "severity": "high" if expected in ["NBS.csv", "GBD.csv"] else "medium",
                    "file": expected,
                    "message": f"缺失预期数据文件: {expected}"
                })
        
        for f in raw_files:
            try:
                if f.suffix == ".csv":
                    df = pd.read_csv(f, nrows=5)
                    row_count = sum(1 for _ in open(f, encoding='utf-8', errors='ignore')) - 1
                elif f.suffix == ".xlsx":
                    df = pd.read_excel(f, nrows=5)
                    row_count = len(pd.read_excel(f))
                else:
                    continue
                
                file_size_mb = f.stat().st_size / (1024 * 1024)
                
                completeness_results[f.name] = {
                    "exists": True,
                    "status": "pass",
                    "rows": row_count,
                    "columns": len(df.columns) if not df.empty else 0,
                    "size_mb": round(file_size_mb, 2),
                    "columns_list": list(df.columns) if not df.empty else []
                }
            except Exception as e:
                completeness_results[f.name] = {
                    "exists": True,
                    "status": "error",
                    "error": str(e)[:200]
                }
                self.results["issues"].append({
                    "type": "completeness",
                    "severity": "medium",
                    "file": f.name,
                    "message": f"文件读取错误: {str(e)[:100]}"
                })
        
        self.results["completeness"] = completeness_results
    
    def _check_data_accuracy(self):
        """检查数据准确性"""
        accuracy_results = {}
        
        nbs_path = self.raw_dir / "NBS.csv"
        if nbs_path.exists():
            try:
                df = pd.read_csv(nbs_path)
                
                regions = df.iloc[:, 0].tolist() if len(df.columns) > 0 else []
                expected_provinces = 31
                actual_provinces = len([r for r in regions if r and str(r).strip()])
                
                accuracy_results["NBS.csv"] = {
                    "province_count": actual_provinces,
                    "expected_provinces": expected_provinces,
                    "coverage_rate": round(actual_provinces / expected_provinces * 100, 1) if expected_provinces > 0 else 0,
                    "status": "pass" if actual_provinces >= expected_provinces else "warning"
                }
                
                year_columns = [col for col in df.columns if str(col).replace('年', '').isdigit()]
                years = [int(str(col).replace('年', '')) for col in year_columns if str(col).replace('年', '').isdigit()]
                
                if years:
                    accuracy_results["NBS.csv"]["year_range"] = f"{min(years)}-{max(years)}"
                    accuracy_results["NBS.csv"]["year_span"] = max(years) - min(years) + 1
                
                for col in year_columns[:3]:
                    values = pd.to_numeric(df[col], errors='coerce')
                    if not values.empty:
                        negative_count = (values < 0).sum()
                        null_count = values.isna().sum()
                        
                        if negative_count > 0:
                            self.results["issues"].append({
                                "type": "accuracy",
                                "severity": "medium",
                                "file": "NBS.csv",
                                "message": f"列 {col} 存在 {negative_count} 个负值"
                            })
                
            except Exception as e:
                accuracy_results["NBS.csv"] = {"status": "error", "error": str(e)[:200]}
        
        gbd_path = self.raw_dir / "GBD.csv"
        if gbd_path.exists():
            try:
                df = pd.read_csv(gbd_path, nrows=1000)
                
                required_cols = ["地理位置", "年份", "死亡或受伤原因", "测量", "数值"]
                missing_cols = [col for col in required_cols if col not in df.columns]
                
                accuracy_results["GBD.csv"] = {
                    "required_columns_present": len(required_cols) - len(missing_cols),
                    "missing_columns": missing_cols,
                    "status": "pass" if not missing_cols else "warning"
                }
                
                if "数值" in df.columns:
                    values = pd.to_numeric(df["数值"], errors='coerce')
                    negative_count = (values < 0).sum()
                    null_count = values.isna().sum()
                    
                    accuracy_results["GBD.csv"]["value_stats"] = {
                        "negative_count": int(negative_count),
                        "null_count": int(null_count),
                        "total_rows": len(df)
                    }
                
            except Exception as e:
                accuracy_results["GBD.csv"] = {"status": "error", "error": str(e)[:200]}
        
        cleaned_disease_path = self.processed_dir / "cleaned_gbd_disease.csv"
        if cleaned_disease_path.exists():
            try:
                df = pd.read_csv(cleaned_disease_path, nrows=100)
                
                expected_cols = ["location_name", "year", "cause_name", "val", "disease_category"]
                present_cols = [col for col in expected_cols if col in df.columns]
                
                accuracy_results["cleaned_gbd_disease.csv"] = {
                    "expected_columns": expected_cols,
                    "present_columns": present_cols,
                    "coverage": f"{len(present_cols)}/{len(expected_cols)}",
                    "status": "pass" if len(present_cols) >= len(expected_cols) - 1 else "warning"
                }
                
            except Exception as e:
                accuracy_results["cleaned_gbd_disease.csv"] = {"status": "error", "error": str(e)[:200]}
        
        self.results["accuracy"] = accuracy_results
    
    def _check_data_consistency(self):
        """检查数据一致性"""
        consistency_results = {}
        
        nbs_path = self.raw_dir / "NBS.csv"
        gbd_path = self.raw_dir / "GBD.csv"
        
        if nbs_path.exists() and gbd_path.exists():
            try:
                nbs_df = pd.read_csv(nbs_path)
                gbd_df = pd.read_csv(gbd_path, nrows=100)
                
                nbs_regions = set(nbs_df.iloc[:, 0].dropna().astype(str).str.strip()) if len(nbs_df.columns) > 0 else set()
                
                gbd_location_col = None
                for col in ["地理位置", "location_name", "Location"]:
                    if col in gbd_df.columns:
                        gbd_location_col = col
                        break
                
                if gbd_location_col:
                    gbd_regions = set(gbd_df[gbd_location_col].dropna().astype(str).str.strip())
                    
                    china_related = {"China", "中国", "China, mainland"}
                    has_china_data = bool(gbd_regions & china_related)
                    
                    consistency_results["region_overlap"] = {
                        "nbs_province_count": len(nbs_regions),
                        "has_china_in_gbd": has_china_data,
                        "status": "pass" if has_china_data else "warning"
                    }
                
            except Exception as e:
                consistency_results["region_overlap"] = {"status": "error", "error": str(e)[:200]}
        
        db_path = self.base_dir / "db" / "health_system.db"
        consistency_results["database"] = {
            "exists": db_path.exists(),
            "size_mb": round(db_path.stat().st_size / (1024 * 1024), 2) if db_path.exists() else 0,
            "status": "pass" if db_path.exists() else "warning"
        }
        
        geojson_dir = self.data_dir / "geojson"
        expected_geojson = ["ne_10m_admin_0_countries.geojson", "中华人民共和国.geojson"]
        geojson_status = {}
        
        if geojson_dir.exists():
            for geo_file in expected_geojson:
                geo_path = geojson_dir / geo_file
                geojson_status[geo_file] = {
                    "exists": geo_path.exists(),
                    "size_kb": round(geo_path.stat().st_size / 1024, 2) if geo_path.exists() else 0
                }
        else:
            for geo_file in expected_geojson:
                geojson_status[geo_file] = {"exists": False}
        
        consistency_results["geojson_files"] = geojson_status
        
        self.results["consistency"] = consistency_results
    
    def _generate_recommendations(self):
        """生成数据质量改进建议"""
        recommendations = []
        
        for issue in self.results["issues"]:
            if issue["type"] == "completeness" and issue["severity"] == "high":
                recommendations.append({
                    "priority": "high",
                    "action": f"补充缺失的核心数据文件: {issue['file']}",
                    "reason": "核心数据缺失将影响分析模块的正常运行"
                })
            elif issue["type"] == "accuracy":
                recommendations.append({
                    "priority": "medium",
                    "action": f"修复数据准确性问题: {issue['message']}",
                    "reason": "数据准确性问题可能导致分析结果偏差"
                })
        
        if not any(r["action"].startswith("补充缺失") for r in recommendations):
            recommendations.append({
                "priority": "low",
                "action": "定期更新数据源，确保数据的时效性",
                "reason": "数据时效性对健康分析至关重要"
            })
        
        recommendations.append({
            "priority": "medium",
            "action": "建立数据质量监控机制，定期执行质量检查",
            "reason": "持续监控可及时发现和解决数据问题"
        })
        
        self.results["recommendations"] = recommendations
    
    def generate_report(self, output_path: Optional[str] = None) -> str:
        """生成数据质量评估报告"""
        if not self.results.get("completeness"):
            self.check_all()
        
        report_lines = [
            "# 数据质量评估报告",
            f"\n**生成时间**: {self.results['check_time']}\n",
            "---\n",
            "## 一、数据完整性检查\n",
        ]
        
        completeness = self.results.get("completeness", {})
        for file_name, info in completeness.items():
            status_icon = "✅" if info.get("status") == "pass" else "❌" if info.get("status") == "missing" else "⚠️"
            report_lines.append(f"- {status_icon} **{file_name}**")
            if info.get("rows"):
                report_lines.append(f"  - 行数: {info['rows']:,}")
            if info.get("columns"):
                report_lines.append(f"  - 列数: {info['columns']}")
            if info.get("size_mb"):
                report_lines.append(f"  - 大小: {info['size_mb']} MB")
        
        report_lines.extend([
            "\n---\n",
            "## 二、数据准确性检查\n",
        ])
        
        accuracy = self.results.get("accuracy", {})
        for file_name, info in accuracy.items():
            status_icon = "✅" if info.get("status") == "pass" else "⚠️"
            report_lines.append(f"- {status_icon} **{file_name}**")
            if info.get("province_count"):
                report_lines.append(f"  - 省份数量: {info['province_count']}/31 (覆盖率: {info['coverage_rate']}%)")
            if info.get("year_range"):
                report_lines.append(f"  - 年份范围: {info['year_range']}")
            if info.get("coverage"):
                report_lines.append(f"  - 关键列覆盖: {info['coverage']}")
        
        report_lines.extend([
            "\n---\n",
            "## 三、数据一致性检查\n",
        ])
        
        consistency = self.results.get("consistency", {})
        if "region_overlap" in consistency:
            info = consistency["region_overlap"]
            status_icon = "✅" if info.get("status") == "pass" else "⚠️"
            report_lines.append(f"- {status_icon} **区域数据一致性**")
            report_lines.append(f"  - NBS省份数量: {info.get('nbs_province_count', 'N/A')}")
            report_lines.append(f"  - GBD包含中国数据: {'是' if info.get('has_china_in_gbd') else '否'}")
        
        if "database" in consistency:
            info = consistency["database"]
            status_icon = "✅" if info.get("status") == "pass" else "⚠️"
            report_lines.append(f"- {status_icon} **数据库状态**")
            report_lines.append(f"  - 存在: {'是' if info.get('exists') else '否'}")
            if info.get("size_mb"):
                report_lines.append(f"  - 大小: {info['size_mb']} MB")
        
        report_lines.extend([
            "\n---\n",
            "## 四、发现的问题\n",
        ])
        
        issues = self.results.get("issues", [])
        if issues:
            for issue in issues:
                severity_icon = "🔴" if issue["severity"] == "high" else "🟡"
                report_lines.append(f"- {severity_icon} **[{issue['type']}]** {issue['message']}")
        else:
            report_lines.append("- ✅ 未发现严重数据质量问题")
        
        report_lines.extend([
            "\n---\n",
            "## 五、改进建议\n",
        ])
        
        recommendations = self.results.get("recommendations", [])
        for rec in recommendations:
            priority_icon = "🔴" if rec["priority"] == "high" else "🟡" if rec["priority"] == "medium" else "🟢"
            report_lines.append(f"- {priority_icon} **{rec['action']}**")
            report_lines.append(f"  - 原因: {rec['reason']}")
        
        report_lines.extend([
            "\n---\n",
            "## 六、数据来源说明\n",
            "| 数据源 | 类型 | 说明 |",
            "|--------|------|------|",
            "| WHO | 国际 | 世界卫生组织官方数据 |",
            "| IHME/GBD | 国际 | 全球疾病负担研究数据 |",
            "| World Bank (WDI/WB_HNP) | 国际 | 世界银行发展指标 |",
            "| NBS (国家统计局) | 国内 | 中国卫生健康统计年鉴 |",
            "| OWID | 国际 | Our World in Data |",
            "",
            "---\n",
            "*报告由系统自动生成*"
        ])
        
        report_content = "\n".join(report_lines)
        
        if output_path:
            with open(output_path, "w", encoding="utf-8") as f:
                f.write(report_content)
        
        return report_content


class APIInterfaceValidator:
    """API接口对接验证器"""
    
    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url
        self.results = {
            "check_time": datetime.now().isoformat(),
            "endpoints": {},
            "issues": [],
            "status": "pending"
        }
    
    def validate_endpoint_structure(self, endpoint: str, expected_fields: List[str], 
                                     actual_response: Dict) -> Dict:
        """验证API端点响应结构"""
        missing_fields = []
        for field in expected_fields:
            if field not in actual_response:
                missing_fields.append(field)
        
        return {
            "endpoint": endpoint,
            "expected_fields": expected_fields,
            "missing_fields": missing_fields,
            "status": "pass" if not missing_fields else "warning"
        }
    
    def check_frontend_backend_mapping(self) -> Dict:
        """检查前后端API映射"""
        mapping_results = {}
        
        api_mappings = {
            "/api/dataset": {
                "frontend_files": ["index.html"],
                "expected_fields": ["items"],
                "description": "首页数据集列表"
            },
            "/api/chart/trend": {
                "frontend_files": ["index.html", "macro-analysis.html"],
                "expected_fields": ["xAxis", "series"],
                "description": "趋势图表数据"
            },
            "/api/geojson/world": {
                "frontend_files": ["index.html", "macro-analysis.html"],
                "expected_fields": ["type", "features"],
                "description": "世界地图GeoJSON"
            },
            "/api/geojson/china": {
                "frontend_files": ["meso-analysis.html"],
                "expected_fields": ["type", "features"],
                "description": "中国地图GeoJSON"
            },
            "/api/geojson/chengdu": {
                "frontend_files": ["micro-analysis.html"],
                "expected_fields": ["type", "features"],
                "description": "成都地图GeoJSON"
            },
            "/api/spatial_analysis": {
                "frontend_files": ["micro-analysis.html"],
                "expected_fields": ["status", "chart_data"],
                "description": "空间可及性分析"
            },
            "/api/map/world-metrics": {
                "frontend_files": ["index.html"],
                "expected_fields": ["status", "data"],
                "description": "全球健康指标地图"
            },
            "/api/analysis/metrics": {
                "frontend_files": ["macro-analysis.html", "meso-analysis.html"],
                "expected_fields": ["status", "data"],
                "description": "分析指标数据"
            }
        }
        
        for endpoint, config in api_mappings.items():
            mapping_results[endpoint] = {
                "description": config["description"],
                "frontend_usage": config["frontend_files"],
                "expected_response_fields": config["expected_fields"],
                "status": "defined"
            }
        
        self.results["endpoints"] = mapping_results
        return mapping_results
    
    def generate_validation_report(self, output_path: Optional[str] = None) -> str:
        """生成接口验证报告"""
        if not self.results.get("endpoints"):
            self.check_frontend_backend_mapping()
        
        report_lines = [
            "# API接口对接验证报告",
            f"\n**生成时间**: {self.results['check_time']}\n",
            "---\n",
            "## 一、API端点清单\n",
            "| 端点 | 描述 | 前端使用页面 | 预期响应字段 |",
            "|------|------|--------------|--------------|",
        ]
        
        for endpoint, info in self.results.get("endpoints", {}).items():
            frontend = ", ".join(info.get("frontend_usage", []))
            fields = ", ".join(info.get("expected_response_fields", []))
            report_lines.append(f"| `{endpoint}` | {info.get('description', '')} | {frontend} | {fields} |")
        
        report_lines.extend([
            "\n---\n",
            "## 二、接口验证状态\n",
        ])
        
        for endpoint, info in self.results.get("endpoints", {}).items():
            status_icon = "✅" if info.get("status") == "pass" else "⚠️" if info.get("status") == "warning" else "📝"
            report_lines.append(f"- {status_icon} **{endpoint}**")
            report_lines.append(f"  - 状态: {info.get('status', 'defined')}")
        
        report_lines.extend([
            "\n---\n",
            "## 三、数据流验证\n",
            "```mermaid",
            "graph LR",
            "    A[前端页面] --> B[API请求]",
            "    B --> C[后端FastAPI]",
            "    C --> D[数据库SQLite]",
            "    D --> C",
            "    C --> B",
            "    B --> A",
            "```",
            "",
            "---\n",
            "*报告由系统自动生成*"
        ])
        
        report_content = "\n".join(report_lines)
        
        if output_path:
            with open(output_path, "w", encoding="utf-8") as f:
                f.write(report_content)
        
        return report_content


if __name__ == "__main__":
    import sys
    base_dir = Path(__file__).parent.parent.parent
    
    checker = DataQualityChecker(str(base_dir))
    report = checker.generate_report(str(base_dir / "reports" / "data_quality_report.md"))
    print(report)
    
    validator = APIInterfaceValidator()
    api_report = validator.generate_validation_report(str(base_dir / "reports" / "api_validation_report.md"))
    print(api_report)
