from datetime import date, timedelta

import streamlit as st

from src import queries
from src.services import ReceiptRegistration, register_receipt
from src.ui import require_role, setup_page, show_dataframe


setup_page("원자재 입고 등록")
require_role("ADMIN", "OPERATOR")
st.title("🛡️⚙️원자재 입고 등록")
st.markdown("---")

if "last_receipt_result" in st.session_state:
    st.success("원자재 입고가 정상적으로 등록되었습니다.")
    st.write(st.session_state.pop("last_receipt_result"))
    st.markdown("---")

materials = queries.active_items_for_select("MATERIAL")
if not materials:
    st.warning("등록된 원자재 품목이 없습니다. 품목을 먼저 등록하세요.")
    st.stop()

material_options = {
    f"{item['item_code']} | {item['item_name']} ({item['unit']})": item
    for item in materials
}

next_lot_id = queries.next_id("lot", "lot_id")

with st.form("receipt_form"):
    material_label = st.selectbox("입고 원자재 품목", list(material_options.keys()))
    material = material_options[material_label]

    lot_no = st.text_input(
        "입고 LOT 번호",
        value=f"RM-{date.today().strftime('%Y%m%d')}-{next_lot_id:04d}",
    )
    received_date = st.date_input("입고일자", value=date.today())
    qty = st.number_input(f"입고수량 ({material['unit']})", min_value=0.0, value=100.0, step=10.0)
    use_expire = st.checkbox("유효기한 있음")
    expire_date = None
    if use_expire:
        expire_date = st.date_input("유효기한", value=date.today() + timedelta(days=365))

    submitted = st.form_submit_button("입고 등록", type="primary")

if submitted:
    data = ReceiptRegistration(
        material_item_id=material["item_id"],
        lot_no=lot_no,
        received_date=received_date,
        qty=qty,
        expire_date=expire_date,
    )
    try:
        result = register_receipt(data)
        st.session_state["last_receipt_result"] = result
        st.rerun()
    except ValueError as exc:
        st.error(str(exc))

st.markdown("---")

st.subheader("최근 입고 LOT")
recent_receipts = queries.lots(lot_type="RECEIPT")
if not recent_receipts.empty:
    show_dataframe(
        recent_receipts.sort_values("received_date", ascending=False).head(10)
    )