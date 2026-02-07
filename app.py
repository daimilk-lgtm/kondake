import streamlit as st
import pandas as pd
import requests
import base64
import io
import streamlit.components.v1 as components
from datetime import datetime, timedelta
import hashlib
import re

# --- 1. 接続設定 ---
REPO = "daimilk-lgtm/kondake"
FILE = "menu.csv"
DICT_FILE = "ingredients.csv"
HIST_FILE = "history.csv"
USER_FILE = "users.csv"
TOKEN = st.secrets.get("GITHUB_TOKEN")

# --- 2. デザイン定義 (仕様死守：左上のノイズ排除) ---
st.set_page_config(page_title="献だけ", layout="centered", initial_sidebar_state="collapsed")
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Noto+Sans+JP:wght@100;300;400&display=swap');
    html, body, [class*="css"], p, div, select, input, label, span {
        font-family: 'Noto Sans JP', sans-serif !important;
        font-weight: 300 !important;
    }
    .main-title { font-weight: 100 !important; font-size: 3rem; text-align: center; margin: 40px 0; letter-spacing: 0.5rem; }
    /* 左上の文字化けを物理的に消去 */
    header[data-testid="stHeader"], section[data-testid="stSidebar"], button[data-testid="stSidebarCollapseButton"] {
        display: none !important;
    }
    .block-container { padding-top: 1rem !important; }
</style>
""", unsafe_allow_html=True)

# --- 3. 認証・GitHub通信関数 ---
def make_hash(password):
    return hashlib.sha256(str.encode(password)).hexdigest()

def is_valid_email(email):
    return re.match(r"[^@]+@[^@]+\.[^@]+", email)

def is_strong_password(pwd):
    return len(pwd) >= 8 and any(c.isalpha() for c in pwd) and any(c.isdigit() for c in pwd)

def get_github_file(filename):
    try:
        url = f"https://api.github.com/repos/{REPO}/contents/{filename}"
        headers = {"Authorization": f"token {TOKEN}", "Accept": "application/vnd.github.v3+json"}
        r = requests.get(url, headers=headers)
        if r.status_code == 200:
            raw = base64.b64decode(r.json()["content"]).decode("utf-8-sig")
            df = pd.read_csv(io.StringIO(raw))
            # GitHub上の列名が email の場合、プログラム内の username に読み替え
            if filename == USER_FILE:
                df = df.rename(columns={"email": "username"})
            return df, r.json()["sha"]
    except: pass
    return pd.DataFrame(columns=["username", "password"]), None

def save_to_github(df, filename, message, current_sha=None):
    # 保存時は元のヘッダー email に戻して保存
    save_df = df.rename(columns={"username": "email"}) if filename == USER_FILE else df
    csv_content = save_df.to_csv(index=False, encoding="utf-8-sig")
    content_b64 = base64.b64encode(csv_content.encode("utf-8")).decode("utf-8")
    url = f"https://api.github.com/repos/{REPO}/contents/{filename}"
    headers = {"Authorization": f"token {TOKEN}", "Accept": "application/vnd.github.v3+json"}
    data = {"message": message, "content": content_b64}
    if current_sha: data["sha"] = current_sha
    res = requests.put(url, headers=headers, json=data)
    return res.status_code

# --- 4. 認証フロー ---
if "authenticated" not in st.session_state:
    st.session_state["authenticated"] = False

if not st.session_state["authenticated"]:
    st.markdown('<h1 class="main-title">献だけ</h1>', unsafe_allow_html=True)
    auth_tab1, auth_tab2 = st.tabs(["ログイン", "新規ユーザー登録"])
    df_users, user_sha = get_github_file(USER_FILE)

    with auth_tab1:
        with st.form("login_form"):
            u_login = st.text_input("メールアドレス")
            p_login = st.text_input("パスワード", type="password")
            if st.form_submit_button("ログイン", use_container_width=True):
                h_pwd = make_hash(p_login)
                if not df_users.empty and "username" in df_users.columns:
                    match = df_users[(df_users["username"] == u_login) & (df_users["password"] == h_pwd)]
                    if not match.empty:
                        st.session_state["authenticated"] = True
                        st.session_state["username"] = u_login
                        st.rerun()
                st.error("ログイン失敗。アドレスまたはパスワードを確認してください")

    with auth_tab2:
        with st.form("reg_form"):
            u_reg = st.text_input("メールアドレス")
            p_reg = st.text_input("パスワード (8文字以上の英数字)", type="password")
            if st.form_submit_button("登録実行", use_container_width=True):
                if not is_valid_email(u_reg):
                    st.error("正しいメールアドレスの形式で入力してください")
                elif not is_strong_password(p_reg):
                    st.error("パスワードは8文字以上、かつ英数字を組み合わせてください")
                elif not df_users.empty and u_reg in df_users["username"].values:
                    st.warning("このメールアドレスは既に登録されています")
                else:
                    new_user = pd.DataFrame([[u_reg, make_hash(p_reg)]], columns=["username", "password"])
                    updated_users = pd.concat([df_users, new_user], ignore_index=True)
                    save_to_github(updated_users, USER_FILE, f"Add {u_reg}", user_sha)
                    st.success("登録完了！ログインしてください")
    st.stop()

# --- 5. メインアプリ (仕様: 日付入力・日曜スタート) ---
col_title, col_logout = st.columns([0.8, 0.2])
with col_logout:
    if st.button("ログアウト"):
        st.session_state["authenticated"] = False
        st.rerun()

st.markdown('<h1 class="main-title">献だけ</h1>', unsafe_allow_html=True)

df_menu, menu_sha = get_github_file(FILE)
df_dict, _ = get_github_file(DICT_FILE)

if df_menu.empty:
    st.error("メニューデータが見つかりません。")
    st.stop()

cats = ["主菜1", "主菜2", "副菜1", "副菜2", "汁物"]
tab_plan, tab_hist, tab_manage = st.tabs(["🗓 献立作成", "📜 履歴", "⚙️ メニュー管理"])

with tab_plan:
    today = datetime.now()
    offset = (today.weekday() + 1) % 7
    default_sun = today - timedelta(days=offset)
    start_date = st.date_input("開始日（日）", value=default_sun)
    
    day_labels = ["日", "月", "火", "水", "木", "金", "土"]
    days_tabs = st.tabs([f"{day_labels[i]}" for i in range(7)])
    
    weekly_plan = {}
    for i, day_tab in enumerate(days_tabs):
        target_date = start_date + timedelta(days=i)
        d_str = target_date.strftime("%Y/%m/%d")
        with day_tab:
            st.markdown(f"##### {d_str} ({day_labels[i]})")
            day_menu = {cat: st.selectbox(cat, ["なし"] + df_menu[df_menu["カテゴリー"] == cat]["料理名"].tolist(), key=f"s_{i}_{cat}") for cat in cats}
            weekly_plan[d_str] = {"menu": day_menu, "weekday": day_labels[i]}
    
    if st.button("確定して買い物リストを生成", type="primary", use_container_width=True):
        st.success("買い物リストを生成しました")
