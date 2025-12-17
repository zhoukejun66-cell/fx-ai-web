import streamlit as st
import yfinance as yf
import feedparser
import pandas as pd
from datetime import datetime

# --- 页面基础设置 ---
# 将标题改为更贴合新闻情绪分析的名称
st.set_page_config(page_title="全球汇率情绪哨兵", page_icon="🚨", layout="centered")

# --- 核心功能 1: 获取数据 ---
@st.cache_data(ttl=3600) # 缓存1小时，避免刷新太频繁被封
def get_data():
    # 获取汇率
    tickers = ["CNY=X", "JPY=X"]
    # 周期改为近3个月，方便观察大趋势
    data = yf.download(tickers, period="3mo", interval="1d", progress=False)['Close'] 
    
    # 获取最新值
    usd_cny = data['CNY=X'].iloc[-1]
    usd_jpy = data['JPY=X'].iloc[-1]
    # 算出日元兑人民币 (100日元 = ?人民币)
    jpy_cny = (usd_cny / usd_jpy) * 100
    
    return usd_cny, usd_jpy, jpy_cny, data

# --- 核心功能 2: 抓取新闻 ---
def get_news():
    # 抓取Yahoo财经新闻RSS (权威且免费)
    feed = feedparser.parse("https://finance.yahoo.com/news/rssindex")
    news_items = []
    # 抓取前10条新闻，以保证关键词覆盖率
    for entry in feed.entries[:10]: 
        news_items.append(f"- {entry.title}")
    return "\n".join(news_items)


# --- 核心功能 3: 新闻情绪权重分析 (替代AI) ---
# 定义一个基于关键词的得分函数，彻底移除API调用
def calculate_sentiment_score(news_text):
    # 预设关键词权重 (数值越大，利好该货币的力度越大)
    weights = {
        # 利多美元 (USD +)
        "Fed hawkish": 6, "CPI surprise": 5, "Non-farm strong": 4, "US rates rise": 7,
        # 利空美元 (USD -)
        "Fed dovish": -6, "Recession fears": -4, "Inflation slows": -5,
        # 利多日元 (JPY +)
        "BOJ exit": 7, "YCC end": 8, "Intervention warning": 6,
        # 利空日元 (JPY -)
        "BOJ dovish": -6, "Japan rates stable": -4, "Kuroda": -3,
        # 利多人民币 (CNY +)
        "China GDP strong": 5, "China stimulus": 4, "PBOC stable": 3,
        # 利空人民币 (CNY -)
        "PBOC cut": -5, "Manufacturing weak": -4, "Trade tensions": -3,
    }
    
    scores = {"USD": 0, "JPY": 0, "CNY": 0}
    
    # 将新闻文本转换为小写进行匹配
    lower_news = news_text.lower()
    
    for keyword, weight in weights.items():
        if keyword.lower() in lower_news:
            # 根据关键词判断影响哪个货币
            if "fed" in keyword.lower() or "us" in keyword.lower() or "cpi" in keyword.lower() or "non-farm" in keyword.lower():
                scores["USD"] += weight
            if "boj" in keyword.lower() or "jpy" in keyword.lower() or "ycc" in keyword.lower() or "japan" in keyword.lower():
                scores["JPY"] += weight
            if "china" in keyword.lower() or "pboc" in keyword.lower() or "gdp" in keyword.lower():
                scores["CNY"] += weight
                
    return scores

# --- 界面展示 ---
st.title("🚨 全球汇率情绪哨兵")
st.write(f"最后更新: {datetime.now().strftime('%Y-%m-%d %H:%M')} (数据缓存1小时)")

# 1. 展示行情
with st.spinner('正在连接全球市场...'):
    try:
        u_c, u_j, j_c, df = get_data()
        c1, c2, c3 = st.columns(3)
        c1.metric("USD/CNY (美元)", f"{u_c:.4f}")
        c2.metric("USD/JPY (日元)", f"{u_j:.2f}")
        c3.metric("100 JPY/CNY", f"{j_c:.2f}")
    except Exception as e:
        st.error(f"获取行情数据失败，请稍后再试。错误: {e}")
        st.stop()


# 2. 新闻情绪分析报告
st.markdown("---")
st.subheader("📰 新闻关键词情绪得分 (零成本预判)")

# 按钮触发分析
if st.button("立即分析新闻情绪"):
    with st.spinner('正在抓取并计算市场情绪...'):
        news_text = get_news() # 抓取新闻
        scores = calculate_sentiment_score(news_text) # 计算得分
        
        st.success("情绪分析完成！得分越高，短期走势越强！")
        
        col_u, col_j, col_c = st.columns(3)
        
        # 定义颜色辅助函数
        def get_sentiment_color_text(score):
            if score > 5:
                return "（极度看涨 🟢）"
            elif score > 1:
                return "（适度看涨 🟡）"
            elif score < -5:
                return "（极度看跌 🔴）"
            elif score < -1:
                return "（适度看跌 🟠）"
            else:
                return "（震荡观望 ⚪）"

        col_u.metric("🇺🇸 美元 (USD)", f"{scores['USD']} 分", get_sentiment_color_text(scores['USD']))
        col_j.metric("🇯🇵 日元 (JPY)", f"{scores['JPY']} 分", get_sentiment_color_text(scores['JPY']))
        col_c.metric("🇨🇳 人民币 (CNY)", f"{scores['CNY']} 分", get_sentiment_color_text(scores['CNY']))
        
        st.markdown("---")
        with st.expander("📝 查看情绪依据 (新闻头条)"):
            st.text(news_text)

# 3. 趋势图
st.markdown("---")
st.subheader("📈 近期走势 (3个月)")
st.line_chart(df)
