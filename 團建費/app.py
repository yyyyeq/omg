import time
from datetime import datetime

import pandas as pd
import streamlit as st
from supabase import Client, create_client


# =========================================================
# 1. 網頁基本設定
# =========================================================
st.set_page_config(
    page_title="團建費登記系統",
    layout="wide",
    page_icon="🍵",
)

st.markdown(
    """
    <style>
    h1 {
        padding-bottom: 0.5rem;
    }

    .expense-card {
        padding: 12px;
        margin-bottom: 8px;
        border: 1px solid #eeeeee;
        border-radius: 8px;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

st.title("🍵 團建費登記系統")


# =========================================================
# 2. 連接 Supabase
# =========================================================
@st.cache_resource
def init_supabase() -> Client:
    """建立並快取 Supabase 連線。"""
    try:
        supabase_url = st.secrets["supabase"]["url"]
        supabase_key = st.secrets["supabase"]["key"]

        return create_client(supabase_url, supabase_key)

    except KeyError as exc:
        st.error(
            "找不到 Supabase 連線資料，"
            "請確認 Streamlit Secrets 是否已設定。"
        )
        st.stop()
        raise exc


supabase = init_supabase()


# =========================================================
# 3. Supabase 資料讀寫函式
# =========================================================
EXPENSE_COLUMNS = [
    "id",
    "日期",
    "類型",
    "點心/店家",
    "飲料",
    "金額",
    "建立時間",
]


def load_expenses() -> pd.DataFrame:
    """從 Supabase 讀取所有消費紀錄。"""
    response = (
        supabase.table("expenses")
        .select("*")
        .order("expense_date", desc=True)
        .order("created_at", desc=True)
        .execute()
    )

    records = response.data or []

    if not records:
        return pd.DataFrame(columns=EXPENSE_COLUMNS)

    df = pd.DataFrame(records)

    df = df.rename(
        columns={
            "expense_date": "日期",
            "expense_type": "類型",
            "snack": "點心/店家",
            "drink": "飲料",
            "amount": "金額",
            "created_at": "建立時間",
        }
    )

    for column in EXPENSE_COLUMNS:
        if column not in df.columns:
            df[column] = ""

    df["金額"] = pd.to_numeric(
        df["金額"],
        errors="coerce",
    ).fillna(0)

    df["飲料"] = df["飲料"].fillna("")

    return df[EXPENSE_COLUMNS]


def add_expense(
    expense_date,
    expense_type: str,
    snack: str,
    drink: str,
    amount: int,
) -> None:
    """新增一筆消費紀錄。"""
    (
        supabase.table("expenses")
        .insert(
            {
                "expense_date": str(expense_date),
                "expense_type": expense_type,
                "snack": snack,
                "drink": drink,
                "amount": int(amount),
            }
        )
        .execute()
    )


def update_expense(
    record_id: int,
    expense_date,
    expense_type: str,
    snack: str,
    drink: str,
    amount: int,
) -> None:
    """修改指定消費紀錄。"""
    (
        supabase.table("expenses")
        .update(
            {
                "expense_date": str(expense_date),
                "expense_type": expense_type,
                "snack": snack,
                "drink": drink,
                "amount": int(amount),
            }
        )
        .eq("id", int(record_id))
        .execute()
    )


def delete_expense(record_id: int) -> None:
    """刪除指定消費紀錄。"""
    (
        supabase.table("expenses")
        .delete()
        .eq("id", int(record_id))
        .execute()
    )


def load_settings() -> dict:
    """從 Supabase 讀取預算設定。"""
    default_settings = {
        "people_count": 40,
        "weeks_count": 4,
        "tea_unit_price": 150,
        "snack_unit_price": 120,
        "last_month_balance": 0,
    }

    response = (
        supabase.table("app_settings")
        .select("setting_key,setting_value")
        .execute()
    )

    records = response.data or []

    for record in records:
        key = record.get("setting_key")
        value = record.get("setting_value")

        if key in default_settings:
            try:
                default_settings[key] = int(float(value))
            except (TypeError, ValueError):
                pass

    return default_settings


def save_settings(settings: dict) -> None:
    """將預算設定寫入 Supabase。"""
    rows = [
        {
            "setting_key": key,
            "setting_value": int(value),
            "updated_at": datetime.now().isoformat(),
        }
        for key, value in settings.items()
    ]

    (
        supabase.table("app_settings")
        .upsert(
            rows,
            on_conflict="setting_key",
        )
        .execute()
    )


def import_expenses(imported_df: pd.DataFrame) -> int:
    """將 CSV 紀錄批次新增至 Supabase。"""
    rows = []

    for _, row in imported_df.iterrows():
        snack = str(row["點心/店家"]).strip()

        if not snack or snack.lower() in {"nan", "none"}:
            continue

        drink = ""
        if not pd.isna(row["飲料"]):
            drink = str(row["飲料"]).strip()

        try:
            amount = int(float(str(row["金額"]).replace(",", "")))
        except (TypeError, ValueError):
            continue

        if amount <= 0:
            continue

        rows.append(
            {
                "expense_date": str(row["日期"]),
                "expense_type": str(row["類型"]),
                "snack": snack,
                "drink": drink,
                "amount": amount,
            }
        )

    if rows:
        supabase.table("expenses").insert(rows).execute()

    return len(rows)


# =========================================================
# 4. 載入最新資料
# 每次開啟網站或操作後 rerun，都會重新讀取 Supabase
# =========================================================
try:
    expenses_df = load_expenses()
    saved_settings = load_settings()

except Exception as exc:
    st.error("目前無法讀取資料，請確認 Supabase 設定及網路連線。")
    st.code(str(exc))
    st.stop()


# =========================================================
# 5. 邊欄：經費參數設定
# =========================================================
st.sidebar.header("⚙️ 月度經費參數設定")

with st.sidebar.form("budget_settings_form"):
    people_count = st.number_input(
        "團隊人數",
        min_value=1,
        value=saved_settings["people_count"],
        step=1,
    )

    weeks_count = st.number_input(
        "本月週數（下午茶用）",
        min_value=1,
        max_value=5,
        value=saved_settings["weeks_count"],
        step=1,
    )

    tea_unit_price = st.number_input(
        "下午茶單價（$/人/週）",
        min_value=0,
        value=saved_settings["tea_unit_price"],
        step=10,
    )

    snack_unit_price = st.number_input(
        "零食額度（$/人/月）",
        min_value=0,
        value=saved_settings["snack_unit_price"],
        step=10,
    )

    st.markdown("---")

    last_month_balance = st.number_input(
        "上月底餘額（$）",
        value=saved_settings["last_month_balance"],
        step=100,
    )

    settings_submitted = st.form_submit_button(
        "💾 儲存經費設定",
        use_container_width=True,
        type="primary",
    )

    if settings_submitted:
        try:
            save_settings(
                {
                    "people_count": people_count,
                    "weeks_count": weeks_count,
                    "tea_unit_price": tea_unit_price,
                    "snack_unit_price": snack_unit_price,
                    "last_month_balance": last_month_balance,
                }
            )

            st.sidebar.success("設定已儲存！")
            time.sleep(0.5)
            st.rerun()

        except Exception as exc:
            st.sidebar.error(f"設定儲存失敗：{exc}")


# =========================================================
# 6. 計算經費
# =========================================================
tea_budget = people_count * weeks_count * tea_unit_price
snack_budget = people_count * snack_unit_price
total_available = tea_budget + snack_budget + last_month_balance

if expenses_df.empty:
    tea_spent = 0
    snack_spent = 0
else:
    tea_spent = expenses_df.loc[
        expenses_df["類型"] == "下午茶",
        "金額",
    ].sum()

    snack_spent = expenses_df.loc[
        expenses_df["類型"] == "零食",
        "金額",
    ].sum()

total_spent = tea_spent + snack_spent

tea_remaining = tea_budget - tea_spent
snack_remaining = snack_budget - snack_spent
total_remaining = total_available - total_spent


# =========================================================
# 7. 經費總覽
# =========================================================
title_col, refresh_col = st.columns([5, 1])

with title_col:
    st.subheader("📋 經費與預算總覽")

with refresh_col:
    if st.button(
        "🔄 更新資料",
        use_container_width=True,
        help="重新讀取其他同事剛新增或修改的資料",
    ):
        st.rerun()


dash_col1, dash_col2 = st.columns(2)

with dash_col1:
    st.markdown(
        f"""
        <div style="
            background-color:#ffeaea;
            padding:20px;
            border-radius:10px;
            border:1px solid #ffcccc;
            margin-bottom:20px;
        ">
            <h4 style="margin:0; color:#c62828;">
                🍵 下午茶專區
            </h4>

            <div style="
                display:flex;
                justify-content:space-between;
                margin-top:15px;
            ">
                <div>
                    總預算：
                    <b>${tea_budget:,.0f}</b>
                </div>

                <div>
                    已支出：
                    <b>${tea_spent:,.0f}</b>
                </div>

                <div style="
                    color:{'green' if tea_remaining >= 0 else 'red'};
                ">
                    剩餘：
                    <b>${tea_remaining:,.0f}</b>
                </div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

with dash_col2:
    st.markdown(
        f"""
        <div style="
            background-color:#e1f5fe;
            padding:20px;
            border-radius:10px;
            border:1px solid #b3e5fc;
            margin-bottom:20px;
        ">
            <h4 style="margin:0; color:#0277bd;">
                🍪 零食專區
            </h4>

            <div style="
                display:flex;
                justify-content:space-between;
                margin-top:15px;
            ">
                <div>
                    總預算：
                    <b>${snack_budget:,.0f}</b>
                </div>

                <div>
                    已支出：
                    <b>${snack_spent:,.0f}</b>
                </div>

                <div style="
                    color:{'green' if snack_remaining >= 0 else 'red'};
                ">
                    剩餘：
                    <b>${snack_remaining:,.0f}</b>
                </div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


dash_col3, dash_col4 = st.columns(2)

with dash_col3:
    st.markdown(
        f"""
        <div style="
            background-color:#f5f5f5;
            padding:15px;
            border-radius:8px;
            border:1px solid #e0e0e0;
        ">
            <span style="font-size:1.1rem;">
                🔙 上月結餘：
            </span>

            <span style="
                font-size:1.4rem;
                font-weight:bold;
                color:#616161;
            ">
                ${last_month_balance:,.0f}
            </span>
        </div>
        """,
        unsafe_allow_html=True,
    )

with dash_col4:
    total_background = (
        "#e8f5e9"
        if total_remaining >= 0
        else "#ffecb3"
    )

    total_border = (
        "#a5d6a7"
        if total_remaining >= 0
        else "#ffe082"
    )

    total_color = (
        "#1b5e20"
        if total_remaining >= 0
        else "#c62828"
    )

    st.markdown(
        f"""
        <div style="
            background-color:{total_background};
            padding:15px;
            border-radius:8px;
            border:1px solid {total_border};
        ">
            <span style="font-size:1.1rem;">
                🎯 本月剩餘總額：
            </span>

            <span style="
                font-size:1.4rem;
                font-weight:bold;
                color:{total_color};
            ">
                ${total_remaining:,.0f}
            </span>
        </div>
        """,
        unsafe_allow_html=True,
    )


# =========================================================
# 8. 資料備份與還原
# =========================================================
st.divider()

with st.expander("💾 資料備份與還原（CSV 檔案）"):
    backup_col, import_col = st.columns(2)

    with backup_col:
        download_df = expenses_df.drop(
            columns=["id", "建立時間"],
            errors="ignore",
        )

        csv_bytes = download_df.to_csv(
            index=False,
        ).encode("utf-8-sig")

        st.download_button(
            label="📥 下載最新紀錄（CSV）",
            data=csv_bytes,
            file_name=(
                "團建費明細備份_"
                f"{datetime.now().strftime('%Y%m%d')}.csv"
            ),
            mime="text/csv",
            use_container_width=True,
        )

    with import_col:
        uploaded_file = st.file_uploader(
            "📂 匯入舊的備份檔案",
            type=["csv"],
        )

        if uploaded_file is not None:
            try:
                imported_df = pd.read_csv(uploaded_file)

                required_columns = {
                    "日期",
                    "類型",
                    "點心/店家",
                    "飲料",
                    "金額",
                }

                if not required_columns.issubset(imported_df.columns):
                    st.error("檔案欄位不正確，無法匯入。")

                else:
                    st.warning(
                        "同一份 CSV 請勿重複匯入，"
                        "否則紀錄會重複。"
                    )

                    if st.button(
                        "確認匯入 Supabase",
                        type="primary",
                        use_container_width=True,
                    ):
                        imported_count = import_expenses(imported_df)

                        st.success(
                            f"成功匯入 {imported_count} 筆紀錄！"
                        )

                        time.sleep(0.8)
                        st.rerun()

            except Exception as exc:
                st.error(f"匯入失敗：{exc}")


# =========================================================
# 9. 新增消費紀錄
# =========================================================
st.divider()
st.subheader("➕ 新增消費紀錄")

with st.form(
    "add_expense_form",
    clear_on_submit=True,
):
    form_col1, form_col2, form_col3, form_col4, form_col5 = (
        st.columns([2, 2, 3, 3, 2])
    )

    with form_col1:
        exp_date = st.date_input(
            "日期",
            datetime.now(),
        )

    with form_col2:
        exp_type = st.selectbox(
            "類型",
            ["下午茶", "零食"],
        )

    with form_col3:
        exp_snack = st.text_input(
            "點心／店家",
            placeholder="如：哈堤手作三明治",
        )

    with form_col4:
        exp_drink = st.text_input(
            "飲料（可選填）",
            placeholder="如：大茗",
        )

    with form_col5:
        exp_amount_str = st.text_input(
            "金額（$）",
            placeholder="如：4877",
        )

    submitted = st.form_submit_button(
        "確認新增紀錄（可按 Enter）",
        use_container_width=True,
        type="primary",
    )

    if submitted:
        clean_amount = (
            exp_amount_str
            .strip()
            .replace(",", "")
        )

        if not exp_snack.strip():
            st.warning("請輸入「點心／店家」名稱！")

        elif not clean_amount.isdigit():
            st.warning("金額請輸入純數字！")

        elif int(clean_amount) <= 0:
            st.warning("金額必須大於 0！")

        else:
            try:
                add_expense(
                    expense_date=exp_date,
                    expense_type=exp_type,
                    snack=exp_snack.strip(),
                    drink=exp_drink.strip(),
                    amount=int(clean_amount),
                )

                st.success(
                    f"✅ 新增成功！已記錄「{exp_snack.strip()}」。"
                )

                time.sleep(0.5)
                st.rerun()

            except Exception as exc:
                st.error(f"新增失敗：{exc}")


# =========================================================
# 10. 編輯消費紀錄
# =========================================================
@st.dialog("✏️ 編輯消費紀錄")
def edit_record_dialog(record_id: int) -> None:
    try:
        response = (
            supabase.table("expenses")
            .select("*")
            .eq("id", int(record_id))
            .limit(1)
            .execute()
        )

        records = response.data or []

        if not records:
            st.error("找不到這筆資料，可能已被其他人刪除。")
            return

        row = records[0]

    except Exception as exc:
        st.error(f"讀取資料失敗：{exc}")
        return

    try:
        default_date = datetime.strptime(
            str(row["expense_date"]),
            "%Y-%m-%d",
        ).date()

    except (TypeError, ValueError):
        default_date = datetime.now().date()

    new_date = st.date_input(
        "日期",
        default_date,
    )

    current_type = str(row.get("expense_type", "下午茶"))

    new_type = st.selectbox(
        "類型",
        ["下午茶", "零食"],
        index=0 if current_type == "下午茶" else 1,
    )

    new_snack = st.text_input(
        "點心／店家",
        value=str(row.get("snack", "")),
    )

    existing_drink = row.get("drink") or ""

    new_drink = st.text_input(
        "飲料",
        value=str(existing_drink),
    )

    try:
        default_amount = int(float(row.get("amount", 0)))
    except (TypeError, ValueError):
        default_amount = 0

    new_amount = st.number_input(
        "金額（$）",
        min_value=0,
        value=default_amount,
        step=10,
    )

    if st.button(
        "儲存修改",
        type="primary",
        use_container_width=True,
    ):
        if not new_snack.strip():
            st.warning("請輸入點心／店家名稱。")

        elif new_amount <= 0:
            st.warning("金額必須大於 0。")

        else:
            try:
                update_expense(
                    record_id=record_id,
                    expense_date=new_date,
                    expense_type=new_type,
                    snack=new_snack.strip(),
                    drink=new_drink.strip(),
                    amount=int(new_amount),
                )

                st.success("修改成功！")
                time.sleep(0.5)
                st.rerun()

            except Exception as exc:
                st.error(f"修改失敗：{exc}")


# =========================================================
# 11. 本月消費明細
# =========================================================
st.divider()
st.subheader("📋 本月消費明細")

valid_df = expenses_df.copy()

if not valid_df.empty:
    valid_df = valid_df.dropna(
        subset=["點心/店家"]
    )

    valid_df = valid_df[
        valid_df["點心/店家"]
        .astype(str)
        .str.strip()
        .ne("")
    ]

if valid_df.empty:
    st.info("目前還沒有任何紀錄！")

else:
    for _, row in valid_df.iterrows():
        record_id = int(row["id"])

        try:
            amount_value = int(float(row["金額"]))
        except (TypeError, ValueError):
            amount_value = 0

        amount_display = f"$ {amount_value:,}"

        snack_value = str(row["點心/店家"]).strip()

        drink_value = ""
        if not pd.isna(row["飲料"]):
            drink_value = str(row["飲料"]).strip()

        (
            card_col1,
            card_col2,
            card_col3,
            card_col4,
            card_col5,
            card_col6,
            card_col7,
        ) = st.columns(
            [2, 1.5, 2.5, 2, 2, 1.5, 1.5]
        )

        with card_col1:
            st.write(f"📅 **{row['日期']}**")

        with card_col2:
            st.markdown(f"🏷️ `{row['類型']}`")

        with card_col3:
            st.write(f"🍵 **{snack_value}**")

        with card_col4:
            if drink_value:
                st.write(f"🥤 {drink_value}")
            else:
                st.write("—")

        with card_col5:
            st.markdown(
                f"""
                💰
                <span style="
                    font-size:1.1rem;
                    font-weight:bold;
                    color:#1b5e20;
                ">
                    {amount_display}
                </span>
                """,
                unsafe_allow_html=True,
            )

        with card_col6:
            if st.button(
                "✏️ 編輯",
                key=f"edit_{record_id}",
                use_container_width=True,
            ):
                edit_record_dialog(record_id)

        with card_col7:
            if st.button(
                "🗑️ 刪除",
                key=f"delete_{record_id}",
                use_container_width=True,
            ):
                try:
                    delete_expense(record_id)
                    st.success("紀錄已刪除！")
                    time.sleep(0.4)
                    st.rerun()

                except Exception as exc:
                    st.error(f"刪除失敗：{exc}")

        st.markdown(
            """
            <hr style="
                margin:8px 0;
                border:0;
                border-top:1px solid #f0f0f0;
            ">
            """,
            unsafe_allow_html=True,
        )
