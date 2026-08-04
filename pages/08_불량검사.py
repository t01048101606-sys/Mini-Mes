from datetime import date

import streamlit as st

from src import queries
from src.services import (
    DefectReasonCodeRegistration,
    InspectionRegistration,
    register_defect_reason_code,
    register_inspection,
    set_defect_reason_code_active,
)
from src.ui import metric_row, require_role, setup_page, show_dataframe


setup_page("불량검사")
require_role("ADMIN", "INSPECTOR")
st.title("🛡️🔍불량검사")
st.markdown("---")

tab_register, tab_history, tab_stats, tab_reason = st.tabs(
    ["검사 등록", "검사 이력 조회", "품목별 불량률", "불량 사유 코드 관리"]
)

with tab_register:
    lot_type_label = st.radio(
        "검사 대상", ["입고검사 (원자재 LOT)", "출하검사 (완제품 LOT)"], horizontal=True
    )
    lot_type = "RECEIPT" if lot_type_label.startswith("입고") else "PRODUCTION"

    uninspected = queries.uninspected_lots(lot_type)

    if not uninspected:
        st.info("검사 대상 LOT가 없습니다. (모든 LOT가 이미 검사 완료되었거나 LOT가 없습니다.)")
    else:
        lot_options = {
            f"{lot['lot_no']} | {lot['item_name']} | 수량 {lot['qty']:,.0f}": lot
            for lot in uninspected
        }

        reason_codes = queries.active_defect_reason_codes()
        reason_code_options = {"(선택 안 함)": None}
        for r in reason_codes:
            reason_code_options[f"{r['reason_code']} | {r['reason_name']}"] = r["reason_code"]

        with st.form("inspection_form"):
            selected_label = st.selectbox("검사 대상 LOT", list(lot_options.keys()))
            selected_lot = lot_options[selected_label]

            inspection_date_input = st.date_input("검사일자", value=date.today())
            checked_qty = st.number_input(
                "검사수량", min_value=0.0, value=float(selected_lot["qty"]), step=1.0
            )
            result = st.selectbox("검사 결과", ["PASS", "PARTIAL", "FAIL"])
            defect_qty = st.number_input("불량수량", min_value=0.0, value=0.0, step=1.0)

            reason_label = st.selectbox("불량 사유 코드", list(reason_code_options.keys()))
            defect_reason = st.text_input("불량 사유 상세 메모 (선택)")

            submitted = st.form_submit_button("검사결과 저장")

        if submitted:
            data = InspectionRegistration(
                lot_id=selected_lot["lot_id"],
                inspection_type=lot_type,
                inspection_date=inspection_date_input,
                checked_qty=checked_qty,
                defect_qty=defect_qty,
                result=result,
                reason_code=reason_code_options[reason_label],
                defect_reason=defect_reason or None,
            )
            try:
                result_data = register_inspection(data)
                st.success("검사결과가 정상적으로 등록되었습니다.")
                st.write(result_data)
            except ValueError as exc:
                st.error(str(exc))

with tab_history:
    col1, col2, col3 = st.columns(3)
    keyword = col1.text_input("LOT 번호 또는 품목명 검색")
    result_filter = col2.selectbox("검사 결과", ["전체", "PASS", "PARTIAL", "FAIL"])
    type_filter = col3.selectbox("검사 유형", ["전체", "RECEIPT", "PRODUCTION"])

    history_df = queries.inspections(
        keyword=keyword, result_filter=result_filter, inspection_type=type_filter
    )

    if not history_df.empty:
        metric_row(
            [
                ("검사 건수", len(history_df)),
                ("총 검사수량", f"{history_df['checked_qty'].sum():,.0f}"),
                ("총 불량수량", f"{history_df['defect_qty'].sum():,.0f}"),
            ]
        )

    show_dataframe(history_df, "조건에 해당하는 검사 이력이 없습니다.")

with tab_stats:
    st.subheader("품목별 불량률")
    stats_df = queries.defect_rate_by_item()
    show_dataframe(stats_df, "검사 이력이 없습니다.")
    if not stats_df.empty:
        st.bar_chart(stats_df.set_index("item_name")["defect_rate_pct"])

    st.markdown("---")

    st.subheader("불량 사유별 집계")
    reason_stats_df = queries.defect_rate_by_reason()
    show_dataframe(reason_stats_df, "불량 이력이 없습니다.")
    if not reason_stats_df.empty:
        st.bar_chart(reason_stats_df.set_index("reason_name")["total_defect_qty"])

with tab_reason:
    st.caption("불량검사 등록 화면에서 선택할 불량 사유 코드를 관리합니다.")

    if "last_reason_code_created" in st.session_state:
        st.success("불량 사유 코드가 등록되었습니다.")
        st.write(st.session_state.pop("last_reason_code_created"))

    with st.form("reason_code_form"):
        new_reason_code = st.text_input("사유 코드 (예: PKG_DAMAGE)")
        new_reason_name = st.text_input("사유명 (예: 포장 손상)")
        reason_submitted = st.form_submit_button("사유 코드 등록", type="primary")

    if reason_submitted:
        data = DefectReasonCodeRegistration(
            reason_code=new_reason_code, reason_name=new_reason_name
        )
        try:
            result = register_defect_reason_code(data)
            st.session_state["last_reason_code_created"] = result
            st.rerun()
        except ValueError as exc:
            st.error(str(exc))

    st.markdown("---")
    st.subheader("등록된 사유 코드")
    reason_df = queries.all_defect_reason_codes()
    show_dataframe(reason_df, "등록된 사유 코드가 없습니다.")

    if not reason_df.empty:
        toggle_options = {
            f"{row['reason_code']} | {row['reason_name']} "
            f"({'사용' if row['is_active'] == 'Y' else '비활성'})": row
            for _, row in reason_df.iterrows()
        }
        toggle_label = st.selectbox("사용여부 변경할 코드", list(toggle_options.keys()))
        toggle_row = toggle_options[toggle_label]
        new_status = "N" if toggle_row["is_active"] == "Y" else "Y"
        action_label = "비활성화" if new_status == "N" else "다시 활성화"

        if st.button(f"{toggle_row['reason_code']} {action_label}"):
            try:
                set_defect_reason_code_active(toggle_row["reason_code"], new_status)
                st.rerun()
            except ValueError as exc:
                st.error(str(exc))

st.markdown("---")
st.caption(
    "`inspection.lot_id`는 UNIQUE 제약이므로 LOT당 검사 이력은 최종 결과 1건만 남는다."
)