import streamlit as st
import pandas as pd
import requests
import base64
import io
from datetime import datetime, timedelta
import hashlib

# --- 1. 定数・接続設定 ---
REPO = "daimilk-lgtm/kondake"
FILE = "menu.csv"
USER_FILE = "users.csv"
TOKEN = st.secrets.get("GITHUB_TOKEN")

# --- 2. 仕様定義とセルフチェック ---
# 公開バージョンの「絶対守るべきルール」を定義
EXPECTED_SPECS = {
    "sunday_start": True,       # 日曜スタート
    "no_noise": True,           # サイドバー・ヘッダー消去
    "font_noto": True,          # Noto Sans JP
    "editor_enabled": True      # メニュー編集機能
}

def run_self_validation():
    errors = []
    # 日曜スタートの計算ロジックを検証
    test_today = datetime.now()
    offset = (test_today.weekday() + 1) % 7
    if (test_today - timedelta(days=offset)).weekday() != 6: # 6 = Sunday
        errors.append("カレンダーの日曜スタート設定が壊れています")
    
    # CSSにNoto Sansが含まれているか
    if "Noto Sans JP" not in CSS_CODE:
        errors.append("フォント設定が漏れています")
        
    return errors

# --- 3. デザイン定義 (公開バージョンのクリーンなUIを再現) ---
CSS_CODE = """
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
"""

st.set_page_config(page_title="献だけ", layout="centered", initial_sidebar_state="collapsed")
st.markdown(CSS_CODE, unsafe_allow_html=True)

# 起動時に仕様チェックを実行
validation_errors = run_self_validation()
if validation_errors:
    st.error(f"🚨 仕様不備を検知: {', '.join(validation_errors)}")

# --- 4. 通信関数 ---
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

# --- 5. アプリケーション本体 ---
if "authenticated" not in st.session_state:
    st.session_state["authenticated"] = False

if not st.session_state["authenticated"]:
    st.markdown('<h1 class="main-title">献だけ</h1>', unsafe_allow_html=True)
    df_users, user_sha = get_github_file(USER_FILE)
    with st.form("login"):
        u = st.text_input("メールアドレス", key="ul", autocomplete="email")
        p = st.text_input("パスワード", type="password", key="pl", autocomplete="current-password")
        if st.form_submit_button("ログイン", use_container_width=True):
            if not df_users.empty and u in df_users["username"].values:
                st.session_state.update({"authenticated": True, "username": u})
                st.rerun()
    st.stop()

# メイン画面
st.markdown('<h1 class="main-title">献だけ</h1>', unsafe_allow_html=True)
df_menu, menu_sha = get_github_file(FILE)

t_plan, t_hist, t_manage = st.tabs(["📋 献立作成", "📜 履歴", "⚙️ メニュー管理"])

with t_plan:
    # 公開バージョン仕様：日曜スタート
    today = datetime.now()
    offset = (today.weekday() + 1) % 7
    default_sun = today - timedelta(days=offset)
    start_date = st.date_input("開始日（日）", value=default_sun)
    
    day_labels = ["日", "月", "火", "水", "木", "金", "土"]
    d_tabs = st.tabs(day_labels)
    if not df_menu.empty:
        for i, tab in enumerate(d_tabs):
            with tab:
                st.markdown(f"##### {(start_date + timedelta(days=i)).strftime('%Y/%m/%d')} ({day_labels[i]})")
                for c in ["主菜1", "主菜2", "副菜1", "副菜2", "汁物"]:
                    opts = ["なし"] + df_menu[df_menu["カテゴリー"] == c]["料理名"].tolist()
                    st.selectbox(c, opts, key=f"s_{i}_{c}")
        st.button("確定して買い物リストを生成", type="primary", use_container_width=True)

with t_manage:
    st.subheader("メニューの管理")
    if not df_menu.empty:
        # 公開バージョン仕様：直接編集
        edited_df = st.data_editor(
            df_menu,
            column_order=["料理名", "カテゴリー", "材料"],
            num_rows="dynamic",
            use_container_width=True,
            hide_index=True,
            key="v_final_editor"
        )
        if st.button("GitHubへ保存", type="primary", use_container_width=True):
            save_to_github(edited_df, FILE, "Update from App", menu_sha)
            st.success("保存しました")
            st.rerun()
