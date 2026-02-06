import streamlit as st
import pandas as pd
import os
from collections import Counter

DATA_FILE = "menu_data.csv"

def seed_data():
    samples = {
        "料理名": ["ハンバーグ", "生姜焼き", "カレー", "肉じゃが", "焼き魚", "刺身", "唐揚げ", "ステーキ", "餃子", "麻婆豆腐", "冷奴", "ポテトサラダ", "ひじき煮", "きんぴらごぼう", "ほうれん草お浸し", "ナムル", "冷やしトマト", "厚揚げ焼き", "大根サラダ", "枝豆", "味噌汁", "豚汁", "わかめスープ", "なめこ汁", "卵スープ"],
        "カテゴリー": ["主菜1", "主菜1", "主菜1", "主菜1", "主菜1", "主菜2", "主菜2", "主菜2", "主菜2", "主菜2", "副菜1", "副菜1", "副菜1", "副菜1", "副菜1", "副菜2", "副菜2", "副菜2", "副菜2", "副菜2", "汁物", "汁物", "汁物", "汁物", "汁物"],
        "材料": ["合挽肉,1/玉ねぎ,1", "豚肉,1/生姜,1", "豚肉,1/玉ねぎ,1", "牛肉,1/じゃがいも,2", "魚,1", "刺身,1", "鶏肉,1", "牛肉,1", "豚ひき肉,1/キャベツ,1", "豆腐,1/ひき肉,1", "豆腐,1/ネギ,1", "じゃがいも,2", "ひじき,1", "ごぼう,1", "ほうれん草,1", "もやし,1", "トマト,1", "厚揚げ,1", "大根,1", "枝豆,1", "豆腐,1/味噌,1", "豚肉,1/大根,1", "わかめ,1", "なめこ,1", "卵,1"]
    }
    pd.DataFrame(samples).to_csv(DATA_FILE, index=False)

if not os.path.exists(DATA_FILE):
    seed_data()

df = pd.read_csv(DATA_FILE)

# --- UIデザイン（細字徹底・タイトル復旧・見出し英語） ---
st.set_page_config(page_title="献だけ", layout="centered")

st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Noto+Sans+JP:wght@100;300&display=swap');

    /* 全体を細字(100-300)で統一。太字を一切排除 */
    html, body, [class*="css"], .stMarkdown, p, label, .stSelectbox, .stButton, table, h1, h2, h3 {
        font-family: 'Noto Sans JP', sans-serif !important;
        font-weight: 100 !important; /* 可能な限り細く */
        color: #444;
    }

    .main { background-color: #ffffff; }
    
    h1 { 
        text-align: center; 
        letter-spacing: 0.4em; 
        padding: 40px 0; 
        font-size: 2.2rem;
    }
    
    h2 {
        font-size: 1.1rem;
        border-bottom: 0.5px solid #eee;
        padding-bottom: 10px;
        margin-top: 40px;
        letter-spacing: 0.2em;
        text-align: center;
    }

    .print-area { padding: 20px; }

    @media print {
        .no-print, .stButton, .stTabs, [data-testid="stSidebar"], header, footer { display: none !important; }
        .print-area { display: block !important; width: 100% !important; border: none; padding: 0; }
    }
    </style>
""", unsafe_allow_html=True)

st.title("献だけ")

# --- 入力エリア ---
st.markdown('<div class="no-print">', unsafe_allow_html=True)
weekdays = ["月", "火", "水", "木", "金", "土", "日"]
cats = ["主菜1", "主菜2", "副菜1", "副菜2", "汁物"]
weekly_selections = {}

tabs = st.tabs(weekdays)
for i, day in enumerate(weekdays):
    with tabs[i]:
        day_picks = []
        cols = st.columns(5)
        for j, cat in enumerate(cats):
            opts = ["なし"] + sorted(df[df["カテゴリー"] == cat]["料理名"].tolist())
            p = cols[j].selectbox(cat, opts, key=f"{day}_{cat}")
            day_picks.append(p)
        weekly_selections[day] = day_picks

memo = st.text_area("Memo", placeholder="...")
st.markdown('</div>', unsafe_allow_html=True)

# --- 生成エリア ---
if st.button("生成", use_container_width=True):
    total = Counter()
    st.markdown('<div class="print-area">', unsafe_allow_html=True)
    
    st.markdown("<h2>MENU</h2>", unsafe_allow_html=True)
    res_table = [[f"{d}"] + [v if v != "なし" else "-" for v in weekly_selections[d]] for d in weekdays]
    st.table(pd.DataFrame(res_table, columns=["曜"] + cats))

    st.markdown("<h2>SHOPPING LIST</h2>", unsafe_allow_html=True)
    for day, dishes in weekly_selections.items():
        for p in dishes:
            if p != "なし":
                row = df[df["料理名"] == p]
                if not row.empty:
                    for it in str(row["材料"].values[0]).split("/"):
                        if "," in it:
                            parts = it.split(",")
                            name = parts[0]
                            num = ''.join(filter(str.isdigit, parts[1] if len(parts)>1 else "1"))
                            total[name.strip()] += int(num) if num else 1
                        else: total[it.strip()] += 1
    
    l_col, r_col = st.columns(2)
    items = sorted(total.items())
    for i, (n, c) in enumerate(items):
        target = l_col if i < len(items)/2 else r_col
        target.markdown(f"□ {n} ({c})")
    
    if memo:
        st.markdown("<br><p style='font-size: 0.8rem; text-align: center; color: #999;'>"+memo+"</p>", unsafe_allow_html=True)
    
    st.markdown('</div>', unsafe_allow_html=True)

# --- サイドバー ---
with st.sidebar:
    if st.button("Reset"):
        seed_data(); st.rerun()
    with st.expander("Add"):
        n_in = st.text_input("Name")
        c_in = st.selectbox("Category", cats)
        i_in = st.text_area("Ingredients")
        if st.button("Save"):
            if n_in and i_in:
                df = pd.concat([df, pd.DataFrame({"料理名":[n_in],"カテゴリー":[c_in],"材料":[i_in]})], ignore_index=True)
                df.to_csv(DATA_FILE, index=False); st.rerun()
