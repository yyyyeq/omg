import streamlit as st
from supabase import create_client

# 1. 初始化 Supabase 連線 (透過 secrets 安全讀取)
@st.cache_resource
def init_connection():
    url = st.secrets["SUPABASE_URL"]
    key = st.secrets["SUPABASE_KEY"]
    return create_client(url, key)

supabase = init_connection()

st.set_page_config(page_title="白卡登記系統", page_icon="📝")
st.title("📝 白卡登記系統")

# 2. 建立輸入表單
with st.form("white_card_form"):
    user_name = st.text_input("使用者姓名")
    card_id = st.text_input("白卡編號")
    submitted = st.form_submit_button("提交登記")

    if submitted:
        if user_name and card_id:
            # 3. 寫入資料到 Supabase 的 white_cards 表格
            data = {
                "name": user_name,
                "card_id": card_id
            }
            try:
                supabase.table("white_cards").insert(data).execute()
                st.success(f"成功！已登記 {user_name} 的卡號 {card_id}")
            except Exception as e:
                st.error(f"寫入失敗: {e}")
        else:
            st.warning("請填寫完整資訊")

# 4. 顯示目前登記的清單
st.divider()
st.subheader("已登記列表")
response = supabase.table("white_cards").select("*").execute()
if response.data:
    st.table(response.data)
