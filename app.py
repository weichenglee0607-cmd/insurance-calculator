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
    st.warning("⚠️ 尚未偵測到 API Key，請至 Streamlit Secrets 設定 GEMINI_API_KEY。")

st.set_page_config(page_title="AI 聯網保單診斷系統", layout="wide")

# --- 2. AI 聯網判讀引擎 (針對重傷優化) ---
def ai_classify(product_name):
    """聯網查詢險種並回傳類別，優先判讀重大傷病"""
    if not product_name or not API_KEY:
        return "待辨識"
    try:
        # 強調「重傷」的判讀邏輯
        prompt = f"""
        你是一位台灣保險經紀人。請判斷險種名稱「{product_name}」屬於哪一類保障？
        可選類別：壽險、意外、醫療、重傷、長照。
        注意：如果險種與重大傷病、癌症、重大疾病、特定傷病相關，請統一歸類為「重傷」。
        請只回傳類別名稱（兩個字），不要解釋。
        """
        response = model.generate_content(prompt)
        res = response.text.strip()
        for cat in ["壽險", "意外", "醫療", "重傷", "長照"]:
            if cat in res: return cat
        return "其他"
    except:
        return "查詢失敗"

# --- 3. 初始化數據 ---
if 'main_df' not in st.session_state:
    st.session_state['main_df'] = pd.DataFrame([
        {"姓名": "新客戶", "險種名稱": "範例:重大傷病定期保險", "類別": "重傷", "保費": 0, "理賠": 0}
    ])

# --- 4. 側邊欄 ---
with st.sidebar:
    st.header("👤 診斷資料設定")
    st.session_state['age'] = st.number_input("年齡", value=27)
    st.session_state['gender'] = st.selectbox("性別", ["男", "女"])
    st.divider()
    uploaded_file = st.file_uploader("📂 載入 Excel", type=["xlsx"])
    mode = st.radio("功能切換：", ["1. 資料錄入", "2. 診斷報告"])

# --- 5. 模式 1：資料錄入 ---
if mode == "1. 資料錄入":
    df = st.session_state['main_df']
    name = df['姓名'].iloc[0] if not df.empty and '姓名' in df.columns else "新客戶"
    st.header(f"📝 {name} 的保單明細表")

    if uploaded_file:
        if st.button("🚀 啟動 AI 聯絡辨識與載入"):
            raw_df = pd.read_excel(uploaded_file)
            name_col = next((c for c in raw_df.columns if "名稱" in c or "險種" in c), raw_df.columns[0])
            
            with st.spinner("AI 正在針對 重大傷病 與其他保障進行聯網判讀..."):
                raw_df['險種名稱'] = raw_df[name_col]
                raw_df['類別'] = raw_df['險種名稱'].apply(ai_classify)
            
            # 清理金額欄位
            for col in ["保費", "理賠"]:
                target = next((c for c in raw_df.columns if col in c), None)
                if target:
                    raw_df[col] = pd.to_numeric(raw_df[target].astype(str).str.replace(r'[^\d.]', '', regex=True), errors='coerce').fillna(0)
            
            st.session_state['main_df'] = raw_df
            st.success("AI 辨識完成（已將重大傷病納入判讀核心）！")
            st.rerun()

    edited_df = st.data_editor(st.session_state['main_df'], num_rows="dynamic", use_container_width=True)
    st.session_state['main_df'] = edited_df

# --- 6. 模式 2：診斷報告 (重傷版) ---
elif mode == "2. 診斷報告":
    df = st.session_state['main_df']
    st.header(f"📊 專業保障診斷報告 (重傷優化版)")
    
    total_p = df.get("保費", pd.Series([0])).sum()
    total_b = df.get("理賠", pd.Series([0])).sum()
    
    c1, c2, c3 = st.columns(3)
    c1.metric("年度總保費", f"{total_p:,.0f} 元")
    c2.metric("預估總保障", f"{total_b:,.0f} 萬元")
    c3.metric("目前年齡", f"{st.session_state['age']} 歲")
    
    st.divider()
    # 雷達圖標籤已改為 重傷
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
