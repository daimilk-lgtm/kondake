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

# --- 2. デザイン定義 (仕様死守) ---
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
    
    /* UI崩れ対策: エクスパンダーのラベル重なりを強制修正 */
    .st-emotion-cache-p4mnd5 { display: none !important; } /* 特定環境でのアイコンバグを消去 */
    summary { font-size: 1.1rem; font-weight: 400 !important; padding: 10px; }
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
            # GitHub(email) -> コード(username)
            if filename == USER_FILE and 'email' in df.columns:
                df = df.rename(columns={'email': 'username'})
            return df, r.json()["sha"]
    except: pass
    return pd.DataFrame(), None

def save_to_github(df, filename, message, current_sha=None):
    # 保存時は email に戻す
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
    t1, t2 = st.tabs(["ログイン", "新規登録"])
    df_users, user_sha = get_github_file(USER_FILE)
    with t1:
        with st.form("l"):
            u = st.text_input("メールアドレス", key="ul", autocomplete="email")
            p = st.text_input("パスワード", type="password", key="pl", autocomplete="current-password")
            if st.form_submit_button("ログイン", use_container_width=True):
                if not df_users.empty and u in df_users["username"].values:
                    if df_users[df_users["username"] == u]["password"].iloc[0] == make_hash(p):
                        st.session_state.update({"authenticated": True, "username": u})
                        st.rerun()
                st.error("ログイン情報が異なります")
    with t2:
        with st.form("r"):
            nu = st.text_input("メールアドレス", key="ur", autocomplete="email")
            np = st.text_input("パスワード (8文字以上)", type="password", key="pr", autocomplete="new-password")
            if st.form_submit_button("登録実行", use_container_width=True):
                if re.match(r"[^@]+@[^@]+\.[^@]+", nu) and len(np) >= 8:
                    new_df = pd.concat([df_users, pd.DataFrame([[nu, make_hash(np)]], columns=["username", "password"])])
                    save_to_github(new_df, USER_FILE, f"Add {nu}", user_sha)
                    st.success("登録完了。ログインしてください")
    st.stop()

# --- 5. メインアプリ (3タブ) ---
st.markdown('<div style="text-align:right">', unsafe_allow_html=True)
if st.button("ログアウト"):
    st.session_state["authenticated"] = False
    st.rerun()
st.markdown('</div>', unsafe_allow_html=True)

st.markdown('<h1 class="main-title">献だけ</h1>', unsafe_allow_html=True)
st.caption(f"Logged in as: {st.session_state['username']}")

df_menu, menu_sha = get_github_file(FILE)

t_plan, t_hist, t_manage = st.tabs(["📋 献立作成", "📜 履歴", "⚙️ メニュー管理"])

with t_plan:
    if not df_menu.empty:
        # 日曜スタート仕様 [cite: 2026-02-06]
        today = datetime.now()
        offset = (today.weekday() + 1) % 7
        default_sun = today - timedelta(days=offset)
        start_date = st.date_input("開始日（日）", value=default_sun)
        
        day_labels = ["日", "月", "火", "水", "木", "金", "土"]
        d_tabs = st.tabs(day_labels)
        cats = ["主菜1", "主菜2", "副菜1", "副菜2", "汁物"]
        for i, tab in enumerate(d_tabs):
            with tab:
                st.markdown(f"##### {(start_date + timedelta(days=i)).strftime('%Y/%m/%d')} ({day_labels[i]})")
                for c in cats:
                    opts = ["なし"] + df_menu[df_menu["カテゴリー"] == c]["料理名"].tolist()
                    st.selectbox(c, opts, key=f"s_{i}_{c}")
        st.button("確定して買い物リストを生成", type="primary", use_container_width=True)

with t_hist:
    st.info("過去の買い物リスト履歴がここに表示されます")

with t_manage:
    st.subheader("登録メニュー一覧")
    if not df_menu.empty:
        # 画像 image_f068b5.png の順序：料理名, カテゴリー, 材料
        cols = ["料理名", "カテゴリー", "材料"]
        display_df = df_menu[cols] if set(cols).issubset(df_menu.columns) else df_menu
        st.dataframe(display_df, use_container_width=True, hide_index=True)
        
        # UI崩れ（_arrow_right露出）を回避するための明示的タイトル
        with st.expander("新しい料理を追加"):
            with st.form("new_dish_form", clear_on_submit=True):
                c1, c2 = st.columns(2)
                with c1:
                    new_cat = st.selectbox("カテゴリー", ["主菜1", "主菜2", "副菜1", "副菜2", "汁物"])
                with c2:
                    new_name = st.text_input("料理名")
                new_ing = st.text_area("材料（カンマ区切り）")
                
                if st.form_submit_button("メニューを保存"):
                    if new_name:
                        new_data = pd.DataFrame([[new_name, new_cat, new_ing]], columns=["料理名", "カテゴリー", "材料"])
                        updated_menu = pd.concat([df_menu, new_data], ignore_index=True)
                        save_to_github(updated_menu, FILE, f"Update {new_name}", menu_sha)
                        st.success(f"{new_name} を保存しました")
                        st.rerun()
                    else:
                        st.error("料理名を入力してください")
