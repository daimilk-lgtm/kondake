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
    except Exception:
        pass
    return None, None

# --- 2. デザイン定義（CSS） ---
st.set_page_config(page_title="献だけ", layout="centered")

st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Noto+Sans+JP:wght@100;300;400&display=swap');
    
    /* 買い物リストを含め、全ての要素を細身(300)に統一 */
    html, body, [class*="css"], p, div, select, input, label, span {
        font-family: 'Noto Sans JP', sans-serif !important;
        font-weight: 300 !important;
        color: #333;
    }
    
    /* タイトル（極細） */
    .main-title {
        font-family: 'Noto Sans JP', sans-serif !important;
        font-weight: 100 !important;
        font-size: 3.2rem;
        letter-spacing: 0.8rem;
        text-align: center;
        margin: 40px 0;
    }

    /* 入力欄の角丸 */
    .stSelectbox [data-baseweb="select"], .stTextInput input, .stTextArea textarea {
        border-radius: 16px !important;
        border: 1px solid #eee !important;
    }

    /* 印刷用：ノイズ排除 */
    @media print {
        .no-print, header, [data-testid="stSidebar"], .stTabs [data-baseweb="tab-list"], button, .stDivider {
            display: none !important;
        }
        .print-area { display: block !important; }
        .print-table { width: 100%; border-collapse: collapse; margin-top: 20px; }
        .print-table th, .print-table td { border: 0.5px solid #ccc; padding: 10px; font-size: 10pt; }
        a { text-decoration: none !important; color: black !important; }
    }
    .print-area { display: none; }
</style>
""", unsafe_allow_html=True)

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
        weekly_memo = st.text_input("週のテーマ", placeholder="テーマ・目標")

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
            day_menu["memo"] = st.text_area("備考", placeholder="予定など", key=f"m_{i}", height=80)
            weekly_plan[d_str] = day_menu

    if st.button("確定して印刷用表示", type="primary", use_container_width=True):
        all_ings = []
        rows_html = ""
        for d, v in weekly_plan.items():
            rows_html += f"<tr><td>{d}</td><td>{v['主菜1']}</td><td>{v['主菜2']}</td><td>{v['副菜1']}</td><td>{v['副菜2']}</td><td>{v['汁物']}</td><td>{v['memo']}</td></tr>"
            for k, dish in v.items():
                if k != "memo" and dish != "なし":
                    ing_raw = df[df["料理名"] == dish]["材料"].iloc[0]
                    items = str(ing_raw).replace("、", ",").split(",")
                    all_ings.extend([x.strip() for x in items if x.strip()])
        
        counts = pd.Series(all_ings).value_counts().sort_index()
        buy_txt = ', '.join([f"{k}({v})" if v > 1 else k for k, v in counts.items()]) if not counts.empty else "なし"

        # 印刷用表示
        st.markdown(f"""
        <div class="print-area">
            <h1 style="font-weight:100; text-align:center;">{start_date.strftime('%Y/%m/%d')} 週 献立表</h1>
            <table class="print-table">
                <thead><tr><th>日付</th><th>主菜1</th><th>主菜2</th><th>副菜1</th><th>副菜2</th><th>汁物</th><th>備考</th></tr></thead>
                <tbody>{rows_html}</tbody>
            </table>
            <h2 style="font-weight:300; border-bottom:1px solid #333; margin-top:30px;">買い物リスト</h2>
            <p style="font-size:11pt;">{buy_txt}</p>
        </div>
        """, unsafe_allow_html=True)

        # 画面用：買い物リスト
        st.subheader("🛒 買い物リスト")
        if not counts.empty:
            c1, c2 = st.columns(2)
            for idx, (item, count) in enumerate(counts.items()):
                # チェックボックス横の文字もCSSにより細身になります
                with (c1 if idx % 2 == 0 else c2):
                    st.checkbox(f"{item} × {count}" if count > 1 else item, key=f"b_{idx}")
        st.success("印刷準備完了。ブラウザメニューの「印刷」からA4出力できます。")

with tab_manage:
    st.subheader("⚙️ メニュー登録")
    with st.form("add", clear_on_submit=True):
        n = st.text_input("料理名")
        c = st.selectbox("カテゴリー", cats)
        m = st.text_area("材料（「、」区切り）")
        if st.form_submit_button("保存"):
            if n and m:
                new_df = pd.concat([df, pd.DataFrame([[n, c, m]], columns=df.columns)], ignore
