"""
MySQL 데이터베이스 연결 및 스키마 관리 모듈
"""
import mysql.connector
from mysql.connector import Error
import streamlit as st
from datetime import datetime


DB_CONFIG = {
    "host": "localhost",
    "port": 3306,
    "user": "root",
    "password": "",
    "database": "car_dashboard",
    "charset": "utf8mb4",
}


def get_connection():
    try:
        conn = mysql.connector.connect(**DB_CONFIG)
        return conn
    except Error as e:
        raise ConnectionError(f"DB 연결 실패: {e}")


def init_database():
    """DB 및 테이블 초기화"""
    try:
        cfg = {k: v for k, v in DB_CONFIG.items() if k != "database"}
        conn = mysql.connector.connect(**cfg)
        cursor = conn.cursor()
        cursor.execute(f"CREATE DATABASE IF NOT EXISTS {DB_CONFIG['database']} CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci")
        conn.database = DB_CONFIG["database"]

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS faq_companies (
                id INT AUTO_INCREMENT PRIMARY KEY,
                company_code VARCHAR(50) UNIQUE NOT NULL,
                company_name VARCHAR(100) NOT NULL,
                faq_url VARCHAR(500) NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            ) CHARACTER SET utf8mb4
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS faq_items (
                id INT AUTO_INCREMENT PRIMARY KEY,
                company_code VARCHAR(50) NOT NULL,
                category VARCHAR(200),
                question TEXT NOT NULL,
                answer LONGTEXT,
                crawled_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                session_id VARCHAR(100),
                INDEX idx_company (company_code),
                INDEX idx_session (session_id),
                INDEX idx_crawled (crawled_at)
            ) CHARACTER SET utf8mb4
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS crawl_sessions (
                id INT AUTO_INCREMENT PRIMARY KEY,
                session_id VARCHAR(100) UNIQUE NOT NULL,
                company_code VARCHAR(50),
                started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                ended_at TIMESTAMP NULL,
                total_count INT DEFAULT 0,
                status VARCHAR(50) DEFAULT 'running'
            ) CHARACTER SET utf8mb4
        """)

        # 기본 기업 등록
        default_companies = [
            ("kia", "기아자동차", "https://www.kia.com/kr/customer-service/center/faq"),
            ("hyundai", "현대자동차", "https://www.hyundai.com/kr/ko/e/customer/center/faq"),
            ("genesis", "제네시스", "https://www.genesis.com/kr/ko/support/faq.html"),
        ]
        for code, name, url in default_companies:
            cursor.execute(
                "INSERT IGNORE INTO faq_companies (company_code, company_name, faq_url) VALUES (%s, %s, %s)",
                (code, name, url)
            )

        conn.commit()
        cursor.close()
        conn.close()
        return True
    except Error as e:
        return False


def get_companies():
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM faq_companies ORDER BY company_name")
    result = cursor.fetchall()
    cursor.close()
    conn.close()
    return result


def add_company(code, name, url):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO faq_companies (company_code, company_name, faq_url) VALUES (%s, %s, %s)",
        (code, name, url)
    )
    conn.commit()
    cursor.close()
    conn.close()


def delete_company(code):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM faq_companies WHERE company_code = %s", (code,))
    cursor.execute("DELETE FROM faq_items WHERE company_code = %s", (code,))
    conn.commit()
    cursor.close()
    conn.close()


def save_faq_items(items, company_code, session_id):
    if not items:
        return 0
    conn = get_connection()
    cursor = conn.cursor()
    count = 0
    for item in items:
        cursor.execute(
            "INSERT INTO faq_items (company_code, category, question, answer, session_id) VALUES (%s, %s, %s, %s, %s)",
            (company_code, item.get("category", ""), item.get("question", ""), item.get("answer", ""), session_id)
        )
        count += 1
    conn.commit()
    cursor.close()
    conn.close()
    return count


def create_session(company_code):
    session_id = f"{company_code}_{datetime.now().strftime('%Y%m%d%H%M%S')}"
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO crawl_sessions (session_id, company_code) VALUES (%s, %s)",
        (session_id, company_code)
    )
    conn.commit()
    cursor.close()
    conn.close()
    return session_id


def finish_session(session_id, count):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "UPDATE crawl_sessions SET ended_at=NOW(), total_count=%s, status='done' WHERE session_id=%s",
        (count, session_id)
    )
    conn.commit()
    cursor.close()
    conn.close()


def get_sessions(company_code=None):
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    if company_code:
        cursor.execute(
            "SELECT * FROM crawl_sessions WHERE company_code=%s ORDER BY started_at DESC",
            (company_code,)
        )
    else:
        cursor.execute("SELECT * FROM crawl_sessions ORDER BY started_at DESC")
    result = cursor.fetchall()
    cursor.close()
    conn.close()
    return result


def get_faq_by_session(session_id):
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute(
        "SELECT * FROM faq_items WHERE session_id=%s ORDER BY id",
        (session_id,)
    )
    result = cursor.fetchall()
    cursor.close()
    conn.close()
    return result


def get_all_faq(company_code=None, search_keyword=None):
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    query = "SELECT f.*, s.started_at as session_started FROM faq_items f LEFT JOIN crawl_sessions s ON f.session_id=s.session_id WHERE 1=1"
    params = []
    if company_code:
        query += " AND f.company_code=%s"
        params.append(company_code)
    if search_keyword:
        query += " AND (f.question LIKE %s OR f.answer LIKE %s OR f.category LIKE %s)"
        kw = f"%{search_keyword}%"
        params.extend([kw, kw, kw])
    query += " ORDER BY f.crawled_at DESC"
    cursor.execute(query, params)
    result = cursor.fetchall()
    cursor.close()
    conn.close()
    return result


def get_faq_stats(company_code=None):
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    if company_code:
        cursor.execute(
            "SELECT COUNT(*) as total, MAX(crawled_at) as last_crawled FROM faq_items WHERE company_code=%s",
            (company_code,)
        )
    else:
        cursor.execute("SELECT COUNT(*) as total, MAX(crawled_at) as last_crawled FROM faq_items")
    result = cursor.fetchone()
    cursor.close()
    conn.close()
    return result
