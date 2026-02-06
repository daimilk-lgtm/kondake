import streamlit as st
import pandas as pd
from datetime import datetime, timedelta

# CSVデータの取得先
CSV_URL = "https://raw.githubusercontent.com/daimilk-lgtm/kondake/main/ingredients.csv"

def get_week_dates(start_date):
    # 日本語の曜日リスト
    wdays = ["月", "火", "水", "木", "金", "土", "日"]
    dates = []
    for i in range(7):
        target_date = start_date + timedelta(days=i)
        w_idx = target_date.weekday()
        dates.append(target_date.strftime(f"%m/%d({wdays[w_idx]})"))
    return dates

st.set_page_config(page_title="献だけ", layout="wide")
st.title("献だけ")

# 1. 日付指定（日曜始まりなどを想定）
selected_date = st.date_input("開始日を選択してください", datetime.now())
week_labels = get_week_dates(selected_date)

# 2. 献立入力エリア
st.header("1. 献立と材料を入力")
cols = st.columns(7)
all_items = []

for i, col in enumerate(cols):
    with col:
        st.write(f"**{week_labels[i]}**")
        st.text_input("献立", key=f"menu_{i}")
        items_raw = st.text_area("材料(改行区切り)", key=f"items_{i}", height=150)
        if items_raw:
            all_items.extend([item.strip() for item in items_raw.splitlines() if item.strip()])

# 3. リスト生成ボタン
if st.button("買い物リストを生成"):
    st.header("2. 整理された買い物リスト")
    
    if all_items:
        unique_items = list(set(all_items)) # 重複カット
        
        try:
            # GitHubから最新の辞書(CSV)を読み込む
            df_dict = pd.read_csv(CSV_URL)
            
            result_data = []
            for item in unique_items:
                # 辞書から種別を検索
                match = df_dict[df_dict["材料"] == item]
                category = match.iloc[0]["種別"] if not match.empty else "99未分類"
                result_data.append({"材料": item, "種別": category})
            
            # データフレームにして種別順にソート
            df_res = pd.DataFrame(result_data).sort_values("種別")
            
            # 種別ごとに表示
            for cat, group in df_res.groupby("種別"):
                st.markdown(f"### {cat}")
                for _, row in group.iterrows():
