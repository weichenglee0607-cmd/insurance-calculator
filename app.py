import streamlit as st
import pandas as pd
import google.generativeai as genai
import plotly.graph_objects as go

# --- 1. 基礎安全設定 ---
st.set_page_config(page_title="AI 保單診斷系統", layout="wide")

# 安全讀取 Key，失敗也不會斷線
try:
    API_KEY = st.secrets["GEMINI_API_KEY"]
    genai.configure(api_key=API_KEY)
    model = genai.GenerativeModel('gemini-1.5-flash')
except:
    st.error("❌ 找不到 API Key！請至 Streamlit Secrets 設定。")

# --- 2. 初始化資料 (避免資料變 0) ---
if 'main_df' not in st.session_state:
    st.session_state.main_df = pd.DataFrame([
        {"姓名": "張曉明", "險種名稱": "南山 10HRL", "類別": "長照", "保費": 31720, "理賠額(萬)": 24}
    ])

# --- 3. 核心功能：AI 聯網辨識 ---
def ai_lookup(name):
    if not name: return "待定"
    try:
        # 強制辨識重傷與長照
        prompt = f"你目前是台灣保險經紀人。判斷險種「{name}」分類：壽險、意外、醫療、重傷、長照。只回兩字。"
        return model.generate_content(prompt).text.strip()
    except: return "查詢中"

# --- 4. 側邊欄與模式 ---
with st.sidebar:
    st.header("👤 診斷資料")
    age = st.number_input("年齡", value=27)
    st.divider()
    up_file = st.file_uploader("📂 載入 Excel", type=["xlsx"])
    mode = st.radio("模式切換：", ["1. 資料錄入", "2. 診斷報告"])

# --- 5. 模式 1：資料錄入 (修復數據變 0 的邏輯) ---
if mode == "1. 資料錄入":
    c_name = st.session_state.main_df['姓名'].iloc[0] if not st.session_state.main_df.empty else "新客戶"
    st.header(f"📝 {c_name} 的保單明細表")

    if up_file:
        if st.button("🚀 啟動 AI 聯網自動分類"):
            raw = pd.read_excel(up_file)
            
            # 自動搜尋關鍵欄位 (防止 KeyError)
            n_col = next((c for c in raw.columns if any(k in c for k in ["名稱", "險種"])), raw.columns[0])
            p_col = next((c for c in raw.columns if "保費" in c), None)
            r_col = next((c for c in raw.columns if any(k in c for k in ["理賠", "保額"])), None)
            
            with st.spinner("AI 正在查詢資料..."):
                new_df = pd.DataFrame()
                new_df['姓名'] = [c_name] * len(raw)
                new_df['險種名稱'] = raw[n_col]
                
                # 清理數字 (防止 0 萬問題)
                def get_val(v):
                    s = str(v).replace('萬','').replace(',','').replace('元','')
                    return pd.to_numeric(s, errors='coerce') or 0
                
                new_df['保費'] = raw[p_col].apply(get_val) if p_col else 0
                new_df['理賠額(萬)'] = raw[r_col].apply(get_val) if r_col else 0
                new_df['類別'] = new_df['險種名稱'].apply(ai_lookup)
                
            st.session_state.main_df = new_df
            st.rerun()

    st.session_state.main_df = st.data_editor(st.session_state.main_df, num_rows="dynamic", use_container_width=True)

# --- 6. 模式 2：診斷報告 (重傷優化) ---
elif mode == "2. 診斷報告":
    df = st.session_state.main_df
    st.header("📊 專業保障診斷報告")

    # 安全計算
    t_p = df['保費'].sum() if '保費' in df.columns else 0
    t_r = df['理賠額(萬)'].sum() if '理賠額(萬)' in df.columns else 0
    
    c1, c2, c3 = st.columns(3)
    c1.metric("總保費", f"{int(t_p):,} 元")
    c2.metric("總保障 (含重傷/長照)", f"{int(t_r):,} 萬元")
    c3.metric("投保年齡", f"{age} 歲")

    st.divider()
    
    # 雷達圖
    cats = ["壽險", "意外", "醫療", "重傷", "長照"]
    vals = []
    for c in cats:
        # 重傷優化辨識
        mask = df['類別'].str.contains(c[:2], na=False)
        if c == "重傷": mask = mask | df['類別'].str.contains("重大", na=False)
        vals.append(df[mask]['理賠額(萬)'].sum() if '理賠額(萬)' in df.columns else 0)
    
    fig = go.Figure(data=go.Scatterpolar(r=vals, theta=cats, fill='toself', line_color='#D62728'))
    fig.update_layout(polar=dict(radialaxis=dict(visible=True, range=[0, max(vals)*1.2 if max(vals)>0 else 100])), showlegend=False)
    st.plotly_chart(fig, use_container_width=True)
