import streamlit as st

from src import queries
from src.ui import metric_row, require_role, setup_page, show_dataframe


setup_page("생산실적 조회")
require_role("ADMIN", "OPERATOR", "INSPECTOR")
st.title("🛡️⚙️🔍생산실적 조회")

st.markdown("---")

col1, col2, col3 = st.columns(3)
keyword = col1.text_input("생산번호, 품목명, 완제품 LOT 검색")
use_date_filter = col2.checkbox("생산일자 필터 사용")
date_from = None
date_to = None
if use_date_filter:
    date_from = col2.date_input("시작일")
    date_to = col3.date_input("종료일")

df = queries.productions(keyword=keyword, date_from=date_from, date_to=date_to)
if not df.empty:
    metric_row(
        [
            ("생산실적 수", len(df)),
            ("총 생산수량", f"{df['production_qty'].sum():,.0f}"),
            ("완제품 LOT 수", df["output_lot_no"].nunique()),
        ]
    )

st.subheader("생산 이벤트와 결과 LOT")
show_dataframe(df)

if not df.empty:
    selected_no = st.selectbox("원자재 투입 확인 생산번호", df["production_no"].tolist())
    production_id = int(df[df["production_no"] == selected_no].iloc[0]["production_id"])
    st.subheader("선택한 생산의 원자재 투입")
    show_dataframe(queries.production_materials(production_id))