# pages/api_checker_page.py
import streamlit as st
from modules.core.guard import SystemGuard

# 初始化系统守卫
guard = SystemGuard()

def show():
    st.title("🔌 接口接入检查中心")
    st.markdown("### 检查内容：搜索引擎API + DPIO接口")
    st.markdown("---")

    # 1. 搜索引擎API检查
    st.subheader("📡 搜索引擎API检查")
    test_query = st.text_input("输入测试搜索关键词", "2025全球卫生资源配置报告")
    if st.button("🚀 开始检查搜索引擎API", type="primary"):
        with st.spinner("正在检查搜索引擎API接入/访问/数据获取..."):
            # 使用 guard.py 中的 ExternalAPIGuard
            api_result = guard.check_external_apis()
            # 查找搜索引擎相关检查项
            search_items = [item for item in api_result.items if "serpapi" in item.name.lower() or "bing" in item.name.lower()]
            # 展示检查项
            st.write("#### 检查项详情")
            for item in search_items:
                if item.status.value == "ok":
                    st.success(f"✅ {item.name}：{item.message}")
                else:
                    st.error(f"❌ {item.name}：{item.message}")
            # 整体结果
            if api_result.overall_status.value == "ok":
                st.success("✅ 搜索引擎API检查通过")
            else:
                st.error(f"❌ 搜索引擎API检查失败")

    st.markdown("---")

    # 2. DPIO接口检查（仅Linux环境可见）
    st.subheader("⚙️ DPIO接口检查（Linux内核/硬件层）")
    st.caption("提示：需Linux系统+DPIO硬件/驱动+管理员权限")
    if st.button("🚀 开始检查DPIO接口", type="secondary"):
        with st.spinner("正在检查DPIO驱动/硬件/帧收发/数据完整性..."):
            # 使用 guard.py 中的 HardwareGuard
            hw_result = guard.check_hardware()
            # 展示检查项
            st.write("#### 检查项详情")
            for item in hw_result.items:
                if item.status.value == "ok":
                    st.success(f"✅ {item.name}：{item.message}")
                else:
                    st.error(f"❌ {item.name}：{item.message}")
            # 展示硬件信息
            if hw_result.metadata:
                st.write("#### 📋 硬件/驱动信息")
                st.json(hw_result.metadata)
            # 整体结果
            if hw_result.overall_status.value == "ok":
                st.success("✅ DPIO接口检查通过：驱动加载正常、硬件绑定成功、可正常收发数据且数据完整！")
            else:
                st.error(f"❌ DPIO接口检查失败")

if __name__ == "__main__":
    show()