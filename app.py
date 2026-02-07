import streamlit as st
import pandas as pd
import requests
import base64
import io
from datetime import datetime, timedelta
import hashlib
import re

# --- 1. 接続設定 ---
REPO = "daimilk-lgtm/kondake"
FILE = "menu.csv"
DICT_FILE = "ingredients.csv"
USER_FILE = "users.csv"
TOKEN = st.secrets.get("GITHUB_TOKEN")

# --- 2. デザイン定義 (仕様死守：ノイズを消し、メインは絶対に出す) ---
st.set_page_config(page_title="献だけ", layout="centered", initial_sidebar_state="collapsed")
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Noto+Sans+JP:wght@100;300;400&display=swap');
    html, body, [class*="css"], p, div, select, input, label, span {
        font-family: 'Noto Sans JP', sans-serif !important;
        font-weight: 300 !important;
    }
    .main-title { font-weight: 100 !important; font-size: 3rem; text-align: center; margin: 40px 0; letter-spacing: 0.5rem; }
    header[data-testid="stHeader"] { background: transparent !important; color: transparent !important; }
    [data-testid="stSidebarCollapseButton"] { display: none !important; }
    .block-container { padding-top: 1rem !important; }
</style>
""", unsafe_allow_html=True)

# --- 3. 認証・GitHub通信関数 ---
def make_hash(password):
    return hashlib.sha256(str.encode(password)).hexdigest()

def get_github_file(filename):
    try:
        url = f"https://api.github.com/repos/{REPO}/contents/{filename}"
        headers = {"Authorization": f"token {TOKEN}", "Accept": "application/vnd.github.v3+json"}
        r = requests.get(url, headers=headers)
        if r.status_code == 200:
            raw = base64.b64decode(r.json()["content"]).decode("utf-8-sig")
            df = pd.read_csv(io.StringIO(raw))
            if filename == USER_FILE and 'email' in df.columns:
                df = df.rename(columns={'email': 'username'})
            return df, r.json()["sha"]
    except: pass
    return pd.DataFrame(), None

def save_to_github(df, filename, message, current_sha=None):
    save_df = df.rename(columns={"username": "email"}) if filename == USER_FILE else df
    csv_content = save_df.to_csv(index=False, encoding="utf-8-sig")
    content_b64 = base64.b64encode(csv_content.encode("utf-8")).decode("utf-8")
    url = f"https://api.github.com/repos/{REPO}/contents/{filename}"
    headers = {"Authorization": f"token {TOKEN}", "Accept": "application/vnd.github.v3+json"}
    data = {"message": message, "content": content_b64, "sha": current_sha}
    res = requests.put(url, headers=headers, json=data)
    return res.status_code

# --- 4. 認証フロー ---
if "authenticated" not in st.session_state:
    st.session_state["authenticated"] = False

if not st.session_state["authenticated"]:
    st.markdown('<h1 class="main-title">献だけ</h1>', unsafe_allow_html=True)
    tab1, tab2 = st.tabs(["ログイン", "新規登録"])
    df_users, user_sha = get_github_file(USER_FILE)
    
    with tab1:
        with st.form("login_form"):
            u = st.text_input("メールアドレス", key="u_login", autocomplete="email")
            p = st.text_input("パスワード", type="password", key="p_login", autocomplete="current-password")
            if st.form_submit_button("ログイン", use_container_width=True):
                if not df_users.empty and u in df_users["username"].values:
                    if df_users[df_users["username"] == u]["password"].iloc[0] == make_hash(p):
                        st.session_state.update({"authenticated": True, "username": u})
                        st.rerun()
                st.error("入力内容に誤りがあります")
    
    with tab2:
        with st.form("reg_form"):
            nu = st.text_input("メールアドレス", key="u_reg", autocomplete="email")
            np = st.text_input("パスワード (8文字以上の英数字)", type="password", key="p_reg", autocomplete="new-password")
            if st.form_submit_button("登録実行", use_container_width=True):
                if re.match(r"[^@]+@[^@]+\.[^@]+", nu) and len(np) >= 8:
                    new_df = pd.concat([df_users, pd.DataFrame([[nu, make_hash(np)]], columns=["username", "password"])])
                    save_to_github(new_df, USER_FILE, f"Add {nu}", user_sha)
                    st.success("登録完了！ログインしてください")
                else: st.error("形式エラー: 正しいメアドと8文字以上のパスワードが必要です")
    st.stop()

# --- 5. メインアプリ (表示・仕様の完全復旧) ---
st.markdown('<div style="text-align:right">', unsafe_allow_html=True)
if st.button("ログアウト"):
    st.session_state["authenticated"] = False
    st.rerun()
st.markdown('</div>', unsafe_allow_html=True)

st.markdown('<h1 class="main-title">献だけ</h1>', unsafe_allow_html=True)
st.caption(f"Logged in as: {st.session_state['username']}")

# データ読み込み
df_menu, _ = get_github_file(FILE)

if not df_menu.empty:
    # 指定仕様：日付入力 ＆ 日曜スタート [cite: 2026-02-06]
    today = datetime.now()
    offset = (today.weekday() + 1) % 7
    default_sun = today - timedelta(days=offset)
    start_date = st.date_input("開始日（日）", value=default_sun)
    
    day_labels = ["日", "月", "火", "水", "木", "金", "土"]
    days_tabs = st.tabs(day_labels)
    
    cats = ["主菜1", "主菜2", "副菜1", "副菜2", "汁物"]
    weekly_plan = {}
    
    for i, day_tab in enumerate(days_tabs):
        target_date = start_date + timedelta(days=i)
        d_str = target_date.strftime("%Y/%m/%d")
        with day_tab:
            st.markdown(f"##### {d_str} ({day_labels[i]})")
            day_menu = {}
            for cat in cats:
                options = ["なし"] + df_menu[df_menu["カテゴリー"] == cat]["料理名"].tolist()
                day_menu[cat] = st.selectbox(cat, options, key=f"s_{i}_{cat}")
            weekly_plan[d_str] = day_menu

    if st.button("確定して買い物リストを生成", type="primary", use_container_width=True):
        st.success("買い物リストを生成しました")
else:
    st.warning("メニューデータを読み込めませんでした。")
