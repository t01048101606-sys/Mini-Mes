from datetime import date

import streamlit as st

from src import queries
from src.services import ShipmentRegistration, register_shipment
from src.ui import metric_row, require_role, setup_page, show_dataframe


setup_page("출하 관리")
require_role("ADMIN", "OPERATOR")
st.title("출하 관리")
st.markdown("---")

tab_register, tab_history = st.tabs(["출하 등록", "출하 이력 조회"])

with tab_register:
    if "last_shipment_result" in st.session_state:
        st.success("출하가 정상적으로 등록되었습니다.")
        st.write(st.session_state.pop("last_shipment_result"))
        st.markdown("---")

    available_lots = queries.finished_goods_lots_with_balance()

    if not available_lots:
        st.info("출하 가능한 완제품 LOT가 없습니다.")
    else:
        next_shipment_id = queries.next_id("shipment", "shipment_id")

        col1, col2 = st.columns(2)
        shipment_no = col1.text_input(
            "출하번호",
            value=f"SHP-{date.today().strftime('%Y%m%d')}-{next_shipment_id:04d}",
        )
        shipment_date = col2.date_input("출하일자", value=date.today())
        customer_name = st.text_input("출하처 (선택)")

        st.subheader("출하할 완제품 LOT 선택")

        lot_labels = {}
        for lot in available_lots:
            badge = ""
            if lot["inspection_result"] == "FAIL":
                badge = "  불합격(출하불가)"
            elif lot["inspection_result"] is None:
                badge = "  검사이력없음"
            elif lot["inspection_result"] in ("PASS", "PARTIAL"):
                badge = f"  {lot['inspection_result']}"
            lot_labels[
                f"{lot['lot_no']} | {lot['item_name']} | 잔량 {lot['remaining_qty']:,.0f}{badge}"
            ] = lot

        selected_labels = st.multiselect("LOT 선택", list(lot_labels.keys()))

        shipment_rows = []
        for label in selected_labels:
            lot = lot_labels[label]
            if lot["inspection_result"] == "FAIL":
                st.error(f"{lot['lot_no']}는 불합격 판정된 LOT라 출하할 수 없습니다. 선택에서 제외하세요.")
                continue
            qty = st.number_input(
                f"{lot['lot_no']} 출하수량",
                min_value=0.0,
                value=float(lot["remaining_qty"]),
                step=1.0,
                key=f"shipment_qty_{lot['lot_id']}",
            )
            shipment_rows.append({"lot_id": lot["lot_id"], "qty": qty})

        if st.button("출하 등록", type="primary"):
            data = ShipmentRegistration(
                shipment_no=shipment_no,
                customer_name=customer_name or None,
                shipment_date=shipment_date,
                shipment_rows=shipment_rows,
            )
            try:
                result = register_shipment(data)
                st.session_state["last_shipment_result"] = result
                st.rerun()
            except ValueError as exc:
                st.error(str(exc))

with tab_history:
    col1, col2, col3 = st.columns(3)
    keyword = col1.text_input("출하번호 또는 출하처 검색")
    use_date_filter = col2.checkbox("출하일자 필터 사용")
    date_from = None
    date_to = None
    if use_date_filter:
        date_from = col2.date_input("시작일", key="hist_date_from")
        date_to = col3.date_input("종료일", key="hist_date_to")

    history_df = queries.shipments(keyword=keyword, date_from=date_from, date_to=date_to)

    if not history_df.empty:
        metric_row(
            [
                ("출하 건수", len(history_df)),
                ("총 출하수량", f"{history_df['total_qty'].sum():,.0f}"),
            ]
        )

    show_dataframe(history_df, "조건에 해당하는 출하 이력이 없습니다.")

    if not history_df.empty:
        selected_no = st.selectbox("상세 확인 출하번호", history_df["shipment_no"].tolist())
        shipment_id = int(
            history_df[history_df["shipment_no"] == selected_no].iloc[0]["shipment_id"]
        )
        st.subheader("출하 상세 내역")
        show_dataframe(queries.shipment_items(shipment_id))

st.markdown("---")
st.caption("불합격(FAIL) 판정된 완제품 LOT는 출하 등록 시 자동으로 차단됩니다.")
