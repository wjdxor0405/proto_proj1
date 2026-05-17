"""
기업 FAQ 조회 페이지
- 크롤링 실행 및 결과 조회
- MySQL 누적 데이터 조회
"""
import streamlit as st
import pandas as pd
from pathlib import Path
import sys, threading, time
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent.parent))

DB_AVAILABLE = False
try:
    from utils.database import (
        init_database, get_companies, add_company, delete_company,
        save_faq_items, create_session, finish_session,
        get_sessions, get_faq_by_session, get_all_faq, get_faq_stats,
        get_connection,
    )
    try:
        conn = get_connection()
        conn.close()
        DB_AVAILABLE = True
    except Exception:
        pass
except Exception:
    pass

CRAWLER_AVAILABLE = False
try:
    from selenium import webdriver
    from bs4 import BeautifulSoup
    CRAWLER_AVAILABLE = True
except ImportError:
    pass


# 세션 상태 초기화
def _init_state():
    defaults = {
        "crawl_running": False,
        "crawl_log": [],
        "last_session_results": [],
        "last_session_id": None,
        "last_company": None,
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v


def render():
    _init_state()
    st.header("🔍 기업 FAQ 조회")

    # DB 상태 배너
    if not DB_AVAILABLE:
        st.warning(
            "⚠️ MySQL 연결 불가. FAQ 누적 저장 기능을 사용하려면 MySQL을 설정하세요.\n\n"
            "`pip install mysql-connector-python` 후 utils/database.py에서 DB_CONFIG를 수정하세요.",
            icon="🗄️"
        )
    else:
        if st.button("🔄 DB 초기화", help="테이블이 없으면 생성합니다."):
            init_database()
            st.success("DB 초기화 완료")

    if not CRAWLER_AVAILABLE:
        st.warning(
            "⚠️ 크롤러 패키지 미설치. 아래 명령어로 설치하세요:\n\n"
            "```\npip install selenium beautifulsoup4\n```",
            icon="🕷️"
        )

    # 사이드 탭
    tab1, tab2, tab3, tab4 = st.tabs(["🕷️ 크롤링 실행", "📌 최근 수집 결과", "🗄️ 누적 데이터 조회", "⚙️ 기업 관리"])

    with tab1:
        _render_crawl_tab()

    with tab2:
        _render_last_session_tab()

    with tab3:
        _render_accumulated_tab()

    with tab4:
        _render_company_manage_tab()


def _render_crawl_tab():
    st.subheader("FAQ 크롤링 실행")

    companies = _get_companies_list()

    if not companies:
        st.info("등록된 기업이 없습니다. [기업 관리] 탭에서 추가하세요.")
        return

    company_map = {f"{c['company_name']} ({c['company_code']})": c for c in companies}
    selected_label = st.selectbox("기업 선택", list(company_map.keys()))
    selected = company_map[selected_label]

    st.info(f"**FAQ URL**: {selected['faq_url']}")

    col1, col2 = st.columns(2)
    with col1:
        if st.button("🚀 크롤링 시작", disabled=st.session_state.crawl_running or not CRAWLER_AVAILABLE, type="primary"):
            _start_crawl(selected)

    with col2:
        if st.session_state.crawl_running:
            st.info("⏳ 크롤링 중...")

    # 로그 출력
    if st.session_state.crawl_log:
        with st.expander("📋 크롤링 로그", expanded=True):
            for log in st.session_state.crawl_log:
                st.text(log)

    if not CRAWLER_AVAILABLE:
        st.error("selenium, beautifulsoup4 패키지를 설치해야 크롤링이 가능합니다.")


def _start_crawl(company):
    st.session_state.crawl_running = True
    st.session_state.crawl_log = [f"[{_now()}] 크롤링 시작: {company['company_name']}"]
    st.session_state.last_session_results = []
    st.session_state.last_company = company["company_code"]

    session_id = None
    if DB_AVAILABLE:
        session_id = create_session(company["company_code"])
    st.session_state.last_session_id = session_id

    def log(msg):
        st.session_state.crawl_log.append(f"[{_now()}] {msg}")

    try:
        from crawlers.kia_crawler import crawl_generic_faq
        results = crawl_generic_faq(
            url=company["faq_url"],
            company_code=company["company_code"],
            company_name=company["company_name"],
            progress_callback=log,
        )
        st.session_state.last_session_results = results
        log(f"✅ 완료: {len(results)}개 수집")

        if DB_AVAILABLE and session_id:
            saved = save_faq_items(results, company["company_code"], session_id)
            finish_session(session_id, saved)
            log(f"💾 DB 저장: {saved}개")

    except Exception as e:
        log(f"❌ 오류: {e}")

    finally:
        st.session_state.crawl_running = False

    st.rerun()


def _render_last_session_tab():
    st.subheader("최근 크롤링 결과")

    results = st.session_state.last_session_results
    company = st.session_state.last_company

    if not results:
        st.info("아직 이번 세션에서 수집된 데이터가 없습니다. [크롤링 실행] 탭에서 크롤링을 시작하세요.")
        return

    st.success(f"✅ 최근 수집: **{company}** - {len(results)}개 FAQ")

    # 검색
    search = st.text_input("🔍 검색", placeholder="질문/답변 키워드", key="last_search")
    df = pd.DataFrame(results)

    if search:
        mask = (
            df["question"].str.contains(search, na=False) |
            df.get("answer", pd.Series()).astype(str).str.contains(search, na=False) |
            df.get("category", pd.Series()).astype(str).str.contains(search, na=False)
        )
        df = df[mask]

    # 카테고리 필터
    if "category" in df.columns:
        cats = ["전체"] + sorted(df["category"].dropna().unique().tolist())
        cat = st.selectbox("카테고리", cats, key="last_cat")
        if cat != "전체":
            df = df[df["category"] == cat]

    st.caption(f"{len(df)}개 결과")

    for _, row in df.iterrows():
        with st.expander(f"❓ {row.get('question', '')[:80]}"):
            if row.get("category"):
                st.caption(f"📂 {row['category']}")
            st.markdown(f"**Q.** {row.get('question', '')}")
            st.markdown(f"**A.** {row.get('answer', '(답변 없음)')}")


def _render_accumulated_tab():
    st.subheader("누적 데이터 조회 (MySQL)")

    if not DB_AVAILABLE:
        st.error("MySQL 연결이 필요합니다.")
        return

    companies = _get_companies_list()
    company_options = {"전체": None}
    for c in companies:
        company_options[f"{c['company_name']}"] = c["company_code"]

    col1, col2, col3 = st.columns(3)
    with col1:
        selected_company_label = st.selectbox("기업 필터", list(company_options.keys()), key="acc_company")
    with col2:
        search_kw = st.text_input("🔍 키워드 검색", key="acc_search")
    with col3:
        view_mode = st.radio("조회 방식", ["전체 누적", "세션별 조회"], horizontal=True)

    company_code = company_options[selected_company_label]

    if view_mode == "세션별 조회":
        sessions = get_sessions(company_code)
        if not sessions:
            st.info("수집 세션이 없습니다.")
            return
        session_labels = {
            f"{s['session_id']} | {s['total_count']}개 | {s['started_at']}": s["session_id"]
            for s in sessions
        }
        chosen_label = st.selectbox("세션 선택", list(session_labels.keys()))
        chosen_sid = session_labels[chosen_label]
        rows = get_faq_by_session(chosen_sid)
        df = pd.DataFrame(rows) if rows else pd.DataFrame()
        st.info(f"이 세션에서 수집된 FAQ: {len(df)}개")
    else:
        rows = get_all_faq(company_code, search_kw or None)
        df = pd.DataFrame(rows) if rows else pd.DataFrame()

        # 통계
        stats = get_faq_stats(company_code)
        k1, k2 = st.columns(2)
        k1.metric("누적 FAQ 수", f"{stats['total']:,}개" if stats["total"] else "0개")
        k2.metric("최근 수집", str(stats["last_crawled"])[:16] if stats["last_crawled"] else "-")

    if df.empty:
        st.info("조회된 데이터가 없습니다.")
        return

    # 표 표시
    display_cols = [c for c in ["company_code", "category", "question", "answer", "crawled_at"] if c in df.columns]
    st.dataframe(df[display_cols], use_container_width=True, height=400, hide_index=True)

    # 상세 보기
    st.markdown("---")
    st.subheader("상세 보기")
    for _, row in df.head(50).iterrows():
        with st.expander(f"❓ {str(row.get('question',''))[:80]}"):
            st.caption(f"📂 {row.get('category', '')} | 🏢 {row.get('company_code', '')} | 🕐 {str(row.get('crawled_at',''))[:16]}")
            st.markdown(f"**Q.** {row.get('question', '')}")
            st.markdown(f"**A.** {row.get('answer', '(답변 없음)')}")


def _render_company_manage_tab():
    st.subheader("기업 FAQ 관리")

    companies = _get_companies_list()

    # 현재 등록된 기업 목록
    st.markdown("**등록된 기업**")
    for c in companies:
        col1, col2, col3, col4 = st.columns([2, 3, 4, 1])
        col1.write(f"**{c['company_name']}**")
        col2.write(f"`{c['company_code']}`")
        col3.write(c['faq_url'][:40] + "...")
        if col4.button("🗑️", key=f"del_{c['company_code']}"):
            if DB_AVAILABLE:
                delete_company(c["company_code"])
                st.success(f"{c['company_name']} 삭제 완료")
                st.rerun()
            else:
                st.error("DB 연결 필요")

    st.markdown("---")
    st.markdown("**새 기업 추가**")

    with st.form("add_company_form"):
        nc1, nc2 = st.columns(2)
        new_code = nc1.text_input("기업 코드 (영문)", placeholder="예: hyundai")
        new_name = nc2.text_input("기업명", placeholder="예: 현대자동차")
        new_url = st.text_input("FAQ URL", placeholder="https://...")
        submitted = st.form_submit_button("➕ 추가", type="primary")

        if submitted:
            if not new_code or not new_name or not new_url:
                st.error("모든 필드를 입력하세요.")
            elif DB_AVAILABLE:
                try:
                    add_company(new_code.strip(), new_name.strip(), new_url.strip())
                    st.success(f"✅ {new_name} 추가 완료")
                    st.rerun()
                except Exception as e:
                    st.error(f"추가 실패: {e}")
            else:
                st.warning("DB 없이는 세션 내에서만 유지됩니다.")
                if "temp_companies" not in st.session_state:
                    st.session_state.temp_companies = []
                st.session_state.temp_companies.append({
                    "company_code": new_code,
                    "company_name": new_name,
                    "faq_url": new_url,
                })
                st.success("임시 추가 완료 (재시작 시 초기화)")
                st.rerun()


def _get_companies_list():
    """DB 또는 임시 목록에서 기업 반환"""
    if DB_AVAILABLE:
        try:
            return get_companies()
        except Exception:
            pass

    # DB 없을 때 기본값 + 임시 추가 목록
    base = [
        {"company_code": "kia", "company_name": "기아자동차", "faq_url": "https://www.kia.com/kr/customer-service/center/faq"},
        {"company_code": "hyundai", "company_name": "현대자동차", "faq_url": "https://www.hyundai.com/kr/ko/e/customer/center/faq"},
        {"company_code": "genesis", "company_name": "제네시스", "faq_url": "https://www.genesis.com/kr/ko/support/faq.html"},
    ]
    extra = st.session_state.get("temp_companies", [])
    return base + extra


def _now():
    return datetime.now().strftime("%H:%M:%S")
