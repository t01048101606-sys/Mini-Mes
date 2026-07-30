import streamlit as st

from src import queries
from src.ui import metric_row, page_title, setup_page, show_dataframe


setup_page("역방향 추적")
st.title("역방향 추적")




output_lots = queries.lots_for_select("PRODUCTION")
if not output_lots:
    st.warning("조회 가능한 완제품 LOT가 없습니다.")
    st.stop()

options = {
    f"{lot['lot_no']} | {lot['item_name']} | 수량 {lot['qty']:,.0f}": lot
    for lot in output_lots
}
selected_label = st.selectbox("완제품 LOT 선택", list(options.keys()))
selected_lot = options[selected_label]


df = queries.reverse_trace(selected_lot["lot_id"])


if not df.empty:
    mat_lots = df["material_lot_no"].dropna().unique()
    mat_items = df["material_name"].dropna().unique() if "material_name" in df.columns else []
    prod_nos = df["production_no"].dropna().unique()

    metric_row(
        [
            ("투입 원자재 LOT 수", f"{len(mat_lots)} 개"),
            ("투입 원자재 품목 수", f"{len(mat_items)} 종"),
            ("연관 생산번호", f"{', '.join(prod_nos)}"),
        ]
    )

st.subheader("추적 결과")
show_dataframe(df, "이 완제품 LOT와 연결된 원자재 투입 이력이 없습니다.")


if not df.empty:
    st.divider()
    st.subheader(" 추적 경로 ")

    mat_lot_str = ", ".join(mat_lots[:5]) + (f" 외 {len(mat_lots)-5}건" if len(mat_lots) > 5 else "")
    prod_no_str = ", ".join(prod_nos)

    st.markdown(
        f"""
        * 완제품 LOT: `{selected_lot['lot_no']}` ({selected_lot['item_name']})
        * ↓
        * 연관 생산실적: `{prod_no_str}`
        * ↓
        * 투입 이력 `production_material`
        * ↓
        * 사용된 원자재 LOT: `{mat_lot_str}`
        """
    )

st.caption(
    "역방향 추적은 완제품에 품질 문제가 발생했을 때 어떤 원자재 LOT가 투입되었는지 소급 추적(Root Cause Analysis)하는 데 활용."
)
