"""
전국 자동차 등록 현황 페이지
"""
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from pathlib import Path
import sys, os

sys.path.insert(0, str(Path(__file__).parent.parent))
from utils.car_data import (
    load_all_files, get_summary_by_region, get_detail_by_region,
    get_vehicle_cols, VEHICLE_TYPES, USE_TYPES
)


DATA_DIR = Path(__file__).parent.parent / "data"

COLORS = {
    "승용": "#4C9BE8",
    "승합": "#F4A261",
    "화물": "#2A9D8F",
    "특수": "#E76F51",
    "총계": "#264653",
}


def render():
    st.header("🚗 전국 자동차 등록 현황")

    # 파일 목록 로드
    all_data = load_all_files()

    if not all_data:
        st.warning("data/ 디렉토리에 xlsx 파일이 없습니다.")
        _show_upload_guide()
        return

    # 에러난 파일 분리
    valid = [d for d in all_data if "error" not in d]
    errors = [d for d in all_data if "error" in d]

    if errors:
        with st.expander(f"⚠️ 파싱 오류 파일 ({len(errors)}개)"):
            for e in errors:
                st.error(f"`{e['filename']}`: {e['error']}")

    if not valid:
        st.error("파싱 가능한 파일이 없습니다.")
        return

    # 파일 선택 (여러 파일 지원)
    file_options = {d["filename"]: d for d in valid}
    col1, col2 = st.columns([2, 1])
    with col1:
        selected_file = st.selectbox(
            "📁 데이터 파일 선택",
            list(file_options.keys()),
            help="data/ 폴더에 파일을 추가하면 자동으로 목록에 나타납니다."
        )
    with col2:
        st.metric("조회 기간", file_options[selected_file]["period"])

    data = file_options[selected_file]
    df = data["df"]
    col_names = data["col_names"]

    # 탭 구성
    tab1, tab2, tab3, tab4 = st.tabs(["📊 시도별 현황", "🔍 지역 상세", "📈 차종별 분석", "📋 원본 데이터"])

    with tab1:
        _render_region_summary(df, col_names)

    with tab2:
        _render_region_detail(df, col_names, data["regions"])

    with tab3:
        _render_vehicle_analysis(df, col_names)

    with tab4:
        _render_raw_data(df)

    # 파일 추가 가이드
    with st.expander("📁 새 데이터 파일 추가 방법"):
        _show_upload_guide()


def _render_region_summary(df, col_names):
    st.subheader("시도별 등록 현황 요약")

    summary = get_summary_by_region(df)

    # 필터 옵션
    c1, c2 = st.columns(2)
    with c1:
        vehicle_type = st.selectbox("차종", ["전체"] + VEHICLE_TYPES, key="v_type_summary")
    with c2:
        use_type = st.selectbox("용도", ["전체"] + USE_TYPES, key="u_type_summary")

    # 표시할 컬럼 결정
    if vehicle_type == "전체" and use_type == "전체":
        display_col = "총계_계"
    elif vehicle_type == "전체":
        display_col = f"총계_{use_type}" if f"총계_{use_type}" in col_names else "총계_계"
    elif use_type == "전체":
        display_col = f"{vehicle_type}_계" if f"{vehicle_type}_계" in col_names else col_names[0]
    else:
        display_col = f"{vehicle_type}_{use_type}"

    if display_col not in summary.columns:
        available = [c for c in col_names if c in summary.columns]
        display_col = available[0] if available else col_names[0]

    plot_df = summary[["시도명", display_col]].dropna().copy()
    plot_df = plot_df[plot_df["시도명"].notna()]
    plot_df = plot_df.sort_values(display_col, ascending=False)

    # KPI 카드
    total = plot_df[display_col].sum()
    max_region = plot_df.iloc[0]["시도명"] if not plot_df.empty else "-"
    max_val = plot_df.iloc[0][display_col] if not plot_df.empty else 0

    k1, k2, k3 = st.columns(3)
    k1.metric("전국 합계", f"{int(total):,} 대")
    k2.metric("최다 지역", max_region)
    k3.metric("최다 지역 등록수", f"{int(max_val):,} 대")

    # 막대 차트
    label = display_col.replace("_", " ")
    fig = px.bar(
        plot_df, x="시도명", y=display_col,
        title=f"시도별 자동차 등록 현황 ({label})",
        color=display_col,
        color_continuous_scale="Blues",
        text=display_col,
    )
    fig.update_traces(texttemplate='%{text:,.0f}', textposition='outside')
    fig.update_layout(height=450, showlegend=False, coloraxis_showscale=False)
    st.plotly_chart(fig, use_container_width=True)

    # 파이 차트
    fig2 = px.pie(plot_df, names="시도명", values=display_col,
                  title="시도별 비율", hole=0.4)
    fig2.update_layout(height=400)
    st.plotly_chart(fig2, use_container_width=True)

    # 표
    st.dataframe(
        plot_df.rename(columns={display_col: f"{label} (대)"}),
        use_container_width=True,
        hide_index=True
    )


def _render_region_detail(df, col_names, regions):
    st.subheader("지역 상세 조회")

    region = st.selectbox("시도 선택", [r for r in regions if pd.notna(r)], key="region_detail")
    detail = get_detail_by_region(df, region)

    if detail.empty:
        st.info("데이터가 없습니다.")
        return

    vehicle_type = st.selectbox("차종", ["전체"] + VEHICLE_TYPES, key="v_type_detail")

    if vehicle_type == "전체":
        show_cols = [c for c in col_names if c.endswith("_계")]
    else:
        show_cols = [c for c in col_names if c.startswith(vehicle_type + "_")]

    available_cols = [c for c in show_cols if c in detail.columns]
    if not available_cols:
        available_cols = col_names[:4]

    display_df = detail[["시군구"] + available_cols].dropna(subset=["시군구"])
    display_df = display_df[display_df["시군구"].notna()].copy()

    for col in available_cols:
        display_df[col] = pd.to_numeric(display_df[col], errors="coerce")

    # 총계 행 분리
    total_row = display_df[display_df["시군구"] == "계"]
    detail_rows = display_df[display_df["시군구"] != "계"]

    if not detail_rows.empty and available_cols:
        primary_col = available_cols[-1]  # 마지막 = '계'
        fig = px.bar(
            detail_rows, x="시군구", y=primary_col,
            title=f"{region} 시군구별 등록 현황",
            color=primary_col, color_continuous_scale="Teal",
            text=primary_col,
        )
        fig.update_traces(texttemplate='%{text:,.0f}', textposition='outside')
        fig.update_layout(height=400, coloraxis_showscale=False)
        st.plotly_chart(fig, use_container_width=True)

    if not total_row.empty:
        st.info(f"**{region} 합계**: {int(total_row[available_cols[-1]].values[0]):,} 대" if available_cols else "")

    st.dataframe(display_df, use_container_width=True, hide_index=True)


def _render_vehicle_analysis(df, col_names):
    st.subheader("차종별 등록 비율 분석")

    summary = get_summary_by_region(df)
    # 전국 합계 행
    nationwide = summary[summary["시군구"] == "계"]

    type_cols = {vt: f"{vt}_계" for vt in VEHICLE_TYPES if f"{vt}_계" in col_names}

    if not type_cols:
        st.warning("차종별 합계 컬럼을 찾을 수 없습니다.")
        return

    # 전국 차종별 파이차트
    pie_data = []
    for vt, col in type_cols.items():
        if vt == "총계":
            continue
        val = pd.to_numeric(nationwide[col], errors="coerce").sum()
        if val > 0:
            pie_data.append({"차종": vt, "등록대수": val})

    if pie_data:
        pie_df = pd.DataFrame(pie_data)
        fig = px.pie(pie_df, names="차종", values="등록대수",
                     title="전국 차종별 등록 비율", hole=0.4,
                     color_discrete_map=COLORS)
        st.plotly_chart(fig, use_container_width=True)

    # 시도별 차종 스택바
    stack_rows = []
    for _, row in summary[summary["시군구"] == "계"].iterrows():
        for vt, col in type_cols.items():
            if vt == "총계":
                continue
            val = pd.to_numeric(row.get(col, 0), errors="coerce")
            stack_rows.append({"시도": row["시도명"], "차종": vt, "등록대수": val if pd.notna(val) else 0})

    if stack_rows:
        stack_df = pd.DataFrame(stack_rows)
        fig2 = px.bar(
            stack_df, x="시도", y="등록대수", color="차종",
            title="시도별 차종 구성",
            color_discrete_map=COLORS,
            barmode="stack",
        )
        fig2.update_layout(height=450)
        st.plotly_chart(fig2, use_container_width=True)


def _render_raw_data(df):
    st.subheader("원본 데이터")

    # 검색
    search = st.text_input("🔍 시도/시군구 검색", placeholder="예: 서울, 강남")
    filtered = df.copy()
    if search:
        mask = (
            filtered["시도명"].astype(str).str.contains(search, na=False) |
            filtered["시군구"].astype(str).str.contains(search, na=False)
        )
        filtered = filtered[mask]

    st.dataframe(filtered, use_container_width=True, height=400)
    st.caption(f"총 {len(filtered)}행")


def _show_upload_guide():
    st.info(
        "**새 파일 추가 방법**\n\n"
        "1. `data/` 폴더에 xlsx 파일을 복사하세요.\n"
        "2. 파일 형식: KOSIS 자동차등록대수현황 xlsx (시도별)\n"
        "3. 앱을 새로고침하면 자동으로 인식됩니다."
    )
