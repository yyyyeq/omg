import sqlite3
from datetime import datetime
from fastapi import FastAPI, Form
from fastapi.responses import HTMLResponse, RedirectResponse

app = FastAPI(title="辦公室備用卡借還系統")

# --- 1. 資料庫初始化 ---
DB_NAME = "cards.db"

def init_db():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS cards (
            card_id TEXT PRIMARY KEY,
            status TEXT DEFAULT 'AVAILABLE',
            borrower TEXT,
            borrowed_at TEXT
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS borrow_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            card_id TEXT,
            borrower TEXT,
            action TEXT,
            timestamp TEXT
        )
    """)
    for card in ["CARD-01", "CARD-02", "CARD-03"]:
        cursor.execute("INSERT OR IGNORE INTO cards (card_id, status) VALUES (?, 'AVAILABLE')", (card,))
    
    conn.commit()
    conn.close()

init_db()

# --- 2. API 與網頁介面 ---

@app.get("/", response_class=HTMLResponse)
def read_root():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT card_id, status, borrower, borrowed_at FROM cards")
    cards = cursor.fetchall()
    conn.close()

    cards_html = ""
    for card_id, status, borrower, borrowed_at in cards:
        if status == "AVAILABLE":
            cards_html += f"""
            <div style="border:2px solid #22c55e; padding:16px; border-radius:8px; margin-bottom:12px; background:#f0fdf4;">
                <h3 style="margin:0; color:#15803d;">🟢 {card_id}（可借用）</h3>
                <form action="/borrow" method="post" style="margin-top:10px;">
                    <input type="hidden" name="card_id" value="{card_id}">
                    <input type="text" name="borrower" placeholder="輸入姓名" required style="padding:6px; border:1px solid #ccc; border-radius:4px;">
                    <button type="submit" style="background:#22c55e; color:white; border:none; padding:6px 12px; border-radius:4px; cursor:pointer;">借用卡片</button>
                </form>
            </div>
            """
        else:
            cards_html += f"""
            <div style="border:2px solid #ef4444; padding:16px; border-radius:8px; margin-bottom:12px; background:#fef2f2;">
                <h3 style="margin:0; color:#b91c1c;">🔴 {card_id}（借出中）</h3>
                <p style="margin:5px 0;">借用人：<b>{borrower}</b></p>
                <p style="margin:5px 0; color:#666; font-size:0.9em;">借出時間：{borrowed_at}</p>
                <form action="/return" method="post" style="margin-top:10px;">
                    <input type="hidden" name="card_id" value="{card_id}">
                    <button type="submit" style="background:#ef4444; color:white; border:none; padding:6px 12px; border-radius:4px; cursor:pointer;">歸還卡片</button>
                </form>
            </div>
            """

    return f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>備用卡借還系統</title>
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
    </head>
    <body style="font-family: Arial, sans-serif; max-width: 500px; margin: 40px auto; padding:0 16px;">
        <h2>💳 辦公室備用卡管理</h2>
        {cards_html}
        <hr style="margin-top:30px;">
        <p style="text-align:center;"><a href="/logs">📜 查看歷史紀錄</a></p>
    </body>
    </html>
    """

@app.post("/borrow")
def borrow_card(card_id: str = Form(...), borrower: str = Form(...)):
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("UPDATE cards SET status='BORROWED', borrower=?, borrowed_at=? WHERE card_id=? AND status='AVAILABLE'", (borrower, now, card_id))
    cursor.execute("INSERT INTO borrow_logs (card_id, borrower, action, timestamp) VALUES (?, ?, 'BORROW', ?)", (card_id, borrower, now))
    conn.commit()
    conn.close()
    return RedirectResponse(url="/", status_code=303)

@app.post("/return")
def return_card(card_id: str = Form(...)):
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT borrower FROM cards WHERE card_id=?", (card_id,))
    row = cursor.fetchone()
    borrower = row[0] if row else "Unknown"
    cursor.execute("UPDATE cards SET status='AVAILABLE', borrower=NULL, borrowed_at=NULL WHERE card_id=?", (card_id,))
    cursor.execute("INSERT INTO borrow_logs (card_id, borrower, action, timestamp) VALUES (?, ?, 'RETURN', ?)", (card_id, borrower, now))
    conn.commit()
    conn.close()
    return RedirectResponse(url="/", status_code=303)

@app.get("/logs", response_class=HTMLResponse)
def view_logs():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT card_id, borrower, action, timestamp FROM borrow_logs ORDER BY id DESC LIMIT 50")
    logs = cursor.fetchall()
    conn.close()

    rows_html = ""
    for card_id, borrower, action, timestamp in logs:
        action_text = "借出" if action == "BORROW" else "歸還"
        rows_html += f"<tr><td>{timestamp}</td><td>{card_id}</td><td>{borrower}</td><td>{action_text}</td></tr>"

    return f"""
    <html>
    <body style="font-family: Arial, sans-serif; max-width: 600px; margin: 40px auto; padding:0 16px;">
        <h2>📜 歷史借還紀錄 (前50筆)</h2>
        <table border="1" cellpadding="8" style="border-collapse:collapse; width:100%;">
            <tr><th>時間</th><th>卡號</th><th>借用人</th><th>動作</th></tr>
            {rows_html}
        </table>
        <p><a href="/">⬅ 返還主頁</a></p>
    </body>
    </html>
    """

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)
