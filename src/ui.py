from __future__ import annotations

import pandas as pd
import streamlit as st

from src.db import DB_PATH, database_exists


def setup_page(title: str):
    st.set_page_config(page_title=f"Mini MES - {title}", layout="wide")
    st.markdown(
        """
        <style>
        .kpi-card {
            border-radius: 14px;
            padding: 18px 20px;
            color: white;
            box-shadow: 0 4px 14px rgba(0,0,0,0.12);
            height: 100%;
        }
        .kpi-card .kpi-label {
            font-size: 13px;
            opacity: 0.88;
            margin-bottom: 4px;
        }
        .kpi-card .kpi-value {
            font-size: 26px;
            font-weight: 700;
            line-height: 1.2;
        }
        .kpi-red    { background: linear-gradient(135deg, #D8481E, #F2764A); }
        .kpi-blue   { background: linear-gradient(135deg, #2B5F8A, #4E8FC0); }
        .kpi-green  { background: linear-gradient(135deg, #2E8B57, #57C78A); }
        .kpi-purple { background: linear-gradient(135deg, #6A4C93, #9A7FC7); }
        .kpi-gold   { background: linear-gradient(135deg, #B8860B, #E0B84B); }
        .kpi-teal   { background: linear-gradient(135deg, #147C7C, #3FB6B6); }

        .alert-badge {
            border-radius: 10px;
            padding: 14px 16px;
            font-weight: 600;
            font-size: 14px;
            border-left: 5px solid;
        }
        .alert-danger  { background: #FDECEA; border-color: #D8481E; color: #7A2A10; }
        .alert-warning { background: #FFF6E0; border-color: #E0B84B; color: #7A5C10; }
        .alert-ok      { background: #E9F7EF; border-color: #2E8B57; color: #1D5C3A; }

        .timeline-item {
            display: flex;
            align-items: flex-start;
            gap: 10px;
            padding: 8px 0;
            border-bottom: 1px solid rgba(0,0,0,0.06);
        }
        .timeline-dot {
            min-width: 10px; min-height: 10px;
            border-radius: 50%;
            margin-top: 6px;
        }
        .dot-production { background: #2B5F8A; }
        .dot-receipt { background: #2E8B57; }
        .dot-shipment { background: #D8481E; }
        .timeline-tag {
            font-size: 11px;
            font-weight: 700;
            padding: 2px 8px;
            border-radius: 999px;
            color: white;
            white-space: nowrap;
        }
        .tag-production { background: #2B5F8A; }
        .tag-receipt { background: #2E8B57; }
        .tag-shipment { background: #D8481E; }

        .stock-row {
            display: flex;
            align-items: center;
            gap: 10px;
            padding: 6px 0;
        }
        .stock-bar-bg {
            flex: 1;
            background: #EEE;
            border-radius: 999px;
            height: 14px;
            overflow: hidden;
        }
        .stock-bar-fill {
            height: 100%;
            border-radius: 999px;
        }
        .stock-label {
            width: 160px;
            font-size: 13px;
            font-weight: 600;
        }
        .stock-value {
            width: 90px;
            font-size: 13px;
            text-align: right;
            color: #555;
        }

        .shortage-card {
            border-radius: 10px;
            padding: 12px 16px;
            margin-bottom: 8px;
            border-left: 5px solid;
        }
        .shortage-bad { background: #FDECEA; border-color: #D8481E; }
        .shortage-ok { background: #E9F7EF; border-color: #2E8B57; }
        </style>
        """,
        unsafe_allow_html=True,
    )


def kpi_row(items: list[tuple[str, str, str]], columns: int = 3):
    import html as _html

    cols = st.columns(columns)
    for idx, (label, value, css_class) in enumerate(items):
        with cols[idx % columns]:
            st.markdown(
                f"""
                <div class="kpi-card {css_class}">
                    <div class="kpi-label">{_html.escape(label)}</div>
                    <div class="kpi-value">{_html.escape(str(value))}</div>
                </div>
                """,
                unsafe_allow_html=True,
            )
            st.write("")


def alert_badge(message: str, level: str = "ok"):
    icon = {"danger": "🔴", "warning": "🟡", "ok": "🟢"}.get(level, "🟢")
    css_class = {"danger": "alert-danger", "warning": "alert-warning", "ok": "alert-ok"}.get(
        level, "alert-ok"
    )
    st.markdown(
        f"""<div class="alert-badge {css_class}">{icon} {message}</div>""",
        unsafe_allow_html=True,
    )


def require_login():
    if not st.session_state.get("logged_in", False):
        st.warning("로그인이 필요합니다. 홈 화면에서 먼저 로그인해주세요.")
        st.page_link("app.py", label="홈으로 이동")
        st.stop()


def require_role(*allowed_roles: str):
    if not st.session_state.get("logged_in", False):
        st.warning("로그인이 필요합니다. 홈 화면에서 먼저 로그인해주세요.")
        st.page_link("app.py", label="홈으로 이동")
        st.stop()
    if allowed_roles and st.session_state.get("user_role") not in allowed_roles:
        st.error("이 페이지에 접근할 권한이 없습니다.")
        st.caption(f"현재 계정 권한: {st.session_state.get('user_role', '알 수 없음')}")
        st.page_link("app.py", label="홈으로 이동")
        st.stop()


def show_database_status():
    if database_exists():
        st.success(f"데이터베이스 연결 대상: {DB_PATH}")
    else:
        st.error(f"데이터베이스 파일을 찾을 수 없습니다: {DB_PATH}")


def show_dataframe(df: pd.DataFrame, empty_message: str = "조건에 해당하는 데이터가 없습니다."):
    if df.empty:
        st.warning(empty_message)
        return
    st.dataframe(df, use_container_width=True, hide_index=True)


def metric_row(values: list[tuple[str, object]]):
    columns = st.columns(len(values))
    for column, (label, value) in zip(columns, values):
        column.metric(label, value)


def row_to_dict(row):
    if row is None:
        return {}
    return {key: row[key] for key in row.keys()}