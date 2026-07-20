from datetime import datetime
from html import escape
from zoneinfo import ZoneInfo

import pandas as pd
import streamlit as st
from supabase import Client, create_client


# =========================================================
# 1. Streamlit 網頁設定
# =========================================================

st.set_page_config(
    page_title="辦公室備用卡借還系統",
    page_icon="💳",
    layout="centered",
    initial_sidebar_state="collapsed",
)

TAIPEI_TZ = ZoneInfo("Asia/Taipei")


# =========================================================
# 2. 自訂畫面樣式
# =========================================================

st.markdown(
    """
    <style>
        .block-container {
            max-width: 760px;
            padding-top: 2rem;
            padding-bottom: 3rem;
        }

        [data-testid="stHeader"] {
            background: transparent;
        }

        .main-title {
            font-size: 2rem;
            font-weight: 800;
            margin-bottom: 0.25rem;
        }

        .sub-title {
            color: #64748b;
            margin-bottom: 1.5rem;
        }

        .card-available {
            border: 2px solid #22c55e;
            background: #f0fdf4;
            border-radius: 12px;
            padding: 18px;
            margin-bottom: 10px;
        }

        .card-borrowed {
            border: 2px solid #ef4444;
            background: #fef2f2;
            border-radius: 12px;
            padding: 18px;
            margin-bottom: 10px;
        }

        .available-title {
            color: #15803d;
            font-size: 1.15rem;
            font-weight: 800;
        }

        .borrowed-title {
            color: #b91c1c;
            font-size: 1.15rem;
            font-weight: 800;
        }

        .card-detail {
            color: #475569;
            margin-top: 6px;
            margin-bottom: 0;
        }

        .small-text {
            color: #64748b;
            font-size: 0.9rem;
            margin-top: 4px;
        }

        div[data-testid="stForm"] {
            border: none;
            padding: 0;
        }

        .status-box {
            border-radius: 10px;
            padding: 12px 16px;
            margin-bottom: 18px;
            background: #f8fafc;
            border: 1px solid #e2e8f0;
        }
    </style>
    """,
    unsafe_allow_html=True,
)


# =========================================================
# 3. Supabase 連線
# =========================================================

@st.cache_resource
def get_supabase_client() -> Client:
    """
    建立並快取 Supabase 連線。

    Streamlit Secrets 必須包含：
    SUPABASE_URL
    SUPABASE_SECRET_KEY
    """
    try:
        supabase_url = st.secrets["SUPABASE_URL"]
        supabase_key = st.secrets["SUPABASE_SECRET_KEY"]
    except KeyError as error:
        st.error(
            "找不到 Supabase 設定。請到 Streamlit App 的 Secrets "
            "加入 SUPABASE_URL 和 SUPABASE_SECRET_KEY。"
        )
        st.stop()
        raise error

    return create_client(supabase_url, supabase_key)


supabase = get_supabase_client()


# =========================================================
# 4. 網站密碼保護
# =========================================================

def check_app_password() -> bool:
    """
    使用 Streamlit Secrets 中的 APP_PASSWORD 保護網站。

    如果沒有設定 APP_PASSWORD，網站不會要求登入。
    正式使用時建議一定要設定。
    """
    app_password = st.secrets.get("APP_PASSWORD", "")

    if not app_password:
        return True

    if st.session_state.get("password_verified", False):
        return True

    st.markdown(
        '<div class="main-title">💳 辦公室備用卡管理</div>',
        unsafe_allow_html=True,
    )
    st.info("請先輸入管理系統密碼。")

    with st.form("login_form"):
        password = st.text_input(
            "系統密碼",
            type="password",
            placeholder="請輸入密碼",
        )

        submitted = st.form_submit_button(
            "登入",
            use_container_width=True,
            type="primary",
        )

    if submitted:
        if password == app_password:
            st.session_state.password_verified = True
            st.rerun()
        else:
            st.error("密碼錯誤，請重新輸入。")

    return False


if not check_app_password():
    st.stop()


# =========================================================
# 5. 資料處理函式
# =========================================================

def format_datetime(value: str | None) -> str:
    """
    將 Supabase 的 UTC／ISO 時間轉成台北時間。
    """
    if not value:
        return ""

    try:
        parsed_time = datetime.fromisoformat(
            value.replace("Z", "+00:00")
        )

        if parsed_time.tzinfo is None:
            parsed_time = parsed_time.replace(
                tzinfo=ZoneInfo("UTC")
            )

        taipei_time = parsed_time.astimezone(TAIPEI_TZ)

        return taipei_time.strftime("%Y-%m-%d %H:%M:%S")

    except (TypeError, ValueError):
        return str(value)


def load_cards() -> list[dict]:
    """
    讀取所有卡片。
    """
    response = (
        supabase
        .table("cards")
        .select("card_id,status,borrower,borrowed_at")
        .order("card_id")
        .execute()
    )

    return response.data or []


def load_logs(limit: int = 50) -> list[dict]:
    """
    讀取最新借還紀錄。
    """
    response = (
        supabase
        .table("borrow_logs")
        .select("id,card_id,borrower,action,timestamp")
        .order("id", desc=True)
        .limit(limit)
        .execute()
    )

    return response.data or []


def borrow_card(card_id: str, borrower: str) -> bool:
    """
    呼叫 Supabase 借卡函式。
    """
    cleaned_borrower = borrower.strip()

    if not cleaned_borrower:
        raise ValueError("請輸入借用人姓名。")

    response = supabase.rpc(
        "borrow_card",
        {
            "input_card_id": card_id,
            "input_borrower": cleaned_borrower,
        },
    ).execute()

    return response.data is True


def return_card(card_id: str) -> bool:
    """
    呼叫 Supabase 還卡函式。
    """
    response = supabase.rpc(
        "return_card",
        {
            "input_card_id": card_id,
        },
    ).execute()

    return response.data is True


# =========================================================
# 6. 標題與功能分頁
# =========================================================

title_col, logout_col = st.columns([5, 1])

with title_col:
    st.markdown(
        '<div class="main-title">💳 辦公室備用卡管理</div>',
        unsafe_allow_html=True,
    )
    st.markdown(
        '<div class="sub-title">查詢備用卡狀態、借用與歸還紀錄</div>',
        unsafe_allow_html=True,
    )

with logout_col:
    if st.secrets.get("APP_PASSWORD", ""):
        if st.button("登出", use_container_width=True):
            st.session_state.password_verified = False
            st.rerun()


card_tab, log_tab = st.tabs(
    [
        "💳 卡片管理",
        "📜 歷史紀錄",
    ]
)


# =========================================================
# 7. 卡片管理
# =========================================================

with card_tab:
    try:
        cards = load_cards()

    except Exception as error:
        st.error(f"讀取卡片失敗：{error}")
        st.stop()

    if not cards:
        st.warning(
            "目前沒有卡片資料，請確認是否已在 Supabase 執行建表 SQL。"
        )

    available_count = sum(
        1 for card in cards
        if card.get("status") == "AVAILABLE"
    )

    borrowed_count = sum(
        1 for card in cards
        if card.get("status") == "BORROWED"
    )

    st.markdown(
        f"""
        <div class="status-box">
            目前共有 <b>{len(cards)}</b> 張卡片：
            🟢 可借用 <b>{available_count}</b> 張，
            🔴 借出中 <b>{borrowed_count}</b> 張
        </div>
        """,
        unsafe_allow_html=True,
    )

    for card in cards:
        card_id = str(card.get("card_id", ""))
        status = card.get("status", "AVAILABLE")
        borrower = card.get("borrower") or ""
        borrowed_at = format_datetime(
            card.get("borrowed_at")
        )

        safe_card_id = escape(card_id)
        safe_borrower = escape(str(borrower))
        safe_borrowed_at = escape(borrowed_at)

        if status == "AVAILABLE":
            st.markdown(
                f"""
                <div class="card-available">
                    <div class="available-title">
                        🟢 {safe_card_id}（可借用）
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )

            with st.form(
                key=f"borrow_form_{card_id}",
                clear_on_submit=True,
            ):
                borrower_input = st.text_input(
                    "借用人姓名",
                    placeholder="請輸入姓名",
                    key=f"borrower_{card_id}",
                    label_visibility="collapsed",
                )

                borrow_submitted = st.form_submit_button(
                    f"借用 {card_id}",
                    type="primary",
                    use_container_width=True,
                )

            if borrow_submitted:
                try:
                    success = borrow_card(
                        card_id=card_id,
                        borrower=borrower_input,
                    )

                    if success:
                        st.success(
                            f"{card_id} 已成功借給"
                            f"「{borrower_input.strip()}」。"
                        )
                        st.rerun()
                    else:
                        st.warning(
                            f"{card_id} 目前可能已被其他人借走，"
                            "請重新整理後確認。"
                        )

                except ValueError as error:
                    st.warning(str(error))

                except Exception as error:
                    st.error(f"借卡失敗：{error}")

        else:
            st.markdown(
                f"""
                <div class="card-borrowed">
                    <div class="borrowed-title">
                        🔴 {safe_card_id}（借出中）
                    </div>

                    <p class="card-detail">
                        借用人：<b>{safe_borrower}</b>
                    </p>

                    <p class="small-text">
                        借出時間：{safe_borrowed_at}
                    </p>
                </div>
                """,
                unsafe_allow_html=True,
            )

            if st.button(
                f"歸還 {card_id}",
                key=f"return_{card_id}",
                use_container_width=True,
            ):
                try:
                    success = return_card(card_id)

                    if success:
                        st.success(f"{card_id} 已成功歸還。")
                        st.rerun()
                    else:
                        st.warning(
                            f"{card_id} 目前不是借出狀態，"
                            "請重新整理後確認。"
                        )

                except Exception as error:
                    st.error(f"還卡失敗：{error}")

        st.markdown("<br>", unsafe_allow_html=True)


# =========================================================
# 8. 歷史紀錄
# =========================================================

with log_tab:
    st.subheader("最近 50 筆借還紀錄")

    try:
        logs = load_logs(limit=50)

    except Exception as error:
        st.error(f"讀取歷史紀錄失敗：{error}")
        logs = []

    if not logs:
        st.info("目前還沒有借還紀錄。")

    else:
        log_rows = []

        for log in logs:
            action = log.get("action")

            log_rows.append(
                {
                    "時間": format_datetime(
                        log.get("timestamp")
                    ),
                    "卡號": log.get("card_id", ""),
                    "借用人": log.get("borrower", ""),
                    "動作": (
                        "借出"
                        if action == "BORROW"
                        else "歸還"
                    ),
                }
            )

        logs_df = pd.DataFrame(log_rows)

        st.dataframe(
            logs_df,
            use_container_width=True,
            hide_index=True,
            column_config={
                "時間": st.column_config.TextColumn(
                    "時間",
                    width="medium",
                ),
                "卡號": st.column_config.TextColumn(
                    "卡號",
                    width="small",
                ),
                "借用人": st.column_config.TextColumn(
                    "借用人",
                    width="medium",
                ),
                "動作": st.column_config.TextColumn(
                    "動作",
                    width="small",
                ),
            },
        )

        csv_data = logs_df.to_csv(
            index=False
        ).encode("utf-8-sig")

        st.download_button(
            label="下載歷史紀錄 CSV",
            data=csv_data,
            file_name="白卡借還紀錄.csv",
            mime="text/csv",
            use_container_width=True,
        )


# =========================================================
# 9. 頁尾
# =========================================================

st.divider()
st.caption("辦公室備用卡借還系統")
