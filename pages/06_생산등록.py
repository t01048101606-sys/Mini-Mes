from datetime import date, timedelta

import streamlit as st

from src import queries
from src.services import (
    ProductionRegistration,
    complete_production_plan,
    register_production,
)
from src.ui import require_role, setup_page


setup_page("생산 등록")
require_role("ADMIN", "OPERATOR")
st.title("🛡️⚙️생산 등록")
st.markdown("---")

if "last_production_result" in st.session_state:
    st.success("생산실적이 정상적으로 등록되었습니다.")
    st.write(st.session_state.pop("last_production_result"))
    st.info(
        """
        저장된 작업:
        1. 완제품 LOT 1건 생성
        2. 생산실적 1건 생성
        3. 선택한 원자재 LOT별 투입 이력 생성
        """
    )
    st.markdown("---")

products = queries.active_items_for_select("PRODUCT")
if not products:
    st.warning("생산 등록에 필요한 제품 품목이 없습니다.")
    st.stop()

product_options = {
    f"{item['item_code']} | {item['item_name']}": item["item_id"] for item in products
}

open_plans = queries.open_production_plans_for_select()
plan_option_map = {"직접 입력 (계획 없이 등록)": None}
for p in open_plans:
    plan_option_map[f"{p['plan_no']} | {p['item_name']} | 계획수량 {p['planned_qty']:,.0f}"] = p

plan_label = st.selectbox("생산계획에서 불러오기 (선택)", list(plan_option_map.keys()))
selected_plan = plan_option_map[plan_label]
if selected_plan:
    st.caption(f"'{selected_plan['plan_no']}' 계획을 기준으로 제품/수량이 자동 채워집니다. 저장 시 이 계획은 완료 처리됩니다.")

st.markdown("---")

product_labels = list(product_options.keys())
default_product_index = 0
if selected_plan:
    for idx, label in enumerate(product_labels):
        if product_options[label] == selected_plan["item_id"]:
            default_product_index = idx
            break

product_label = st.selectbox(
    "생산할 완제품 품목", product_labels, index=default_product_index
)
product_item_id = product_options[product_label]

col1, col2 = st.columns(2)
production_date = col1.date_input("생산일자", value=date.today())
expire_date = col2.date_input("완제품 유효기한", value=date.today() + timedelta(days=180))

next_production_id = queries.next_id("production", "production_id")

production_no = st.text_input(
    "생산번호",
    value=f"PRD-{date.today().strftime('%Y%m%d')}-{next_production_id:04d}",
)
output_lot_no = st.text_input(
    "생성할 완제품 LOT 번호",
    value=f"FG-{date.today().strftime('%Y%m%d')}-{next_production_id:04d}",
)
default_qty = float(selected_plan["planned_qty"]) if selected_plan else 1000.0
qty = st.number_input("생산수량", min_value=0.0, value=default_qty, step=100.0)

st.markdown("---")
st.subheader("투입 원자재")

bom_df = queries.bom_for_product(product_item_id)
material_rows: list[dict] = []

if bom_df.empty:
    st.info("이 품목은 등록된 BOM이 없습니다. 원자재를 수동으로 선택하세요. (BOM 관리 페이지에서 등록 가능)")

    material_lots = queries.lots_for_select("RECEIPT")
    if not material_lots:
        st.warning("투입 가능한 원자재 LOT가 없습니다.")
        st.stop()

    material_options = {
        f"{lot['lot_no']} | {lot['item_name']} | 보유 {lot['qty']:,.0f}": lot
        for lot in material_lots
    }
    selected_material_labels = st.multiselect(
        "원자재 LOT 선택",
        list(material_options.keys()),
        default=list(material_options.keys())[:3],
    )
    for label in selected_material_labels:
        lot = material_options[label]
        used_qty = st.number_input(
            f"{lot['lot_no']} 투입수량",
            min_value=0.0,
            value=float(qty),
            step=100.0,
            key=f"manual_qty_{lot['lot_id']}",
        )
        material_rows.append(
            {
                "material_item_id": lot["item_id"],
                "material_lot_id": lot["lot_id"],
                "qty": used_qty,
            }
        )

else:
    st.caption("BOM 기준 필요 원자재량이 자동 계산됩니다. 실제 투입할 LOT와 수량을 확인/조정하세요.")

    # 전체 원자재 잔량 대비 부족 여부를 먼저 한눈에 보여준다.
    stock_df = queries.material_stock_summary()
    stock_by_item = dict(zip(stock_df["item_id"], stock_df["remaining_qty"])) if not stock_df.empty else {}

    shortage_rows = []
    for _, bom_row in bom_df.iterrows():
        _material_item_id = int(bom_row["material_item_id"])
        _required_qty = float(bom_row["qty_per_unit"]) * qty
        _remaining_qty = float(stock_by_item.get(_material_item_id, 0.0))
        _shortage_qty = _required_qty - _remaining_qty
        if _shortage_qty > 0:
            shortage_rows.append(
                {
                    "원자재": bom_row["material_name"],
                    "필요수량": round(_required_qty, 1),
                    "현재잔량": round(_remaining_qty, 1),
                    "부족수량": round(_shortage_qty, 1),
                }
            )

    if shortage_rows:
        st.error(
            f"생산수량 {qty:,.0f} 기준, {len(shortage_rows)}개 원자재가 부족합니다. "
            "원자재 입고 등록 후 다시 시도하거나 생산수량을 조정하세요."
        )
        st.dataframe(shortage_rows, use_container_width=True, hide_index=True)
    else:
        st.success(f"생산수량 {qty:,.0f} 기준, BOM상 필요한 모든 원자재 재고가 충분합니다.")

    st.markdown("---")

    for _, bom_row in bom_df.iterrows():
        material_item_id = int(bom_row["material_item_id"])
        required_qty = float(bom_row["qty_per_unit"]) * qty

        st.markdown(
            f"**{bom_row['material_name']}** ({bom_row['material_code']}) "
            f"— 필요수량 약 **{required_qty:,.1f} {bom_row['material_unit']}**"
        )

        available_lots = queries.material_lots_with_balance_for_item(material_item_id)
        if not available_lots:
            st.error(f"'{bom_row['material_name']}'의 사용 가능한 재고 LOT가 없습니다.")
            st.markdown("---")
            continue

        lot_label_map = {
            f"{lot['lot_no']} | 잔량 {lot['remaining_qty']:,.0f}": lot
            for lot in available_lots
        }

        # 필요수량을 채울 때까지 잔량이 큰 순서로 LOT를 기본 선택한다.
        default_labels = []
        remaining_needed = required_qty
        for label, lot in lot_label_map.items():
            if remaining_needed <= 0:
                break
            default_labels.append(label)
            remaining_needed -= lot["remaining_qty"]

        selected_labels = st.multiselect(
            f"{bom_row['material_name']} 투입 LOT 선택",
            list(lot_label_map.keys()),
            default=default_labels,
            key=f"bom_select_{material_item_id}",
        )

        remaining_needed = required_qty
        for label in selected_labels:
            lot = lot_label_map[label]
            default_use = min(lot["remaining_qty"], remaining_needed) if remaining_needed > 0 else 0.0
            used_qty = st.number_input(
                f"　└ {lot['lot_no']} 투입수량",
                min_value=0.0,
                value=float(default_use if default_use > 0 else lot["remaining_qty"]),
                step=1.0,
                key=f"bom_qty_{lot['lot_id']}",
            )
            remaining_needed -= used_qty
            material_rows.append(
                {
                    "material_item_id": material_item_id,
                    "material_lot_id": lot["lot_id"],
                    "qty": used_qty,
                }
            )

        st.markdown("---")

submitted = st.button("생산실적 저장", type="primary")

if submitted:
    data = ProductionRegistration(
        product_item_id=product_item_id,
        output_lot_no=output_lot_no,
        production_no=production_no,
        production_date=production_date,
        qty=qty,
        expire_date=expire_date,
        material_rows=material_rows,
    )
    try:
        result = register_production(data)
        if selected_plan:
            try:
                complete_production_plan(selected_plan["plan_id"], result["production_id"])
            except ValueError:
                pass  # 생산실적 저장은 성공했으므로 계획 연결 실패는 조용히 무시
        st.session_state["last_production_result"] = result
        st.rerun()
    except ValueError as exc:
        st.error(str(exc))

st.caption(
    "현재 스키마에는 재고 이동 테이블이 없으므로 원자재 LOT 수량 차감은 하지 않는다."
)