import streamlit as st
import pandas as pd
from datetime import datetime, timedelta

CSV_URL = "https://raw.githubusercontent.com/daimilk-lgtm/kondake/main/ingredients.csv"

def get_week_dates(start_date):
    wdays = ["月", "火", "水", "木", "金", "土", "日"]
    return [(start_date + timedelta(days=i)).strftime(f"%m/%d({wdays[(start_date + timedelta(days=i)).weekday()]})") for i in range(7)]

st.set_page_config(page_title="献だけ", layout="wide")
st.title("献だけ")

selected_date = st.date_input("開始日を選択", datetime.now())
week_labels = get_week_dates(selected_date)

st.header("1. 献立と材料を入力")
cols = st.columns(7)
all_items = []
for i, col in enumerate(cols):
    with col:
        st.write(f"**{week_labels[i]}**")
        st.text_input("献立", key=f"menu_{i}")
        items_raw = st.text_area("材料", key=f"items_{i}", height=150)
        if items_raw:
            all_items.extend([item.strip() for item in items_raw.splitlines() if item.strip()])

if st.button("確定して印刷用表示"):
    st.header("🛒 買い物リスト")
    if all_items:
        try:
            df_dict = pd.read_csv(CSV_URL)
            result_data = []
            for item in list(set(all_items)):
                category = "99未分類"
                # 「人参 × 2」のように個数があっても「人参」が含まれていればマッチさせる判定
                for _, row in df_dict.iterrows():
                    if row["材料"] in item:
                        category = row["種別"]
                        break
                result_data.append({"表示名": item, "種別": category})
            
            df_res = pd.DataFrame(result_data).sort_values("種別")
            
            # 見やすさの改善：2列表示
            list_cols = st.columns(2)
            for idx, (cat, group) in enumerate(df_res.groupby("種別")):
                with list_cols[idx % 2]:
                    # 「種別名：材料」の形式で表示
                    st.markdown(f"#### 【{cat}】")
                    for _, row in group.iterrows():
                        st.write(f"□ {row['表示名']}")
            
            st.success("印刷準備完了。ブラウザの「印刷」からA4で出力できます。")
        except Exception as e:
            st.error(f"エラー: {e}")
