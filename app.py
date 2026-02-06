import streamlit as st
import pandas as pd
import requests
import base64
import io
from datetime import datetime, timedelta

# --- 1. 接続設定 ---
REPO = "daimilk-lgtm/kondake"
FILE = "menu.csv"
DICT_FILE = "ingredients.csv"
TOKEN = st.secrets.get("GITHUB_TOKEN")

@st.cache_data(ttl=60)
def get_menu_data():
    try:
        url = f"https://api.github.com/repos/{REPO}/contents/{FILE}"
        headers = {"Authorization": f"token {TOKEN}", "Accept": "application/vnd.github.v3+json"}
        r = requests.get(url, headers=headers)
        if r.status_code == 200:
            raw = base64.b64decode(r.json()["content"]).decode("utf-8-sig")
            df = pd.read_csv(io.StringIO(raw))
            df.columns = [c.strip() for c in df.columns]
            return df, r.json()["sha"]
    except: pass
    return None, None

@st.cache_data(ttl=60)
def get_dict_data():
    try:
        url = f"https://raw.githubusercontent.com/{REPO}/main/{DICT_FILE}"
        return pd.read_csv(url)
    except: return None

# --- 2. デザイン定義（CSS） ---
st.set_page_config(page_title="献だけ", layout="centered")

st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Noto+Sans+JP:wght@100;300;400&display=swap');
    
    html, body, [class*="css"], p, div, select, input, label, span, .stCheckbox {
        font-family: 'Noto Sans JP', sans-serif !important;
        font-weight: 300 !important;
        color: #333;
    }
    .main-title {
        font-family: 'Noto Sans JP', sans-serif !important;
        font-weight: 100 !important;
        font-size: 3.2rem;
        letter-spacing: 0.8rem;
        text-align: center;
        margin: 40px 0;
    }
    .stSelectbox [data-baseweb="select"], .stTextInput input, .stTextArea textarea {
        border-radius: 16px !important;
        border: 1px solid #eee !important;
        background-color: #fafafa !important;
    }
    .shopping-card {
        background-color: #ffffff;
        padding: 15px 20px;
        border-radius: 16px;
        border: 1px solid #f0f0f0;
        margin-bottom: 15px;
        box-shadow: 0 4px 12px rgba(0,0,0,0.03);
        break-inside: avoid;
    }
    .category-label { font-size: 0.8rem; font-weight: 400; color: #999; margin-bottom: 5px; }
    .item-row { font-size: 1.1rem; font-weight: 300; padding: 4px 0; border-bottom: 0.5px solid #f9f9f9; }
    
    .memo-space {
        margin-top: 20px;
        padding: 20px;
        border: 1px dashed #ccc;
        border-radius: 10px;
        min-height: 120px;
    }
    .memo-title { font-size: 0.9rem; color: #999; margin-bottom: 10px; }

    /* 印刷プレビュー修正：リストエリア(print-content)以外を非表示にする */
    @media print {
        header, [data-testid="stSidebar"], [data-testid="stHeader"], .stTabs, button, .stDivider, footer, .no-print {
            display: none !important;
        }
        /* 画面上の余計なコンテナ余白を削る */
        [data-testid="stAppViewContainer"] > section:nth-child(2) {
            padding-top: 0rem !important;
        }
        .main-title { font-size: 2.2rem !important; margin: 10px 0 !important; }
        .shopping-card { 
            box-shadow: none !important; 
            border: 1px solid #eee !important; 
            padding: 10px !important; 
            margin-bottom: 10px !important; 
        }
        .item-row { font-size: 1rem !important; }
    }
</style>
""", unsafe_allow_html=True)

st.markdown('<h1 class="main-title">献だけ</h1>', unsafe_allow_html=True)

df_menu, sha = get_menu_data()
df_dict = get_dict_data()

if df_menu is None:
    st.error("GitHub接続エラー。Secretsを確認してください。")
    st.stop()

tab_plan, tab_manage = st.tabs(["🗓 献立作成", "⚙️ メニュー管理"])

with tab_plan:
    today = datetime.now()
    offset = (today.weekday() + 1) % 7
    default_sun = today - timedelta(days=offset)
    start_date = st.date_input("開始日（日）", value=default_sun)

    day_labels = ["日", "月", "火", "水", "木", "金", "土"]
    days_tabs = st.tabs([f"{day_labels[i]}" for i in range(7)])
    cats = ["主菜1", "主菜2", "副菜1", "副菜2", "汁物"]
    weekly_plan = {}

    # 入力フォーム全体を no-print クラスで包む（印刷時に隠すため）
    for i, day_tab in enumerate(days_tabs):
        d_str = (start_date + timedelta(days=i)).strftime("%m/%d")
        with day_tab:
            st.markdown(f"##### {d_str} ({day_labels[i]})")
            day_menu = {cat: st.selectbox(cat, ["なし"] + df_menu[df_menu["カテゴリー"] == cat]["料理名"].tolist(), key=f"s_{i}_{cat}") for cat in cats}
            weekly_plan[d_str] = day_menu

    if st.button("確定して買い物リストを生成", type="primary", use_container_width=True):
        st.divider()
        st.markdown("### 🛒 買い物リスト")
        
        all_ings_list = []
        for d, v in weekly_plan.items():
            for cat, dish in v.items():
                if dish != "なし":
                    ing_raw = df_menu[df_menu["料理名"] == dish]["材料"].iloc[0]
                    items = str(ing_raw).replace("、", ",").split(",")
                    all_ings_list.extend([x.strip() for x in items
