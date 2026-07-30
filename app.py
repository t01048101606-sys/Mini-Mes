import streamlit as st

from src import queries
from src.ui import (
    metric_row,
    setup_page,
    show_database_status,
    show_dataframe,
)

setup_page("홈 / 로그인")

if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
if "user_id" not in st.session_state:
    st.session_state.user_id = ""

show_database_status()

if not st.session_state.logged_in:
    st.title("MES SYSTEM LOGIN",text_alignment="center")

    col_left, col_center, col_right = st.columns([1, 2, 1])

    with col_center:
        st.write("")
        with st.form("login_form"):
            st.subheader(" 사용자 인증")
            user_id = st.text_input("아이디", value="admin", placeholder="아이디 입력")
            password = st.text_input(
                "비밀번호", type="password", value="1234", placeholder="비밀번호 입력"
            )
            login_button = st.form_submit_button("로그인", use_container_width=True)

        if login_button:
            if user_id == "admin" and password == "1234":
                st.session_state.logged_in = True
                st.session_state.user_id = user_id
                st.success("로그인되었습니다!")
                st.rerun()
            else:
                st.error("아이디 또는 비밀번호가 올바르지 않습니다.")

else:
    
    col_user, col_logout = st.columns([4, 1])
    with col_user:
        st.title(f" {st.session_state.user_id} 님, 환영합니다!")
        st.caption("MES에 정상 접속 중입니다.")
    with col_logout:
        st.write("")
        if st.button(" 로그아웃", use_container_width=True):
            st.session_state.logged_in = False
            st.session_state.user_id = ""
            st.rerun()

    st.divider()

    
    st.subheader(" 시스템 현황 요약")
    counts = queries.table_counts()
    if not counts.empty:
        count_map = dict(zip(counts["table_name"], counts["row_count"]))
        metric_row(
            [
                ("등록 품목 수", f"{count_map.get('item', 0):,} 개"),
                ("보유 LOT 수", f"{count_map.get('lot', 0):,} 개"),
                ("생산실적 수", f"{count_map.get('production', 0):,} 건"),
                ("원자재 투입 건수", f"{count_map.get('production_material', 0):,} 건"),
            ]
        )

    st.write("")

    
    st.subheader(" 주요 기능 메뉴")
    m_col1, m_col2, m_col3, m_col4, m_col5, m_col6, m_col7 = st.columns(7)

    with m_col1:
        st.info(" **품목 조회**\n\n품목 기준정보가 제품과 원자재를 함께 관리하는 방식.")
    with m_col2:
            st.info(" **LOT 조회**\n\n품목과 LOT의 차이, 원자재 LOT와 완제품 LOT의 차이를 확인.")
    with m_col3:
        st.success(" **생산 실적 조회**\n\n생산 이벤트와 생산 결과 완제품 LOT가 어떻게 연결되는지 확인.")
    with m_col4:
        st.warning(" **생산 등록**\n\n완제품 LOT, 생산실적, 원자재 투입 이력을 하나의 트랜잭션으로 저장.")
    with m_col5:
            st.warning(" **정방향 LOT 추적**\n\n 특정 원자재 LOT가 어떤 완제품 LOT 생산에 사용되었는지 추적.")
    with m_col6:
            st.warning(" **역방향 LOT 추적**\n\n완제품 LOT에서 시작해 생산에 사용된 원자재 LOT를 찾기.")
    with m_col7:
            st.warning(" **생산현황 DASHBOARD**\n\n계산 가능한 범위의 생산 수량, LOT 수, 사용 횟수를 집계.")

    st.write("")

    
    st.subheader(" 최근 등록된 생산실적")
    recent_prods = queries.productions().head(5)
    show_dataframe(recent_prods, "등록된 생산실적이 없습니다.")





