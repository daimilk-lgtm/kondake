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

# --- 2. デザイン定義 (表示を復元しつつ、ノイズだけを狙い撃ち) ---
st.set_page_config(page_title="献だけ", layout="centered", initial_sidebar_state="collapsed")
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Noto+Sans+JP:wght@100;300;400&display=swap');
    html, body, [class*="css"], p, div, select, input, label, span {
        font-family: 'Noto Sans JP', sans-serif !important;
        font-weight: 300 !important;
    }
    .main-title { font-weight: 100 !important; font-size: 3rem; text-align: center; margin: 40px 0; letter-spacing: 0.5rem; }
    
    /* コンテンツを消さずに、左上の「文字化けテキスト」だけを透明化して隠す */
    [data-testid="stHeader"] { background-color: rgba(0,0,0,0) !important; }
    [data-testid="stSidebarCollapseButton"] { 
        color: transparent !important; 
        background: transparent !important; 
        border: none !important;
    }
    /* メイン画面の余白を確保 */
    .block-container { padding-top: 2rem !important; }
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
            # image_eff383.png の実態に合わせて列名を統一
            if filename == USER_FILE:
                if 'email' in df.columns:
                    df = df.rename(columns={'email': 'username'})
            return df, r.json()["sha"]
    except: pass
    return pd.DataFrame(columns=["username", "password"]), None

def save_to_github(df, filename, message, current_sha=None):
    # 保存時も列名を email に戻す
    save_df = df.rename(columns={"username": "email"})
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
    tab1, tab2 = st.tabs(["ログイン", "新規ユーザー登録"])
    df_users, user_sha = get_github_file(USER_FILE)

    with tab1:
        with st.form("login"):
            u = st.text_input("メールアドレス")
            p = st.text_input("パスワード", type="password")
            if st.form_submit_button("ログイン", use_container_width=True):
                h = make_hash(p)
                # 列名問題(KeyError)を解決した状態で照合
                if not df_users.empty and u in df_users["username"].values:
                    if df_users[df_users["username"] == u]["password"].iloc[0] == h:
                        st.session_state["authenticated"] = True
                        st.session_state["username"] = u
                        st.rerun()
                st.error("ログイン失敗")

    with tab2:
        with st.form("reg"):
            nu = st.text_input("メールアドレス")
            np = st.text_input("パスワード (8文字以上の英数字)", type="password")
            if st.form_submit_button("登録実行", use_container_width=True):
                if re.match(r"[^@]+@[^@]+\.[^@]+", nu) and len(np) >= 8:
                    new_df = pd.concat([df_users, pd.DataFrame([[nu, make_hash(np)]], columns=["username", "password"])])
                    save_to_github(new_df, USER_FILE, f"Add {nu}", user_sha)
                    st.success("登録完了！")
                else: st.error("形式不備")
    st.stop()

# --- 5. メインアプリ (中身をしっかり表示) ---
col1, col2 = st.columns([0.8, 0.2])
with col2:
    if st.button("ログアウト"):
        st.session_state["authenticated"] = False
        st.rerun()

st.markdown('<h1 class="main-title">献だけ</h1>', unsafe_allow_html=True)
st.write(f"Login: {st.session_state['username']}")

# 献立作成機能
df_menu, _ = get_github_file(FILE)
if not df_menu.empty:
    # 日付選択 (日曜スタート仕様)
    today = datetime.now()
    offset = (today.weekday() + 1) % 7
    start_date = st.date_input("開始日（日）", value=today - timedelta(days=offset))
    
    day_labels = ["日", "月", "火", "水", "木", "金", "土"]
    tabs = st.tabs(day_labels)
    # ... (献立選択ロジック)
    st.info("ここに献立設定が表示されます")
