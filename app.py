import streamlit as st
import pandas as pd
import requests
import base64
import io
import json
import streamlit.components.v1 as components
from datetime import datetime, timedelta
import re
import smtplib
from email.mime.text import MIMEText
import random
import string
import hashlib
import os

# ==============================================================================
# 【仕様定義書 / SPECIFICATIONS & USER REQUESTS】
# ------------------------------------------------------------------------------
# [基本仕様]
# 1. 接続・保存機能 (Storage): GitHub API (menu.csv, history.csv, ingredients.csv).
# 2. 献立作成ロジック (Planning): 主菜1, 副菜1, 副菜2, 汁物の4枠。
# 3. 買い物リスト & 印刷 (Shopping & Print): カテゴリ別表示 & A4最適化印刷.
# 4. 履歴管理 (History): 自動保存。履歴タブでの料理名修正・行削除機能。
# 5. UI/UX: スマホ操作優先（キーボード自動起動防止、マルチセレクト維持）。
#
# [ユーザー個別依頼 & 運用ルール]
# - 「主菜2」は献立作成枠から除外。定番アイテムとしてのみ再利用。
# - uid列は完全に排除。
# - 【最重要】修正時は必ず「全文」を出力すること。一部省略は厳禁。
# - 【最重要】既存の細かい仕様（印刷、CSS等）は指示がない限り絶対に変えない。
# - 【最重要】ユーザーからの追加指示は、毎回このセクションに書き足して更新すること。
# - [2026/02/22] 買い物リストの編集(📝)・削除(🗑️)ボタンを復活。
# - [2026/02/22] 材料名の抽出ロジックを修正し、材料が繋がって表示されるバグを解消。
# - [2026/02/22] 確定献立表のヘッダーを「メニュー1, メニュー2...」の通し番号形式に変更し、最後を「汁物」に固定。
# - [2026/02/22] パスワード保存方式をPBKDF2（SHA256）によるハッシュ化方式に変更。
# ==============================================================================

VERSION = "1.9.5"

# --- 1. 接続・認証設定 ---
REPO = "daimilk-lgtm/kondake"
FILE = "menu.csv"
DICT_FILE = "ingredients.csv"
HIST_FILE = "history.csv"
DRAFT_FILE = "draft.json"
USERS_FILE = "users.json"
TOKEN = st.secrets.get("GITHUB_TOKEN")

# SMTP設定
SMTP_USER = st.secrets.get("SMTP_USER")
SMTP_PASS = st.secrets.get("SMTP_PASS")

def make_pw_hash(password, salt=None):
    if salt is None:
        salt = base64.b64encode(os.urandom(16)).decode('utf-8')
    pw_hash = hashlib.pbkdf2_hmac('sha256', password.encode(), salt.encode(), 100000)
    return f"{salt}${base64.b64encode(pw_hash).decode('utf-8')}"

def check_pw_hash(password, hash_str):
    if "$" not in hash_str: return password == hash_str
    salt, original_hash = hash_str.split("$")
    new_hash = make_pw_hash(password, salt)
    return new_hash == hash_str

def get_github_content(filename):
    url = f"https://api.github.com/repos/{REPO}/contents/{filename}"
    headers = {"Authorization": f"token {TOKEN}", "Accept": "application/vnd.github.v3+json"}
    try:
        r = requests.get(url, headers=headers)
        if r.status_code == 200:
            content = base64.b64decode(r.json()["content"]).decode("utf-8-sig")
            return content, r.json()["sha"]
        else: return None, r.status_code
    except Exception as e: return None, str(e)

def save_to_github(content, filename, message, current_sha=None):
    content_b64 = base64.b64encode(content.encode("utf-8")).decode("utf-8")
    url = f"https://api.github.com/repos/{REPO}/contents/{filename}"
    headers = {"Authorization": f"token {TOKEN}", "Accept": "application/vnd.github.v3+json"}
    data = {"message": message, "content": content_b64}
    if current_sha: data["sha"] = current_sha
    res = requests.put(url, headers=headers, json=data)
    return res.status_code

def send_otp_email(to_email, otp):
    if not SMTP_USER or not SMTP_PASS: return False, "SMTP設定不足"
    msg = MIMEText(f"献だけ：パスワード再設定用のワンタイムパスコードは 【 {otp} 】 です。")
    msg["Subject"] = "【献だけ】パスワード再設定コード"; msg["From"] = SMTP_USER; msg["To"] = to_email
    try:
        with smtplib.SMTP_SSL("smtp.gmail.com", 465, timeout=10) as server:
            server.login(SMTP_USER, SMTP_PASS)
            server.send_message(msg)
        return True, "Success"
    except: return False, "送信失敗"

# --- 2. デザイン定義 ---
st.set_page_config(page_title="献だけ", layout="centered", initial_sidebar_state="collapsed")

st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Noto+Sans+JP:wght@100;300;400&display=swap');
    [data-testid="stSidebar"] { display: none; }
    html, body, [class*="css"], p, div, select, input, label, span { font-family: 'Noto Sans JP', sans-serif !important; font-weight: 300 !important; }
    .main-title { font-weight: 100 !important; font-size: 3rem; text-align: center; margin: 40px 0 20px 0; letter-spacing: 0.5rem; }
    .auth-header { position: absolute; top: -10px; right: 0; text-align: right; padding: 10px; z-index: 1000; }
    .user-id { font-size: 0.75rem; color: #666; }
    .preview-table { width: 100%; border-collapse: collapse; font-size: 0.85rem; margin-top: 10px; margin-bottom: 20px; overflow-x: auto; display: block; }
    .preview-table th, .preview-table td { border: 1px solid #eee; padding: 6px; text-align: left; min-width: 80px; }
    .preview-table th { background-color: #fcfcfc; font-weight: 400; }
</style>
""", unsafe_allow_html=True)

# --- 3. 認証ロジック ---
if 'authenticated' not in st.session_state: st.session_state['authenticated'] = False
if 'user_email' not in st.session_state: st.session_state['user_email'] = ""
if 'reset_mode' not in st.session_state: st.session_state['reset_mode'] = "none"
if 'reset_target_email' not in st.session_state: st.session_state['reset_target_email'] = ""
if 'reset_otp' not in st.session_state: st.session_state['reset_otp'] = ""
if 'show_forgot_pw' not in st.session_state: st.session_state['show_forgot_pw'] = False

def get_users_data():
    content, sha = get_github_content(USERS_FILE)
    if content: return json.loads(content), sha
    return {}, None

if not st.session_state['authenticated']:
    st.markdown('<h1 class="main-title">献だけ</h1>', unsafe_allow_html=True)
    if st.session_state['reset_mode'] != "none":
        if st.session_state['reset_mode'] == "sent":
            otp_input = st.text_input("6桁のパスコードを入力", max_chars=6)
            if st.button("コードを確認", use_container_width=True):
                if otp_input == st.session_state['reset_otp']: st.session_state['reset_mode'] = "verified"; st.rerun()
        elif st.session_state['reset_mode'] == "verified":
            with st.form("new_pass_form"):
                new_p = st.text_input("新しいパスワード", type="password")
                if st.form_submit_button("パスワードを更新", use_container_width=True):
                    users, sha = get_users_data()
                    users[st.session_state['reset_target_email']] = make_pw_hash(new_p)
                    save_to_github(json.dumps(users, ensure_ascii=False), USERS_FILE, "Reset Pass", sha)
                    st.session_state['reset_mode'] = "none"; st.rerun()
    else:
        tab_log, tab_reg = st.tabs(["ログイン", "新規ユーザー登録"])
        with tab_log:
            with st.form("login_form"):
                e = st.text_input("メールアドレス")
                p = st.text_input("パスワード", type="password")
                if st.form_submit_button("ログイン", use_container_width=True):
                    users, _ = get_users_data()
                    if e in users and check_pw_hash(p, users[e]):
                        st.session_state['authenticated'] = True; st.session_state['user_email'] = e; st.rerun()
            if st.button("パスワードを忘れた場合", use_container_width=True):
                st.session_state['show_forgot_pw'] = True; st.rerun()
            if st.session_state['show_forgot_pw']:
                re_email = st.text_input("登録メールアドレス")
                if st.button("再設定コードを送信"):
                    users, _ = get_users_data()
                    if re_email in users:
                        otp = ''.join(random.choices(string.digits, k=6))
                        success, _ = send_otp_email(re_email, otp)
                        if success: st.session_state['reset_otp'] = otp; st.session_state['reset_target_email'] = re_email; st.session_state['reset_mode'] = "sent"; st.rerun()
        with tab_reg:
            with st.form("reg_form"):
                ne, np = st.text_input("メールアドレス"), st.text_input("パスワード", type="password")
                if st.form_submit_button("登録する"):
                    users, sha = get_users_data()
                    if ne not in users:
                        users[ne] = make_pw_hash(np)
                        save_to_github(json.dumps(users, ensure_ascii=False), USERS_FILE, "Reg User", sha); st.rerun()
    st.stop()

# --- 4. メイン ---
st.markdown(f'<div class="auth-header"><span class="user-id">{st.session_state["user_email"]}</span></div>', unsafe_allow_html=True)
if st.button("ログアウト"): st.session_state['authenticated'] = False; st.rerun()
st.markdown('<h1 class="main-title">献だけ</h1>', unsafe_allow_html=True)

def get_menu_data():
    content, sha = get_github_content(FILE)
    if content: return pd.read_csv(io.StringIO(content)), sha
    return None, None

@st.cache_data(ttl=60)
def get_history_data():
    content, sha = get_github_content(HIST_FILE)
    if content:
        df = pd.read_csv(io.StringIO(content))
        if "user" not in df.columns: df["user"] = "unknown"
        return df, sha
    return pd.DataFrame(columns=["日付", "曜日", "料理名", "user"]), None

@st.cache_data(ttl=60)
def get_dict_data():
    try: return pd.read_csv(f"https://raw.githubusercontent.com/{REPO}/main/{DICT_FILE}")
    except: return None

df_menu, menu_sha = get_menu_data()
df_dict = get_dict_data()
df_hist, hist_sha = get_history_data()
draft_content, draft_sha = get_github_content(DRAFT_FILE)
draft_data = json.loads(draft_content) if draft_content and isinstance(draft_content, str) else {}

cats = ["主菜1", "副菜1", "副菜2", "汁物"]
tab_plan, tab_hist, tab_manage = st.tabs(["🗓 献立作成", "📜 履歴", "⚙️ 管理"])

with tab_plan:
    today = datetime.now()
    start_date = st.date_input("開始日", value=today - timedelta(days=(today.weekday() + 1) % 7))
    day_labels = ["日", "月", "火", "水", "木", "金", "土"]
    days_tabs = st.tabs(day_labels)
    weekly_plan = {}
    for i, day_tab in enumerate(days_tabs):
        target_date = start_date + timedelta(days=i)
        d_str = target_date.strftime("%Y/%m/%d")
        with day_tab:
            st.markdown(f"##### {d_str}({day_labels[i]})")
            day_menu = {cat: st.multiselect(cat, df_menu[df_menu["カテゴリー"] == cat]["料理名"].tolist(), key=f"s_{i}_{cat}", default=[v for v in draft_data.get(f"s_{i}_{cat}", []) if v in df_menu["料理名"].tolist()]) for cat in cats}
            weekly_plan[d_str] = {"menu": day_menu, "weekday": day_labels[i], "memo": st.text_input("メモ", key=f"memo_{i}", value=draft_data.get(f"memo_{i}", ""))}

    if st.button("一時保存", use_container_width=True):
        cur_draft = {f"s_{i}_{cat}": st.session_state[f"s_{i}_{cat}"] for i in range(7) for cat in cats}
        for i in range(7): cur_draft[f"memo_{i}"] = st.session_state[f"memo_{i}"]
        save_to_github(json.dumps(cur_draft, ensure_ascii=False), DRAFT_FILE, "Draft Upd", draft_sha); st.toast("保存完了")

    if st.button("確定して買い物リストを生成", type="primary", use_container_width=True):
        all_ings_list, new_history_entries = [], []
        max_menu_cols = max([sum(len(d["menu"].get(c, [])) for c in ["主菜1", "副菜1", "副菜2"]) for d in weekly_plan.values()] + [1])
        h_html = "<tr><th>日付</th>" + "".join([f"<th>メニュー{j+1}</th>" for j in range(max_menu_cols)]) + "<th>汁物</th></tr>"
        r_html = ""
        for d_str, data in weekly_plan.items():
            row = f"<td>{d_str}({data['weekday']})</td>"
            items = []
            for c in ["主菜1", "副菜1", "副菜2"]:
                for dish in data["menu"].get(c, []):
                    items.append(dish)
                    new_history_entries.append({"日付": d_str, "曜日": data["weekday"], "料理名": dish, "user": st.session_state['user_email']})
                    raw_material = str(df_menu[df_menu["料理名"] == dish]["材料"].iloc[0])
                    # 改行や読点、全角スペースなどで確実に分離
                    all_ings_list.extend([x.strip() for x in re.split(r'[、,\n\r\s・/]+', raw_material) if x.strip()])
            for j in range(max_menu_cols): row += f"<td>{items[j] if j < len(items) else '-'}</td>"
            soup = data["menu"].get("汁物", [])
            for s_dish in soup:
                new_history_entries.append({"日付": d_str, "曜日": data["weekday"], "料理名": s_dish, "user": st.session_state['user_email']})
                all_ings_list.extend([x.strip() for x in re.split(r'[、,\n\r\s・/]+', str(df_menu[df_menu["料理名"]==s_dish]["材料"].iloc[0])) if x.strip()])
            row += f"<td>{', '.join(soup) if soup else '-'}</td>"
            r_html += f"<tr>{row}</tr>"
            if data["memo"]: all_ings_list.extend([f"{d_str}メモ: " + x.strip() for x in re.split(r'[、,\n\r\s・/]+', data["memo"]) if x.strip()])
        
        st.session_state["current_rows_html"], st.session_state["current_header_html"] = r_html, h_html
        counts = pd.Series(all_ings_list).value_counts()
        st.session_state["shopping_list_data"] = []
        for i, (item, count) in enumerate(counts.items()):
            cat = "99未分類"
            if "メモ:" in str(item): cat = "📝 各日メモ"
            elif df_dict is not None:
                for _, r in df_dict.iterrows():
                    if str(r["材料"]) in str(item): cat = r["種別"]; break
            st.session_state["shopping_list_data"].append({"id": f"item_{i}", "item": item, "count": int(count), "cat": cat})

    if "shopping_list_data" in st.session_state:
        st.markdown(f'<table class="preview-table">{st.session_state["current_header_html"]}{st.session_state["current_rows_html"]}</table>', unsafe_allow_html=True)
        s_data = st.session_state["shopping_list_data"]
        for c in sorted(list(set(d["cat"] for d in s_data))):
            st.markdown(f"**【{c}】**")
            for item_obj in [d for d in s_data if d["cat"] == c]:
                i_id = item_obj["id"]
                if st.session_state.get(f"del_{i_id}", False): continue
                
                col_chk, col_ed, col_dl = st.columns([7, 1.5, 1.5])
                with col_chk:
                    st.checkbox(f"{item_obj['item']} ({item_obj['count']})", key=f"chk_{i_id}")
                with col_ed:
                    if st.button("📝", key=f"btn_ed_{i_id}"): st.session_state[f"edit_{i_id}"] = True
                with col_dl:
                    if st.button("🗑️", key=f"btn_dl_{i_id}"): st.session_state[f"del_{i_id}"] = True; st.rerun()
                
                if st.session_state.get(f"edit_{i_id}", False):
                    new_val = st.text_input("材料名を修正", value=item_obj["item"], key=f"inp_{i_id}")
                    if st.button("確定", key=f"save_{i_id}"):
                        for d in st.session_state["shopping_list_data"]:
                            if d["id"] == i_id: d["item"] = new_val; break
                        st.session_state[f"edit_{i_id}"] = False; st.rerun()

        # 印刷用
        active = [d for d in st.session_state["shopping_list_data"] if not st.session_state.get(f"del_{d['id']}", False)]
        cards = "".join([f'<div style="border:1px solid #ccc;padding:5px;width:45%;break-inside:avoid;"><h3>{cat}</h3>' + "".join([f'<div>□ {r["item"]} ({r["count"]})</div>' for r in active if r["cat"]==cat]) + '</div>' for cat in sorted(list(set(d["cat"] for d in active)))])
        b64 = base64.b64encode(f"<html><body><h2>献立</h2><table>{st.session_state['current_header_html']}{st.session_state['current_rows_html']}</table><h2>リスト</h2><div style='display:flex;flex-wrap:wrap;gap:10px;'>{cards}</div></body></html>".encode('utf-8')).decode('utf-8')
        components.html(f'<button id="pb" style="width:100%;background:#262730;color:white;padding:12px;border:none;border-radius:8px;">A4印刷</button><script>document.getElementById("pb").onclick=function(){{var w=window.open();w.document.write(atob("{b64}"));w.document.close();w.print();}};</script>', height=60)

with tab_hist:
    u_hist = df_hist[df_hist["user"] == st.session_state['user_email']]
    if not u_hist.empty:
        disp = u_hist.copy().sort_values(["日付", "料理名"], ascending=[False, True])
        st.dataframe(disp.drop(columns=["user"]), use_container_width=True, hide_index=True)

with tab_manage:
    with st.form("add_menu"):
        an, ac, am = st.text_input("料理名"), st.selectbox("カテゴリ", ["主菜1", "主菜2", "副菜1", "副菜2", "汁物"]), st.text_area("材料")
        if st.form_submit_button("追加"):
            if an and am:
                save_to_github(pd.concat([df_menu, pd.DataFrame([[an, ac, am]], columns=df_menu.columns)]).to_csv(index=False, encoding="utf-8-sig"), FILE, f"Add: {an}", menu_sha); st.cache_data.clear(); st.rerun()
    st.markdown(f'<div style="text-align:right;color:#ddd;font-size:0.6rem;">v{VERSION}</div>', unsafe_allow_html=True)
