import streamlit as st

from src import queries
from src.ui import require_role, setup_page, show_dataframe


setup_page("LOT 추적")
require_role("ADMIN", "OPERATOR", "INSPECTOR")
st.title("🛡️⚙️🔍정방향 추적")
st.markdown("---")


material_lots = queries.lots_for_select("RECEIPT")
if not material_lots:
    st.warning("원자재 LOT가 없습니다.")
    st.stop()

options = {
    f"{lot['lot_no']} | {lot['item_name']} | 수량 {lot['qty']:,.0f}": lot["lot_id"]
    for lot in material_lots
}
selected_label = st.selectbox("원자재 LOT", list(options.keys()))

df = queries.forward_trace(options[selected_label])

st.subheader("추적 결과")
show_dataframe(df, "이 원자재 LOT를 사용한 생산실적이 없습니다.")

if not df.empty:
    first = df.iloc[0]
    st.subheader("추적 경로")
    st.markdown(
        f"""
        `{first['material_lot_no']}`
        -> `production_material`
        -> 생산실적 {', '.join(df['production_no'].tolist())}
        -> 완제품 LOT {', '.join(df['output_lot_no'].tolist())}
        """
    )


st.markdown("---")


st.title("🛡️⚙️🔍역방향 추적")

st.markdown("---")


output_lots = queries.lots_for_select("PRODUCTION")
if not output_lots:
    st.warning("완제품 LOT가 없습니다.")
    st.stop()

options = {
    f"{lot['lot_no']} | {lot['item_name']} | 수량 {lot['qty']:,.0f}": lot["lot_id"]
    for lot in output_lots
}
selected_label = st.selectbox("완제품 LOT", list(options.keys()))

df = queries.reverse_trace(options[selected_label])

st.subheader("추적 결과")
show_dataframe(df, "이 완제품 LOT와 연결된 원자재 투입 이력이 없습니다.")

if not df.empty:
    first = df.iloc[0]
    st.subheader("추적 경로")
    st.markdown(
        f"""
        `{first['output_lot_no']}`
        -> 생산실적 `{first['production_no']}`
        -> `production_material`
        -> 원자재 LOT {', '.join(df['material_lot_no'].tolist())}
        """
    )


st.markdown("---")

st.caption(
    "역방향 추적은 완제품 품질 문제가 발생했을 때 생산에 사용된 원자재 LOT를 확인하는 데 사용한다."
)

st.caption(
    "정방향 추적은 원자재 문제가 발생했을 때 해당 원자재를 사용한 완제품 LOT를 찾는 데 사용한다."
)