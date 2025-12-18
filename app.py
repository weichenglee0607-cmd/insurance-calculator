import streamlit as st
import pandas as pd
import io
import pdfplumber
import plotly.graph_objects as go
from PIL import Image

st.set_page_config(page_title="AI 專業保單診斷系統", layout="wide")

# --- 1. 資料清理與自動對應功能 ---
def clean_and_prepare_df(df):
    """確保欄位名稱正確，並將文字金額轉為數字"""
    # 欄位名稱自動對應
    mapping = {
        "保費": ["保費", "保費 (年繳)", "保費(年繳)", "年繳保費"],
        "理賠": ["理賠", "預估理賠額 (萬)", "預估理賠額(萬)", "預估理賠額", "保額"],
        "類別": ["類別", "保障類別", "種類"]
    }
    for target, aliases in mapping.items():
        for alias in aliases:
            if alias in df.columns and target not in df.columns:
                df[target] = df[alias]
    
    # 清理金額格式 (移除 萬, 元, 逗號)
    for col in ["保費", "理賠"]:
        if col in df.columns:
            df[col] = df[col].astype(str).str.replace(r'[^\d.]', '', regex=True)
            df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
    return df

# --- 2. 初始化 Session State ---
if 'current_df' not in st.session_state:
    st.session_state['current_df'] = pd.DataFrame([
        {"姓名": "張曉明", "險種名稱": "範例保單", "類別": "醫療", "保費 (年繳)": 0, "預估理賠額 (萬)": 0}
    ])

# --- 3. 側邊欄 ---
with st.sidebar:
    st.header("👤 客戶資料")
    st.session_state['c_age'] = st.number_input("投保年齡", value=st.session_state.get('c_age', 27))
    st.session_state['c_gender'] = st.selectbox("性別", ["男", "女"])
    st.divider()
    uploaded_file = st.file_uploader("載入檔案 (Excel/PDF/圖片)", type=["pdf", "xlsx", "png", "jpg", "jpeg"])
    st.divider()
    mode = st.radio("功能切換：", ["1. 資料錄入", "2. 診斷報告"])

# --- 4. 模式 1：資料錄入 ---
if mode == "1. 資料錄入":
    # 取得當前姓名以更新標題
    try:
        current_name = st.session_state['current_df']['姓名'].iloc[0]
    except:
        current_name = "新客戶"
        
    st.header(f"📝 {current_name} 的保單明細表")
    
    # 編輯表格
    edited_df = st.data_editor(
        st.session_state['current_df'], 
        num_rows="dynamic", 
        use_container_width=True, 
        key="pro_editor_fixed"
    )
    st.session_state['current_df'] = edited_df
    
    # 下載按鈕
    if not edited_df.empty:
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            edited_df.to_excel(writer, index=False)
        st.download_button(
            label=f"💾 下載 {current_name} 的專屬 Excel",
            data=output.getvalue(),
            file_name=f"{current_name}_保單.xlsx"
        )

    st.divider()
    st.subheader("🔍 參考視窗")
    
    # 匯入邏輯
    if uploaded_file:
        f_type = uploaded_file.name.split('.')[-1].lower()
        if f_type == 'xlsx':
            if st.button("🚀 確認匯入此 Excel 資料"):
                st.session_state['current_df'] = pd.read_excel(uploaded_file)
                st.rerun()
        elif f_type == 'pdf':
            with pdfplumber.open(uploaded_file) as pdf:
                text = "".join([page.extract_text() for page in pdf.pages])
            st.text_area("PDF 內容", value=text, height=300)
        elif f_type in ['png', 'jpg', 'jpeg']:
            st.image(Image.open(uploaded_file), use_container_width=True)
    else:
        st.info("💡 尚未載入參考檔案。")

# --- 5. 模式 2：診斷報告 ---
elif mode == "2. 診斷報告":
    df = st.session_state['current_df'].copy()
    df = clean_and_prepare_df(df)
    
    # 再次確認姓名
    try:
        r_name = df['姓名'].iloc[0]
    except:
        r_name = "客戶"
        
    st.header(f"📊 {r_name} 先生/小姐 專屬保障診斷報告")
    
    # 數值計算
    total_p = df["保費"].sum()
    total_benefit = df["理賠"].sum()
    
    c1, c2, c3 = st.columns(3)
    c1.metric("年度總保費", f"{total_p:,.0f} 元")
    c2.metric("預估總保障額度", f"{total_benefit:,.0f} 萬元")
    c3.metric("投保年齡", f"{st.session_state['c_age']} 歲")

    st.divider()
    
    # 雷達圖
    l_col, r_col = st.columns([1.2, 1])
    cat_keywords = {"壽險": "壽", "意外": "意外", "醫療": "醫", "重疾": "重|疾|傷", "長照": "長|照"}
    
    if '類別' in df.columns:
        vals = []
        for label, key in cat_keywords.items():
            val = df[df['類別'].astype(str).str.contains(key, na=False, regex=True)]["理賠"].sum()
            vals.append(val)
            
        with l_col:
            fig = go.Figure(data=go.Scatterpolar(r=vals, theta=list(cat_keywords.keys()), fill='toself'))
            max_v = max(vals) if max(vals) > 0 else 100
            fig.update_layout(polar=dict(radialaxis=dict(visible=True, range=[0, max_v * 1.2])), showlegend=False)
            st.plotly_chart(fig, use_container_width=True)
            
        with r_col:
            st.subheader("💡 專家診斷建議")
            for label, v in zip(cat_keywords.keys(), vals):
                if v == 0: st.error(f"❌ **{label}缺口**")
                elif v < 100: st.warning(f"⚠️ **{label}偏低** ({v:,.0f}萬)")
                else: st.success(f"✅ **{label}充足** ({v:,.0f}萬)")
