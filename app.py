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
HIST_FILE = "history.csv"
USER_FILE = "users.csv"
TOKEN = st.secrets.get("GITHUB_TOKEN")

# --- 2. デザイン定義 (仕様死守：ノイズ消去・Noto Sans JP) ---
st.set_page_config(page_title="献だけ", layout="centered", initial_sidebar_state="collapsed")
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Noto+Sans+JP:wght@100;300;400&display=swap');
    html, body, [class*="css"], p, div, select, input, label, span {
        font-family: 'Noto Sans JP', sans-serif !important;
        font-weight: 300 !important;
    }
    .main-title { font-weight: 100 !important; font-size: 3rem; text-align: center; margin: 40px 0; letter-spacing: 0.5rem; }
    /* 左上のノイズを透明化して隠す */
    header[data-testid="stHeader"] { background: transparent !important; color: transparent !important; }
    [data-testid="stSidebarCollapseButton"] { display: none !important; }
    .block-container { padding-top: 1rem !important; }
</style>
""", unsafe_allow_html=True)

# --- 3. 共通・GitHub通信関数 ---
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
            # 列名補正: GitHub(email) -> コード内(username)
            if filename == USER_FILE and 'email' in df.columns:
                df = df.rename(columns={'email': 'username'})
            return df, r.json()["sha"]
    except: pass
    return pd.DataFrame(), None

def save_to_github(df, filename, message, current_sha=None):
    # 列名復元: コード内(username) -> GitHub(email)
    save_df = df.rename(columns={"username": "email"}) if filename == USER_FILE else df
    csv_content = save_df.to_csv(index=False, encoding="utf-8-sig")
    content_b64 = base64.b64encode(csv_content.encode("utf-8")).decode("utf-8")
    url = f"https://api.github.com/repos/{REPO}/contents/{filename}"
    headers = {"Authorization": f"token {TOKEN}", "Accept": "application/vnd.github.v3+json"}
    data = {"message": message, "content": content_b64, "sha": current_sha}
    res = requests.put(url, headers=headers, json=data)
    return res.status_code

# --- 4. 認証フロー (オートフィル対応) ---
if "authenticated" not in st.session_state:
    st.session_state["authenticated"] = False

if not st.session_state["authenticated"]:
    st.markdown('<h1 class="main-title">献だけ</h1>', unsafe_allow_html=True)
    tab1, tab2 = st.tabs(["ログイン", "新規ユーザー登録"])
    df_users, user_sha = get_github_file(USER_FILE)
    
    with tab1:
        with st.form("login_form"):
            u_login = st.text_input("メールアドレス", key="u_log", autocomplete="email")
            p_login = st.text_input("パスワード", type="password", key="p_log", autocomplete="current-password")
            if st.form_submit_button("ログイン", use_container_width=True):
                if not df_users.empty and u_login in df_users["username"].values:
                    if df_users[df_users["username"] == u_login]["password"].iloc[0] == make_hash(p_login):
                        st.session_state.update({"authenticated": True, "username": u_login})
                        st.rerun()
                st.error("ログイン情報が正しくありません")
    
    with tab2:
        with st.form("reg_form"):
            u_reg = st.text_input("メールアドレス", key="u_reg", autocomplete="email")
            p_reg = st.text_input("パスワード (8文字以上の英数字)", type="password", key="p_reg", autocomplete="new-password")
            if st.form_submit_button("登録実行", use_container_width=True):
                if re.match(r"[^@]+@[^@]+\.[^@]+", u_reg) and len(p_reg) >= 8:
                    new_df = pd.concat([df_users, pd.DataFrame([[u_reg, make_hash(p_reg)]], columns=["username", "password"])])
                    save_to_github(new_df, USER_FILE, f"Add {u_reg}", user_sha)
                    st.success("登録完了！ログインしてください")
                else: st.error("形式不備: 8文字以上の英数字が必要です")
    st.stop()

# --- 5. メインアプリ (3タブ構造維持) ---
st.markdown('<div style="text-align:right">', unsafe_allow_html=True)
if st.button("ログアウト"):
    st.session_state["authenticated"] = False
    st.rerun()
st.markdown('</div>', unsafe_allow_html=True)

st.markdown('<h1 class="main-title">献だけ</h1>', unsafe_allow_html=True)
st.caption(f"Logged in as: {st.session_state['username']}")

df_menu, menu_sha = get_github_file(FILE)
df_dict, _ = get_github_file(DICT_FILE)

# 3タブ構成の復元
t_plan, t_hist, t_manage = st.tabs(["📋 献立作成", "📜 履歴", "⚙️ メニュー管理"])

# --- タブ1: 献立作成 (日曜スタート仕様) ---
with t_plan:
    if not df_menu.empty:
        # 仕様：日付選択 ＆ 日曜スタート [cite: 2026-02-06]
        today = datetime.now()
        offset = (today.weekday() + 1) % 7
        default_sun = today - timedelta(days=offset)
        start_date = st.date_input("開始日（日）", value=default_sun)
        
        day_labels = ["日", "月", "火", "水", "木", "金", "土"]
        days_tabs = st.tabs(day_labels)
        cats = ["主菜1", "主菜2", "副菜1", "副菜2", "汁物"]
        
        for i, day_tab in enumerate(days_tabs):
            with day_tab:
                target_date = (start_date + timedelta(days=i)).strftime('%Y/%m/%d')
                st.markdown(f"##### {target_date} ({day_labels[i]})")
                for cat in cats:
                    opts = ["なし"] + df_menu[df_menu["カテゴリー"] == cat]["料理名"].tolist()
                    st.selectbox(cat, opts, key=f"s_{i}_{cat}")
        
        st.button("確定して買い物リストを生成", type="primary", use_container_width=True)
    else: st.warning("メニューデータが読み込めません")

# --- タブ2: 履歴 ---
with t_hist:
    st.subheader("過去の献立履歴")
    st.info("ここに保存済みの履歴が表示されます")

# --- タブ3: メニュー管理 (追加機能) ---
with t_manage:
    st.subheader("登録メニュー一覧")
    if not df_menu.empty:
        st.dataframe(df_menu, use_container_width=True, hide_index=True)
        with st.expander("新しい料理を追加"):
            with st.form("add_menu"):
                n_cat = st.selectbox("カテゴリー", ["主菜1", "主菜2", "副菜1", "副菜2", "汁物"])
                n_name = st.text_input("料理名")
                if st.form_submit_button("保存"):
                    new_row = pd.DataFrame([[n_cat, n_name]], columns=["カテゴリー", "料理名"])
                    updated_menu = pd.concat([df_menu, new_row], ignore_index=True)
                    save_to_github(updated_menu, FILE, f"Add {n_name}", menu_sha)
                    st.success(f"{n_name} を追加しました")
