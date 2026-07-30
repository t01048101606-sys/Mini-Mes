import streamlit as st

from src import queries
from src.ui import metric_row, page_title, setup_page, show_dataframe


setup_page("생산현황")
st.title("생산현황")



counts = queries.table_counts()
count_map = dict(zip(counts["table_name"], counts["row_count"]))
metric_row(
    [
        ("등록 품목 수", f"{count_map.get('item', 0):,} 개"),
        ("발행 LOT 수", f"{count_map.get('lot', 0):,} 개"),
        ("총 생산실적 건수", f"{count_map.get('production', 0):,} 건"),
        ("원자재 투입 이력", f"{count_map.get('production_material', 0):,} 건"),
    ]
)


by_date = queries.production_by_date()
by_item = queries.production_by_item()
lot_use = queries.lot_use_counts()

all_productions = queries.productions()
recent = (
    all_productions.sort_values("production_date", ascending=False).head(5)
    if not all_productions.empty and "production_date" in all_productions.columns
    else all_productions.head(5)
)


col1, col2 = st.columns(2)

with col1:
    st.subheader(" 일자별 생산량")
    if not by_date.empty:
        st.bar_chart(by_date, x="production_date", y="production_qty")
    show_dataframe(by_date)

with col2:
    st.subheader(" 품목별 생산량")
    if not by_item.empty:
        st.bar_chart(by_item, x="item_name", y="production_qty")
    show_dataframe(by_item)

st.divider()


col_recent, col_lot = st.columns(2)

with col_recent:
    st.subheader(" 최근 생산실적 ")
    show_dataframe(recent, "최근 생산실적 데이터가 없습니다.")

with col_lot:
    st.subheader(" LOT별 원자재 사용 횟수")
    show_dataframe(lot_use, "LOT 사용 횟수 데이터가 없습니다.")

