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

    /* 印刷用表示エリア（通常時は隠す） */
    .print-only { display: none; }

    /* 印刷プレビューの決定打：全要素を一度消し、印刷専用エリアだけを強制表示 */
    @media print {
        body * { visibility: hidden; }
        .print-only, .print-only * { visibility: visible; }
        .print-only {
            display: block !important;
            position: absolute;
            left: 0;
            top: 0;
            width: 100%;
        }
        .shopping-card { 
            box-shadow: none !important; 
            border: 1px solid #eee !important; 
            break-inside: avoid;
        }
    }
</style>
""", unsafe_allow_html=True)

st.markdown('<h1 class="main-title no-print">献だけ</h1>', unsafe_allow_html=True)

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
                    all_ings_list.extend([x.strip() for x in items if x.strip()])
        
        if all_ings_list:
            counts = pd.Series(all_ings_list).value_counts()
            result_data = []
            for item, count in counts.items():
                category = "99未分類"
                if df_dict is not None:
                    for _, row in df_dict.iterrows():
                        if row["材料"] in item:
                            category = row["種別"]
                            break
                display_name = f"{item} × {count}" if count > 1 else item
                result_data.append({"name": display_name, "cat": category})
            
            df_res = pd.DataFrame(result_data).sort_values("cat")

            # --- 画面表示用と印刷専用エリアの同時生成 ---
            cards_html = ""
            for cat, group in df_res.groupby("cat"):
                items_html = "".join([f'<div class="item-row">□ {row["name"]}</div>' for _, row in group.iterrows()])
                cards_html += f"""
                <div class="shopping-card">
                    <div class="category-label">{cat}</div>
                    {items_html}
                </div>
                """
            
            memo_html = """
                <div class="memo-space">
                    <div class="memo-title">MEMO (その他、買い忘れなど)</div>
                </div>
            """

            # 画面への表示
            st.markdown(cards_html + memo_html, unsafe_allow_html=True)
            
            # 印刷専用エリア（CSSで印刷時のみ表示される）
            st.markdown(f"""
                <div class="print-only">
                    <h1 style="font-family: 'Noto Sans JP'; font-weight: 100; text-align: center; font-size: 2.2rem; letter-spacing: 0.5rem;">献だけ</h1>
                    <div style="font-size: 0.9rem; text-align: right; margin-bottom: 10px;">{start_date.strftime('%Y/%m/%d')} 週</div>
                    {cards_html}
                    {memo_html}
                </div>
            """, unsafe_allow_html=True)
            
            st.success("リスト完成。ブラウザの『印刷』からA4出力できます。")
        else:
            st.info("メニューを選択してください。")

with tab_manage:
    st.subheader("⚙️ メニュー管理")
    with st.form("add", clear_on_submit=True):
        n = st.text_input("料理名")
        c = st.selectbox("カテゴリー", cats)
        m = st.text_area("材料（「、」区切り）")
        if st.form_submit_button("保存"):
            if n and m:
                new_df = pd.concat([df_menu, pd.DataFrame([[n, c, m]], columns=df_menu.columns)], ignore_index=True)
                csv_b64 = base64.b64encode(new_df.to_csv(index=False, encoding="utf-8-sig").encode("utf-8")).decode("utf-8")
                res = requests.put(f"https://api.github.com/repos/{REPO}/contents/{FILE}", 
                    headers={"Authorization": f"token {TOKEN}"},
                    json={"message": f"Add {n}", "content": csv_b64, "sha": sha})
                if res.status_code == 200:
                    st.cache_data.clear()
                    st.rerun()
    st.dataframe(df_menu, use_container_width=True)
