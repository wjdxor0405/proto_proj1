"""
자동차 등록 현황 데이터 로더 모듈
- data/ 디렉토리에 xlsx 파일 추가 시 자동 인식
"""
import os
import glob
import pandas as pd
from pathlib import Path


DATA_DIR = Path(__file__).parent.parent / "data"

VEHICLE_TYPES = ["승용", "승합", "화물", "특수", "총계"]
USE_TYPES = ["관용", "자가용", "영업용", "계"]


def get_xlsx_files():
    """data 디렉토리의 모든 xlsx 파일 목록"""
    files = glob.glob(str(DATA_DIR / "*.xlsx"))
    return sorted(files)


def parse_car_excel(filepath):
    """
    자동차 등록 현황 xlsx 파싱
    반환: {
        'period': str,
        'filename': str,
        'df_raw': DataFrame,
        'df_parsed': DataFrame,
        'regions': list,
    }
    """
    df_raw = pd.read_excel(filepath, sheet_name='데이터', header=None)

    # 헤더 3행 파싱 (row0=기간, row1=차종, row2=용도)
    periods = df_raw.iloc[0, 2:].tolist()  # 예: ['2026.04', ...]
    vehicle_types_row = df_raw.iloc[1, 2:].tolist()
    use_types_row = df_raw.iloc[2, 2:].tolist()

    # 컬럼명 구성
    col_names = []
    for p, vt, ut in zip(periods, vehicle_types_row, use_types_row):
        vt = str(vt).strip() if pd.notna(vt) else ""
        ut = str(ut).strip() if pd.notna(ut) else ""
        col_names.append(f"{vt}_{ut}")

    # 데이터 행 (row3 이후)
    data_rows = df_raw.iloc[3:].copy()
    data_rows.columns = ["시도명", "시군구"] + col_names

    # 시도명 forward fill
    data_rows["시도명"] = data_rows["시도명"].ffill()
    data_rows = data_rows.reset_index(drop=True)

    # 숫자 컬럼 변환
    for col in col_names:
        data_rows[col] = pd.to_numeric(data_rows[col], errors='coerce')

    period = str(periods[0]) if periods else "Unknown"
    filename = Path(filepath).name

    # 광역시도 목록 (시군구 == '계' 또는 NaN 아닌 시도명)
    regions = data_rows["시도명"].unique().tolist()

    return {
        "period": period,
        "filename": filename,
        "filepath": filepath,
        "df": data_rows,
        "col_names": col_names,
        "regions": regions,
    }


def load_all_files():
    """모든 xlsx 파일 파싱하여 리스트 반환"""
    files = get_xlsx_files()
    results = []
    for fp in files:
        try:
            parsed = parse_car_excel(fp)
            results.append(parsed)
        except Exception as e:
            results.append({"filepath": fp, "filename": Path(fp).name, "error": str(e)})
    return results


def get_summary_by_region(df):
    """시도별 합계(시군구='계') 추출"""
    summary = df[df["시군구"] == "계"].copy()
    return summary


def get_detail_by_region(df, region):
    """특정 시도의 시군구별 데이터 추출"""
    return df[df["시도명"] == region].copy()


def get_vehicle_cols(col_names, vehicle_type=None):
    """차종별 컬럼 필터링"""
    if vehicle_type:
        return [c for c in col_names if c.startswith(vehicle_type + "_")]
    return col_names


def get_use_cols(col_names, use_type=None):
    """용도별 컬럼 필터링"""
    if use_type:
        return [c for c in col_names if c.endswith("_" + use_type)]
    return col_names
