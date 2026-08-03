import html

import plotly.express as px
import streamlit as st

from src import queries
from src.services import authenticate_user
from src.ui import (
    alert_badge,
    kpi_row,
    metric_row,
    setup_page,
    show_database_status,
    show_dataframe,
)


st.title("라면공장 MES SYSTEM LOGIN", text_alignment="center")

setup_page("홈 / 로그인")

if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
if "user_id" not in st.session_state:
    st.session_state.user_id = ""
if "user_name" not in st.session_state:
    st.session_state.user_name = ""
if "user_role" not in st.session_state:
    st.session_state.user_role = ""

if not st.session_state.logged_in:
    col_left, col_center, col_right = st.columns([1, 2, 1])

    with col_center:
        try:
            st.image("assets/ramen_banner.jpg", use_container_width=True)
        except Exception:
            pass 
   
    with col_center:
        st.write("")
        with st.form("login_form"):
            st.subheader(" 사용자 인증")
            user_id_input = st.text_input("아이디", placeholder="아이디 입력")
            password_input = st.text_input(
                "비밀번호", type="password", placeholder="비밀번호 입력"
            )
            login_button = st.form_submit_button("로그인", use_container_width=True)

        if login_button:
            user = authenticate_user(user_id_input, password_input)
            if user is not None:
                st.session_state.logged_in = True
                st.session_state.user_id = user["user_id"]
                st.session_state.user_name = user["user_name"]
                st.session_state.user_role = user["role"]
                st.success("로그인되었습니다!")
                st.rerun()
            else:
                st.error("아이디 또는 비밀번호가 올바르지 않거나, 비활성화된 계정입니다.")

else:

    role_theme = {
        "ADMIN": ("#D8481E", "🛡️"),
        "OPERATOR": ("#2B5F8A", "⚙️"),
        "INSPECTOR": ("#2E8B57", "🔍"),
    }
    banner_color, banner_icon = role_theme.get(st.session_state.user_role, ("#6A4C93", "👤"))

    col_user, col_logout = st.columns([4, 1])
    with col_user:
        st.markdown(
            f"""
            <div style="background: linear-gradient(90deg, {banner_color}, {banner_color}CC);
                        border-radius: 12px; padding: 16px 20px; color: white; margin-bottom: 8px;">
                <div style="font-size: 22px; font-weight: 700;">
                    {banner_icon} {html.escape(st.session_state.user_name)} 님, 환영합니다!
                </div>
                <div style="font-size: 13px; opacity: 0.9;">
                    라면공장 MES에 {html.escape(st.session_state.user_role)} 권한으로 접속 중입니다.
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )
    with col_logout:
        st.write("")
        if st.button(" 로그아웃", use_container_width=True):
            st.session_state.logged_in = False
            st.session_state.user_id = ""
            st.session_state.user_name = ""
            st.session_state.user_role = ""
            st.rerun()

    st.divider()
    show_database_status()

    st.subheader(" 주요 기능 메뉴")

    ALL_ROLES = ("ADMIN", "OPERATOR", "INSPECTOR")
    menu_items = [
        ("품목 관리", "조회 / 신규 등록 / 수정·단종", "pages/01_품목관리.py", ALL_ROLES),
        ("BOM 관리", "제품별 표준 배합 등록", "pages/02_BOM 관리.py", ("ADMIN", "OPERATOR")),
        ("원자재 입고 등록", "원자재 RECEIPT LOT 등록", "pages/03_원자재입고.py", ("ADMIN", "OPERATOR")),
        ("LOT 조회", "입고·생산 LOT 조회", "pages/04_LOT조회.py", ALL_ROLES),
        ("생산계획", "계획 등록 및 BOM 기반 부족 확인", "pages/05_생산계획.py", ("ADMIN", "OPERATOR")),
        ("생산 등록", "BOM 기반 자동 소요량 계산", "pages/06_생산등록.py", ("ADMIN", "OPERATOR")),
        ("생산실적 조회", "생산 이벤트 및 원자재 투입 이력", "pages/07_생산실적조회.py", ALL_ROLES),
        ("불량검사", "입고·출하 검사 등록 및 통계", "pages/08_불량검사.py", ("ADMIN", "INSPECTOR")),
        ("출하 관리", "완제품 LOT 출하 등록 / 이력 조회", "pages/09_출하관리.py", ("ADMIN", "OPERATOR")),
        ("LOT 추적", "정방향 / 역방향 추적", "pages/10_LOT추적.py", ALL_ROLES),
        ("재고 현황", "잔량 / 유효기한 임박 / 부족 확인", "pages/11_재고현황.py", ALL_ROLES),
        ("사용자 관리", "계정 등록 / 권한 관리 (ADMIN 전용)", "pages/12_사용자관리.py", ("ADMIN",)),
    ]

    current_role = st.session_state.get("user_role")
    visible_menu_items = [
        (title, desc, path) for title, desc, path, roles in menu_items if current_role in roles
    ]

    menu_cols = st.columns(3)
    for idx, (title, desc, path) in enumerate(visible_menu_items):
        with menu_cols[idx % 3]:
            with st.container(border=True):
                st.markdown(f"**{title}**")
                st.caption(desc)
                st.page_link(path, label="이동", icon="➡️")

    st.markdown("---")

    st.subheader(" 시스템 현황 요약")
    counts = queries.table_counts()
    if not counts.empty:
        count_map = dict(zip(counts["table_name"], counts["row_count"]))

        kpis = [
            ("등록 품목 수", f"{count_map.get('item', 0):,} 개", "kpi-red"),
            ("보유 LOT 수", f"{count_map.get('lot', 0):,} 개", "kpi-blue"),
            ("생산실적 수", f"{count_map.get('production', 0):,} 건", "kpi-green"),
            ("원자재 투입 건수", f"{count_map.get('production_material', 0):,} 건", "kpi-purple"),
            ("BOM 등록 건수", f"{count_map.get('bom', 0):,} 건", "kpi-gold"),
            ("검사 이력 수", f"{count_map.get('inspection', 0):,} 건", "kpi-teal"),
        ]
        kpi_row(kpis, columns=3)

    st.write("")

    by_date = queries.production_by_date()
    by_item = queries.production_by_item()
    lot_use = queries.lot_use_counts()
    recent = queries.productions().sort_values("production_date", ascending=False).head(5)
    stock_df = queries.material_stock_summary()
    expiring_df = queries.expiring_material_lots(days=30)
    activity_df = queries.recent_activity(limit=8)

    st.markdown("---")

    st.subheader("재고 알림")
    alert_col1, alert_col2 = st.columns(2)
    with alert_col1:
        low_stock_count = int((stock_df["remaining_qty"] <= 0).sum()) if not stock_df.empty else 0
        if low_stock_count > 0:
            alert_badge(f"잔량 소진된 원자재 {low_stock_count}건 — 재고 현황 페이지에서 확인하세요.", "danger")
        else:
            alert_badge("잔량 소진된 원자재가 없습니다.", "ok")
    with alert_col2:
        if not expiring_df.empty:
            alert_badge(f"30일 이내 유효기한 임박 LOT {len(expiring_df)}건", "warning")
        else:
            alert_badge("30일 이내 유효기한 임박 LOT가 없습니다.", "ok")

    st.markdown("---")

    st.subheader("일자별 생산량")
    show_dataframe(by_date)
    if not by_date.empty:
        fig_date = px.bar(
            by_date,
            x="production_date",
            y="production_qty",
            color="production_qty",
            color_continuous_scale=["#FCE4DA", "#D8481E"],
            labels={"production_date": "생산일자", "production_qty": "생산수량"},
        )
        fig_date.update_layout(
            showlegend=False,
            coloraxis_showscale=False,
            margin=dict(l=10, r=10, t=10, b=10),
            plot_bgcolor="rgba(0,0,0,0)",
            paper_bgcolor="rgba(0,0,0,0)",
        )
        st.plotly_chart(fig_date, use_container_width=True)

    st.markdown("---")

    st.subheader("품목별 생산량")
    show_dataframe(by_item)
    if not by_item.empty:
        fig_item = px.bar(
            by_item.sort_values("production_qty", ascending=True),
            x="production_qty",
            y="item_name",
            orientation="h",
            color="production_qty",
            color_continuous_scale=["#DCEAF5", "#2B5F8A"],
            labels={"item_name": "품목", "production_qty": "생산수량"},
        )
        fig_item.update_layout(
            showlegend=False,
            coloraxis_showscale=False,
            margin=dict(l=10, r=10, t=10, b=10),
            plot_bgcolor="rgba(0,0,0,0)",
            paper_bgcolor="rgba(0,0,0,0)",
        )
        st.plotly_chart(fig_item, use_container_width=True)

    st.markdown("---")

    st.subheader("최근 활동")
    if activity_df.empty:
        st.info("최근 활동 이력이 없습니다.")
    else:
        tag_map = {
            "PRODUCTION": ("tag-production", "dot-production", "생산"),
            "RECEIPT": ("tag-receipt", "dot-receipt", "입고"),
            "SHIPMENT": ("tag-shipment", "dot-shipment", "출하"),
        }
        rows_html = []
        for _, row in activity_df.iterrows():
            tag_class, dot_class, tag_label = tag_map.get(
                row["event_type"], ("tag-production", "dot-production", row["event_type"])
            )
            qty_text = f"{row['qty']:,.0f}" if row["qty"] is not None else "-"
            rows_html.append(
                f"""
                <div class="timeline-item">
                    <div class="timeline-dot {dot_class}"></div>
                    <div style="flex:1;">
                        <span class="timeline-tag {tag_class}">{tag_label}</span>
                        <b>{html.escape(str(row['ref_no']))}</b>
                        &nbsp;|&nbsp; {html.escape(str(row['item_name']))}
                        &nbsp;|&nbsp; 수량 {qty_text}
                        &nbsp;|&nbsp; <span style="color:#888;">{html.escape(str(row['event_date']))}</span>
                    </div>
                </div>
                """
            )
        st.markdown("".join(rows_html), unsafe_allow_html=True)

    st.markdown("---")

    st.subheader("최근 생산실적")
    show_dataframe(recent)

    st.markdown("---")

    st.subheader("LOT별 원자재 사용 횟수")
    show_dataframe(lot_use)
