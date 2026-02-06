import streamlit as st
import pandas as pd
import sqlite3
import requests
import base64
from datetime import datetime, timedelta

# --- 1. GitHub連携設定 ---
TOKEN = st.secrets.get("GITHUB_TOKEN")
REPO = st.secrets.get("GITHUB_REPO")
FILE_PATH = st.secrets.get("GITHUB_FILE", "menu.csv")

# GitHubからCSVを読み込む関数
@st.cache_data(ttl=60)
def get_csv_from_github():
    url = f"https://api.github.com/repos/{REPO}/contents/{FILE_PATH}"
    headers = {"Authorization": f"token {TOKEN}"}
    res = requests.get(url, headers=headers)
    if res.status_code == 200:
        content = base64.b64decode(res.json()["content"]).decode("utf-8-sig")
        from io import StringIO
        df = pd.read_csv(StringIO(content))
        df["カテゴリー"] = df["カテゴリー"].str.strip()
        return df, res.json()["sha"]
    return pd.DataFrame(), None

# GitHubのCSVを更新する関数
def update_github_csv(df, sha):
    url = f"https://api.github.com/repos/{REPO}/contents/{FILE_PATH}"
    headers = {"Authorization": f"token {TOKEN}"}
    # CSVを文字列にしてBase64エンコード
    content_base64 = base64.b64encode(df.to_csv(index=False).encode("utf-8-sig")).decode("utf-8")
    data = {
        "message": "Update menu via app",
        "content": content_base64,
        "sha": sha
    }
    res = requests.put(url, headers=headers, json=data)
    return res.status_code == 200

# データの初期読み込み
df_master, current_sha = get_csv_from_github()
conn = sqlite3.connect(':memory:', check_same_thread=False)
if not df_master.empty:
    df_master.to_sql('menu_table', conn, index=False, if_exists='replace')

# --- 2. デザイン設定 ---
st.set_page_config(page_title="献だけ", layout="wide")
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Noto+Sans+JP:wght@100;300&display=swap');
    html, body, [class*="css"], p, div, select, input, h2, h3 {
        font-family: 'Noto Sans JP', sans-serif !important;
        font-weight: 300 !important;
    }
    .title-wrapper { text-align: center; padding: 1rem 0; }
    .title-text { font-size: 3rem; font-weight: 100; letter-spacing: 0.5em; color: #333; }
    .thin-title { font-weight: 300 !important; font-size: 1.5rem; margin-top: 2rem; margin-bottom: 1rem; }
    .date-text { text-align: right; font-size: 0.8rem; color: #666; }
</style>
<div class="title-wrapper"><div class="title-text">献だけ</div></div>
""", unsafe_allow_html=True)

today = datetime.now()
st.markdown(f'<div class="date-text">作成日: {today.strftime("%Y/%m/%d")}</div>', unsafe_allow_html=True)

# --- 3. メインタブ構成 ---
main_tab1, main_tab2 = st.tabs(["🗓 献立作成", "⚙️ メニュー管理"])

# --- タブ1: 献立作成 ---
with main_tab1:
    if not df_master.empty:
        # 日曜スタートの日付設定
        start_date = st.date_input("開始日（日曜日）
