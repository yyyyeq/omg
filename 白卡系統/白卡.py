import streamlit as st
from supabase import create_client

# 1. 初始化 Supabase
@st.cache_resource
def init_connection():
    # 這裡的 key 對應到你在 Streamlit Cloud 設定的 Secrets
    url = st.secrets["SUPABASE_URL"]
    key = st.secrets["SUPABASE_KEY"]
    return create_client(url, key)

supabase = init_connection()

st.title("📝 白卡登記系統")

# 2. 表單輸入
with st.form("white_card_form"):
    user_name = st.text_input("姓名")
    card_id = st.text_input("卡號")
    submit = st.form_submit_button("提交")

    if submit:
        # 直接寫入 Supabase
        supabase.table("white_cards").insert({"name": user_name, "card_id": card_id}).execute()
        st.success("資料已更新！")

# 3. 顯示表格 (從 Supabase 讀取)
st.subheader("目前登記狀況")
data = supabase.table("white_cards").select("*").execute()
st.table(data.data)
