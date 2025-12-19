import streamlit as st
import pandas as pd
import google.generativeai as genai
import plotly.graph_objects as go

# --- 1. 頁面基礎設定 (確保能打開) ---
st.set_page_config(page_title="AI 保單診斷系統", layout="wide")

# 安全讀取 API Key (請至 Streamlit Secrets 設定 GEMINI_API_KEY)
API_KEY = st.secrets.get("GEMINI_API_KEY", "")
if API_KEY:
    genai.configure(api_key=API_KEY)
    model = genai.GenerativeModel('gemini-1.5-flash')
else:
    st.error("❌ 找不到 API Key！請檢查 Secrets 設定。")

# --- 2. 初始化 Session (防止數據為 0 或打不開) ---
if 'main_df' not in st.session_state:
    st.session_state.main_df = pd.DataFrame([
        {"姓名": "張曉明", "險種名稱": "範例長照保險", "類別": "長照", "保費": 31720, "理賠額(萬)": 24}
    ])

# --- 3. AI 聯網判讀 (針對重傷優化) ---
def ai_lookup(p_name):
    if not p_name or not API_KEY: return "待辨識"
    try:
        prompt = f"你是台灣保險專家。請判斷險種「{p_name}」屬於：壽險、意外、醫療、重傷、長照 哪一類？只回傳兩字。"
        response = model.generate_content(prompt)
        return response.text.strip()
    except:
        return "查詢失敗"

# --- 4. 側邊欄與功能切換 ---
with st.sidebar:
    st.header("👤 基本資料")
    c_age = st.number_input("年齡", value=27)
    st.divider()
    up_file = st.file_uploader("📂 載入 Excel", type=["xlsx"])
    mode = st.radio("模式切換：", ["1. 資料錄入", "2. 診斷報告"])

# --- 模式 1：資料錄入 (強化數據提取) ---
if mode == "1. 資料錄入":
    c_name = st.session_state.main_df['姓名'].iloc[0] if not st.session_state.main_df.empty else "新客戶"
    st.header(f"📝 {c_name} 的保單明細表")

    if up_file:
        if st.button("🚀 啟動 AI 辨識與數據提取"):
            raw = pd.read_excel(up_file)
            # 自動搜尋關鍵欄位
            n_col = next((c for c in raw.columns if any(k in str(c) for k in ["名稱", "險種"])), raw.columns[0])
            p_col = next((c for c in raw.columns if "保費" in str(c)), None)
            r_col = next((c for c in raw.columns if any(k in str(c) for k in ["理賠", "保額", "額度"])), None)
            
            with st.spinner("AI 正在查詢並清理數據..."):
                new_df = pd.DataFrame()
                new_df['姓名'] = [c_name] * len(raw)
                new_df['險種名稱'] = raw[n_col]
                
                # 數字清理器：移除萬、元、逗號
                def clean_num(v):
                    import re
                    s = re.sub(r'[^\d.]', '', str(v))
                    return pd.to_numeric(s, errors='coerce') or 0
                
                new_df['保費'] = raw[p_col].apply(clean_num) if p_col else 0
                new_df['理賠額(萬)'] = raw[r_col].apply(clean_num) if r_col else 0
                new_df['類別'] = new_df['險種名稱'].apply(ai_lookup)
                
            st.session_state.main_df = new_df
            st.rerun()

    st.session_state.main_df = st.data_editor(st.session_state.main_df, num_rows="dynamic", use_container_width=True)

# --- 模式 2：診斷報告 (重傷與缺口顯示) ---
elif mode == "2. 診斷報告":
    df = st.session_state.main_df
    st.header("📊 專業保障診斷報告")

    # 數據總計
    t_p = df['保費'].sum() if '保費' in df.columns else 0
    t_r = df['理賠額(萬)'].sum() if '理賠額(萬)' in df.columns else 0
    
    c1, c2, c3 = st.columns(3)
    c1.metric("年度總保費", f"{int(t_p):,} 元")
    c2.metric("預估總保障 (含重傷/長照)", f"{int(t_r):,} 萬元")
    c3.metric("客戶年齡", f"{c_age} 歲")

    st.divider()
    
    # 雷達圖數據與缺口建議
    cats = ["壽險", "意外", "醫療", "重傷", "長照"]
    vals = []
    for c in cats:
        # 模糊比對：包含「重傷」或「重大」都算重傷
        mask = df['類別'].str.contains(c[:2], na=False)
        if c == "重傷": mask = mask | df['類別'].str.contains("重大", na=False)
        vals.append(df[mask]['理賠額(萬)'].sum() if '理賠額(萬)' in df.columns else 0)
    
    l, r = st.columns([1.2, 1])
    with l:
        fig = go.Figure(data=go.Scatterpolar(r=vals, theta=cats, fill='toself', line_color='#D62728'))
        fig.update_layout(polar=dict(radialaxis=dict(visible=True, range=[0, max(vals)*1.2 if max(vals)>0 else 100])), showlegend=False)
        st.plotly_chart(fig, use_container_width=True)
    
    with r:
        st.subheader("💡 缺口診斷建議")
        for label, v in zip(cats, vals):
            if v == 0: st.error(f"❌ **{label}缺口**：數據為 0")
            elif label == "重傷" and v < 100: st.warning(f"⚠️ **{label}偏低** ({v}萬，重傷建議 100 萬以上)")
            else: st.success(f"✅ **{label}數據**：{v} 萬元")
