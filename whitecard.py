import sqlite3
from datetime import datetime
from fastapi import FastAPI, Form
from fastapi.responses import HTMLResponse, RedirectResponse

app = FastAPI(title="白卡登記系統")

# --- 1. 資料庫初始化 ---
DB_NAME = "whitecard.db"

def init_db():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS whitecard_records (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT,
            type TEXT,
            snack TEXT,
            drink TEXT,
            amount INTEGER,
            created_at TEXT
        )
    """)
    conn.commit()
    conn.close()

init_db()

# --- 2. API 與網頁介面 ---

@app.get("/", response_class=HTMLResponse)
def read_root():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT id, date, type, snack, drink, amount FROM whitecard_records ORDER BY id DESC")
    records = cursor.fetchall()
    
    # 計算總消費金額
    cursor.execute("SELECT SUM(amount) FROM whitecard_records")
    total_amount = cursor.fetchone()[0] or 0
    conn.close()

    today_str = datetime.now().strftime("%Y-%m-%d")

    # 組合紀錄表格 HTML
    rows_html = ""
    for r_id, r_date, r_type, r_snack, r_drink, r_amount in records:
        drink_display = r_drink if r_drink else "-"
        rows_html += f"""
        <tr>
            <td style="padding:10px; border-bottom:1px solid #ddd;">{r_date}</td>
            <td style="padding:10px; border-bottom:1px solid #ddd;"><span style="background:#e0f2fe; color:#0369a1; padding:2px 8px; border-radius:4px; font-size:0.9em;">{r_type}</span></td>
            <td style="padding:10px; border-bottom:1px solid #ddd;"><b>{r_snack}</b></td>
            <td style="padding:10px; border-bottom:1px solid #ddd; color:#666;">{drink_display}</td>
            <td style="padding:10px; border-bottom:1px solid #ddd; font-weight:bold; color:#15803d;">${r_amount:,}</td>
            <td style="padding:10px; border-bottom:1px solid #ddd; text-align:center;">
                <form action="/delete" method="post" style="margin:0;" onsubmit="return confirm('確定要刪除這筆紀錄嗎？');">
                    <input type="hidden" name="record_id" value="{r_id}">
                    <button type="submit" style="background:#ef4444; color:white; border:none; padding:4px 8px; border-radius:4px; cursor:pointer;">刪除</button>
                </form>
            </td>
        </tr>
        """

    if not rows_html:
        rows_html = "<tr><td colspan='6' style='text-align:center; padding:20px; color:#888;'>目前尚無白卡登記紀錄</td></tr>"

    return f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>🍵 白卡登記系統</title>
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
    </head>
    <body style="font-family: Arial, sans-serif; max-width: 700px; margin: 30px auto; padding:0 16px; background-color:#f9fafb;">
        <div style="background:white; padding:24px; border-radius:12px; box-shadow:0 1px 3px rgba(0,0,0,0.1);">
            <h2 style="margin-top:0; color:#1f2937;">🍵 辦公室白卡登記系統</h2>
            
            <!-- 累計統計 -->
            <div style="background:#f3f4f6; padding:12px 16px; border-radius:8px; margin-bottom:20px;">
                <span style="font-weight:bold; color:#374151;">💰 目前累計總金額：</span>
                <span style="font-size:1.3em; font-weight:bold; color:#059669;">${total_amount:,} 元</span>
            </div>

            <!-- 新增紀錄表單 -->
            <form action="/add" method="post" style="background:#f0fdf4; padding:16px; border-radius:8px; border:1px solid #bbf7d0; margin-bottom:24px;">
                <h4 style="margin-top:0; margin-bottom:12px; color:#166534;">➕ 新增白卡登記</h4>
                <div style="display:grid; grid-template-columns: 1fr 1fr; gap:10px; margin-bottom:10px;">
                    <div>
                        <label style="font-size:0.85em; color:#374151;">日期：</label>
                        <input type="date" name="date" value="{today_str}" required style="width:100%; padding:8px; border:1px solid #ccc; border-radius:4px; box-sizing:border-box;">
                    </div>
                    <div>
                        <label style="font-size:0.85em; color:#374151;">類型：</label>
                        <select name="type" style="width:100%; padding:8px; border:1px solid #ccc; border-radius:4px; box-sizing:border-box;">
                            <option value="下午茶">下午茶</option>
                            <option value="零食">零食</option>
                            <option value="其他">其他</option>
                        </select>
                    </div>
                </div>
                <div style="display:grid; grid-template-columns: 1fr 1fr 1fr; gap:10px; margin-bottom:12px;">
                    <div>
                        <label style="font-size:0.85em; color:#374151;">點心 / 店家：</label>
                        <input type="text" name="snack" placeholder="如：50嵐" required style="width:100%; padding:8px; border:1px solid #ccc; border-radius:4px; box-sizing:border-box;">
                    </div>
                    <div>
                        <label style="font-size:0.85em; color:#374151;">飲料 (選填)：</label>
                        <input type="text" name="drink" placeholder="如：四季春" style="width:100%; padding:8px; border:1px solid #ccc; border-radius:4px; box-sizing:border-box;">
                    </div>
                    <div>
                        <label style="font-size:0.85em; color:#374151;">金額 ($)：</label>
                        <input type="number" name="amount" placeholder="金額" min="1" required style="width:100%; padding:8px; border:1px solid #ccc; border-radius:4px; box-sizing:border-box;">
                    </div>
                </div>
                <button type="submit" style="width:100%; background:#16a34a; color:white; border:none; padding:10px; border-radius:4px; font-weight:bold; cursor:pointer;">新增紀錄 (Enter)</button>
            </form>

            <!-- 歷史紀錄列表 -->
            <h3 style="color:#1f2937;">📋 登記明細紀錄</h3>
            <table style="width:100%; border-collapse:collapse; text-align:left;">
                <thead>
                    <tr style="background:#f3f4f6; color:#4b5563;">
                        <th style="padding:10px;">日期</th>
                        <th style="padding:10px;">類型</th>
                        <th style="padding:10px;">品項/店家</th>
                        <th style="padding:10px;">飲料</th>
                        <th style="padding:10px;">金額</th>
                        <th style="padding:10px; text-align:center;">操作</th>
                    </tr>
                </thead>
                <tbody>
                    {rows_html}
                </tbody>
            </table>
        </div>
    </body>
    </html>
    """

@app.post("/add")
def add_record(
    date: str = Form(...),
    type: str = Form(...),
    snack: str = Form(...),
    drink: str = Form(""),
    amount: int = Form(...)
):
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO whitecard_records (date, type, snack, drink, amount, created_at) VALUES (?, ?, ?, ?, ?, ?)",
        (date, type, snack.strip(), drink.strip(), amount, now)
    )
    conn.commit()
    conn.close()
    return RedirectResponse(url="/", status_code=303)

@app.post("/delete")
def delete_record(record_id: int = Form(...)):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM whitecard_records WHERE id=?", (record_id,))
    conn.commit()
    conn.close()
    return RedirectResponse(url="/", status_code=303)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8001)
