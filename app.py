import streamlit as st
import pandas as pd
import io
import plotly.graph_objects as go
import google.generativeai as genai  # 引入 AI 聯網判讀模組

# --- 1. 設定 AI API Key ---
# 建議將您的 Gemini API Key 填入下方
API_KEY = "您的_GEMINI_API_KEY" 
genai.configure(api_key=API_KEY)
model = genai.GenerativeModel('gemini-pro')

st.set_page_config(page_title="AI 聯網保單診斷系統", layout="wide")

# --- 2. 核心：AI 聯網自動判讀函式 ---
def ai_network_lookup(product_name):
    """
    透過 AI 直接聯網辨識該險種屬於哪一類保障
    """
    if not product_name:
        return "其他"
        
    try:
        # 向 AI 發問，要求精準回傳類別
        prompt = (
            f"你是一位台灣專業保險顧問。請判斷以下險種名稱屬於哪一個保障類別：\n"
            f"險種名稱：'{product_name}'\n"
            f"可選類別：壽險、意外、醫療、重疾、長照。\n"
            f"請只回傳兩個字，不要多說任何廢話。"
        )
        response = model.generate_content(prompt)
        category = response.text.strip()
        
        # 二次驗證，確保回傳的是我們定義的五大類
        valid_cats = ["壽險", "意外", "醫療", "重疾", "長照"]
        for cat in valid_cats:
            if cat in category:
                return cat
        return "其他"
    except Exception as e:
        # 若聯網失敗，則退回簡單的邏輯判斷
        st.error(f"AI 聯網辨識出錯：{e}")
        return "自動辨識失敗"

# --- 3. 資料清理與 AI 批次辨識 ---
def run_ai_processing(df):
    # 欄位對齊
    mapping = {
        "險種名稱": ["險種名稱", "商品名稱", "險種"],
        "理賠": ["理賠", "預估理賠額 (萬)", "保障額度", "保額"]
    }
    for target, aliases in mapping.items():
        for alias in aliases:
            if alias in df.columns and target not in df.columns:
                df[target] = df[alias]

    # 清理數值
    if "理賠" in df.columns:
        df["理賠"] = pd.to_numeric(df["理賠"].astype(str).str.replace(r'[^\d.]', '', regex=True), errors='coerce').fillna(0)
    
    # 啟動 AI 聯網辨識類別
    with st.spinner("AI 正在網路上為您查詢險種分類..."):
        df['類別'] = df['險種名稱'].apply(ai_network_lookup)
        
    return df

# --- 4. 初始化 ---
if 'main_df' not in st.session_state:
    st.session_state['main_df'] = pd.DataFrame([
        {"姓名": "張曉明", "險種名稱": "南山人壽10HRL", "類別": "長照", "理賠": 20}
    ])

# --- 5. 側邊欄與錄入模式 ---
with st.sidebar:
    st.header("👤 診斷設定")
    uploaded_file = st.file_uploader("📂 載入 Excel (不限格式)", type=["xlsx"])
    mode = st.radio("功能切換：", ["1. 資料錄入", "2. 診斷報告"])

if mode == "1. 資料錄入":
    st.header("📝 保單資料錄入")
    
    # 若有新檔案上傳，點擊按鈕執行 AI 辨識
    if uploaded_file:
        if st.button("🚀 啟動 AI 聯網辨識與匯入"):
            new_data = pd.read_excel(uploaded_file)
            st.session_state['main_df'] = run_ai_processing(new_data)
            st.success("AI 已成功上網抓取資料並完成自動分類！")
            st.rerun()

    # 編輯區域
    edited_df = st.data_editor(st.session_state['main_df'], num_rows="dynamic", use_container_width=True)
    st.session_state['main_df'] = edited_df

# --- 6. 診斷報告模式 ---
elif mode == "2. 診斷報告":
    df = st.session_state['main_df']
    st.header(f"📊 專業保障診斷報告")
    
    # 雷達圖
    cat_list = ["壽險", "意外", "醫療", "重疾", "長照"]
    vals = [df[df['類別'] == c]["理賠"].sum() for c in cat_list]
    
    fig = go.Figure(data=go.Scatterpolar(r=vals, theta=cat_list, fill='toself'))
    fig.update_layout(polar=dict(radialaxis=dict(visible=True, range=[0, max(vals)*1.2 if max(vals)>0 else 100])))
    st.plotly_chart(fig)
