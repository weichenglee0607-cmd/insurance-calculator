import streamlit as st
import pandas as pd

# 網頁基礎設定
st.set_page_config(page_title="專業保單診斷系統", layout="wide")

st.title("🛡️ 客戶保障診斷系統")

# 1. 側邊欄資料輸入
with st.sidebar:
    st.header("👤 客戶資料")
    name = st.text_input("客戶姓名", value="吳○君")
    age = st.number_input("年齡", value=30)
    st.info("💡 您可以直接在右側表格增減保單內容")

# 2. 現有保單明細 (依據您提供的 PDF 資料)
st.subheader(f"📋 {name} 的保單明細")

data = {
    "保險項目": ["LTN 長照終身", "ADE 意外失能", "AHI 意外住院", "HSME 醫療實支", "OMR 意外實支", "SDCA 重大傷病", "WP 豁免附約"],
    "保險金額": ["10,000元", "1,000,000元", "20單位", "1單位", "100,000元", "2,000,000元", "-"],
    "保費": [25930, 980, 1100, 21159, 1974, 14400, 1028],
    "期滿(民國)": [143, 164, 164, 169, 164, 123, 143]
}

df = pd.DataFrame(data)

# 讓表格可動態編輯
edited_df = st.data_editor(df, num_rows="dynamic", use_container_width=True)

# 3. 計算總額
st.divider()
total_premium = edited_df["保費"].sum()

c1, c2 = st.columns(2)
with c1:
    st.metric("年度總保費", f"{total_premium:,} 元")
with c2:
    st.write(f"📅 每月負擔約 **{int(total_premium/12):,}** 元")

st.bar_chart(edited_df.set_index("保險項目")["保費"])
