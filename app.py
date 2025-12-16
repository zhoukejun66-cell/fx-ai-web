import streamlit as st
import yfinance as yf
import feedparser
from openai import OpenAI
import pandas as pd
from datetime import datetime

# --- 页面基础设置 ---
st.set_page_config(page_title="全球汇率AI参谋", page_icon="📈", layout="centered")

# --- 读取密钥 ---
# 这一步会从Streamlit后台读取你的密码，非常安全
try:
    api_key = st.secrets["OPENAI_API_KEY"]
    base_url = st.secrets.get("BASE_URL", "https://api.openai.com/v1") # 默认OpenAI，可兼容DeepSeek
    client = OpenAI(api_key=api_key, base_url=base_url)
except:
    st.error("⚠️ 未检测到 API Key，请在 Streamlit 后台 Secrets 中配置！")
    st.stop()

# --- 核心功能 1: 获取数据 ---
@st.cache_data(ttl=3600) # 缓存1小时，避免刷新太频繁被封
def get_data():
    # 获取汇率
    tickers = ["CNY=X", "JPY=X"]
    data = yf.download(tickers, period="1mo", interval="1d", progress=False)['Close']
    
    # 获取最新值
    usd_cny = data['CNY=X'].iloc[-1]
    usd_jpy = data['JPY=X'].iloc[-1]
    # 算出日元兑人民币 (100日元 = ?人民币)
    jpy_cny = (usd_cny / usd_jpy) * 100
    
    return usd_cny, usd_jpy, jpy_cny, data

# --- 核心功能 2: 抓取新闻 ---
def get_news():
    # 抓取Yahoo财经新闻RSS
    feed = feedparser.parse("https://finance.yahoo.com/news/rssindex")
    news_items = []
    for entry in feed.entries[:6]: # 只看前6条
        news_items.append(f"- {entry.title}")
    return "\n".join(news_items)

# --- 核心功能 3: AI分析 ---
def ask_ai(news, cny, jpy):
    prompt = f"""
    你是一个外汇交易专家。基于以下数据和新闻进行分析：
    【实时汇率】USD/CNY: {cny:.4f}, USD/JPY: {jpy:.2f}
    【全球财经新闻】
    {news}
    
    请输出一份中文简报，包含：
    1. **市场情绪**：用一个词形容（如：恐慌、贪婪、观望）。
    2. **下周走势预判**：
       - 美元：[看涨/看跌/震荡]
       - 日元：[看涨/看跌/震荡]
       - 人民币：[看涨/看跌/震荡]
    3. **关键逻辑**：简述理由（不超过100字）。
    """
    
    response = client.chat.completions.create(
        model="deepseek-chat", # 改为 DeepSeek 的免费/低成本基础模型
        messages=[{"role": "user", "content": prompt}]
    )
    return response.choices[0].message.content

# --- 界面展示 ---
st.title("🌏 全球汇率 AI 参谋")
st.write(f"最后更新: {datetime.now().strftime('%m-%d %H:%M')}")

# 1. 展示行情
with st.spinner('正在连接全球市场...'):
    try:
        u_c, u_j, j_c, df = get_data()
        c1, c2, c3 = st.columns(3)
        c1.metric("USD/CNY", f"{u_c:.4f}")
        c2.metric("USD/JPY", f"{u_j:.2f}")
        c3.metric("100 JPY/CNY", f"{j_c:.2f}")
    except Exception as e:
        st.error(f"获取行情数据失败，请稍后再试。错误: {e}")
        st.stop()

# 2. AI 分析报告
st.markdown("---")
st.subheader("🤖 AI 走势预判")

# 按钮触发AI分析（为了省钱，点一下才运行）
if st.button("开始分析 (读取最新新闻)"):
    with st.spinner('AI 正在阅读华尔街新闻...'):
        news_text = get_news()
        report = ask_ai(news_text, u_c, u_j)
        st.success("分析完成！")
        st.markdown(report)
        with st.expander("查看原始新闻来源"):
            st.text(news_text)

# 3. 趋势图 Switch to DeepSeek model
st.markdown("---")
st.subheader("📊 近期走势 (30天)")
st.line_chart(df)
