import streamlit as st
import pandas as pd
import google.generativeai as genai
import plotly.graph_objects as go

# --- 1. 基礎設定 ---
st.set_page_config(page_title="AI 專業保單診斷系統", layout="wide")

# 安全讀取 API Key (請確保已在 Secrets 設定 GEMINI_API_KEY)
try:
    API_KEY = st.secrets["GEMINI_API_KEY"]
    genai.configure(api_key=API_KEY)
    model = genai.GenerativeModel('gemini-1.5-flash')
except:
    st.error("❌ 找不到 API Key！請檢查 Secrets 設定。")

# --- 2. 初始化 Session (確保數據格式) ---
if 'main_df' not in st.session_state:
    st.session_state.main_df = pd.DataFrame([
        {"姓名": "張曉明", "險種名稱": "南山 10HRL", "類別": "長照", "保費": 31720, "理賠額": 24}
    ])

# --- 3. AI 聯網判讀功能 ---
def ai_lookup(name):
    if not name or name == "南山 10HRL": return "長照"
    try:
        prompt = f"你目前是台灣保險經紀人。判斷險種「{name}」分類：壽險、意外、醫療、重傷、長照。只回傳兩字。"
        return model.generate_content(prompt).text.strip()
    except: return "其他"

# --- 4. 側邊欄 ---
with st.sidebar:
    st.header("👤 診斷設定")
    age = st.number_input("年齡", value=27)
    st.divider()
    up_file = st.file_uploader("📂 載入 Excel", type=["xlsx"])
    mode = st.radio("功能切換：", ["1. 資料錄入", "2. 診斷報告"])

# --- 5. 模式 1：資料錄入 (強化數據提取) ---
if mode == "1. 資料錄入":
    df = st.session_state.main_df
    c_name = df['姓名'].iloc[0] if not df.empty else "新客戶"
    st.header(f"📝 {c_name} 的保單明細表")

    if up_file:
        if st.button("🚀 啟動 AI 辨識並讀取數字"):
            raw = pd.read_excel(up_file)
            
            # 強力搜尋欄位：只要名稱包含相關關鍵字就抓取
            n_col = next((c for c in raw.columns if any(k in str(c) for k in ["名稱", "險種", "商品"])), raw.columns[0])
            p_col = next((c for c in raw.columns if "保費" in str(c)), None)
            r_col = next((c for c in raw.columns if any(k in str(c) for k in ["理賠", "保額", "額度", "保障"])), None)
            
            with st.spinner("AI 正在解析您的保單並強制提取數據..."):
                new_df = pd.DataFrame()
                new_df['姓名'] = [c_name] * len(raw)
                new_df['險種名稱'] = raw[n_col]
                
                # 數字清理器：解決 0 萬與文字干擾問題
                def force_num(v):
                    if pd.isna(v): return 0
                    # 移除非數字字符，保留小數點
                    import re
                    s = re.sub(r'[^\d.]', '', str(v))
                    return pd.to_numeric(s, errors='coerce') or 0
                
                new_df['保費'] = raw[p_col].apply(force_num) if p_col else 0
                new_df['理賠額'] = raw[r_col].apply(force_num) if r_col else 0
                new_df['類別'] = new_df['險種名稱'].apply(ai_lookup)
                
            st.session_state.main_df = new_df
            st.success("數據提取成功！")
            st.rerun()

    # 顯示並允許手動修正表格
    st.session_state.main_df = st.data_editor(st.session_state.main_df, num_rows="dynamic", use_container_width=True)

# --- 6. 模式 2：診斷報告 (數據視覺化) ---
elif mode == "2. 診斷報告":
    df = st.session_state.main_df
    st.header("📊 專業保障診斷報告")

    # 指標顯示
    t_p = df['保費'].sum()
    t_r = df['理賠額'].sum()
    
    c1, c2, c3 = st.columns(3)
    c1.metric("年度總保費", f"{int(t_p):,} 元")
    c2.metric("預估總保障 (含重傷/長照)", f"{int(t_r):,} 萬元")
    c3.metric("目前年齡", f"{age} 歲")

    st.divider()
    
    # 雷達圖
    cats = ["壽險", "意外", "醫療", "重傷", "長照"]
    vals = []
    for c in cats:
        # 模糊比對類別，確保重傷與重大傷病合併
        mask = df['類別'].astype(str).str.contains(c[:2], na=False)
        if c == "重傷": mask = mask | df['類別'].astype(str).str.contains("重大", na=False)
        vals.append(df[mask]['理賠額'].sum())
    
    l, r = st.columns([1.2, 1])
    with l:
        fig = go.Figure(data=go.Scatterpolar(r=vals, theta=cats, fill='toself', line_color='#E44D26'))
        max_v = max(vals) if max(vals) > 0 else 100
        fig.update_layout(polar=dict(radialaxis=dict(visible=True, range=[0, max_v * 1.2])), showlegend=False)
        st.plotly_chart(fig, use_container_width=True)
    
    with r:
        st.subheader("💡 缺口診斷建議")
        for label, v in zip(cats, vals):
            if v == 0:
                st.error(f"❌ **{label}缺口**：保障金額 0 萬")
            elif label == "重傷" and v < 100:
                st.warning(f"⚠️ **{label}偏低**：{v:,.0f} 萬 (重傷建議 100 萬以上)")
            else:
                st.success(f"✅ **{label}數據**：{v:,.0f} 萬")
