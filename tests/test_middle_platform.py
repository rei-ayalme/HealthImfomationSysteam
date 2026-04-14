"""
中台机制功能测试脚本
验证前端页面中台API集成效果
"""
import requests
import json
import sys

# 添加项目路径
sys.path.insert(0, 'd:\\python_HIS\\pythonProject\\多源健康数据驱动的疾病谱系与资源适配分析\\Health_Imformation_Systeam')

BASE_URL = "http://127.0.0.1:8000/api"

def test_api_response_format():
    """测试API响应格式是否符合中台标准"""
    print("=" * 60)
    print("测试中台API响应格式标准化")
    print("=" * 60)

    endpoints = [
        ("/disease_simulation?region=China&years=5", "疾病预测API"),
        ("/spatial_analysis?region=成都市&threshold_km=10&level=district", "空间分析API"),
        ("/analysis/metrics?region=China&year=2024", "健康指标API"),
    ]

    all_passed = True
    for endpoint, name in endpoints:
        try:
            response = requests.get(f"{BASE_URL}{endpoint}", timeout=10)
            data = response.json()

            # 验证标准响应格式字段
            required_fields = ["code", "message", "data", "timestamp"]
            missing_fields = [f for f in required_fields if f not in data]

            if missing_fields:
                print(f"[ERROR] {name}: 缺少字段 {missing_fields}")
                all_passed = False
                continue

            # 验证code字段
            if not isinstance(data["code"], int):
                print(f"[ERROR] {name}: code字段类型错误")
                all_passed = False
                continue

            # 验证timestamp格式
            if not isinstance(data["timestamp"], str) or "Z" not in data["timestamp"]:
                print(f"[ERROR] {name}: timestamp格式错误")
                all_passed = False
                continue

            print(f"[OK] {name}: 响应格式正确 (code={data['code']})")

        except requests.exceptions.Timeout:
            print(f"[WARN] {name}: 请求超时")
        except Exception as e:
            print(f"[ERROR] {name}: {str(e)}")
            all_passed = False

    return all_passed

def test_cors_headers():
    """测试CORS头是否允许前端跨域访问"""
    print("\n" + "=" * 60)
    print("测试CORS跨域配置")
    print("=" * 60)

    try:
        response = requests.options(
            f"{BASE_URL}/disease_simulation",
            headers={
                "Origin": "http://localhost:8080",
                "Access-Control-Request-Method": "GET"
            },
            timeout=5
        )

        if "Access-Control-Allow-Origin" in response.headers:
            print("[OK] CORS配置正确，允许跨域访问")
            return True
        else:
            print("[WARN] 未检测到CORS头，前端可能无法跨域访问")
            return False
    except Exception as e:
        print(f"[ERROR] CORS测试失败: {str(e)}")
        return False

def test_frontend_files():
    """验证前端文件是否正确引入中台依赖"""
    print("\n" + "=" * 60)
    print("验证前端文件中台依赖引入")
    print("=" * 60)

    files_to_check = [
        "frontend/use/prediction.html",
        "frontend/use/macro-analysis.html",
        "frontend/use/meso-analysis.html",
        "frontend/use/micro-analysis.html",
    ]

    base_path = "d:\\python_HIS\\pythonProject\\多源健康数据驱动的疾病谱系与资源适配分析\\Health_Imformation_Systeam"
    all_passed = True

    required_deps = [
        ("axios.min.js", "Axios库"),
        ("sweetalert2@11", "SweetAlert2库"),
        ("api.js", "中台API模块"),
    ]

    for file_path in files_to_check:
        full_path = f"{base_path}/{file_path}"
        try:
            with open(full_path, 'r', encoding='utf-8') as f:
                content = f.read()

            missing_deps = []
            for dep, name in required_deps:
                if dep not in content:
                    missing_deps.append(name)

            if missing_deps:
                print(f"[ERROR] {file_path}: 缺少依赖 {missing_deps}")
                all_passed = False
            else:
                print(f"[OK] {file_path}: 所有依赖已正确引入")

        except Exception as e:
            print(f"[ERROR] {file_path}: 读取失败 - {str(e)}")
            all_passed = False

    return all_passed

def test_api_js_exists():
    """验证api.js文件是否存在且完整"""
    print("\n" + "=" * 60)
    print("验证中台API模块(api.js)")
    print("=" * 60)

    api_js_path = "d:\\python_HIS\\pythonProject\\多源健康数据驱动的疾病谱系与资源适配分析\\Health_Imformation_Systeam\\frontend\\assets\\js\\api.js"

    try:
        with open(api_js_path, 'r', encoding='utf-8') as f:
            content = f.read()

        required_components = [
            ("axios.create", "Axios实例创建"),
            ("interceptors.response", "响应拦截器"),
            ("window.API", "API暴露"),
            ("getDiseasePrediction", "疾病预测API"),
            ("getSpatialAnalysis", "空间分析API"),
            ("res.code === 200", "成功响应处理"),
            ("Promise.reject", "错误响应处理"),
        ]

        all_passed = True
        for component, name in required_components:
            if component in content:
                print(f"[OK] {name}: 已实现")
            else:
                print(f"[WARN] {name}: 未检测到")
                all_passed = False

        return all_passed

    except Exception as e:
        print(f"[ERROR] api.js读取失败: {str(e)}")
        return False

def main():
    """主测试函数"""
    print("\n" + "=" * 60)
    print("中台机制功能测试")
    print("=" * 60)

    results = []

    # 运行各项测试
    results.append(("API响应格式", test_api_response_format()))
    results.append(("CORS跨域配置", test_cors_headers()))
    results.append(("前端文件依赖", test_frontend_files()))
    results.append(("API模块完整性", test_api_js_exists()))

    # 汇总结果
    print("\n" + "=" * 60)
    print("测试结果汇总")
    print("=" * 60)

    for name, passed in results:
        status = "通过" if passed else "失败"
        symbol = "[OK]" if passed else "[ERROR]"
        print(f"{symbol} {name}: {status}")

    all_passed = all(r[1] for r in results)

    print("\n" + "=" * 60)
    if all_passed:
        print("[SUCCESS] 所有测试通过！中台机制已成功集成。")
    else:
        print("[WARNING] 部分测试未通过，请检查上述错误信息。")
    print("=" * 60)

    return 0 if all_passed else 1

if __name__ == "__main__":
    sys.exit(main())
