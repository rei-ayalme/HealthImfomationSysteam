# utils/auth.py
import streamlit as st
import hashlib

def hash_password(password: str):
    """哈希加密密码"""
    return hashlib.sha256(str.encode(password)).hexdigest()

def check_password():
    """Streamlit 基础登录验证逻辑"""
    def password_entered():
        if hash_password(st.session_state["password"]) == st.session_state["hashed_admin_pwd"]:
            st.session_state["password_correct"] = True
            del st.session_state["password"]
        else:
            st.session_state["password_correct"] = False

    # 预设管理员密码哈希（实际开发中应存入 .env 或数据库）
    st.session_state["hashed_admin_pwd"] = hash_password("admin123")

    if st.session_state.get("password_correct", False):
        return True

    st.text_input("管理员密码", type="password", on_change=password_entered, key="password")
    if "password_correct" in st.session_state:
        st.error("😕 密码错误")
    return False