import streamlit as st
import pandas as pd
import io
import google.generativeai as genai
import plotly.graph_objects as go

# --- 1. 頁面基礎設定 (解決打不開的問題) ---
st.set_page_config(page_title="AI 聯網保單診斷系統", layout="wide")

# 安全讀取 API Key (請確保已在 Streamlit Secrets 設定 GEMINI_API_KEY)
API_KEY = st.secrets.get("GEMINI_API_KEY", "")
if API_KEY:
    genai.configure(api_key=API_KEY)
    model = genai.GenerativeModel('gemini-1.5-flash')
else:
    st.error("❌ 找不到 API Key！請檢查 Secrets 設定。")

# --- 2. 初始化 Session 資料 (解決數據為 0 的問題) ---
if 'main_df' not in st.session_state:
    st.session_state.main_df = pd.DataFrame([
        {"姓名": "張曉明", "險種名稱": "南山人壽10HRL", "類別": "長照", "保費": 31720, "理賠額(萬)": 24}
    ])

# --- 3. 核心功能：AI 聯網辨識 (重傷優化) ---
def ai_lookup(p_name):
    if not API_KEY or not p_name: return "待定"
    try:
        prompt = f"你是台灣保險專家。判斷險種「{p_name}」類別：壽險、意外、醫療、重傷、長照。只回傳兩字，不要解釋。"
        response = model.generate_content(prompt)
        return response.text.strip()
    except: return "查詢中"

# --- 4. 側邊欄控制 ---
with st.sidebar:
    st.header("👤 基本資料設定")
    c_age = st.number_input("投保年齡", value=27)
    st.divider()
    up_file = st.file_uploader("📂 載入 Excel 檔案", type=["xlsx"])
    mode = st.radio("模式切換：", ["1. 資料錄入", "2. 診斷報告"])

# --- 5. 模式 1：資料錄入 (修復數據 0 與表格空白問題) ---
if mode == "1. 資料錄入":
    # 標題連動
    cur_name = st.session_state.main_df['姓名'].iloc[0] if not st.session_state.main_df.empty else "新客戶"
    st.header(f"📝 {cur_name} 的保單明細表")

    if up_file:
        if st.button("🚀 啟動 AI 聯網辨識並匯入"):
            try:
                raw = pd.read_excel(up_file)
                # 自動搜尋欄位 (解決欄位對不上的問題)
                n_col = next((c for c in raw.columns if any(k in c for k in ["名稱", "險種", "商品"])), raw.columns[0])
                p_col = next((c for c in raw.columns if "保費" in c), None)
                r_col = next((c for c in raw.columns if any(k in c for k in ["理賠", "保額", "額度"])), None)
                
                with st.spinner("AI 正在分析 重傷 與 長照 分類..."):
                    new_df = pd.DataFrame()
                    new_df['姓名'] = [cur_name] * len(raw)
                    new_df['險種名稱'] = raw[n_col]
                    
                    # 強制提取數字 (解決 0 萬問題)
                    def to_clean_num(v):
                        s = str(v).replace('萬','').replace(',','').replace('元','')
                        return pd.to_numeric(s, errors='coerce') or 0
                    
                    new_df['保費'] = raw[p_col].apply(to_clean_num) if p_col else 0
                    new_df['理賠額(萬)'] = raw[r_col].apply(to_clean_num) if r_col else 0
                    
                    # 執行 AI 聯網辨識
                    new_df['類別'] = new_df['險種名稱'].apply(ai_lookup)
                
                st.session_state.main_df = new_df
                st.success("AI 聯網判讀完成！")
                st.rerun()
            except Exception as e:
                st.error(f"匯入出錯：{e}")

    # 顯示編輯表格
    st.session_state.main_df = st.data_editor(st.session_state.main_df, num_rows="dynamic", use_container_width=True)

# --- 6. 模式 2：診斷報告 (重傷優化版) ---
elif mode == "2. 診斷報告":
    df = st.session_state.main_df
    st.header("📊 專業保障診斷報告")
    
    # 指標計算
    t_p = df['保費'].sum() if '保費' in df.columns else 0
    t_r = df['理賠額(萬)'].sum() if '理賠額(萬)' in df.columns else 0
    
    c1, c2, c3 = st.columns(3)
    c1.metric("年度總保費", f"{int(t_p):,} 元")
    c2.metric("預估總保障 (含重傷/長照)", f"{int(t_r):,} 萬元")
    c3.metric("客戶年齡", f"{c_age} 歲")
    
    st.divider()
    
    # 雷達圖
    cats = ["壽險", "意外", "醫療", "重傷", "長照"]
    vals = []
    for c in cats:
        # 模糊比對類別，將重大疾病與重傷合併
        mask = df['類別'].str.contains(c[:2], na=False)
        if c == "重傷": mask = mask | df['類別'].str.contains("重大", na=False)
        vals.append(df[mask]['理賠額(萬)'].sum() if '理賠額(萬)' in df.columns else 0)
    
    fig = go.Figure(data=go.Scatterpolar(r=vals, theta=cats, fill='toself', line_color='#E44D26'))
    fig.update_layout(polar=dict(radialaxis=dict(visible=True, range=[0, max(vals)*1.2 if max(vals)>0 else 100])), showlegend=False)
    st.plotly_chart(fig, use_container_width=True)
