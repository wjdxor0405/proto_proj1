"""
자동차 대시보드 메인 앱
- 전국 자동차 등록 현황
- 기업 FAQ 조회
"""
import streamlit as st
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent))

st.set_page_config(
    page_title="자동차 등록 & FAQ 대시보드",
    page_icon="🚗",
    layout="wide",
    initial_sidebar_state="expanded",
)

# CSS 스타일
st.markdown("""
<style>
    /* 사이드바 스타일 */
    .sidebar-title {
        font-size: 20px;
        font-weight: 700;
        color: #1a1a2e;
        padding: 10px 0;
    }
    /* 메트릭 카드 */
    [data-testid="metric-container"] {
        background-color: #f0f4ff;
        border: 1px solid #d0d8ff;
        border-radius: 10px;
        padding: 10px 15px;
    }
    /* 탭 스타일 */
    .stTabs [data-baseweb="tab-list"] {
        gap: 8px;
    }
    .stTabs [data-baseweb="tab"] {
        border-radius: 8px 8px 0 0;
        font-weight: 600;
    }
    /* 헤더 */
    h1 { color: #1a1a2e; }
    h2 { color: #16213e; }
    h3 { color: #0f3460; }
    /* expander */
    .streamlit-expanderHeader {
        font-weight: 600;
    }
</style>
""", unsafe_allow_html=True)


# 사이드바 네비게이션
with st.sidebar:
    st.markdown("## 🚗 자동차 대시보드")
    st.markdown("---")

    page = st.radio(
        "메뉴",
        ["🚗 전국 자동차 등록 현황", "🔍 기업 FAQ 조회"],
        label_visibility="collapsed",
    )

    st.markdown("---")
    st.markdown("### 📌 시스템 정보")

    # DB 상태
    db_ok = False
    try:
        from utils.database import get_connection
        conn = get_connection()
        conn.close()
        db_ok = True
    except Exception:
        pass

    st.markdown(f"**MySQL**: {'🟢 연결됨' if db_ok else '🔴 미연결'}")

    # 크롤러 상태
    crawler_ok = False
    try:
        import selenium
        from bs4 import BeautifulSoup
        crawler_ok = True
    except ImportError:
        pass

    st.markdown(f"**크롤러**: {'🟢 준비됨' if crawler_ok else '🔴 미설치'}")

    # 데이터 파일 수
    data_dir = Path(__file__).parent / "data"
    xlsx_count = len(list(data_dir.glob("*.xlsx")))
    st.markdown(f"**데이터 파일**: {xlsx_count}개")

    st.markdown("---")
    st.markdown(
        "<small>📦 필요 패키지<br>"
        "• streamlit<br>"
        "• pandas, openpyxl<br>"
        "• plotly<br>"
        "• selenium<br>"
        "• beautifulsoup4<br>"
        "• mysql-connector-python</small>",
        unsafe_allow_html=True
    )


# 페이지 라우팅
if "전국 자동차" in page:
    from pages.car_page import render
    render()
else:
    from pages.faq_page import render
    render()
