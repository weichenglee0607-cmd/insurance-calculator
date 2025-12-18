import streamlit as st
import pandas as pd
import io
import pdfplumber
import plotly.graph_objects as go
from PIL import Image

st.set_page_config(page_title="AI 專業保單診斷系統", layout="wide")

# --- 1. AI 強化辨識功能 ---
def advanced_clean_df(df):
    """強化版資料清理：自動校準名稱、清理數值、關鍵字語意辨識"""
    # 欄位對應
    mapping = {
        "姓名": ["姓名", "客戶姓名"],
        "險種名稱": ["險種名稱", "商品名稱", "保險名稱", "險種"],
        "保費": ["保費", "保費 (年繳)", "保費(年繳)", "年繳保費"],
        "理賠": ["理賠", "預估理賠額 (萬)", "預估理賠額(萬)", "保障額度", "保額"],
        "類別": ["類別", "保障類別", "種類"]
    }
    for target, aliases in mapping.items():
        for alias in aliases:
            if alias in df.columns and target not in df.columns:
                df[target] = df[alias]
    
    # 數值清理 (移除 萬, 元, 逗號)
    for col in ["保費", "理賠"]:
        if col in df.columns:
            df[col] = df[col].astype(str).str.replace(r'[^\d.]', '', regex=True)
            df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
            
    # 如果缺少類別欄位，先建立空的
    if "類別" not in df.columns:
        df["類別"] = ""
    else:
        df["類別"] = df["類別"].fillna("")
        
    return df

# --- 2. 初始化 ---
if 'main_df' not in st.session_state:
    st.session_state['main_df'] = pd.DataFrame([
        {"姓名": "張曉明", "險種名稱": "長期照顧終身保險", "類別": "", "保費": 31720, "理賠": 20}
    ])

# --- 3. 側邊欄 ---
with st.sidebar:
    st.header("👤 客戶基本資料")
    st.session_state['age'] = st.number_input("投保年齡", value=st.session_state.get('age', 27))
    st.session_state['gender'] = st.selectbox("性別", ["男", "女"])
    st.divider()
    uploaded_file = st.file_uploader("📂 載入檔案 (Excel/PDF/圖片)", type=["pdf", "xlsx", "png", "jpg", "jpeg"])
    mode = st.radio("功能切換：", ["1. 資料錄入", "2. 診斷報告"])

# --- 4. 模式 1：資料錄入 ---
if mode == "1. 資料錄入":
    df_current = st.session_state['main_df']
    name = df_current['姓名'].iloc[0] if not df_current.empty and '姓名' in df_current.columns else "新客戶"
    st.header(f"📝 {name} 的保單明細表")
    
    edited_df = st.data_editor(st.session_state['main_df'], num_rows="dynamic", use_container_width=True, key="editor_v_final")
    st.session_state['main_df'] = edited_df

    if uploaded_file and uploaded_file.name.endswith('.xlsx'):
        if st.button("🚀 確認匯入此 Excel 資料"):
            new_data = pd.read_excel(uploaded_file)
            st.session_state['main_df'] = advanced_clean_df(new_data)
            st.rerun()

# --- 5. 模式 2：診斷報告 (強化辨識邏輯) ---
elif mode == "2. 診斷報告":
    df = st.session_state['main_df'].copy()
    df = advanced_clean_df(df)
    
    name = df['姓名'].iloc[0] if not df.empty and '姓名' in df.columns else "客戶"
    st.header(f"📊 {name} 專屬保障診斷報告")
    
    # 數值計算
    total_p = df["保費"].sum()
    total_benefit = df["理賠"].sum()
    
    c1, c2, c3 = st.columns(3)
    c1.metric("年度總保費", f"{total_p:,.0f} 元")
    c2.metric("預估總保障額度", f"{total_benefit:,.0f} 萬元")
    c3.metric("投保年齡", f"{st.session_state['age']} 歲")

    st.divider()
    
    # --- 關鍵：強化版類別辨識邏輯 ---
    l, r = st.columns([1.2, 1])
    # 擴充關鍵字庫，涵蓋更多保險實務名稱
    cat_rules = {
        "壽險": "壽|身故|祝壽",
        "意外": "意外|傷害|骨折|意外醫療",
        "醫療": "醫療|住院|手術|實支實付|日額",
        "重疾": "重|疾|傷|癌症|癌|重大傷病|重大疾病",
        "長照": "長|照|長期照顧|失能|扶助|看護"
    }
    
    vals = []
    for label, pattern in cat_rules.items():
        # 同時掃描「類別」欄位與「險種名稱」欄位
        mask_cat = df['類別'].astype(str).str.contains(pattern, na=False, regex=True)
        mask_name = df['險種名稱'].astype(str).str.contains(pattern, na=False, regex=True)
        
        # 只要其中一個欄位符合，就計入該保障類別
        val = df[mask_cat | mask_name]["理賠"].sum()
        vals.append(val)
            
    with l:
        fig = go.Figure(data=go.Scatterpolar(r=vals, theta=list(cat_rules.keys()), fill='toself', line_color='#E44D26'))
        m_v = max(vals) if max(vals) > 0 else 100
        fig.update_layout(polar=dict(radialaxis=dict(visible=True, range=[0, m_v * 1.2])), showlegend=False)
        st.plotly_chart(fig, use_container_width=True)
            
    with r:
        st.subheader("💡 專家診斷建議")
        for label, v in zip(cat_rules.keys(), vals):
            if v == 0: st.error(f"❌ **{label}缺口**")
            elif v < 100: st.warning(f"⚠️ **{label}偏低** ({v:,.0f}萬)")
            else: st.success(f"✅ **{label}充足** ({v:,.0f}萬)")
