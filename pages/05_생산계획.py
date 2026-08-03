from datetime import date, timedelta

import pandas as pd
import streamlit as st

from src import queries
from src.services import (
    ProductionPlanRegistration,
    cancel_production_plan,
    register_production_plan,
)
from src.ui import metric_row, require_role, setup_page, show_dataframe


setup_page("생산계획")
require_role("ADMIN", "OPERATOR")
st.title("생산계획")
st.markdown("---")

tab_register, tab_list, tab_shortage = st.tabs(
    ["계획 등록", "계획 조회 / 취소", "계획 대비 원자재 부족 확인"]
)

with tab_register:
    if "last_plan_created" in st.session_state:
        st.success("생산계획이 등록되었습니다.")
        st.write(st.session_state.pop("last_plan_created"))

    products = queries.active_items_for_select("PRODUCT")
    if not products:
        st.warning("등록된 제품이 없습니다.")
    else:
        product_options = {
            f"{item['item_code']} | {item['item_name']}": item["item_id"] for item in products
        }

        next_plan_id = queries.next_id("production_plan", "plan_id")

        with st.form("plan_form"):
            product_label = st.selectbox("계획 대상 제품", list(product_options.keys()))
            plan_no = st.text_input(
                "계획번호",
                value=f"PLAN-{date.today().strftime('%Y%m%d')}-{next_plan_id:04d}",
            )
            plan_date = st.date_input("계획일자", value=date.today() + timedelta(days=7))
            planned_qty = st.number_input("계획수량", min_value=0.0, value=1000.0, step=100.0)

            plan_submitted = st.form_submit_button("계획 등록", type="primary")

        if plan_submitted:
            data = ProductionPlanRegistration(
                plan_no=plan_no,
                item_id=product_options[product_label],
                planned_qty=planned_qty,
                plan_date=plan_date,
            )
            try:
                result = register_production_plan(data)
                st.session_state["last_plan_created"] = result
                st.rerun()
            except ValueError as exc:
                st.error(str(exc))

with tab_list:
    col1, col2 = st.columns(2)
    keyword = col1.text_input("계획번호 또는 품목명 검색")
    status_filter = col2.selectbox("상태", ["전체", "OPEN", "COMPLETED", "CANCELED"])

    plans_df = queries.production_plans(keyword=keyword, status_filter=status_filter)

    if not plans_df.empty:
        metric_row(
            [
                ("계획 건수", len(plans_df)),
                ("진행중(OPEN)", int((plans_df["status"] == "OPEN").sum())),
                ("완료(COMPLETED)", int((plans_df["status"] == "COMPLETED").sum())),
            ]
        )

    show_dataframe(plans_df, "등록된 생산계획이 없습니다.")

    open_plans = plans_df[plans_df["status"] == "OPEN"] if not plans_df.empty else plans_df
    if not open_plans.empty:
        st.markdown("---")
        st.subheader("계획 취소")
        cancel_options = {
            f"{row['plan_no']} | {row['item_name']} | {row['planned_qty']:,.0f}": int(row["plan_id"])
            for _, row in open_plans.iterrows()
        }
        cancel_label = st.selectbox("취소할 계획", list(cancel_options.keys()))
        if st.button("선택한 계획 취소", type="secondary"):
            try:
                cancel_production_plan(cancel_options[cancel_label])
                st.rerun()
            except ValueError as exc:
                st.error(str(exc))

with tab_shortage:
    st.caption("OPEN 상태인 생산계획을 기준으로, BOM상 필요한 원자재가 현재 재고로 충분한지 확인합니다.")

    open_for_check = queries.open_production_plans_for_select()
    if not open_for_check:
        st.info("확인할 OPEN 상태의 생산계획이 없습니다.")
    else:
        plan_options = {
            f"{p['plan_no']} | {p['item_name']} | {p['planned_qty']:,.0f}": p for p in open_for_check
        }
        plan_label = st.selectbox("확인할 계획", list(plan_options.keys()))
        selected_plan = plan_options[plan_label]

        bom_df = queries.bom_for_product(selected_plan["item_id"])

        if bom_df.empty:
            st.info("이 제품은 등록된 BOM이 없어 부족량을 계산할 수 없습니다.")
        else:
            stock_df = queries.material_stock_summary()
            stock_by_item = (
                dict(zip(stock_df["item_id"], stock_df["remaining_qty"])) if not stock_df.empty else {}
            )

            rows = []
            for _, bom_row in bom_df.iterrows():
                material_item_id = int(bom_row["material_item_id"])
                required_qty = float(bom_row["qty_per_unit"]) * float(selected_plan["planned_qty"])
                remaining_qty = float(stock_by_item.get(material_item_id, 0.0))
                shortage_qty = max(required_qty - remaining_qty, 0.0)
                rows.append(
                    {
                        "원자재": bom_row["material_name"],
                        "필요수량": round(required_qty, 1),
                        "현재잔량": round(remaining_qty, 1),
                        "부족수량": round(shortage_qty, 1),
                        "단위": bom_row["material_unit"],
                    }
                )

            result_df = pd.DataFrame(rows)
            shortage_count = int((result_df["부족수량"] > 0).sum())

            if shortage_count > 0:
                st.error(f"{shortage_count}개 원자재가 부족합니다. 입고 발주가 필요합니다.")
            else:
                st.success("계획 수량 기준 모든 원자재가 충분합니다.")

            show_dataframe(result_df)

st.markdown("---")
st.caption(
    "생산계획이 실제로 실행되면, 생산 등록 화면에서 이 계획을 선택해 생산실적으로 전환할 수 있습니다."
)
