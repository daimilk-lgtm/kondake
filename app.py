import streamlit as st
import pandas as pd
from datetime import datetime, timedelta

# GitHub上のCSV（売場辞書）のURL
CSV_URL = "https://raw.githubusercontent.com/daimilk-lgtm/kondake/main/ingredients.csv"

def get_week_dates(start_date):
    wdays = ["日", "月", "火", "水", "木", "金", "土"]
    dates = []
    for i in range(7):
        target_date = start_date + timedelta(days=i)
        w_idx = (target_date.weekday() + 1) % 7
        dates.append(target_date.strftime(f"%m/%d({wdays[w_idx]})"))
    return dates

# --- 1. デザイン定義（細身のフォント・角丸・カードUI） ---
st.set_page_config(page_title="献だけ", layout="centered")

st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Noto+Sans+JP:wght@100;300;400&display=swap');
    
    /* フォントウェイト300を基本に設定 */
    html, body, [class*="css"], p, div, select, input, label, span, .stCheckbox {
        font-family: 'Noto Sans JP', sans-serif !important;
        font-weight: 300 !important;
        color: #333;
    }
    
    /* 極細タイトルロゴ(100) */
    .main-title {
        font-family: 'Noto Sans JP', sans-serif !important;
        font-weight: 100 !important;
        font-size: 3.2rem;
        letter-spacing: 0.8rem;
        text-align: center;
        margin: 40px 0;
    }

    /* 角丸モダンな入力欄 */
    .stTextInput input, .stTextArea textarea {
        border-radius: 12px !important;
        border: 1px solid #eee !important;
        background-color: #fafafa !important;
    }

    /* 買い物リストの整理されたカード形式 */
    .shopping-card {
        background-color: #ffffff;
        padding: 20px;
        border-radius: 16px;
        border: 1px solid #f0f0f0;
        margin-bottom: 20px;
        box-shadow: 0 4px 12px rgba(0,0,0,0.03);
    }

    .category-label {
        font-size: 0.8rem;
        font-weight: 400;
        color: #999;
        letter-spacing: 0.1rem;
        margin-bottom: 8px;
    }

    .item-row {
        font-size: 1.2rem;
        font-weight: 300;
        padding: 5px 0;
        border-bottom: 0.5px solid #f9f9f9;
    }
</style>
""", unsafe_allow_html=True)

st.markdown('<h1 class="main-title">献だけ</h1>', unsafe_allow_html=True)

# --- 2. 日付・献立カテゴリー設定 ---
today = datetime.now()
offset = (today.weekday() + 1) % 7
default_sun = today - timedelta(days=offset)

col_d, _ = st.columns([1, 2])
with col_d:
    start_date = st.date_input("開始日（日）", value=default_sun)

week_labels = get_week_dates(start_date)
menu_cats = ["主菜1", "主菜2", "副菜1", "副菜2", "汁物"]

st.divider()
st.markdown("### 🗓 1週間の献立作成")

# 7日間のタブ入力
days_tabs = st.tabs([f"{label}" for label in week_labels])
all_items = []

for i, day_tab in enumerate(days_tabs):
    with day_tab:
        # 5つのカテゴリー別献立入力
        for cat in menu_cats:
            st.text_input(f"{cat}", key=f"menu_{i}_{cat}", placeholder=f"{cat}を入力")
        
        st.markdown("---")
        # 材料入力（ここで入力したものが買い物リストに並ぶ）
        items_raw = st.text_area("材料（改行区切り）", key=f"items_{i}", height=120, placeholder="人参\n豚バラ")
        
        if items_raw:
            all_items.extend([j.strip() for j in items_raw.splitlines() if j.strip()])

# --- 3. 買い物リスト生成（売場順ソート） ---
if st.button("確定して買い物リストを生成", type="primary", use_container_width=True):
    st.divider()
    st.markdown("### 🛒 買い物リスト（売場順）")
    
    if all_items:
        try:
            # GitHubから辞書を取得
            df_dict = pd.read_csv(CSV_URL)
            unique_items = sorted(list(set(all_items)))
            
            result_data = []
            for item in unique_items:
                category = "99未分類"
                # 部分一致ロジックで売場を特定
                for _, row in df_dict.iterrows():
                    if row["材料"] in item:
                        category = row["種別"]
                        break
                result_data.append({"name": item, "cat": category})
            
            # カテゴリー（売場）順に並べ替え
            df_res = pd.DataFrame(result_data).sort_values("cat")

            # 売場ごとにカード表示
            for cat, group in df_res.groupby("cat"):
                items_html = "".join([f'<div class="item-row">□ {row["name"]}</div>' for _, row in group.iterrows()])
                st.markdown(f"""
                    <div class="shopping-card">
                        <div class="category-label">{cat}</div>
                        {items_html}
                    </div>
                """, unsafe_allow_html=True)
                
            st.success("最短ルートの買い物リストが完成しました。")
            
        except Exception as e:
            st.error(f"データの読み込みに失敗しました。ingredients.csvがGitHubに存在するか確認してください。")
    else:
        st.info("材料が入力されていません。")
