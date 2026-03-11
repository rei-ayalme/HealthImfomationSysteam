# pages/api_checker_page.py
import streamlit as st
from modules.search_api_checker import check_search_engine
from modules.dpio_checker import check_dpio_interface

def show():
    st.title("🔌 接口接入检查中心")
    st.markdown("### 检查内容：搜索引擎API + DPIO接口")
    st.markdown("---")

    # 1. 搜索引擎API检查
    st.subheader("📡 搜索引擎API检查")
    test_query = st.text_input("输入测试搜索关键词", "2025全球卫生资源配置报告")
    if st.button("🚀 开始检查搜索引擎API", type="primary"):
        with st.spinner("正在检查搜索引擎API接入/访问/数据获取..."):
            search_result = check_search_engine(test_query)
            # 展示检查项
            st.write("#### 检查项详情")
            for item in search_result.check_items:
                if item["status"]:
                    st.success(f"✅ {item['item']}：{item['msg']}")
                else:
                    st.error(f"❌ {item['item']}：{item['msg']}")
            # 展示结果
            if search_result.status:
                st.markdown("#### 📊 测试获取数据（前3条）")
                for i, res in enumerate(search_result.data["results"], 1):
                    st.write(f"**结果{i}**")
                    st.write(f"标题：{res['title']}")
                    st.write(f"摘要：{res['snippet'][:100]}...")
                    st.write(f"链接：{res['link']}")
                    st.markdown("---")
            else:
                st.error(f"❌ 搜索引擎API检查失败：{search_result.error_msg}")

    st.markdown("---")

    # 2. DPIO接口检查（仅Linux环境可见）
    st.subheader("⚙️ DPIO接口检查（Linux内核/硬件层）")
    st.caption("提示：需Linux系统+DPIO硬件/驱动+管理员权限")
    if st.button("🚀 开始检查DPIO接口", type="secondary"):
        with st.spinner("正在检查DPIO驱动/硬件/帧收发/数据完整性..."):
            dpio_result = check_dpio_interface()
            # 展示检查项
            st.write("#### 检查项详情")
            for item in dpio_result.check_items:
                if item["status"]:
                    st.success(f"✅ {item['item']}：{item['msg']}")
                else:
                    st.error(f"❌ {item['item']}：{item['msg']}")
            # 展示硬件信息
            if dpio_result.hardware_info:
                st.write("#### 📋 硬件/驱动信息")
                st.json(dpio_result.hardware_info)
            # 整体结果
            if dpio_result.status:
                st.success("✅ DPIO接口检查通过：驱动加载正常、硬件绑定成功、可正常收发数据且数据完整！")
            else:
                st.error(f"❌ DPIO接口检查失败：{dpio_result.error_msg}")

if __name__ == "__main__":
    show()