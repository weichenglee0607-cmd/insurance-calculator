import streamlit as st
import pandas as pd
import google.generativeai as genai
import plotly.graph_objects as go

# --- 1. 頁面專業設定 ---
st.set_page_config(page_title="AI 專業保單診斷系統", layout="wide")

# 安全讀取 API Key
try:
    API_KEY = st.secrets["GEMINI_API_KEY"]
    genai.configure(api_key=API_KEY)
    model = genai.GenerativeModel('gemini-1.5-flash')
except:
    st.error("❌ API Key 讀取失敗，請確認 Streamlit Secrets 設定。")

# --- 2. 數據初始化 ---
if 'main_df' not in st.session_state:
    st.session_state.main_df = pd.DataFrame([
        {"姓名": "張曉明", "險種名稱": "南山 10HRL", "類別": "長照", "保費": 31720, "理賠額": 24}
    ])

# --- 3. AI 聯網判讀 (強化重傷與長照辨識) ---
def ai_lookup(name):
    if not name or name == "南山 10HRL": return "長照"
    try:
        # 增加語意理解，區分重傷與傳統重疾
        prompt = f"""
        你是一位台灣保險經紀人。請精準判斷險種名稱「{name}」的保障類別。
        規則：
        1. 包含重大傷病、癌症、卡、特定傷病、重大疾病 -> 歸類為「重傷」。
        2. 包含長期照顧、失能、扶助 -> 歸類為「長照」。
        3. 僅回傳兩字：壽險、意外、醫療、重傷、長照。
        """
        response = model.generate_content(prompt)
        return response.text.strip()
    except: return "待確認"

# --- 4. 模式切換 ---
with st.sidebar:
    st.header("👤 診斷資料設定")
    age = st.number_input("客戶年齡", value=27)
    st.divider()
    up_file = st.file_uploader("📂 載入 Excel 檔案", type=["xlsx"])
    mode = st.radio("功能切換：", ["1. 資料錄入", "2. 診斷報告"])

# --- 5. 模式 1：資料錄入 ---
if mode == "1. 資料錄入":
    df = st.session_state.main_df
    c_name = df['姓名'].iloc[0] if not df.empty else "新客戶"
    st.header(f"📝 {c_name} 的保單明細表")

    if up_file:
        if st.button("🚀 啟動 AI 深度辨識"):
            raw = pd.read_excel(up_file)
            
            # 自動搜尋關鍵欄位 (防止數據變 0)
            n_col = next((c for c in raw.columns if any(k in str(c) for k in ["名稱", "險種"])), raw.columns[0])
            p_col = next((c for c in raw.columns if "保費" in str(c)), None)
            r_col = next((c for c in raw.columns if any(k in str(c) for k in ["理賠", "保額", "額度"])), None)
            
            with st.spinner("AI 正在分析險種與提取數據..."):
                new_df = pd.DataFrame()
                new_df['姓名'] = [c_name] * len(raw)
                new_df['險種名稱'] = raw[n_col]
                
                # 強化數字提取 (處理文字與數字混合)
                def get_num(v):
                    import re
                    s = re.sub(r'[^\d.]', '', str(v))
                    return pd.to_numeric(s, errors='coerce') or 0
                
                new_df['保費'] = raw[p_col].apply(get_num) if p_col else 0
                new_df['理賠額'] = raw[r_col].apply(get_num) if r_col else 0
                new_df['類別'] = new_df['險種名稱'].apply(ai_lookup)
                
            st.session_state.main_df = new_df
            st.rerun()

    st.session_state.main_df = st.data_editor(st.session_state.main_df, num_rows="dynamic", use_container_width=True)

# --- 6. 模式 2：診斷報告 ---
elif mode == "2. 診斷報告":
    df = st.session_state.main_df
    st.header(f"📊 {df['姓名'].iloc[0] if not df.empty else '客戶'} 專業診斷報告")

    # 數據指標
    t_p = df['保費'].sum()
    t_r = df['理賠額'].sum()
    
    col1, col2, col3 = st.columns(3)
    col1.metric("年度總保費", f"{int(t_p):,} 元")
    col2.metric("預估總保障額度", f"{int(t_r):,} 萬元")
    col3.metric("投保年齡", f"{age} 歲")

    st.divider()
    
    # 雷達圖
    cats = ["壽險", "意外", "醫療", "重傷", "長照"]
    vals = [df[df['類別'].astype(str).str.contains(c[:2], na=False)]['理賠額'].sum() for c in cats]
    
    l, r = st.columns([1.2, 1])
    with l:
        fig = go.Figure(data=go.Scatterpolar(r=vals, theta=cats, fill='toself', line_color='#E44D26', marker=dict(size=8)))
        fig.update_layout(polar=dict(radialaxis=dict(visible=True, range=[0, max(vals)*1.2 if max(vals)>0 else 100])), showlegend=False)
        st.plotly_chart(fig, use_container_width=True)
    
    with r:
        st.subheader("💡 專家診斷建議")
        for label, v in zip(cats, vals):
            if v == 0:
                st.error(f"❌ **{label}缺口**：尚未偵測到相關保障。")
            elif label == "重傷" and v < 100:
                st.warning(f"⚠️ **{label}偏低**：保障額度 {v:,.0f} 萬 (重傷建議 100 萬以上)。")
            elif v < 100:
                st.warning(f"⚠️ **{label}偏低**：目前額度 {v:,.0f} 萬。")
            else:
                st.success(f"✅ **{label}充足**：保障額度 {v:,.0f} 萬。")
