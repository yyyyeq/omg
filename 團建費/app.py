import streamlit as st
import pandas as pd
from datetime import datetime

# ---------------------------------------------------------
# 1. 網頁基本設定
# ---------------------------------------------------------
st.set_page_config(page_title="🍵 團建費登記系統", layout="wide", page_icon="🍵")

# CSS 自訂樣式微調
st.markdown("""
    <style>
    /* 調整大標題樣式 */
    h1 {
        padding-bottom: 0.5rem;
    }
    /* 加強 Expander 標題文字樣式 */
    .st-emotion-cache-ke03o4 {
        font-weight: bold;
    }
    </style>
""", unsafe_allow_html=True)

st.title("🍵 團建費登記系統")

# 初始化 Session State (確保資料在跨操作時保存)
if "expenses_df" not in st.session_state:
    st.session_state.expenses_df = pd.DataFrame(columns=["日期", "類型", "點心/店家", "飲料", "金額"])

# ---------------------------------------------------------
# 2. 邊欄 (Sidebar)：經費參數設定
# ---------------------------------------------------------
st.sidebar.header("⚙️ 月度經費參數設定")

people_count = st.sidebar.number_input("團隊人數", min_value=1, value=40, step=1)
weeks_count = st.sidebar.number_input("本月週數 (下午茶用)", min_value=1, max_value=5, value=4, step=1)
tea_unit_price = st.sidebar.number_input("下午茶單價 ($/人/週)", min_value=0, value=150, step=10)
snack_unit_price = st.sidebar.number_input("零食額度 ($/人/月)", min_value=0, value=120, step=10)
st.sidebar.markdown("---") # 分割線
last_month_balance = st.sidebar.number_input("上月底餘額 ($)", value=0, step=100)

# 計算經費：下午茶按週計算、零食按月計算
tea_budget = people_count * weeks_count * tea_unit_price
snack_budget = people_count * snack_unit_price
total_available = tea_budget + snack_budget + last_month_balance

# ---------------------------------------------------------
# 3. 主畫面：總覽儀表板 (卡片式視覺)
# ---------------------------------------------------------
st.subheader("📋 經費與預算總覽")

df = st.session_state.expenses_df

tea_spent = pd.to_numeric(df[df["類型"] == "下午茶"]["金額"], errors='coerce').sum() if not df.empty else 0
snack_spent = pd.to_numeric(df[df["類型"] == "零食"]["金額"], errors='coerce').sum() if not df.empty else 0
total_spent = tea_spent + snack_spent

tea_remaining = tea_budget - tea_spent
snack_remaining = snack_budget - snack_spent
total_remaining = total_available - total_spent

# 上半部：預算與支出卡片
dash_col1, dash_col2 = st.columns(2)

with dash_col1:
    st.markdown(f"""
        <div style="background-color:#ffeaea; padding: 20px; border-radius: 10px; border: 1px solid #ffcccc; margin-bottom: 20px;">
            <h4 style="margin: 0; color:#c62828;">🍵 下午茶專區 (按週計算)</h4>
            <div style="display: flex; justify-content: space-between; margin-top: 15px;">
                <div>總預算: <b>${tea_budget:,.0f}</b></div>
                <div>已支出: <b>${tea_spent:,.0f}</b></div>
                <div style="color: {'green' if tea_remaining >= 0 else 'red'};">剩餘: <b>${tea_remaining:,.0f}</b></div>
            </div>
        </div>
    """, unsafe_allow_html=True)

with dash_col2:
    st.markdown(f"""
        <div style="background-color:#e1f5fe; padding: 20px; border-radius: 10px; border: 1px solid #b3e5fc; margin-bottom: 20px;">
            <h4 style="margin: 0; color:#0277bd;">🍪 零食專區 (按月計算)</h4>
            <div style="display: flex; justify-content: space-between; margin-top: 15px;">
                <div>總預算: <b>${snack_budget:,.0f}</b></div>
                <div>已支出: <b>${snack_spent:,.0f}</b></div>
                <div style="color: {'green' if snack_remaining >= 0 else 'red'};">剩餘: <b>${snack_remaining:,.0f}</b></div>
            </div>
        </div>
    """, unsafe_allow_html=True)

# 下半部：結餘與總結
dash_col3, dash_col4 = st.columns(2)

with dash_col3:
    st.markdown(f"""
        <div style="background-color:#f5f5f5; padding: 15px; border-radius: 8px; border: 1px solid #e0e0e0;">
            <span style="font-size:1.1rem;">🔙 上月結餘：</span>
            <span style="font-size:1.4rem; font-weight: bold; color: #616161;">${last_month_balance:,.0f}</span>
        </div>
    """, unsafe_allow_html=True)

with dash_col4:
    st.markdown(f"""
        <div style="background-color:{'#e8f5e9' if total_remaining >= 0 else '#ffecb3'}; padding: 15px; border-radius: 8px; border: 1px solid {'#a5d6a7' if total_remaining >= 0 else '#ffe082'};">
            <span style="font-size:1.1rem;">🎯 本月剩餘總額：</span>
            <span style="font-size:1.4rem; font-weight: bold; color: {'#1b5e20' if total_remaining >= 0 else '#c62828'};">${total_remaining:,.0f}</span>
        </div>
    """, unsafe_allow_html=True)

# ---------------------------------------------------------
# 4. 資料備份與還原 (可收折 Expander)
# ---------------------------------------------------------
st.divider()
with st.expander("💾 資料備份與還原 ( CSV 檔案 )"):
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
                if set(["日期", "類型", "點心/店家", "飲料", "金額"]).issubset(imported_df.columns):
                    st.session_state.expenses_df = imported_df
                    st.success("✅ 資料成功還原！")
                    st.rerun()
                else:
                    st.error("⚠️ 檔案欄位不正確，匯入失敗！")
            except Exception as e:
                st.error("⚠️ 檔案格式不符，匯入失敗！")

# ---------------------------------------------------------
# 5. 新增消費紀錄
# ---------------------------------------------------------
st.divider()
st.subheader("➕ 新增消費紀錄")

f_col1, f_col2, f_col3, f_col4, f_col5 = st.columns([2, 2, 3, 3, 2])
with f_col1:
    exp_date = st.date_input("日期", datetime.now())
with f_col2:
    exp_type = st.selectbox("類型", ["下午茶", "零食"])
with f_col3:
    exp_snack = st.text_input("點心 / 店家", placeholder="如：50嵐")
with f_col4:
    exp_drink = st.text_input("飲料 (可選填)", placeholder="如：四季春茶")
with f_col5:
    exp_amount_str = st.text_input("金額 ($)", placeholder="如：120")

# 新增按鈕
if st.button("確認新增紀錄", use_container_width=True, type="primary"):
    clean_amount = exp_amount_str.strip().replace(",", "")
    
    if not exp_snack.strip():
        st.warning("⚠️ 請輸入「點心 / 店家」名稱！")
    elif not clean_amount.isdigit() or int(clean_amount) <= 0:
        st.warning("⚠️ 請在金額欄位輸入「大於 0 的純數字」！")
    else:
        new_data = pd.DataFrame([{
            "日期": str(exp_date),
            "類型": exp_type,
            "點心/店家": exp_snack.strip(),
            "飲料": exp_drink.strip(),
            "金額": int(clean_amount)
        }])
        st.session_state.expenses_df = pd.concat([st.session_state.expenses_df, new_data], ignore_index=True)
        st.success(f"✅ 新增成功！已記錄「{exp_snack.strip()}」下午茶/零食。")
        st.rerun()

# ---------------------------------------------------------
# 6. 本月消費明細列表 (線上編輯模式：可直接雙擊修改、刪除列)
# ---------------------------------------------------------
st.divider()
st.subheader("📋 本月消費明細列表 (雙擊表格儲存格可直接修改金額或內容)")

if not st.session_state.expenses_df.empty:
    edited_df = st.data_editor(
        st.session_state.expenses_df,
        use_container_width=True,
        hide_index=True,
        num_rows="dynamic",  # 允許刪除或新增整列
        column_config={
            "日期": st.column_config.TextColumn("日期", alignment="center"),
            "類型": st.column_config.SelectboxColumn("類型", options=["下午茶", "零食"], alignment="center"),
            "點心/店家": st.column_config.TextColumn("點心 / 店家", alignment="left"),
            "飲料": st.column_config.TextColumn("飲料", alignment="left"),
            "金額": st.column_config.NumberColumn(
                "金額",
                format="$ %d",        # 帶有 $ 符號與千分位
                alignment="center",   # 金額置中顯示
                min_value=0
            ),
        }
    )
    # 同步修改後的資料回 Session State，讓上面的儀表板數字即時連動！
    if not edited_df.equals(st.session_state.expenses_df):
        st.session_state.expenses_df = edited_df
        st.rerun()
else:
    st.info("目前還沒有任何紀錄，可以直接新增或匯入備份檔案！")
