import streamlit as st
import pandas as pd
from datetime import datetime, timedelta

# CSVデータの取得先
CSV_URL = "https://raw.githubusercontent.com/daimilk-lgtm/kondake/main/ingredients.csv"

def get_week_dates(start_date):
    wdays = ["月", "火", "水", "木", "金", "土", "日"]
    dates = []
    for i in range(7):
        target_date = start_date + timedelta(days=i)
        w_idx = target_date.weekday()
        dates.append(target_date.strftime(f"%m/%d({wdays[w_idx]})"))
    return dates

st.set_page_config(page_title="献だけ", layout="wide")
st.title("献だけ")

# 1. 日付指定
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
if st.button("確定して印刷用表示"):
    st.header("🛒 買い物リスト")
    
    if all_items:
        unique_items = list(set(all_items))
        
        try:
            df_dict = pd.read_csv(CSV_URL)
            result_data = []
            
            for input_item in unique_items:
                category = "99未分類"
                # あいまい検索：入力された文字の中に、辞書の材料名が含まれているか判定
                for _, row in df_dict.iterrows():
                    if row["材料"] in input_item:
                        category = row["種別"]
                        break
                result_data.append({"表示名": input_item, "種別": category})
            
            # 種別でソート
            df_res = pd.DataFrame(result_data).sort_values("種別")
            
            # 元のデザイン（1列表示）を維持
            for cat, group in df_res.groupby("種別"):
                # ご要望の「種別：材料名」のスタイル
                st.markdown(f"### {cat}")
                for _, row in group.iterrows():
                    st.write(f"□ {row['表示名']}")
                    
            st.info("印刷準備完了。ブラウザの「印刷」からA4で出力できます。")
                    
        except Exception as e:
            st.error(f"データの読み込みに失敗しました: {e}")
    else:
        st.info("材料が入力されていません。")
