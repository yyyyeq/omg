import streamlit as st
import pandas as pd
from datetime import datetime
import os

# 1. 網頁基本設定
st.set_page_config(page_title="團建費登記系統", layout="wide")
st.title("🍵 團建費登記系統")

CSV_FILE = "team_expenses.csv"

# 初始化 CSV 檔案（如果不存在就建立）
if not os.path.exists(CSV_FILE):
    df_init = pd.DataFrame(columns=["日期", "類型", "點心/店家", "飲料/備註", "金額"])
    df_init.to_csv(CSV_FILE, index=False, encoding="utf-8-sig")

# 載入歷史消費資料
def load_data():
    return pd.read_csv(CSV_FILE)

# 儲存新消費資料
def save_expense(date, exp_type, snack, drink, amount):
    df = load_data()
    new_row = pd.DataFrame([{
        "日期": str(date),
        "類型": exp_type,
        "點心/店家": snack,
        "飲料/備註": drink,
        "金額": float(amount)
    }])
    df = pd.concat([df, new_row], ignore_index=True)
    df.to_csv(CSV_FILE, index=False, encoding="utf-8-sig")

# ---------------------------------------------------------
# 2. 邊欄 (Sidebar)：經費參數設定
# ---------------------------------------------------------
st.sidebar.header("⚙️ 月度經費參數設定")

people_count = st.sidebar.number_input("團隊人數", min_value=1, value=10, step=1)
weeks_count = st.sidebar.number_input("本月週數", min_value=1, max_value=5, value=4, step=1)
tea_unit_price = st.sidebar.number_input("下午茶單價（每人每週）", min_value=0, value=150, step=10)
snack_unit_price = st.sidebar.number_input("零食單價（每人每週）", min_value=0, value=50, step=10)
last_month_balance = st.sidebar.number_input("上月底餘額 ($)", value=0, step=100)

# 計算各項經費
tea_budget = people_count * weeks_count * tea_unit_price
snack_budget = people_count * weeks_count * snack_unit_price
total_available = tea_budget + snack_budget + last_month_balance

# ---------------------------------------------------------
# 3. 主畫面：總覽儀表板
# ---------------------------------------------------------
expenses_df = load_data()

# 累計花費
tea_spent = expenses_df[expenses_df["類型"] == "下午茶"]["金額"].sum() if not expenses_df.empty else 0
snack_spent = expenses_df[expenses_df["類型"] == "零食"]["金額"].sum() if not expenses_df.empty else 0
total_spent = tea_spent + snack_spent

# 剩餘預算
tea_remaining = tea_budget - tea_spent
snack_remaining = snack_budget - snack_spent
total_remaining = total_available - total_spent

st.subheader("📊 經費與預算總覽")
col1, col2, col3, col4 = st.columns(4)
col1.metric("下午茶總預算", f"${tea_budget:,}", delta=f"剩 ${tea_remaining:,}", delta_color="normal" if tea_remaining >= 0 else "inverse")
col2.metric("零食總預算", f"${snack_budget:,}", delta=f"剩 ${snack_remaining:,}", delta_color="normal" if snack_remaining >= 0 else "inverse")
col3.metric("上月結餘", f"${last_month_balance:,}")
col4.metric("本月可用總額", f"${total_available:,}", delta=f"總剩餘 ${total_remaining:,}", delta_color="normal" if total_remaining >= 0 else "inverse")

st.divider()

# ---------------------------------------------------------
# 4. 輸入新紀錄區塊
# ---------------------------------------------------------
st.subheader("➕ 新增消費紀錄")
with st.form("expense_form", clear_on_submit=True):
    f_col1, f_col2, f_col3, f_col4, f_col5 = st.columns([2, 2, 3, 3, 2])
    
    with f_col1:
        exp_date = st.date_input("日期", datetime.now())
    with f_col2:
        exp_type = st.selectbox("類型", ["下午茶", "零食"])
    with f_col3:
        exp_snack = st.text_input("點心 / 店家", placeholder="如：50嵐、得正")
    with f_col4:
        exp_drink = st.text_input("飲料 / 細項備註", placeholder="如：微糖微冰")
    with f_col5:
        exp_amount = st.number_input("金額 ($)", min_value=0.0, step=10.0)
        
    submitted = st.form_submit_button("新增紀錄", use_container_width=True)
    if submitted:
        if exp_amount > 0 and exp_snack:
            save_expense(exp_date, exp_type, exp_snack, exp_drink, exp_amount)
            st.success("✅ 已成功新增消費紀錄！")
            st.rerun()
        else:
            st.warning("⚠️ 請輸入店家/點心名稱與正確金額！")

# ---------------------------------------------------------
# 5. 消費明細與下載
# ---------------------------------------------------------
st.divider()
st.subheader("📋 本月消費明細列表")

if not expenses_df.empty:
    # 依日期降冪排序
    sorted_df = expenses_df.sort_values(by="日期", ascending=False)
    st.dataframe(sorted_df, use_container_width=True)
    
    # 匯出 CSV 按鈕
    csv_data = sorted_df.to_csv(index=False, encoding="utf-8-sig").encode("utf-8-sig")
    st.download_button(
        label="📥 下載 Excel (CSV) 明細",
        data=csv_data,
        file_name=f"團建經費明細_{datetime.now().strftime('%Y%m')}.csv",
        mime="text/csv",
    )
else:
    st.info("目前還沒有任何消費紀錄喔！")