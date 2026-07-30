import streamlit as st

from src import queries
from src.ui import metric_row, page_title, setup_page, show_dataframe


setup_page("정방향 추적")
st.title("정방향 추적")




material_lots = queries.lots_for_select("RECEIPT")
if not material_lots:
    st.warning("조회 가능한 원자재 LOT가 없습니다.")
    st.stop()

options = {
    f"{lot['lot_no']} | {lot['item_name']} | 보유 {lot['qty']:,.0f}": lot
    for lot in material_lots
}
selected_label = st.selectbox("원자재 LOT 선택", list(options.keys()))
selected_lot = options[selected_label]


df = queries.forward_trace(selected_lot["lot_id"])


if not df.empty:
    output_lots = df["output_lot_no"].dropna().unique()
    prod_nos = df["production_no"].dropna().unique()

    metric_row(
        [
            ("영향받은 완제품 LOT", f"{len(output_lots)} 개"),
            ("연관 생산실적", f"{len(prod_nos)} 건"),
            ("총 사용 투입량", f"{df['used_qty'].sum():,.0f}" if "used_qty" in df.columns else "-"),
        ]
    )

st.subheader("추적 결과")
show_dataframe(df, "이 원자재 LOT를 사용한 생산실적이 없습니다.")


if not df.empty:
    st.divider()
    st.subheader(" 추적 경로")

    
    output_lot_str = ", ".join(output_lots[:5]) + (f" 외 {len(output_lots)-5}건" if len(output_lots) > 5 else "")
    prod_no_str = ", ".join(prod_nos[:5]) + (f" 외 {len(prod_nos)-5}건" if len(prod_nos) > 5 else "")

    st.markdown(
        f"""
        * 원자재 LOT: `{selected_lot['lot_no']}` {selected_lot['item_name']}
        * ↓
        * 투입 이력 `production_material`
        * ↓
        * 생산실적: `{prod_no_str}`
        * ↓
        * 완제품 LOT: `{output_lot_str}`
        """
    )

st.caption(
    "정방향 추적은 원자재 품질 문제가 발생했을 때 해당 원자재가 투입된 완제품 LOT를 추적/회수(Recall)하는 데 활용."
)
