import streamlit as st
import pandas as pd
import io
import google.generativeai as genai
import plotly.graph_objects as go

# --- 1. 安全讀取 AI API Key ---
API_KEY = st.secrets.get("GEMINI_API_KEY", "")
if API_KEY:
    genai.configure(api_key=API_KEY)
    model = genai.GenerativeModel('gemini-1.5-flash')
else:
    st.warning("⚠️ 尚未在 Streamlit Secrets 設定 GEMINI_API_KEY，AI 功能將受限。")

st.set_page_config(page_title="AI 聯網保單診斷系統", layout="wide")

# --- 2. AI 聯網判讀功能 (針對重傷優化) ---
def ai_classify_insurance(product_name):
    if not product_name or not API_KEY: return "待辨識"
    try:
        prompt = f"""
        你是一位台灣專業保險經紀人。請判斷險種名稱「{product_name}」屬於哪一類保障？
        可選類別：壽險、意外、醫療、重傷、長照。
        注意：
        1. 若包含重大傷病、癌症、重大疾病，請歸類為「重傷」。
        2. 若包含長期照顧、失能，請歸類為「長照」。
        請只回傳類別名稱（兩個字），不要解釋。
        """
        response = model.generate_content(prompt)
        res = response.text.strip()
        for cat in ["壽險", "意外", "醫療", "重傷", "長照"]:
            if cat in res: return cat
        return "其他"
    except: return "查詢中..."

# --- 3. 初始化資料庫結構 ---
if 'main_df' not in st.session_state:
    st.session_state['main_df'] = pd.DataFrame([
        {"姓名": "張曉明", "險種名稱": "南山人壽10HRL", "類別": "長照", "保費": 31720, "理賠": 24}
    ])

# --- 4. 側邊欄 ---
with st.sidebar:
    st.header("👤 診斷設定")
    st.session_state['age'] = st.number_input("年齡", value=st.session_state.get('age', 27))
    st.session_state['gender'] = st.selectbox("性別", ["男", "女"])
    st.divider()
    uploaded_file = st.file_uploader("📂 載入 Excel", type=["xlsx"])
    mode = st.radio("功能切換：", ["1. 資料錄入", "2. 診斷報告"])

# --- 5. 模式 1：資料錄入 (修復數據為 0 的問題) ---
if mode == "1. 資料錄入":
    df = st.session_state['main_df']
    name = df['姓名'].iloc[0] if not df.empty and '姓名' in df.columns else "新客戶"
    st.header(f"📝 {name} 的保單明細表")

    if uploaded_file:
        if st.button("🚀 啟動 AI 聯網自動分類"):
            raw_df = pd.read_excel(uploaded_file)
            
            # 強制欄位對齊邏輯
            # 尋找最像名稱、保費、理賠的欄位
            name_col = next((c for c in raw_df.columns if "名稱" in c or "險種" in c), raw_df.columns[0])
            premium_col = next((c for c in raw_df.columns if "保費" in c), None)
            benefit_col = next((c for c in raw_df.columns if "理賠" in c or "保額" in c), None)
            
            with st.spinner("AI 正在查詢資料並清理數據..."):
                new_df = pd.DataFrame()
                new_df['姓名'] = [name] * len(raw_df)
                new_df['險種名稱'] = raw_df[name_col]
                
                # 清理並轉換數字 (處理「萬」或逗號)
                def clean_num(v):
                    if pd.isna(v): return 0
                    s = str(v).replace('萬', '').replace(',', '').replace('元', '')
                    return pd.to_numeric(s, errors='coerce') or 0

                new_df['保費'] = raw_df[premium_col].apply(clean_num) if premium_col else 0
                new_df['理賠'] = raw_df[benefit_col].apply(clean_num) if benefit_col else 0
                
                # AI 自動判斷類別
                new_df['類別'] = new_df['險種名稱'].apply(ai_classify_insurance)
                
            st.session_state['main_df'] = new_df
            st.success("AI 辨識完成！資料已正確載入。")
            st.rerun()

    # 表格編輯 (維持 iPad 寬度)
    edited_df = st.data_editor(st.session_state['main_df'], num_rows="dynamic", use_container_width=True, key="main_editor_v2")
    st.session_state['main_df'] = edited_df

# --- 6. 模式 2：診斷報告 (重傷優化) ---
elif mode == "2. 診斷報告":
    df = st.session_state['main_df']
    st.header(f"📊 專業保障診斷報告 (重傷優化版)")
    
    # 數值計算
    total_p = df.get("保費", pd.Series([0])).sum()
    total_b = df.get("理賠", pd.Series([0])).sum()
    
    c1, c2, c3 = st.columns(3)
    c1.metric("年度總保費", f"{total_p:,.0f} 元")
    c2.metric("預估總保障額度", f"{total_b:,.0f} 萬元")
    c3.metric("投保年齡", f"{st.session_state['age']} 歲")
    
    st.divider()
    cats = ["壽險", "意外", "醫療", "重傷", "長照"]
    vals = [df[df['類別'] == c]["理賠"].sum() if '類別' in df.columns else 0 for c in cats]
    
    l, r = st.columns([1.2, 1])
    with l:
        fig = go.Figure(data=go.Scatterpolar(r=vals, theta=cats, fill='toself', line_color='#E44D26'))
        fig.update_layout(polar=dict(radialaxis=dict(visible=True, range=[0, max(vals)*1.2 if max(vals)>0 else 100])), showlegend=False)
        st.plotly_chart(fig, use_container_width=True)

    with r:
        st.subheader("💡 專家診斷建議")
        for label, v in zip(cats, vals):
            if v == 0: st.error(f"❌ **{label}缺口**")
            elif label == "重傷" and v < 100: st.warning(f"⚠️ **{label}偏低** (建議重大傷病至少備足 100 萬)")
            elif v < 100: st.warning(f"⚠️ **{label}偏低**")
            else: st.success(f"✅ **{label}充足**")
