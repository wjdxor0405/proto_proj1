"""
기아자동차 FAQ 크롤러
Beautiful Soup + Selenium 활용
"""
import time
import re
from datetime import datetime

try:
    from selenium import webdriver
    from selenium.webdriver.common.by import By
    from selenium.webdriver.chrome.options import Options
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC
    SELENIUM_AVAILABLE = True
except ImportError:
    SELENIUM_AVAILABLE = False

try:
    from bs4 import BeautifulSoup
    BS4_AVAILABLE = True
except ImportError:
    BS4_AVAILABLE = False


COMPANY_CODE = "kia"
COMPANY_NAME = "기아자동차"
FAQ_URL = "https://www.kia.com/kr/customer-service/center/faq"


def _get_driver():
    opts = Options()
    opts.add_argument("--headless")
    opts.add_argument("--no-sandbox")
    opts.add_argument("--disable-dev-shm-usage")
    opts.add_argument("--disable-gpu")
    opts.add_argument("--window-size=1280,800")
    opts.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120 Safari/537.36")
    driver = webdriver.Chrome(options=opts)
    return driver


def crawl_kia_faq(progress_callback=None):
    """
    기아 FAQ 크롤링
    반환: list of {category, question, answer}
    """
    if not SELENIUM_AVAILABLE or not BS4_AVAILABLE:
        raise ImportError("selenium 및 beautifulsoup4 패키지가 필요합니다.")

    driver = _get_driver()
    results = []

    try:
        if progress_callback:
            progress_callback("페이지 로딩 중...")
        driver.get(FAQ_URL)
        time.sleep(3)

        # 카테고리 탭 목록 파악
        try:
            wait = WebDriverWait(driver, 10)
            wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, ".faq-wrap, .tab-list, [class*='faq'], [class*='tab']")))
        except Exception:
            pass

        soup = BeautifulSoup(driver.page_source, "html.parser")

        # 카테고리 탭 추출 시도
        category_tabs = []
        tab_selectors = [
            ".tab-list li", ".category-list li", "[class*='tab-item']",
            ".faq-category li", "ul.tab li", ".tabs li"
        ]
        for sel in tab_selectors:
            tabs = soup.select(sel)
            if tabs:
                category_tabs = tabs
                break

        categories = []
        for tab in category_tabs:
            text = tab.get_text(strip=True)
            data_id = tab.get("data-id") or tab.get("data-tab") or tab.get("id", "")
            if text:
                categories.append({"text": text, "elem": tab, "data_id": data_id})

        if progress_callback:
            progress_callback(f"카테고리 {len(categories)}개 발견, FAQ 수집 중...")

        if not categories:
            # 카테고리 없이 바로 FAQ 수집
            items = _extract_faq_from_soup(soup, category="전체")
            results.extend(items)
        else:
            # 카테고리별 클릭 후 수집
            cat_elements = driver.find_elements(By.CSS_SELECTOR, ", ".join(tab_selectors))
            for i, cat in enumerate(categories[:10]):  # 최대 10개 카테고리
                try:
                    if i < len(cat_elements):
                        driver.execute_script("arguments[0].click();", cat_elements[i])
                        time.sleep(2)
                    soup = BeautifulSoup(driver.page_source, "html.parser")
                    items = _extract_faq_from_soup(soup, category=cat["text"])
                    results.extend(items)
                    if progress_callback:
                        progress_callback(f"[{cat['text']}] {len(items)}개 수집")
                except Exception as e:
                    if progress_callback:
                        progress_callback(f"[{cat['text']}] 오류: {e}")

        # 결과가 없으면 전체 페이지에서 재시도
        if not results:
            soup = BeautifulSoup(driver.page_source, "html.parser")
            results = _extract_faq_from_soup(soup, "전체")

    finally:
        driver.quit()

    return results


def _extract_faq_from_soup(soup, category="전체"):
    """BeautifulSoup으로 FAQ Q&A 추출"""
    items = []

    # 방법 1: accordion/toggle 패턴
    faq_selectors = [
        (".faq-list li", ".question, .q, [class*='question']", ".answer, .a, [class*='answer']"),
        (".accordion-item", ".accordion-header, .accordion-title", ".accordion-body, .accordion-content"),
        ("[class*='faq-item']", "[class*='question'], [class*='title']", "[class*='answer'], [class*='content']"),
        ("dl", "dt", "dd"),
    ]

    for container_sel, q_sel, a_sel in faq_selectors:
        containers = soup.select(container_sel)
        if not containers:
            continue
        for container in containers:
            q_elem = container.select_one(q_sel)
            a_elem = container.select_one(a_sel)
            if q_elem:
                q_text = q_elem.get_text(strip=True)
                a_text = a_elem.get_text(strip=True) if a_elem else ""
                if q_text and len(q_text) > 5:
                    items.append({
                        "category": category,
                        "question": q_text,
                        "answer": a_text,
                    })
        if items:
            break

    # 방법 2: 텍스트 패턴으로 Q: A: 형태 찾기
    if not items:
        text = soup.get_text("\n")
        lines = [l.strip() for l in text.split("\n") if l.strip()]
        i = 0
        while i < len(lines):
            line = lines[i]
            if re.match(r'^Q[\.\:]\s*.+', line) or line.startswith("질문"):
                q_text = re.sub(r'^Q[\.\:]\s*', '', line)
                a_text = ""
                if i + 1 < len(lines):
                    next_line = lines[i + 1]
                    if re.match(r'^A[\.\:]\s*.+', next_line) or next_line.startswith("답변"):
                        a_text = re.sub(r'^A[\.\:]\s*', '', next_line)
                        i += 1
                if q_text:
                    items.append({"category": category, "question": q_text, "answer": a_text})
            i += 1

    return items


# 범용 크롤러 (다른 기업 확장용)
def crawl_generic_faq(url, company_code, company_name, progress_callback=None):
    """
    범용 FAQ 크롤러 - 기업 URL만 주면 동작
    """
    if not SELENIUM_AVAILABLE or not BS4_AVAILABLE:
        raise ImportError("selenium 및 beautifulsoup4 패키지가 필요합니다.")

    driver = _get_driver()
    results = []
    try:
        if progress_callback:
            progress_callback(f"{company_name} FAQ 페이지 로딩 중...")
        driver.get(url)
        time.sleep(3)
        soup = BeautifulSoup(driver.page_source, "html.parser")
        results = _extract_faq_from_soup(soup, category="전체")
        if progress_callback:
            progress_callback(f"{len(results)}개 FAQ 수집 완료")
    finally:
        driver.quit()
    return results
