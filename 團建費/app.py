import streamlit as st
import pandas as pd
from datetime import datetime

# 1. 網頁基本設定
st.set_page_config(page_title="團建費登記系統", layout="wide")
st.title("🍵 團建費登記系統")

# 初始化 Session State (讓資料保存在當前階段)
if "expenses_df" not in st.session_state:
    st.session_state.expenses_df = pd.DataFrame(columns=["日期", "類型", "點心/店家", "飲料", "金額"])

# ---------------------------------------------------------
# 2. 邊欄 (Sidebar)：經費參數設定
# ---------------------------------------------------------
st.sidebar.header("⚙️ 月度經費參數設定")

people_count = st.sidebar.number_input("團隊人數", min_value=1, value=10, step=1)
weeks_count = st.sidebar.number_input("本月週數", min_value=1, max_value=5, value=4, step=1)
tea_unit_price = st.sidebar.number_input("下午茶單價（每人每週）", min_value=0, value=150, step=10)
snack_unit_price = st.sidebar.number_input("零食單價（每人每週）", min_value=0, value=50, step=10)
last_month_balance = st.sidebar.number_input("上月底餘額 ($)", value=0, step=100)

# 計算經費
tea_budget = people_count * weeks_count * tea_unit_price
snack_budget = people_count * weeks_count * snack_unit_price
total_available = tea_budget + snack_budget + last_month_balance

# ---------------------------------------------------------
# 3. 主畫面：總覽儀表板
# ---------------------------------------------------------
df = st.session_state.expenses_df

tea_spent = pd.to_numeric(df[df["類型"] == "下午茶"]["金額"], errors='coerce').sum() if not df.empty else 0
snack_spent = pd.to_numeric(df[df["類型"] == "零食"]["金額"], errors='coerce').sum() if not df.empty else 0
total_spent = tea_spent + snack_spent

tea_remaining = tea_budget - tea_spent
snack_remaining = snack_budget - snack_spent
total_remaining = total_available - total_spent

st.subheader("📊 經費與預算總覽")
col1, col2, col3, col4 = st.columns(4)
col1.metric("下午茶總預算", f"${tea_budget:,.0f}", delta=f"剩 ${tea_remaining:,.0f}")
col2.metric("零食總預算", f"${snack_budget:,.0f}", delta=f"剩 ${snack_remaining:,.0f}")
col3.metric("上月結餘", f"${last_month_balance:,.0f}")
col4.metric("本月可用總額", f"${total_available:,.0f}", delta=f"總剩餘 ${total_remaining:,.0f}")

st.divider()

# ---------------------------------------------------------
# 4. 資料備份與恢復（匯入/匯出區塊）
# ---------------------------------------------------------
st.subheader("💾 資料備份與還原")
b_col1, b_col2 = st.columns(2)

with b_col1:
    # 下載 CSV 按鈕
    csv_bytes = st.session_state.expenses_df.to_csv(index=False, encoding="utf-8-sig").encode("utf-8-sig")
    st.download_button(
        label="📥 儲存並下載最新紀錄 (CSV)",
        data=csv_bytes,
        file_name=f"團建費明細備份_{datetime.now().strftime('%Y%m%d')}.csv",
        mime="text/csv",
        use_container_width=True
    )

with b_col2:
    # 匯入 CSV
    uploaded_file = st.file_uploader("📂 匯入舊的備份檔案 (CSV)", type=["csv"], label_visibility="collapsed")
    if uploaded_file is not None:
        try:
            imported_df = pd.read_csv(uploaded_file)
            st.session_state.expenses_df = imported_df
            st.success("✅ 資料成功還原！")
            st.rerun()
        except Exception as e:
            st.error("⚠️ 檔案格式不符，匯入失敗！")

st.divider()

# ---------------------------------------------------------
# 5. 新增消費紀錄
# ---------------------------------------------------------
st.subheader("➕ 新增消費紀錄")
with st.form("expense_form", clear_on_submit=True):
    f_col1, f_col2, f_col3, f_col4, f_col5 = st.columns([2, 2, 3, 3, 2])
    with f_col1:
        exp_date = st.date_input("日期", datetime.now())
    with f_col2:
        exp_type = st.selectbox("類型", ["下午茶", "零食"])
    with f_col3:
        exp_snack = st.text_input("點心 / 店家", placeholder="如：50嵐")
    with f_col4:
        exp_drink = st.text_input("飲料", placeholder="如：四季春茶")
    with f_col5:
        exp_amount = st.number_input("金額 ($)", min_value=0, value=0, step=10)
        
    submitted = st.form_submit_button("新增紀錄", use_container_width=True)
    if submitted:
        if exp_amount > 0 and exp_snack.strip() != "":
            new_data = pd.DataFrame([{
                "日期": str(exp_date),
                "類型": exp_type,
                "點心/店家": exp_snack,
                "飲料": exp_drink,
                "金額": int(exp_amount)
            }])
            st.session_state.expenses_df = pd.concat([st.session_state.expenses_df, new_data], ignore_index=True)
            st.success("✅ 新增成功！請記得點擊上方「儲存並下載」按鈕備份喔！")
            st.rerun()
        else:
            st.warning("⚠️ 請輸入點心/店家名稱與大於 0 的金額！")

# ---------------------------------------------------------
# 6. 消費明細列表
# ---------------------------------------------------------
st.subheader("📋 本月消費明細列表")
if not st.session_state.expenses_df.empty:
    st.dataframe(st.session_state.expenses_df, use_container_width=True)
else:
    st.info("目前還沒有任何紀錄，可以直接新增或匯入備份檔案！")
