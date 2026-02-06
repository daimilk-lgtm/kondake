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

# --- 2. デザイン定義 ---
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

    for i, day_tab in enumerate(days_tabs):
        d_str = (start_date + timedelta(days=i)).strftime("%m/%d")
        with day_tab:
            st.markdown(f"##### {d_str} ({day_labels[i]})")
            day_menu = {cat: st.selectbox(cat, ["なし"] + df_menu[df_menu["カテゴリー"] == cat]["料理名"].tolist(), key=f"s_{i}_{cat}") for cat in cats}
            weekly_plan[d_str] = day_menu

    if st.button("確定して買い物リストを生成", type="primary", use_container_width=True):
        st.divider()
        
        # --- データ集計ロジック ---
        all_ings_list = []
        plan_table_html = '<table style="width:100%; border-collapse:collapse; margin-bottom:20px; font-size:0.8rem; border:1px solid #eee;">'
        plan_table_html += '<tr style="background:#fafafa;"><th>日付</th><th>主菜</th><th>副菜・汁物</th></tr>'
        
        for i, (d_str, v) in enumerate(weekly_plan.items()):
            day_dishes = []
            for cat, dish in v.items():
                if dish != "なし":
                    day_dishes.append(dish)
                    ing_raw = df_menu[df_menu["料理名"] == dish]["材料"].iloc[0]
                    items = str(ing_raw).replace("、", ",").split(",")
                    all_ings_list.extend([x.strip() for x in items if x.strip()])
            
            # 献立表の行を作成
            main_dishes = f"{v.get('主菜1','-')} / {v.get('主菜2','-')}".replace("なし", "-")
            sub_dishes = f"{v.get('副菜1','-')}, {v.get('副菜2','-')}, {v.get('汁物','-')}".replace("なし", "-")
            plan_table_html += f'<tr><td style="border:1px solid #eee; padding:5px;">{d_str}({day_labels[i]})</td><td style="border:1px solid #eee; padding:5px;">{main_dishes}</td><td style="border:1px solid #eee; padding:5px;">{sub_dishes}</td></tr>'
        
        plan_table_html += '</table>'

        if all_ings_list:
            counts = pd.Series(all_ings_list).value_counts()
            result_data = []
            for item, count in counts.items():
                category = "99未分類"
                if df_dict is not None:
                    for _, row in df_dict.iterrows():
                        if row["材料"] in item: category = row["種別"]; break
                display_name = f"{item} × {count}" if count > 1 else item
                result_data.append({"name": display_name, "cat": category})
            
            df_res = pd.DataFrame(result_data).sort_values("cat")

            # 買い物カードHTML生成
            cards_html = ""
            for cat, group in df_res.groupby("cat"):
                items_html = "".join([f'<div style="font-size:1.1rem; padding:4px 0; border-bottom:0.5px solid #f9f9f9;">□ {row["name"]}</div>' for _, row in group.iterrows()])
                cards_html += f'<div style="border:1px solid #eee; padding:15px; border-radius:12px; margin-bottom:10px; break-inside:avoid;"><div style="font-size:0.8rem; color:#999;">{cat}</div>{items_html}</div>'
            
            memo_html = '<div style="margin-top:20px; padding:20px; border:1px dashed #ccc; border-radius:10px; min-height:100px;"><div style="font-size:0.9rem; color:#999;">MEMO</div></div>'

            # --- 画面表示 ---
            st.markdown("### 🛒 買い物リスト")
            st.markdown(cards_html + memo_html, unsafe_allow_html=True)
            
            # 印刷用隠しエリア（献立表 + 買い物リスト + メモ）
            printable_content = f'<div id="printable-area"><h2 style="text-align:center; font-weight:100;">献だけ</h2><p style="text-align:right; font-size:0.8rem;">{start_date.strftime("%Y/%m/%d")} 週</p><h4 style="border-bottom:1px solid #333;">今週の献立</h4>{plan_table_html}<h4 style="border-bottom:1px solid #333;">買い物リスト</h4>{cards_html}{memo_html}</div>'
            st.markdown(f'<div style="display:none;">{printable_content}</div>', unsafe_allow_html=True)
            
            # 印刷ボタン
            st.components.v1.html(f"""
                <script>
                function printList() {{
                    var content = window.parent.document.getElementById("printable-area").innerHTML;
                    var win = window.open('', '', 'height=700,width=900');
                    win.document.write('<html><head><title>印刷</title>');
                    win.document.write('<style>body{{font-family:"Noto Sans JP",sans-serif; padding:20px; color:#333;}} table{{width:100%; border-collapse:collapse;}} th,td{{border:1px solid #eee; padding:5px; text-align:left;}}</style>');
                    win.document.write('</head><body>');
                    win.document.write(content);
                    win.document.write('</body></html>');
                    win.document.close();
                    win.print();
                }}
                </script>
                <button onclick="printList()" style="width:100%; padding:12px; background:#333; color:white; border:none; border-radius:10px; cursor:pointer; font-weight:bold;">この内容をA4印刷する</button>
            """, height=65)
        else:
            st.info("メニューを選択してください。")

with tab_manage:
    st.subheader("⚙️ メニュー登録")
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
