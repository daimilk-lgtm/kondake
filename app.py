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
    offset = (today.weekday() + 1) % 7
    default_sun = today - timedelta(days=offset)
    
    col_date, col_memo = st.columns([1, 2])
    with col_date:
        start_date = st.date_input("開始日（日）", value=default_sun)
    with col_memo:
        weekly_memo = st.text_input("今週の全体メモ（テーマなど）", placeholder="例：ヘルシー週間、冷蔵庫一掃")

    st.divider()

    # 曜日タブ：日〜土
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
                day_menu[cat] = st.selectbox(f"{cat}", ["なし"] + opts, key=f"sel_{i}_{cat}")
            # 仕様：フリースペース（デイリーメモ）
            day_menu["memo"] = st.text_area("今日のメモ・予定", placeholder="例：塾で遅め、旦那飲み会", key=f"memo_{i}", height=70)
            weekly_plan[d_str] = day_menu

    st.divider()

    # 買い物リスト生成と印刷用表示
    if st.button("献立を確定（買い物リスト・印刷用表示）", type="primary", use_container_width=True):
        # 買い物リスト集計
        all_ings = []
        for d_menu in weekly_plan.values():
            for k, dish in d_menu.items():
                if k != "memo" and dish != "なし":
                    m_data = df[df["料理名"] == dish]["材料"].iloc[0]
                    items = str(m_data).replace("、", ",").split(",")
                    all_ings.extend([x.strip() for x in items if x.strip()])

        # --- 印刷用表示エリア ---
        st.markdown('<div class="print-only">', unsafe_allow_html=True)
        st.write(f"## 献立表：{start_date.strftime('%Y/%m/%d')} 〜")
        st.write(f"**今週のメモ:** {weekly_memo}")
        
        # 印刷用テーブル
        print_df = pd.DataFrame(weekly_plan).T
        st.table(print_df)
        
        if all_ings:
            st.write("### 🛒 買い物リスト")
            counts = pd.Series(all_ings).value_counts().sort_index()
            st.write(", ".join([f"{k}({v})" if v > 1 else k for k, v in counts.items()]))
        st.markdown('</div>', unsafe_allow_html=True)

        # 画面用表示
        st.subheader("🛒 買い物リスト（画面用）")
        if all_ings:
            counts = pd.Series(all_ings).value_counts().sort_index()
            c1, c2 = st.columns(2)
            for idx, (item, count) in enumerate(counts.items()):
                with (c1 if idx % 2 == 0 else c2):
                    st.checkbox(f"{item} × {count}" if count > 1 else item, key=f"b_{idx}")
        st.info("ブラウザの印刷機能（Ctrl+P / 共有>印刷）を使うとA4に最適化された献立表が印刷できます。")

with tab_manage:
    st.subheader("メニュー管理")
    with st.form("add_form", clear_on_submit=True):
        name = st.text_input("料理名")
        cat = st.selectbox("カテゴリー", cats)
        ing = st.text_area("材料（「、」区切り）")
        if st.form_submit_button("保存"):
            if name and ing:
                new_row = pd.DataFrame([[name, cat, ing]], columns=df.columns)
                up_df = pd.concat([df, new_row], ignore_index=True)
                csv_b64 = base64.b64encode(up_df.to_csv(index=False, encoding="utf-8-sig").encode("utf-8")).decode("utf-8")
                res = requests.put(f"https://api.github.com/repos/{REPO}/contents/{FILE}", 
                                   headers={"Authorization": f"token {TOKEN}"},
                                   json={"message": f"Add {name}", "content": csv_b64, "sha": sha})
                if res.status_code == 200:
                    st.success("追加完了")
                    st.cache_data.clear()
                    st.rerun()

    st.dataframe(df, use_container_width=True)
