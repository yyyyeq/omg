import streamlit as st
import pandas as pd
from datetime import datetime
from supabase import create_client, Client

# ---------------------------------------------------------
# 1. 網頁基本設定與 Supabase 連線
# ---------------------------------------------------------
st.set_page_config(page_title="團建費登記系統", layout="wide", page_icon="🍵")

st.markdown("""
    <style>
    h1 { padding-bottom: 0.5rem; }
    .st-emotion-cache-ke03o4 { font-weight: bold; }
    </style>
""", unsafe_allow_html=True)

st.title("🍵 團建費登記系統")

# 初始化 Supabase 連線
try:
    supabase_url = st.secrets["SUPABASE_URL"]
    supabase_key = st.secrets["SUPABASE_KEY"]
    supabase: Client = create_client(supabase_url, supabase_key)
except Exception as e:
    st.error("⚠️ 雲端資料庫連線失敗，請檢查 Streamlit Cloud 的 Secrets 設定！")
    st.stop()

# 從 Supabase 讀取最新資料
def get_expenses():
    try:
        response = supabase.schema("public").table("expenses").select("*").execute()
        df = pd.DataFrame(response.data)
        if df.empty:
            return pd.DataFrame(columns=["id", "date", "type", "snack", "drink", "amount"])
        return df
    except Exception as e:
        st.error(f"⚠️ 資料讀取失敗: {e}")
        return pd.DataFrame(columns=["id", "date", "type", "snack", "drink", "amount"])

expenses_df = get_expenses()

# 資料預處理：轉換日期格式與產生月份欄位 (YYYY-MM)
if not expenses_df.empty:
    expenses_df["amount"] = pd.to_numeric(expenses_df["amount"], errors="coerce").fillna(0)
    expenses_df["date_dt"] = pd.to_datetime(expenses_df["date"], errors="coerce")
    expenses_df["month"] = expenses_df["date_dt"].dt.strftime("%Y-%m")
    
    # 取得歷史所有月份，並確保「當前月份」也在清單中
    current_month_str = datetime.now().strftime("%Y-%m")
    month_set = set(expenses_df["month"].dropna().unique())
    month_set.add(current_month_str)
    all_months = sorted(list(month_set))
else:
    expenses_df["month"] = ""
    all_months = [datetime.now().strftime("%Y-%m")]

# ---------------------------------------------------------
# 2. 邊欄 (Sidebar)：月份選擇與經費參數設定
# ---------------------------------------------------------
st.sidebar.header("📅 月份選擇")
# 預設選擇最新月份 (清單最後一個)
selected_month = st.sidebar.selectbox(
    "選擇檢視月份",
    all_months,
    index=len(all_months) - 1
)

st.sidebar.markdown("---")
st.sidebar.header(f"⚙️ {selected_month} 經費參數")

people_count = st.sidebar.number_input("團隊人數", min_value=1, value=40, step=1)
weeks_count = st.sidebar.number_input("本月週數 (下午茶用)", min_value=1, max_value=5, value=4, step=1)
tea_unit_price = st.sidebar.number_input("下午茶單價 ($/人/週)", min_value=0, value=160, step=10)
snack_unit_price = st.sidebar.number_input("零食額度 ($/人/月)", min_value=0, value=120, step=10)

# 計算所選月份的基礎額度
current_tea_budget = people_count * weeks_count * tea_unit_price
current_snack_budget = people_count * snack_unit_price
monthly_standard_budget = current_tea_budget + current_snack_budget

# ---------------------------------------------------------
# 自動計算上月滾動結餘
# ---------------------------------------------------------
# 找出早於目前所選月份的所有歷史月份
earlier_months = [m for m in all_months if m < selected_month]
auto_balance = 0

if earlier_months and not expenses_df.empty:
    for m in earlier_months:
        m_spent = expenses_df[expenses_df["month"] == m]["amount"].sum()
        # 每個歷史月份按標準額度計算結餘 (若歷史月份有不同週數或人數，亦可在此微調)
        auto_balance += (monthly_standard_budget - m_spent)

st.sidebar.markdown("---")
balance_mode = st.sidebar.radio("上月結餘計算方式", ["自動累計帶入", "手動輸入"], index=0)

if balance_mode == "自動累計帶入":
    last_month_balance = st.sidebar.number_input("上月累計結餘 ($)", value=int(auto_balance), step=100)
else:
    last_month_balance = st.sidebar.number_input("上月自訂結餘 ($)", value=0, step=100)

total_available = monthly_standard_budget + last_month_balance

# ---------------------------------------------------------
# 3. 主畫面：總覽儀表板 (篩選當前月份)
# ---------------------------------------------------------
st.subheader(f"📋 【{selected_month}】經費與預算總覽")

# 篩選所選月份的花費明細
current_month_df = expenses_df[expenses_df["month"] == selected_month] if not expenses_df.empty else pd.DataFrame()

tea_spent = current_month_df[current_month_df["type"] == "下午茶"]["amount"].sum() if not current_month_df.empty else 0
snack_spent = current_month_df[current_month_df["type"] == "零食"]["amount"].sum() if not current_month_df.empty else 0
total_spent = tea_spent + snack_spent

tea_remaining = current_tea_budget - tea_spent
snack_remaining = current_snack_budget - snack_spent
total_remaining = total_available - total_spent

dash_col1, dash_col2 = st.columns(2)

with dash_col1:
    st.markdown(f"""
        <div style="background-color:#ffeaea; padding: 20px; border-radius: 10px; border: 1px solid #ffcccc; margin-bottom: 20px;">
            <h4 style="margin: 0; color:#c62828;">🍵 下午茶專區 </h4>
            <div style="display: flex; justify-content: space-between; margin-top: 15px;">
                <div>本月預算: <b>${current_tea_budget:,.0f}</b></div>
                <div>已支出: <b>${tea_spent:,.0f}</b></div>
                <div style="color: {'green' if tea_remaining >= 0 else 'red'};">剩餘: <b>${tea_remaining:,.0f}</b></div>
            </div>
        </div>
    """, unsafe_allow_html=True)

with dash_col2:
    st.markdown(f"""
        <div style="background-color:#e1f5fe; padding: 20px; border-radius: 10px; border: 1px solid #b3e5fc; margin-bottom: 20px;">
            <h4 style="margin: 0; color:#0277bd;">🍪 零食專區 </h4>
            <div style="display: flex; justify-content: space-between; margin-top: 15px;">
                <div>本月預算: <b>${current_snack_budget:,.0f}</b></div>
                <div>已支出: <b>${snack_spent:,.0f}</b></div>
                <div style="color: {'green' if snack_remaining >= 0 else 'red'};">剩餘: <b>${snack_remaining:,.0f}</b></div>
            </div>
        </div>
    """, unsafe_allow_html=True)

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
# 4. 新增消費紀錄
# ---------------------------------------------------------
st.divider()
st.subheader("➕ 新增消費紀錄")

with st.form("add_expense_form", clear_on_submit=True):
    f_col1, f_col2, f_col3, f_col4, f_col5 = st.columns([2, 2, 3, 3, 2])
    with f_col1:
        exp_date = st.date_input("日期", datetime.now())
    with f_col2:
        exp_type = st.selectbox("類型", ["下午茶", "零食"])
    with f_col3:
        exp_snack = st.text_input("點心 / 店家", placeholder="如：哈堤手作三明治")
    with f_col4:
        exp_drink = st.text_input("飲料 (可選填)", placeholder="如：大茗")
    with f_col5:
        exp_amount_str = st.text_input("金額 ($)", placeholder="如：4877")

    submitted = st.form_submit_button("確認新增紀錄 (可直接按 Enter)", use_container_width=True, type="primary")

    if submitted:
        clean_amount = exp_amount_str.strip().replace(",", "")
        if not exp_snack.strip():
            st.warning("⚠️ 請輸入「點心 / 店家」名稱！")
        elif not clean_amount.isdigit() or int(clean_amount) <= 0:
            st.warning("⚠️ 請在金額欄位輸入「大於 0 的純數字」！")
        else:
            new_data = {
                "date": str(exp_date),
                "type": exp_type,
                "snack": exp_snack.strip(),
                "drink": exp_drink.strip(),
                "amount": int(clean_amount)
            }
            supabase.schema("public").table("expenses").insert(new_data).execute()
            st.success("✅ 已成功新增至雲端！")
            st.rerun()

# ---------------------------------------------------------
# 5. 當月消費明細 (僅顯示所選月份)
# ---------------------------------------------------------
st.divider()
st.subheader(f"📋 【{selected_month}】消費明細")

@st.dialog("✏️ 編輯消費紀錄")
def edit_record_dialog(row_id, row_data):
    d_date = datetime.strptime(str(row_data["date"]), "%Y-%m-%d") if str(row_data["date"]) not in ["nan", "None", ""] else datetime.now()
    new_date = st.date_input("日期", d_date)
    new_type = st.selectbox("類型", ["下午茶", "零食"], index=0 if str(row_data["type"]) == "下午茶" else 1)
    new_snack = st.text_input("點心 / 店家", value=str(row_data["snack"]))
    new_drink = st.text_input("飲料", value=str(row_data["drink"]) if str(row_data["drink"]) not in ["nan", "None"] else "")
    new_amount = st.number_input("金額 ($)", value=int(row_data["amount"]), min_value=0, step=10)
    
    if st.button("儲存修改", type="primary", use_container_width=True):
        updated_data = {
            "date": str(new_date),
            "type": new_type,
            "snack": new_snack.strip(),
            "drink": new_drink.strip(),
            "amount": int(new_amount)
        }
        supabase.schema("public").table("expenses").update(updated_data).eq("id", row_id).execute()
        st.success("修改成功！")
        st.rerun()

if not current_month_df.empty:
    # 依日期由新到舊排序
    current_month_df = current_month_df.sort_values(by="date", ascending=False)
    
    for _, row in current_month_df.iterrows():
        amt_val = int(row['amount']) if pd.notnull(row['amount']) else 0
        snack_val = str(row['snack']) if str(row['snack']) not in ['nan', 'None'] else ''
        drink_val = str(row['drink']) if str(row['drink']) not in ['nan', 'None', ''] else ''

        card_col1, card_col2, card_col3, card_col4, card_col5, card_col6, card_col7 = st.columns([2, 1.5, 2.5, 2, 2, 1.5, 1.5])
        
        with card_col1:
            st.write(f"📅 **{row['date']}**")
        with card_col2:
            st.markdown(f"🏷️ `{row['type']}`")
        with card_col3:
            st.write(f"🍵 **{snack_val}**")
        with card_col4:
            st.write(f"🥤 {drink_val}" if drink_val else "—")
        with card_col5:
            st.markdown(f"💰 <span style='font-size:1.1rem; font-weight:bold; color:#1b5e20;'>$ {amt_val:,}</span>", unsafe_allow_html=True)
        with card_col6:
            if st.button("✏️ 編輯", key=f"edit_{row['id']}", use_container_width=True):
                edit_record_dialog(row['id'], row)
        with card_col7:
            if st.button("🗑️ 刪除", key=f"del_{row['id']}", use_container_width=True):
                supabase.schema("public").table("expenses").delete().eq("id", row['id']).execute()
                st.rerun()
        st.markdown("<hr style='margin: 8px 0; border: 0.5px solid #f0f0f0;'>", unsafe_allow_html=True)
else:
    st.info(f"【{selected_month}】目前還沒有任何紀錄，可以直接新增！")
