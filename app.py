import streamlit as st
import pandas as pd
import io
import google.generativeai as genai
import plotly.graph_objects as go

# --- 1. 設定頁面 (必須放在最前面) ---
st.set_page_config(page_title="AI 保單診斷系統", layout="wide")

# --- 2. 安全讀取 API Key ---
# 請確保您已在 Streamlit Secrets 設定 GEMINI_API_KEY
API_KEY = st.secrets.get("GEMINI_API_KEY", "")

if API_KEY:
    genai.configure(api_key=API_KEY)
    model = genai.GenerativeModel('gemini-1.5-flash')
else:
    st.error("❌ 找不到 API Key！請至 Streamlit Secrets 設定 GEMINI_API_KEY。")

# --- 3. 初始化資料 (避免 IndexError) ---
if 'df' not in st.session_state:
    st.session_state.df = pd.DataFrame([
        {"姓名": "張曉明", "險種名稱": "南山人壽10HRL", "類別": "長照", "保費": 31720, "理賠": 24}
    ])

# --- 4. 側邊欄 ---
with st.sidebar:
    st.header("👤 基本設定")
    age = st.number_input("年齡", value=27)
    st.divider()
    uploaded_file = st.file_uploader("📂 載入 Excel", type=["xlsx"])
    mode = st.radio("切換模式：", ["1. 資料錄入", "2. 診斷報告"])

# --- 5. AI 辨識邏輯 ---
def ai_classify(name):
    if not API_KEY or not name: return "待辨識"
    try:
        prompt = f"判斷險種「{name}」屬於：壽險、意外、醫療、重傷、長照 哪一類？只回傳兩字。"
        return model.generate_content(prompt).text.strip()
    except: return "查詢失敗"

# --- 模式 1：資料錄入 ---
if mode == "1. 資料錄入":
    # 標題
    c_name = st.session_state.df['姓名'].iloc[0] if not st.session_state.df.empty else "新客戶"
    st.header(f"📝 {c_name} 的保單明細表")

    # 處理匯入
    if uploaded_file:
        if st.button("🚀 執行 AI 自動分類"):
            raw = pd.read_excel(uploaded_file)
            # 強制清理數字
            for col in raw.columns:
                if "保費" in col or "理賠" in col or "保額" in col:
                    raw[col] = pd.to_numeric(raw[col].astype(str).str.replace(r'[^\d.]', '', regex=True), errors='coerce').fillna(0)
            
            # AI 辨識 (找尋名稱欄位)
            name_col = next((c for c in raw.columns if "名稱" in c or "險種" in c), raw.columns[0])
            with st.spinner("AI 聯網辨識中..."):
                raw['類別'] = raw[name_col].apply(ai_classify)
            
            # 統一欄位名並存入
            raw.rename(columns={name_col: "險種名稱"}, inplace=True)
            st.session_state.df = raw
            st.rerun()

    # 表格編輯器
    edited = st.data_editor(st.session_state.df, num_rows="dynamic", use_container_width=True)
    st.session_state.df = edited

# --- 模式 2：診斷報告 ---
elif mode == "2. 診斷報告":
    df = st.session_state.df
    st.header("📊 專業保障診斷報告 (重傷優化版)")
    
    # 計算數值 (安全讀取)
    p_col = next((c for c in df.columns if "保費" in c), None)
    r_col = next((c for c in df.columns if "理賠" in c or "保額" in c), None)
    
    total_p = df[p_col].sum() if p_col else 0
    total_r = df[r_col].sum() if r_col else 0
    
    c1, c2, c3 = st.columns(3)
    c1.metric("年度總保費", f"{int(total_p):,} 元")
    c2.metric("預估總保障", f"{int(total_r):,} 萬元")
    c3.metric("投保年齡", f"{age} 歲")
    
    st.divider()
    
    # 雷達圖
    cats = ["壽險", "意外", "醫療", "重傷", "長照"]
    # 修正：AI 辨識出的「癌症/重大疾病」會自動對應到「重傷」
    vals = []
    for c in cats:
        val = df[df['類別'].str.contains(c[:2], na=False) | (df['類別'].str.contains("重", na=False) if c=="重傷" else False)][r_col].sum() if r_col else 0
        vals.append(val)
    
    fig = go.Figure(data=go.Scatterpolar(r=vals, theta=cats, fill='toself', line_color='#E44D26'))
    fig.update_layout(polar=dict(radialaxis=dict(visible=True, range=[0, max(vals)*1.2 if max(vals)>0 else 100])), showlegend=False)
    st.plotly_chart(fig, use_container_width=True)
