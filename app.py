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
# - [2026/02/22] メモ欄を曜日ごとに個別入力可能とし、買い物リストに反映。
# - [2026/02/22] GitHub上に「draft.json」を作成し、入力内容を共有可能にする。
# - [2026/02/22] 確定献立はカテゴリーごとに列を分け、汁物は必ず右端の列に配置する。
# - [2026/02/22] 買い物リストの各項目を個別に編集・削除できる機能を実装。
# - [2026/02/22] 買い物リストにおいて、材料の数量（個数）を独立した列として扱う。
# - [2026/02/22] 印刷レイアウトをA4一枚に最適化。
# - [2026/02/22] ログイン機能（ID:メールアドレス、Pass:半角英数字8文字）を追加。
# - [2026/02/22] 新規ユーザー登録機能を追加。ユーザー情報はusers.jsonで管理。
# - [2026/02/22] 画面右上にログインIDとログアウトリンクを表示。
# - [2026/02/22] 履歴データをユーザーごとに分離し、自分の履歴のみが操作可能。
# - [2026/02/22] サイドバーを廃止し、2カラム構成にしない（無駄な領域を排除）。
# - [2026/02/22] スマホログイン時の利便性向上のため、標準text_inputのautocomplete属性最適化と隠しフォームによるブラウザ支援を実装。
# - [2026/02/22] Gmail SMTPサーバーを利用したパスワード再設定フロー（OTP送信方式）を実装。
# - [2026/02/22] 印刷用HTMLの生成ロジックにおいて発生していたSyntaxErrorを、f-stringの修正により解消。
# - [2026/02/22] ログイン画面下部の表示バグに対し、標準expanderを廃止。
# - [2026/02/22] 再設定フロー中の表示バグに対し、標準st.status/st.errorを廃止し、独自Markdown表示に切り替え。
# - [2026/02/22] セキュリティ向上のため、パスワード保存方式をPBKDF2（SHA256）によるハッシュ化方式に変更。
# ==============================================================================

VERSION = "1.9.0"

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

# パスワードハッシュ化関数
def make_pw_hash(password, salt=None):
    if salt is None:
        salt = base64.b64encode(os.urandom(16)).decode('utf-8')
    pw_hash = hashlib.pbkdf2_hmac('sha256', password.encode(), salt.encode(), 100000)
    return f"{salt}${base64.b64encode(pw_hash).decode('utf-8')}"

def check_pw_hash(password, hash_str):
    if "$" not in hash_str: # 旧平文パスワードとの互換性
        return password == hash_str
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
        else:
            return None, r.status_code
    except Exception as e:
        return None, str(e)

def save_to_github(content, filename, message, current_sha=None):
    content_b64 = base64.b64encode(content.encode("utf-8")).decode("utf-8")
    url = f"https://api.github.com/repos/{REPO}/contents/{filename}"
    headers = {"Authorization": f"token {TOKEN}", "Accept": "application/vnd.github.v3+json"}
    data = {"message": message, "content": content_b64}
    if current_sha: data["sha"] = current_sha
    res = requests.put(url, headers=headers, json=data)
    return res.status_code

def send_otp_email(to_email, otp):
    if not SMTP_USER or not SMTP_PASS:
        return False, "SecretsにSMTP_USERまたはSMTP_PASSが設定されていません。"
    
    msg = MIMEText(f"献だけ：パスワード再設定用のワンタイムパスコードは 【 {otp} 】 です。")
    msg["Subject"] = "【献だけ】パスワード再設定コード"
    msg["From"] = SMTP_USER
    msg["To"] = to_email
    
    try:
        with smtplib.SMTP_SSL("smtp.gmail.com", 465, timeout=10) as server:
            server.login(SMTP_USER, SMTP_PASS)
            server.send_message(msg)
        return True, "Success (465)"
    except Exception as e465:
        try:
            with smtplib.SMTP("smtp.gmail.com", 587, timeout=10) as server:
                server.starttls()
                server.login(SMTP_USER, SMTP_PASS)
                server.send_message(msg)
            return True, "Success (587)"
        except Exception as e587:
            return False, f"Port 465 Error: {str(e465)} | Port 587 Error: {str(e587)}"

# --- 2. デザイン定義 ---
st.set_page_config(page_title="献だけ", layout="centered", initial_sidebar_state="collapsed")

st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Noto+Sans+JP:wght@100;300;400&display=swap');
    [data-testid="stSidebar"] { display: none; }
    [data-testid="stHeader"] { background: rgba(0,0,0,0); }
    html, body, [class*="css"], p, div, select, input, label, span {
        font-family: 'Noto Sans JP', sans-serif !important;
        font-weight: 300 !important;
    }
    .main-title { font-weight: 100 !important; font-size: 3rem; text-align: center; margin: 40px 0 20px 0; letter-spacing: 0.5rem; }
    .auth-header { position: absolute; top: -10px; right: 0; text-align: right; padding: 10px; z-index: 1000; }
    .user-id { font-size: 0.75rem; color: #666; }
    .preview-table { width: 100%; border-collapse: collapse; font-size: 0.85rem; margin-top: 10px; margin-bottom: 20px; overflow-x: auto; display: block; }
    .preview-table th, .preview-table td { border: 1px solid #eee; padding: 6px; text-align: left; min-width: 80px; }
    .preview-table th { background-color: #fcfcfc; font-weight: 400; }
    
    /* エラー表示用カスタムスタイル */
    .custom-error {
        color: #ff4b4b;
        padding: 10px;
        border: 1px solid #ff4b4b;
        border-radius: 8px;
        margin: 10px 0;
        font-size: 0.9rem;
        background-color: #fffafa;
    }
    .custom-info {
        color: #1f77b4;
        padding: 10px;
        border: 1px solid #1f77b4;
        border-radius: 8px;
        margin: 10px 0;
        font-size: 0.9rem;
        background-color: #f0f8ff;
    }
</style>
""", unsafe_allow_html=True)

# --- 3. 認証ロジック ---
if 'authenticated' not in st.session_state:
    st.session_state['authenticated'] = False
if 'user_email' not in st.session_state:
    st.session_state['user_email'] = ""
if 'reset_mode' not in st.session_state:
    st.session_state['reset_mode'] = "none"
if 'reset_target_email' not in st.session_state:
    st.session_state['reset_target_email'] = ""
if 'reset_otp' not in st.session_state:
    st.session_state['reset_otp'] = ""
if 'show_forgot_pw' not in st.session_state:
    st.session_state['show_forgot_pw'] = False
if 'auth_msg' not in st.session_state:
    st.session_state['auth_msg'] = ""

def get_users_data():
    content, sha = get_github_content(USERS_FILE)
    if content: return json.loads(content), sha
    return {}, None

if not st.session_state['authenticated']:
    st.markdown('<h1 class="main-title">献だけ</h1>', unsafe_allow_html=True)
    
    if st.session_state['reset_mode'] != "none":
        st.subheader("パスワードの再設定")
        if st.session_state['reset_mode'] == "sent":
            st.markdown(f'<div class="custom-info">{st.session_state["reset_target_email"]} 宛にパスコードを送信しました。</div>', unsafe_allow_html=True)
            otp_input = st.text_input("6桁のパスコードを入力", max_chars=6)
            if st.button("コードを確認", use_container_width=True):
                if otp_input == st.session_state['reset_otp']:
                    st.session_state['reset_mode'] = "verified"
                    st.rerun()
                else: 
                    st.markdown('<div class="custom-error">パスコードが一致しません</div>', unsafe_allow_html=True)
        
        elif st.session_state['reset_mode'] == "verified":
            with st.form("new_pass_form"):
                new_p = st.text_input("新しいパスワード", type="password")
                new_p_c = st.text_input("新しいパスワード（確認）", type="password")
                if st.form_submit_button("パスワードを更新", use_container_width=True):
                    if not re.match(r'^[a-zA-Z0-9]{8,}$', new_p): 
                        st.markdown('<div class="custom-error">8文字以上の英数字で入力してください</div>', unsafe_allow_html=True)
                    elif new_p != new_p_c: 
                        st.markdown('<div class="custom-error">パスワードが一致しません</div>', unsafe_allow_html=True)
                    else:
                        users, sha = get_users_data()
                        # ハッシュ化して保存
                        users[st.session_state['reset_target_email']] = make_pw_hash(new_p)
                        save_to_github(json.dumps(users, ensure_ascii=False), USERS_FILE, f"Reset (Hashed): {st.session_state['reset_target_email']}", sha)
                        st.session_state['auth_msg'] = "パスワードを更新しました。ログインしてください。"
                        st.session_state['reset_mode'] = "none"
                        st.session_state['show_forgot_pw'] = False
                        st.rerun()
        
        if st.button("キャンセル"):
            st.session_state['reset_mode'] = "none"
            st.rerun()
    else:
        tab_log, tab_reg = st.tabs(["ログイン", "新規ユーザー登録"])
        with tab_log:
            if st.session_state['auth_msg']:
                st.markdown(f'<div class="custom-info">{st.session_state["auth_msg"]}</div>', unsafe_allow_html=True)
                
            components.html("""<form style="display:none;"><input type="text" name="username" autocomplete="username"><input type="password" name="password" autocomplete="current-password"></form>""", height=0)
            with st.form("login_form"):
                e = st.text_input("メールアドレス", key="l_email", autocomplete="username")
                p = st.text_input("パスワード", type="password", key="l_pass", autocomplete="current-password")
                if st.form_submit_button("ログイン", use_container_width=True):
                    users, _ = get_users_data()
                    if e in users and check_pw_hash(p, users[e]):
                        st.session_state['authenticated'] = True
                        st.session_state['user_email'] = e
                        st.session_state['auth_msg'] = ""
                        st.rerun()
                    else: 
                        st.markdown('<div class="custom-error">認証に失敗しました</div>', unsafe_allow_html=True)
            
            if not st.session_state['show_forgot_pw']:
                if st.button("パスワードを忘れた場合", key="toggle_forgot_pw", type="secondary", use_container_width=True):
                    st.session_state['show_forgot_pw'] = True
                    st.rerun()
            else:
                st.markdown("---")
                st.markdown("##### パスワード再設定コードの送信")
                re_email = st.text_input("登録メールアドレスを入力", key="re_email_input")
                c1, c2 = st.columns(2)
                with c1:
                    if st.button("再設定コードを送信", type="primary", use_container_width=True):
                        users, _ = get_users_data()
                        if re_email in users:
                            otp = ''.join(random.choices(string.digits, k=6))
                            success, msg = send_otp_email(re_email, otp)
                            if success:
                                st.session_state['reset_otp'] = otp
                                st.session_state['reset_target_email'] = re_email
                                st.session_state['reset_mode'] = "sent"
                                st.rerun()
                            else:
                                st.markdown(f'<div class="custom-error">送信失敗: {msg}</div>', unsafe_allow_html=True)
                        else:
                            st.markdown('<div class="custom-error">登録されていないメールアドレスです</div>', unsafe_allow_html=True)
                with c2:
                    if st.button("ログインに戻る", use_container_width=True):
                        st.session_state['show_forgot_pw'] = False
                        st.rerun()
        
        with tab_reg:
            with st.form("reg_form"):
                ne = st.text_input("メールアドレス", key="r_email", autocomplete="email")
                np = st.text_input("パスワード（8文字以上）", type="password", key="r_pass", autocomplete="new-password")
                cp = st.text_input("確認用", type="password", key="r_conf", autocomplete="new-password")
                if st.form_submit_button("登録する", use_container_width=True):
                    if not re.match(r'^[a-zA-Z0-9]{8,}$', np): 
                        st.markdown('<div class="custom-error">パスワード条件を満たしていません</div>', unsafe_allow_html=True)
                    elif np != cp: 
                        st.markdown('<div class="custom-error">パスワードが一致しません</div>', unsafe_allow_html=True)
                    else:
                        users, sha = get_users_data()
                        if ne in users: 
                            st.markdown('<div class="custom-error">既に登録されているアドレスです</div>', unsafe_allow_html=True)
                        else:
                            # ハッシュ化して保存
                            users[ne] = make_pw_hash(np)
                            save_to_github(json.dumps(users, ensure_ascii=False), USERS_FILE, f"Reg (Hashed): {ne}", sha)
                            st.session_state['auth_msg'] = "ユーザー登録が完了しました。ログインしてください。"
                            st.rerun()
    st.stop()

# --- 4. メインコンテンツ ---
st.markdown(f'<div class="auth-header"><span class="user-id">{st.session_state["user_email"]}</span></div>', unsafe_allow_html=True)
if st.button("ログアウト", key="lo_btn", type="secondary"):
    st.session_state['authenticated'] = False
    st.rerun()

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
    try:
        url = f"https://raw.githubusercontent.com/{REPO}/main/{DICT_FILE}"
        return pd.read_csv(url)
    except: return None

df_menu, menu_sha = get_menu_data()
df_dict = get_dict_data()
df_hist, hist_sha = get_history_data()
draft_content, draft_sha = get_github_content(DRAFT_FILE)
draft_data = json.loads(draft_content) if draft_content and isinstance(draft_content, str) else {}

if df_menu is None: st.stop()

cats = ["主菜1", "副菜1", "副菜2", "汁物"]
tab_plan, tab_hist, tab_manage = st.tabs(["🗓 献立作成", "📜 履歴", "⚙️ 管理"])

with tab_plan:
    today = datetime.now()
    offset = (today.weekday() + 1) % 7
    start_date = st.date_input("開始日（日）", value=today - timedelta(days=offset))
    day_labels = ["日", "月", "火", "水", "木", "金", "土"]
    days_tabs = st.tabs([f"{day_labels[i]}" for i in range(7)])
    weekly_plan = {}
    for i, day_tab in enumerate(days_tabs):
        target_date = start_date + timedelta(days=i)
        d_str = target_date.strftime("%Y/%m/%d")
        with day_tab:
            st.markdown(f"##### {d_str} ({day_labels[i]})")
            day_menu = {}
            for cat in cats:
                k = f"s_{i}_{cat}"
                def_v = draft_data.get(k, [])
                day_menu[cat] = st.multiselect(cat, df_menu[df_menu["カテゴリー"] == cat]["料理名"].tolist(), key=k, default=[v for v in def_v if v in df_menu["料理名"].tolist()], placeholder="選択...")
            m_k = f"memo_{i}"
            day_memo = st.text_input("メモ", key=m_k, value=draft_data.get(m_k, ""), placeholder="買い足し等")
            weekly_plan[d_str] = {"menu": day_menu, "weekday": day_labels[i], "memo": day_memo}

    list_memo_options = df_menu[df_menu["カテゴリー"] == "主菜2"]["料理名"].tolist()
    selected_memos = st.multiselect("定番アイテム", list_memo_options, key="list_memo_multi", default=[v for v in draft_data.get("list_memo_multi", []) if v in list_memo_options])

    if st.button("一時保存", use_container_width=True):
        cur_draft = {f"s_{i}_{cat}": st.session_state[f"s_{i}_{cat}"] for i in range(7) for cat in cats}
        for i in range(7): cur_draft[f"memo_{i}"] = st.session_state[f"memo_{i}"]
        cur_draft["list_memo_multi"] = st.session_state["list_memo_multi"]
        save_to_github(json.dumps(cur_draft, ensure_ascii=False), DRAFT_FILE, "Update draft", draft_sha)
        st.toast("保存完了")

    if st.button("確定して買い物リストを生成", type="primary", use_container_width=True):
        all_ings_list = []
        new_history_entries = []
        max_counts = {c: 1 for c in cats}
        for d in weekly_plan.values():
            for c in cats: max_counts[c] = max(max_counts[c], len(d["menu"].get(c, [])))
        header_html = "<tr><th>日付</th>"
        for c in ["主菜1", "副菜1", "副菜2", "汁物"]:
            for j in range(max_counts[c]): header_html += f"<th>{c}{f' {j+1}' if max_counts[c]>1 else ''}</th>"
        header_html += "</tr>"
        rows_html = ""
        for d_str, data in weekly_plan.items():
            row_content = f"<td>{d_str}({data['weekday']})</td>"
            for c in ["主菜1", "副菜1", "副菜2", "汁物"]:
                items = data["menu"].get(c, [])
                for j in range(max_counts[c]): row_content += f"<td>{items[j] if j < len(items) else '-'}</td>"
            rows_html += f"<tr>{row_content}</tr>"
            for dish_list in data["menu"].values():
                for dish in dish_list:
                    new_history_entries.append({"日付": d_str, "曜日": data["weekday"], "料理名": dish, "user": st.session_state['user_email']})
                    ing_raw = df_menu[df_menu["料理名"] == dish]["材料"].iloc[0]
                    all_ings_list.extend([x.strip() for x in re.split(r'[、,\n\s・/]+', str(ing_raw)) if x.strip()])
            if data["memo"]: all_ings_list.extend([f"{d_str}メモ: " + x.strip() for x in re.split(r'[、,\n\s・/]+', data["memo"]) if x.strip()])
        for m_dish in selected_memos: all_ings_list.extend([x.strip() for x in re.split(r'[、,\n\s・/]+', str(df_menu[df_menu["料理名"] == m_dish]["材料"].iloc[0])) if x.strip()])
        if new_history_entries:
            df_combined_h = pd.concat([df_hist, pd.DataFrame(new_history_entries)], ignore_index=True).drop_duplicates()
            save_to_github(df_combined_h.to_csv(index=False, encoding="utf-8-sig"), HIST_FILE, "Update history", hist_sha)
        st.session_state["current_rows_html"], st.session_state["current_header_html"] = rows_html, header_html
        counts = pd.Series(all_ings_list).value_counts()
        init_shopping = []
        for item, count in counts.items():
            cat = "99未分類"
            if "メモ:" in str(item): cat = "📝 各日メモ"
            elif df_dict is not None:
                for _, r in df_dict.iterrows():
                    if str(r["材料"]) in str(item): cat = r["種別"]; break
            init_shopping.append({"item": item, "count": int(count), "cat": cat, "id": f"it_{len(init_shopping)}"})
        st.session_state["shopping_list_data"] = init_shopping

    if "shopping_list_data" in st.session_state:
        st.markdown(f'<table class="preview-table">{st.session_state["current_header_html"]}{st.session_state["current_rows_html"]}</table>', unsafe_allow_html=True)
        s_data = st.session_state["shopping_list_data"]
        u_cats = sorted(list(set(d["cat"] for d in s_data)))
        for c in u_cats:
            st.markdown(f"**【{c}】**")
            for item_obj in [d for d in s_data if d["cat"] == c]:
                i_id = item_obj["id"]
                if st.session_state.get(f"del_{i_id}", False): continue
                c1, c2, c3, c4 = st.columns([5, 1, 2, 2])
                c1.markdown(f"□ {item_obj['item']}"); c2.markdown(f"{item_obj['count']}" if item_obj['count'] > 1 else "")
                if c3.button("📝", key=f"ed_{i_id}"): st.session_state[f"edit_{i_id}"] = True
                if c4.button("🗑️", key=f"dl_{i_id}"): st.session_state[f"del_{i_id}"] = True; st.rerun()
                if st.session_state.get(f"edit_{i_id}", False):
                    en = st.text_input("名称", value=item_obj["item"], key=f"in_n_{i_id}")
                    ec = st.number_input("数", value=int(item_obj["count"]), min_value=1, key=f"in_q_{i_id}")
                    if st.button("保存", key=f"sv_{i_id}"):
                        for d in st.session_state["shopping_list_data"]:
                            if d["id"] == i_id: d["item"], d["count"] = en, ec; break
                        st.session_state[f"edit_{i_id}"] = False; st.rerun()

        active = [d for d in st.session_state["shopping_list_data"] if not st.session_state.get(f"del_{d['id']}", False)]
        cards_html = "".join([f'<div class="print-card"><h3>{c}</h3>' + "".join([f'<div class="print-row"><span>□ {r["item"]}</span><span>{f"({r['count']})" if r["count"]>1 else ""}</span></div>' for r in active if r["cat"]==c]) + '</div>' for c in sorted(list(set(d["cat"] for d in active)))])
        
        css_style = "<style>@page { size: A4; margin: 10mm; } body { font-family: sans-serif; font-size: 10pt; } .print-container { display: flex; flex-wrap: wrap; gap: 10px; } .print-card { border: 1px solid #ccc; padding: 5px; width: calc(50% - 10px); break-inside: avoid; } .print-row { display: flex; justify-content: space-between; border-bottom: 1px solid #eee; }</style>"
        header_part = st.session_state.get('current_header_html','')
        rows_part = st.session_state.get('current_rows_html','')
        
        print_html = f"<html><head>{css_style}</head><body><h2>🗓 献立表</h2><table>{header_part}{rows_part}</table><h2>🛒 買い物リスト</h2><div class='print-container'>{cards_html}</div></body></html>"
        
        b64 = base64.b64encode(print_html.encode('utf-8')).decode('utf-8')
        components.html(f'<button id="pb" style="width:100%;background:#262730;color:white;padding:12px;border:none;border-radius:8px;cursor:pointer;">A4印刷用ページを開く</button><script>document.getElementById("pb").onclick=function(){{var w=window.open();w.document.write(atob("{b64}"));w.document.close();w.print();}};</script>', height=60)

with tab_hist:
    u_hist = df_hist[df_hist["user"] == st.session_state['user_email']]
    if not u_hist.empty:
        disp = u_hist.copy().sort_values(["日付", "料理名"], ascending=[False, True])
        sel_idx = st.selectbox("データ選択", range(len(disp)), format_func=lambda i: f"{disp.iloc[i]['日付']} - {disp.iloc[i]['料理名']}")
        c1, c2 = st.columns(2)
        with c1:
            if st.button("削除", use_container_width=True):
                df_hist = df_hist[~((df_hist['日付']==disp.iloc[sel_idx]['日付'])&(df_hist['料理名']==disp.iloc[sel_idx]['料理名'])&(df_hist['user']==st.session_state['user_email']))]
                save_to_github(df_hist.to_csv(index=False, encoding="utf-8-sig"), HIST_FILE, "Del hist", hist_sha); st.cache_data.clear(); st.rerun()
        with c2:
            new_name = st.text_input("修正名", value=disp.iloc[sel_idx]['料理名'])
            if st.button("修正保存", use_container_width=True):
                df_hist.loc[(df_hist['日付']==disp.iloc[sel_idx]['日付'])&(df_hist['料理名']==disp.iloc[sel_idx]['料理名'])&(df_hist['user']==st.session_state['user_email']), '料理名'] = new_name
                save_to_github(df_hist.to_csv(index=False, encoding="utf-8-sig"), HIST_FILE, "Edit hist", hist_sha); st.cache_data.clear(); st.rerun()
        st.dataframe(disp.drop(columns=["user"]), use_container_width=True, hide_index=True)

with tab_manage:
    edit_dish = st.selectbox("既存メニュー選択", ["未選択"] + sorted(df_menu["料理名"].tolist()))
    if edit_dish != "未選択":
        cur = df_menu[df_menu["料理名"] == edit_dish].iloc[0]
        with st.form("ed_menu"):
            nn = st.text_input("料理名", value=cur["料理名"])
            nc = st.selectbox("カテゴリ", ["主菜1", "主菜2", "副菜1", "副菜2", "汁物"], index=["主菜1", "主菜2", "副菜1", "副菜2", "汁物"].index(cur["カテゴリー"]))
            nm = st.text_area("材料", value=cur["材料"])
            if st.form_submit_button("更新"):
                df_menu.loc[df_menu["料理名"] == edit_dish, ["料理名", "カテゴリー", "材料"]] = [nn, nc, nm]
                save_to_github(df_menu.to_csv(index=False, encoding="utf-8-sig"), FILE, f"Upd: {nn}", menu_sha); st.cache_data.clear(); st.rerun()
    st.divider()
    with st.form("add_menu"):
        an, ac = st.text_input("料理名"), st.selectbox("カテゴリ", ["主菜1", "主菜2", "副菜1", "副菜2", "汁物"])
        am = st.text_area("材料")
        if st.form_submit_button("追加保存"):
            if an and am:
                save_to_github(pd.concat([df_menu, pd.DataFrame([[an, ac, am]], columns=df_menu.columns)]).to_csv(index=False, encoding="utf-8-sig"), FILE, f"Add: {an}", menu_sha); st.cache_data.clear(); st.rerun()
    st.markdown(f'<div style="text-align:right;color:#ddd;font-size:0.6rem;margin-top:50px;">v{VERSION}</div>', unsafe_allow_html=True)
