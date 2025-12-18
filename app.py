import streamlit as st
import pandas as pd
import io
import pdfplumber
import plotly.graph_objects as go
from PIL import Image

st.set_page_config(page_title="AI 專業保單診斷系統", layout="wide")

# --- 1. 核心欄位標準化 ---
def standardize_df(df):
    """自動校準欄位名稱，解決抓不到資料的問題"""
    # 建立映射表
    mapping = {
        "保費": ["保費", "保費 (年繳)", "年繳保費", "金額"],
        "理賠": ["理賠", "預估理賠額 (萬)", "預估理賠額(萬)", "保障額度", "保額"],
        "類別": ["類別", "保障類別", "險種"]
    }
    for target, aliases in mapping.items():
        for alias in aliases:
            if alias in df.columns and target not in df.columns:
                df[target] = df[alias]
    return df

if 'current_df' not in st.session_state:
    st.session_state['current_df'] = pd.DataFrame([
        {"姓名": "張曉明", "險種名稱": "範例保單", "類別": "醫療", "保費 (年繳)": 0, "預估理賠額 (萬)": 0}
    ])

# --- 2. 側邊欄 ---
with st.sidebar:
    st.header("👤 客戶資料")
    st.session_state['c_age'] = st.number_input("投保年齡", value=st.session_state.get('c_age', 27))
    st.session_state['c_gender'] = st.selectbox("性別", ["男", "女"])
    st.divider()
    uploaded_file = st.file_uploader("載入檔案", type=["pdf", "xlsx", "png", "jpg", "jpeg"])
    mode = st.radio("功能切換：", ["1. 資料錄入", "2. 診斷報告"])

# --- 3. 模式 1：資料錄入 ---
if mode == "1. 資料錄入":
    df = st.session_state['current_df']
    name = df['姓名'].iloc[0] if not df.empty and '姓名' in df.columns else "新客戶"
    st.header(f"📝 {name} 的保單明細表")
    
    edited_df = st.data_editor(st.session_state['current_df'], num_rows="dynamic", use_container_width=True, key="fixed_editor")
    st.session_state['current_df'] = edited_df
    
    if uploaded_file and uploaded_file.name.endswith('.xlsx'):
        if st.button("確認從 Excel 匯入"):
            loaded_df = pd.read_excel(uploaded_file)
            st.session_state['current_df'] = loaded_df
            st.rerun()

# --- 4. 模式 2：診斷報告 (解決 0 萬與空圖問題) ---
elif mode == "2. 診斷報告":
    df = st.session_state['current_df'].copy()
    df = standardize_df(df) # 執行欄位自動校準
    
    name = df['姓名'].iloc[0] if not df.empty and '姓名' in df.columns else "客戶"
    
    st.header(f"📊 {name} 先生/小姐 專屬保障診斷報告")
    
    # 強制轉換數值，確保計算不是 0
    df["保費"] = pd.to_numeric(df.get("保費", 0), errors='coerce').fillna(0)
    df["理賠"] = pd.to_numeric(df.get("理賠", 0), errors='coerce').fillna(0)
    
    total_p = df["保費"].sum()
    total_benefit = df["理賠"].sum()
    
    c1, c2, c3 = st.columns(3)
    c1.metric("年度總保費", f"{total_p:,} 元")
    c2.metric("預估總保障額度", f"{total_benefit:,.0f} 萬元")
    c3.metric("投保年齡", f"{st.session_state['c_age']} 歲")

    st.divider()
    
    # 雷達圖邏輯
    l_col, r_col = st.columns([1.2, 1])
    cats = ["壽險", "意外", "醫療", "重疾", "長照"]
    
    # 檢查類別資料是否存在
    if '類別' in df.columns:
        vals = [df[df['類別'].str.contains(c, na=False)]["理賠"].sum() for c in cats]
        
        with l_col:
            fig = go.Figure(data=go.Scatterpolar(r=vals, theta=cats, fill='toself', line_color='#1f77b4'))
            fig.update_layout(polar=dict(radialaxis=dict(visible=True, range=[0, max(vals)*1.2 if max(vals)>0 else 100])))
            st.plotly_chart(fig, use_container_width=True)
            
        with r_col:
            st.subheader("💡 診斷建議")
            for c, v in zip(cats, vals):
                if v == 0: st.error(f"❌ **{c}缺口**：尚未規劃")
                elif v < 100: st.warning(f"⚠️ **{c}偏低**：現有 {v} 萬")
                else: st.success(f"✅ **{c}充足**：已備 {v} 萬")
    else:
        st.error("請在第一頁確認是否有『類別』欄位，且填寫了壽險/意外/醫療等關鍵字。")
