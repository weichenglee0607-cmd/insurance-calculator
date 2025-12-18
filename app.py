import streamlit as st
import pandas as pd
import io
import google.generativeai as genai
import plotly.graph_objects as go

# --- 1. 基礎設定 (確保打得開) ---
st.set_page_config(page_title="AI 專業保單診斷", layout="wide")

# 安全讀取 API Key
API_KEY = st.secrets.get("GEMINI_API_KEY", "")
if API_KEY:
    genai.configure(api_key=API_KEY)
    model = genai.GenerativeModel('gemini-1.5-flash')
else:
    st.error("❌ 找不到 API Key！請檢查 Secrets 設定。")

# --- 2. 初始化 Session (防止 IndexError) ---
if 'main_df' not in st.session_state:
    # 預設一筆資料，防止讀取時崩潰
    st.session_state.main_df = pd.DataFrame([
        {"姓名": "張曉明", "險種名稱": "範例長照險", "類別": "長照", "保費": 31720, "理賠額(萬)": 24}
    ])

# --- 3. 核心功能：AI 聯網辨識 (重傷優化) ---
def ai_lookup(p_name):
    if not API_KEY or not p_name: return "待定"
    try:
        # 強制辨識「重傷」與「長照」專業術語
        prompt = f"判斷台灣險種「{p_name}」類別：壽險、意外、醫療、重傷、長照。只回傳兩字。"
        return model.generate_content(prompt).text.strip()
    except: return "查詢中"

# --- 4. 側邊欄 ---
with st.sidebar:
    st.header("👤 基本資料")
    client_age = st.number_input("年齡", value=27)
    st.divider()
    up_file = st.file_uploader("📂 載入 Excel (xlsx)", type=["xlsx"])
    mode = st.radio("模式：", ["1. 資料錄入", "2. 診斷報告"])

# --- 5. 模式 1：資料錄入 ---
if mode == "1. 資料錄入":
    # 標題連動
    c_name = st.session_state.main_df['姓名'].iloc[0] if not st.session_state.main_df.empty else "新客戶"
    st.header(f"📝 {c_name} 的保單明細表")

    # 匯入邏輯
    if up_file:
        if st.button("🚀 啟動 AI 辨識並匯入"):
            raw = pd.read_excel(up_file)
            
            # 自動搜尋關鍵欄位 (防止 KeyError)
            name_col = next((c for c in raw.columns if any(k in c for k in ["名稱", "險種", "商品"])), raw.columns[0])
            p_col = next((c for c in raw.columns if "保費" in c), None)
            r_col = next((c for c in raw.columns if any(k in c for k in ["理賠", "保額", "額度"])), None)
            
            with st.spinner("AI 正在連網判讀中..."):
                # 建立乾淨的 DataFrame
                new_df = pd.DataFrame()
                new_df['姓名'] = [c_name] * len(raw)
                new_df['險種名稱'] = raw[name_col]
                
                # 清理數值 (防止資料變 0)
                def get_num(v):
                    s = str(v).replace('萬','').replace(',','').replace('元','')
                    return pd.to_numeric(s, errors='coerce') or 0
                
                new_df['保費'] = raw[p_col].apply(get_num) if p_col else 0
                new_df['理賠額(萬)'] = raw[r_col].apply(get_num) if r_col else 0
                
                # 執行辨識
                new_df['類別'] = new_df['險種名稱'].apply(ai_lookup)
                
            st.session_state.main_df = new_df
            st.rerun()

    # 確保表格能正常編輯且不變空白
    st.session_state.main_df = st.data_editor(st.session_state.main_df, num_rows="dynamic", use_container_width=True)

# --- 6. 模式 2：診斷報告 ---
elif mode == "2. 診斷報告":
    df = st.session_state.main_df
    st.header("📊 專業保障診斷報告")

    # 安全計算 (防止 0 萬問題)
    r_field = '理賠額(萬)' if '理賠額(萬)' in df.columns else '理賠'
    p_field = '保費'
    
    total_p = df[p_field].sum() if p_field in df.columns else 0
    total_r = df[r_field].sum() if r_field in df.columns else 0
    
    c1, c2, c3 = st.columns(3)
    c1.metric("總保費", f"{int(total_p):,} 元")
    c2.metric("總保障 (含重傷/長照)", f"{int(total_r):,} 萬元")
    c3.metric("客戶年齡", f"{client_age} 歲")

    st.divider()
    
    # 雷達圖繪製 (優化重傷判定)
    cats = ["壽險", "意外", "醫療", "重傷", "長照"]
    vals = []
    for c in cats:
        # 模糊搜尋類別，確保包含「重傷」或「重大」都能被計入
        mask = df['類別'].str.contains(c[:2], na=False)
        if c == "重傷": mask = mask | df['類別'].str.contains("重大", na=False)
        vals.append(df[mask][r_field].sum() if r_field in df.columns else 0)
    
    fig = go.Figure(data=go.Scatterpolar(r=vals, theta=cats, fill='toself', line_color='#D62728'))
    fig.update_layout(polar=dict(radialaxis=dict(visible=True, range=[0, max(vals)*1.2 if max(vals)>0 else 100])), showlegend=False)
    st.plotly_chart(fig, use_container_width=True)
