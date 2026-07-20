import streamlit as st
import pandas as pd
from datetime import datetime
from supabase import create_client, Client

# ---------------------------------------------------------
# 1. 網頁基本設定與 Supabase 連線
# ---------------------------------------------------------
st.set_page_config(page_title=" 團建費登記系統", layout="wide", page_icon="🍵")

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

# 從 Supabase 讀取最新資料 (明確指定 schema("public"))
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

# ---------------------------------------------------------
# 2. 邊欄 (Sidebar)：經費參數設定
# ---------------------------------------------------------
st.sidebar.header("⚙️ 月度經費參數設定")

people_count = st.sidebar.number_input("團隊人數", min_value=1, value=40, step=1)
weeks_count = st.sidebar.number_input("本月週數 (下午茶用)", min_value=1, max_value=5, value=4, step=1)
tea_unit_price = st.sidebar.number_input("下午茶單價 ($/人/週)", min_value=0, value=150, step=10)
snack_unit_price = st.sidebar.number_input("零食額度 ($/人/月)", min_value=0, value=120, step=10)
st.sidebar.markdown("---")
last_month_balance = st.sidebar.number_input("上月底餘額 ($)", value=0, step=100)

# 計算經費
tea_budget = people_count * weeks_count * tea_unit_price
snack_budget = people_count * snack_unit_price
total_available = tea_budget + snack_budget + last_month_balance

# ---------------------------------------------------------
# 3. 主畫面：總覽儀表板
# ---------------------------------------------------------
st.subheader("📋 經費與預算總覽")

tea_spent = pd.to_numeric(expenses_df[expenses_df["type"] == "下午茶"]["amount"], errors='coerce').sum() if not expenses_df.empty else 0
snack_spent = pd.to_numeric(expenses_df[expenses_df["type"] == "零食"]["amount"], errors='coerce').sum() if not expenses_df.empty else 0
total_spent = tea_spent + snack_spent

tea_remaining = tea_budget - tea_spent
snack_remaining = snack_budget - snack_spent
total_remaining = total_available - total_spent

# 儀表板卡片
dash_col1, dash_col2 = st.columns(2)

with dash_col1:
    st.markdown(f"""
        <div style="background-color:#ffeaea; padding: 20px; border-radius: 10px; border: 1px solid #ffcccc; margin-bottom: 20px;">
            <h4 style="margin: 0; color:#c62828;">🍵 下午茶專區 </h4>
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
            <h4 style="margin: 0; color:#0277bd;">🍪 零食專區 </h4>
            <div style="display: flex; justify-content: space-between; margin-top: 15px;">
                <div>總預算: <b>${snack_budget:,.0f}</b></div>
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
# 4. 新增消費紀錄 (對應英文欄位名稱寫入)
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
            # 寫入 Supabase (指定 public schema)
            supabase.schema("public").table("expenses").insert(new_data).execute()
            st.success(f"✅ 已成功新增至雲端！")
            st.rerun()

# ---------------------------------------------------------
# 5. 本月消費明細 (對應英文欄位名稱編輯與呈現)
# ---------------------------------------------------------
st.divider()
st.subheader("📋 本月消費明細")

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
        # 更新 Supabase (指定 public schema)
        supabase.schema("public").table("expenses").update(updated_data).eq("id", row_id).execute()
        st.success("修改成功！")
        st.rerun()

if not expenses_df.empty:
    for _, row in expenses_df.iterrows():
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
                # 從 Supabase 刪除 (指定 public schema)
                supabase.schema("public").table("expenses").delete().eq("id", row['id']).execute()
                st.rerun()
        st.markdown("<hr style='margin: 8px 0; border: 0.5px solid #f0f0f0;'>", unsafe_allow_html=True)
else:
    st.info("目前還沒有任何紀錄，可以直接新增！")
