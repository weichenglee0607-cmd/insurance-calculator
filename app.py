import streamlit as st
import pandas as pd
import io
import google.generativeai as genai
import plotly.graph_objects as go

# --- 1. 頁面初始化 (解決打不開的問題) ---
st.set_page_config(page_title="AI 保單診斷系統", layout="wide")

# 安全讀取 API Key (解決 AI 功能失效)
API_KEY = st.secrets.get("GEMINI_API_KEY", "")
if API_KEY:
    genai.configure(api_key=API_KEY)
    model = genai.GenerativeModel('gemini-1.5-flash')
else:
    st.error("❌ 找不到 API Key！請檢查 Streamlit Secrets 設定。")

# --- 2. 資料結構初始化 (解決 IndexError) ---
# 使用 safer 方式初始化，避免匯入時變數消失
if 'main_df' not in st.session_state:
    st.session_state.main_df = pd.DataFrame([
        {"姓名": "張曉明", "險種名稱": "南山 10HRL", "類別": "長照", "保費": 31720, "理賠": 24}
    ])

# --- 3. AI 聯網判讀 (解決長照/重傷判定太弱問題) ---
def ai_classify(name):
    if not API_KEY or not name: return "待辨識"
    try:
        # 強制 AI 辨識「重傷」與「長照」的專業關鍵字
        prompt = f"你是台灣保險專家，判斷險種「{name}」類別：壽險、意外、醫療、重傷、長照。只回傳兩字。"
        return model.generate_content(prompt).text.strip()
    except: return "查詢失敗"

# --- 4. 側邊欄 ---
with st.sidebar:
    st.header("👤 客戶資料")
    c_age = st.number_input("年齡", value=27)
    st.divider()
    uploaded_file = st.file_uploader("📂 載入 Excel (xlsx)", type=["xlsx"])
    mode = st.radio("模式切換：", ["1. 資料錄入", "2. 診斷報告"])

# --- 5. 模式 1：資料錄入 (解決資料變 0 與表格空白問題) ---
if mode == "1. 資料錄入":
    # 標題自動連動姓名
    try:
        title_name = st.session_state.main_df['姓名'].iloc[0]
    except:
        title_name = "新客戶"
    st.header(f"📝 {title_name} 的保單明細表")

    if uploaded_file:
        if st.button("🚀 執行 AI 分類"):
            try:
                raw = pd.read_excel(uploaded_file)
                # 自動搜尋欄位並清理數字
                for col in raw.columns:
                    if any(k in col for k in ["保費", "理賠", "保額", "額度"]):
                        raw[col] = pd.to_numeric(raw[col].astype(str).str.replace(r'[^\d.]', '', regex=True), errors='coerce').fillna(0)
                
                # 自動定位名稱欄位
                name_col = next((c for c in raw.columns if any(k in c for k in ["名稱", "險種", "商品"])), raw.columns[0])
                
                with st.spinner("AI 正在連網辨識各家險種..."):
                    raw['類別'] = raw[name_col].apply(ai_classify)
                
                # 統一欄位名稱，避免 KeyError
                raw.rename(columns={name_col: "險種名稱"}, inplace=True)
                st.session_state.main_df = raw
                st.success("匯入成功！")
                st.rerun()
            except Exception as e:
                st.error(f"匯入過程發生錯誤：{e}")

    # 確保表格能正常顯示
    edited = st.data_editor(st.session_state.main_df, num_rows="dynamic", use_container_width=True, key="main_editor")
    st.session_state.main_df = edited

# --- 6. 模式 2：診斷報告 (解決雷達圖空心問題) ---
elif mode == "2. 診斷報告":
    df = st.session_state.main_df
    st.header(f"📊 {title_name if 'title_name' in locals() else '客戶'} 專業診斷報告")

    # 動態抓取欄位進行計算
    p_col = next((c for c in df.columns if "保費" in c), None)
    r_col = next((c for c in df.columns if any(k in c for k in ["理賠", "保額", "額度"])), None)
    
    total_p = df[p_col].sum() if p_col else 0
    total_r = df[r_col].sum() if r_col else 0
    
    # 指標顯示
    c1, c2, c3 = st.columns(3)
    c1.metric("年度總保費", f"{int(total_p):,} 元")
    c2.metric("預估總保障 (包含重傷/長照)", f"{int(total_r):,} 萬元")
    c3.metric("目前年齡", f"{c_age} 歲")

    st.divider()
    
    # 雷達圖繪製 (解決重傷分類問題)
    cats = ["壽險", "意外", "醫療", "重傷", "長照"]
    vals = []
    for c in cats:
        # 使用模糊比對，確保「重大傷病」與「重傷」能合併計算
        mask = df['類別'].str.contains(c[:2], na=False)
        if c == "重傷":
            mask = mask | df['類別'].str.contains("重大", na=False) | df['險種名稱'].str.contains("癌症", na=False)
        vals.append(df[mask][r_col].sum() if r_col else 0)
    
    fig = go.Figure(data=go.Scatterpolar(r=vals, theta=cats, fill='toself', line_color='#E44D26'))
    fig.update_layout(polar=dict(radialaxis=dict(visible=True, range=[0, max(vals)*1.2 if max(vals)>0 else 100])), showlegend=False)
    st.plotly_chart(fig, use_container_width=True)
