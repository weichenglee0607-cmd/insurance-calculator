import streamlit as st
import pandas as pd
import io
import pdfplumber
import plotly.graph_objects as go
from PIL import Image

st.set_page_config(page_title="AI 專業保單診斷系統", layout="wide")

# --- 1. 資料清理與格式轉換 ---
def clean_and_fix_df(df):
    # 欄位自動對應映射
    mapping = {
        "姓名": ["姓名", "客戶姓名"],
        "險種名稱": ["險種名稱", "商品名稱", "險種"],
        "保費": ["保費", "保費 (年繳)", "保費(年繳)", "年繳保費"],
        "理賠": ["理賠", "預估理賠額 (萬)", "預估理賠額(萬)", "保障額度", "保額"],
        "類別": ["類別", "保障類別", "種類"]
    }
    for target, aliases in mapping.items():
        for alias in aliases:
            if alias in df.columns and target not in df.columns:
                df[target] = df[alias]
    
    # 強制轉換數值欄位，移除單位文字 (如 萬, 元)
    for col in ["保費", "理賠"]:
        if col in df.columns:
            df[col] = df[col].astype(str).str.replace(r'[^\d.]', '', regex=True)
            df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
    return df

# --- 2. 初始化 Session State ---
if 'main_df' not in st.session_state:
    st.session_state['main_df'] = pd.DataFrame([
        {"姓名": "張曉明", "險種名稱": "範例保單", "類別": "醫療", "保費": 31720, "理賠": 20}
    ])

# --- 3. 側邊欄 ---
with st.sidebar:
    st.header("👤 客戶基本資料")
    st.session_state['age'] = st.number_input("投保年齡", value=st.session_state.get('age', 27))
    st.session_state['gender'] = st.selectbox("性別", ["男", "女"])
    st.divider()
    uploaded_file = st.file_uploader("📂 載入檔案 (Excel/PDF/圖片)", type=["pdf", "xlsx", "png", "jpg", "jpeg"])
    st.divider()
    mode = st.radio("功能切換：", ["1. 資料錄入", "2. 診斷報告"])

# --- 4. 模式 1：資料錄入 ---
if mode == "1. 資料錄入":
    # 安全抓取姓名
    df_current = st.session_state['main_df']
    name = df_current['姓名'].iloc[0] if not df_current.empty and '姓名' in df_current.columns else "新客戶"
    
    st.header(f"📝 {name} 的保單明細表")
    
    # 編輯表格 (使用固定的 key 並直接與 main_df 連動)
    edited_df = st.data_editor(
        st.session_state['main_df'], 
        num_rows="dynamic", 
        use_container_width=True,
        key="data_editor_final"
    )
    st.session_state['main_df'] = edited_df

    # 下載按鈕
    if not edited_df.empty:
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            edited_df.to_excel(writer, index=False)
        st.download_button(label=f"💾 下載 {name} 的專屬 Excel", data=output.getvalue(), file_name=f"{name}_保單.xlsx")

    st.divider()
    
    # 處理上傳檔案
    if uploaded_file:
        f_ext = uploaded_file.name.split('.')[-1].lower()
        if f_ext == 'xlsx':
            if st.button("🚀 確認匯入此 Excel 資料"):
                new_data = pd.read_excel(uploaded_file)
                st.session_state['main_df'] = clean_and_fix_df(new_data)
                st.rerun() # 強制刷新以顯示新資料
        elif f_ext == 'pdf':
            with pdfplumber.open(uploaded_file) as pdf:
                text = "".join([page.extract_text() for page in pdf.pages])
            st.text_area("📄 PDF 提取文字", value=text, height=300)
        elif f_ext in ['png', 'jpg', 'jpeg']:
            st.image(Image.open(uploaded_file), use_container_width=True)

# --- 5. 模式 2：診斷報告 ---
elif mode == "2. 診斷報告":
    df_report = st.session_state['main_df'].copy()
    df_report = clean_and_fix_df(df_report)
    
    name = df_report['姓名'].iloc[0] if not df_report.empty and '姓名' in df_report.columns else "客戶"
    st.header(f"📊 {name} 專屬保障診斷報告")
    
    total_p = df_report["保費"].sum()
    total_benefit = df_report["理賠"].sum()
    
    c1, c2, c3 = st.columns(3)
    c1.metric("年度總保費", f"{total_p:,.0f} 元")
    c2.metric("預估總保障額度", f"{total_benefit:,.0f} 萬元")
    c3.metric("投保年齡", f"{st.session_state['age']} 歲")

    st.divider()
    
    # 雷達圖繪製
    l, r = st.columns([1.2, 1])
    # 類別關鍵字模糊匹配
    cat_keys = {"壽險": "壽", "意外": "意外", "醫療": "醫", "重疾": "重|疾|傷", "長照": "長|照"}
    
    if '類別' in df_report.columns:
        vals = []
        for label, k in cat_keys.items():
            v = df_report[df_report['類別'].astype(str).str.contains(k, na=False, regex=True)]["理賠"].sum()
            vals.append(v)
            
        with l:
            fig = go.Figure(data=go.Scatterpolar(r=vals, theta=list(cat_keys.keys()), fill='toself'))
            m_v = max(vals) if max(vals) > 0 else 100
            fig.update_layout(polar=dict(radialaxis=dict(visible=True, range=[0, m_v * 1.2])), showlegend=False)
            st.plotly_chart(fig, use_container_width=True)
            
        with r:
            st.subheader("💡 專家診斷建議")
            for label, v in zip(cat_keys.keys(), vals):
                if v == 0: st.error(f"❌ **{label}缺口**")
                elif v < 100: st.warning(f"⚠️ **{label}偏低** ({v:,.0f}萬)")
                else: st.success(f"✅ **{label}充足** ({v:,.0f}萬)")
