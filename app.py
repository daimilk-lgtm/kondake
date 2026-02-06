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
            df = pd.read_csv(io.StringIO(raw))
            df.columns = [c.strip() for c in df.columns]
            return df, r.json()["sha"]
    except: pass
    return None, None

# --- 2. 徹底したデザイン・スタイル定義（CSS） ---
st.set_page_config(page_title="献だけ", layout="centered")

st.markdown(f"""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Noto+Sans+JP:wght@100;300;400&display=swap');
    
    /* 全体：極細フォントと広い余白 */
    html, body, [class*="css"], p, div, select, input, label {{
        font-family: 'Noto Sans JP', sans-serif !important;
        font-weight: 300 !important;
        color: #333;
    }}
    
    /* タイトル：究極の細身デザイン */
    .main-title {{
        font-family: 'Noto Sans JP', sans-serif !important;
        font-weight: 100 !important;
        font-size: 3.2rem;
        letter-spacing: 0.8rem;
        text-align: center;
        margin: 40px 0;
        color: #222;
    }}

    /* 入力パーツ：モダンな角丸 */
    .stSelectbox [data-baseweb="select"], .stTextInput input, .stTextArea textarea {{
        border-radius: 16px !important;
        border: 1px solid #eee !important;
        padding: 10px !important;
        background-color: #fafafa !important;
    }}

    /* 印刷専用レイアウト（A4一枚完結） */
    @media print {{
        .no-print, header, [data-testid="stSidebar"], .stTabs [data-baseweb="tab-list"], button, .stDivider {{
            display: none !important;
        }}
        .print-area {{
            display: block !important;
            width: 100% !important;
            padding: 20px !important;
        }}
        .print-table {{
            width: 100%;
            border-collapse: collapse;
            margin-bottom: 30px;
        }}
        .print-table th, .print-table td {{
            border: 0.5px solid #ddd;
            padding: 12px;
            text-align: left;
            font-size: 11pt;
        }}
        .print-table th {{ background-color: #f9f9f9; font-weight: 400; }}
        .list-title {{ border-bottom: 1px solid #333; padding-bottom: 5px; margin-top: 30px; font-size: 14pt; }}
    }}
    .print-area {{ display: none; }}
</style>
""", unsafe_allow_html=True)

# ロゴ風タイトル
st.markdown('<h1 class="main-title">献だけ</h1>', unsafe_allow_html=True)

df, sha = get_data()
if df is None:
    st.error("GitHub接続エラー。Secretsを再確認してください。")
    st.stop()

tab_plan, tab_manage = st.tabs(["🗓 献立作成", "⚙️ メニュー管理"])

with tab_plan:
    # 日曜スタート初期化
    today = datetime.now()
    offset = (today.weekday() + 1) % 7
    default_sun = today - timedelta(days=offset)
    
    col_d, col_m = st.columns([1, 2])
    with col_d:
        start_date = st.date_input("開始日（日）", value=default_sun)
    with col_m:
        weekly_memo = st.text_input("今週の全体テーマ", placeholder="例：旬の野菜を食べる")

    st.divider()

    day_labels = ["日", "月", "火", "水", "木", "金", "土"]
    days_tabs = st.tabs([f"{day_labels[i]}" for i in range(7)])
    
    cats = ["主菜1", "主菜2", "副菜1", "副菜2", "汁物"]
    weekly_plan = {}

    for i, day_tab in enumerate(days_tabs):
        d_obj = start_date + timedelta(days=i)
        d_str = d_obj.strftime("%m/%d")
        with day_tab:
            st.markdown(f"##### {d_str} ({day_labels[i]})")
            day_menu = {}
            for cat in cats:
                opts = df[df["カテゴリー"] == cat]["料理名"].tolist()
                day_menu[cat] = st.selectbox(cat, ["なし"] + opts, key=f"s_{i}_{cat}")
            day_menu["memo"] = st.text_area("備考・予定", placeholder="例：遅め", key=f"m_{i}", height=80)
            weekly_plan[d_str] = day_menu

    if st.button("献立を確定（買い物リスト・印刷用レイアウト生成）", type="primary", use_container_width=True):
        # 買い物リスト合算ロジック
        all_ings = []
        for day, data in weekly_plan.items():
            for k, dish in data.items():
                if k != "memo" and dish != "なし":
                    ing_raw = df[df["料理名"] == dish]["材料"].iloc[0]
                    items = str(ing_raw).replace("、", ",").split(",")
                    all_ings.extend([x.strip() for x in items if x.strip()])
        
        counts = pd.Series(all_ings).value_counts().sort_index()

        # --- 印刷専用エリア（ブラウザ印刷時にのみ出現） ---
        st.markdown(f"""
        <div class="print-area">
            <h2 style="font-weight:100; text-align:center;">{start_date.strftime('%Y/%m/%d')} 週の献立</h2>
            <p><strong>今週のテーマ:</strong> {weekly_memo}</p>
            <table class="print-table">
                <thead>
                    <tr>
                        <th>日付</th><th>主菜1</th><th>主菜
