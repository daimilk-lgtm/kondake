import streamlit as st
import pandas as pd
import requests
import base64
import io
from datetime import datetime, timedelta

# --- 1. 接続設定 ---
REPO = "daimilk-lgtm/kondake"
FILE = "menu.csv"
TOKEN = st.secrets.get("GITHUB_TOKEN")

@st.cache_data(ttl=60)
def get_data():
    try:
        url = f"https://api.github.com/repos/{REPO}/contents/{FILE}"
        headers = {"Authorization": f"token {TOKEN}", "Accept": "application/vnd.github.v3+json"}
        r = requests.get(url, headers=headers)
        if r.status_code == 200:
            raw = base64.b64decode(r.json()["content"]).decode("utf-8-sig")
            return pd.read_csv(io.StringIO(raw)), r.json()["sha"]
    except: pass
    return None, None

# --- 2. デザイン・スタイル定義（CSS） ---
st.set_page_config(page_title="献だけ", layout="centered")

st.markdown(f"""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Noto+Sans+JP:wght@100;300;400&display=swap');
    
    /* 全体フォント設定：細身(300)で清潔感を出す */
    html, body, [class*="css"], p, div, select, input, label {{
        font-family: 'Noto Sans JP', sans-serif !important;
        font-weight: 300 !important;
        letter-spacing: 0.05rem;
    }}
    
    /* 入力欄の角丸と余白 */
    .stSelectbox [data-baseweb="select"], .stTextInput input, .stTextArea textarea {{
        border-radius: 12px !important;
        border: 1px solid #eee !important;
    }}
    
    /* 曜日タブのスタイル */
    .stTabs [data-baseweb="tab-list"] {{
        gap: 4px;
        background-color: transparent;
    }}
    .stTabs [data-baseweb="tab"] {{
        border-radius: 8px 8px 0 0;
        padding: 8px 12px;
        background-color: #fcfcfc;
    }}
    
    /* 印刷用設定（Ctrl+PでA4一枚に収める） */
    @media print {{
        .no-print, header, [data-testid="stSidebar"], .stTabs [data-baseweb="tab-list"], button {{
            display: none !important;
        }}
        .print-only {{
            display: block !important;
        }}
        .main-content {{
            width: 100% !important;
            margin: 0 !important;
            padding: 0 !important;
        }}
        table {{
            width: 100%;
            border-collapse: collapse;
            font-size: 10pt;
        }}
        th, td {{
            border: 1px solid #ccc;
            padding: 8px;
            text-align: left;
        }}
    }}
    .print-only {{ display: none; }}
</style>
""", unsafe_allow_html=True)

st.title("献だけ")

df, sha = get_data()
if df is None:
    st.error("GitHub接続エラー。Secretsを再確認してください。")
    st.stop()

# --- 3. メインロジック ---
tab_plan, tab_manage = st.tabs(["🗓 献立作成", "⚙️ メニュー管理"])

with tab_plan:
    # 日付入力：初期値は直近の日曜日
    today = datetime.now()
    offset = (
