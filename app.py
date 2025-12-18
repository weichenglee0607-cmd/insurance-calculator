import streamlit as st
import pandas as pd
import io
import pdfplumber
import plotly.graph_objects as go
from PIL import Image

st.set_page_config(page_title="AI 專業保單診斷系統", layout="wide")

# --- 1. 自動校準功能 (關鍵修復) ---
def clean_data(df):
    """清理資料，確保數值與類別能被系統辨識"""
    # 統一欄位名稱
    mapping = {
        "保費": ["保費", "保費 (年繳)", "年繳保費", "金額", "保費(年繳)"],
        "理賠": ["理賠", "預估理賠額 (萬)", "預估理賠額(萬)", "保障額度", "保額", "預估理賠額"],
        "類別": ["類別", "保障類別", "險種類型", "種類"]
    }
    for target, aliases in mapping.items():
        for alias in aliases:
            if alias in df.columns and target not in df.columns:
                df[target] = df[alias]
    
    # 清理數值：移除「萬」、「元」或逗號，並轉為數字
    if "理賠" in df.columns:
        df["理賠"] = df["理賠"].astype(str).str.replace(r'[^\d.]', '', regex=True)
        df["理賠"] = pd.to_numeric(df["理賠"], errors='coerce').fillna(0)
    if "保費" in df.columns:
        df["保費"] = df["保費"].astype(str).str.replace(r'[^\d.]', '', regex=True)
        df["保費"] = pd.to_numeric(df["保費"], errors='coerce').fillna(0)
        
    return df

if 'current_df' not in st.session_state:
    st.session_state['current_df'] = pd.DataFrame([
        {"姓名": "張曉明", "險種名稱": "範例保單", "類別": "醫療", "保費 (年繳)": 0, "預估理賠額 (萬)": 0}
    ])

# --- 2. 側邊欄 ---
with st.sidebar:
    st.header("👤 基本資料")
    st.session_state['c_age'] = st.number_input("投保年齡", value=st.session_state.get('c_age', 27))
    st.session_state['c_gender'] = st.selectbox("性別", ["男", "女"])
    st.divider()
    uploaded_file = st.file_uploader("載入檔案 (Excel/PDF/圖片)", type=["pdf", "xlsx", "png", "jpg", "jpeg"])
    mode = st.radio("功能切換：", ["1. 資料錄入", "2. 診斷報告"])

# --- 3. 模式 1：資料錄入 ---
if mode == "1. 資料錄入":
    df = st.session_state['current_df']
    name = df['姓名'].iloc[0] if not df.empty and '姓名' in df.columns else "新客戶"
    st.header(f"📝 {name} 的保單明細表")
    
    edited_df = st.data_editor(st.session_state['current_df'], num_rows="dynamic", use_container_width=True, key="pro_editor")
    st.session_state['current_df'] = edited_df
    
    if uploaded_file and uploaded_file.name.endswith('.xlsx'):
        if st.button("🚀 確認匯入 Excel"):
            loaded_df = pd.read_excel(uploaded_file)
            st.session_state['current_df'] = loaded_df
            st.success("匯入成功，請切換至診斷報告查看圖表！")
            st.rerun()

# --- 4. 模式 2：診斷報告 (修正 0 萬問題) ---
elif mode == "2. 診斷報告":
    df = st.session_state['current_df'].copy()
    df = clean_data(df) # 執行深度清理
    
    name = df['姓名'].iloc[0] if not df.empty and '姓名' in df.columns else "客戶"
    st.header(f"📊 {name} 先生/小姐 專屬保障診斷報告")
    
    total_p = df["保費"].sum()
    total_benefit = df["理賠"].sum()
    
    c1, c2, c3 = st.columns(3)
    c1.metric("年度總保費", f"{total_p:,.0f} 元")
    c2.metric("預估總保障額度", f"{total_benefit:,.0f} 萬元")
    c3.metric("投保年齡", f"{st.session_state['c_age']} 歲")

    st.divider()
    
    l_col, r_col = st.columns([1.2, 1])
    # 定義標準類別與模糊匹配關鍵字
    cat_map = {"壽險": "壽", "意外": "意外", "醫療": "醫", "重疾": "重|疾|傷", "長照": "長|照"}
    
    if '類別' in df.columns:
        # 轉成字串並清理空格以利比對
        df['類別'] = df['類別'].astype(str).str.strip()
        vals = []
        for label, keyword in cat_map.items():
            # 使用模糊比對，只要類別中包含關鍵字就加總
            val = df[df['類別'].str.contains(keyword, na=False, regex=True)]["理賠"].sum()
            vals.append(val)
        
        with l_col:
            fig = go.Figure(data=go.Scatterpolar(r=vals, theta=list(cat_map.keys()), fill='toself', line_color='#1f77b4'))
            # 動態調整雷達圖刻度，確保圖形不會縮太小
            max_val = max(vals) if max(vals) > 0 else 100
            fig.update_layout(polar=dict(radialaxis=dict(visible=True, range=[0, max_val * 1.2])), showlegend=False)
            st.plotly_chart(fig, use_container_width=True)
            
        with r_col:
            st.subheader("💡 專家診斷建議")
            for label, v in zip(cat_map.keys(), vals):
                if v == 0: st.error(f"❌ **{label}缺口**：尚未規畫保障")
                elif v < 100: st.warning(f"⚠️ **{label}偏低**：目前僅 {v:,.0f} 萬")
                else: st.success(f"✅ **{label}充足**：已備 {v:,.0f} 萬保障")
    else:
        st.error("表格缺少『類別』欄位，請返回錄入頁確認。")
