from datetime import date, timedelta

import streamlit as st

from src import queries
from src.services import ProductionRegistration, register_production
from src.ui import page_title, setup_page


setup_page("생산 등록")
st.title("생산 등록")



products = queries.active_items_for_select("PRODUCT")
material_lots = queries.lots_for_select("RECEIPT")

if not products or not material_lots:
    st.warning("생산 등록에 필요한 제품 품목 또는 원자재 LOT가 없습니다.")
    st.stop()

product_options = {
    f"{item['item_code']} | {item['item_name']}": item["item_id"]
    for item in products
}
material_options = {
    f"{lot['lot_no']} | {lot['item_name']} | 보유 {lot['qty']:,.0f}": lot
    for lot in material_lots
}


st.subheader("1. 투입 원자재 LOT 선택")
selected_material_labels = st.multiselect(
    "투입할 원자재 LOT를 선택하세요.",
    options=list(material_options.keys()),
    default=list(material_options.keys())[:3],
)

if not selected_material_labels:
    st.info("투입할 원자재 LOT를 최소 1개 이상 선택해 주세요.")


st.subheader("2. 생산 정보 및 투입 수량 입력")

with st.form("production_form"):
    product_label = st.selectbox("생산할 완제품 품목", list(product_options.keys()))
    
    col_d1, col_d2 = st.columns(2)
    with col_d1:
        production_date = st.date_input("생산일자", value=date.today())
        production_no = st.text_input("생산번호", value=f"PRD-{date.today().strftime('%Y%m%d')}-NEW")
        qty = st.number_input("생산수량", min_value=1.0, value=1000.0, step=100.0)
    with col_d2:
        expire_date = st.date_input("완제품 유효기한", value=date.today() + timedelta(days=180))
        output_lot_no = st.text_input("생성할 완제품 LOT 번호", value=f"FG-NEW-{date.today().strftime('%Y%m%d')}-001")

    st.markdown("---")
    st.markdown("**선택한 원자재별 투입 수량**")

    material_rows = []
    for label in selected_material_labels:
        lot = material_options[label]
        max_stock = float(lot["qty"])
        
        
        used_qty = st.number_input(
            f"[{lot['lot_no']}] {lot['item_name']} 투입수량 (보유: {max_stock:,.0f})",
            min_value=0.0,
            max_value=max_stock,
            value=min(float(qty), max_stock),
            step=10.0,
            key=f"material_qty_{lot['lot_id']}",
        )
        material_rows.append(
            {
                "material_item_id": lot["item_id"],
                "material_lot_id": lot["lot_id"],
                "qty": used_qty,
            }
        )

    submitted = st.form_submit_button("생산실적 저장")


if submitted:
    if not selected_material_labels:
        st.error("투입 원자재 LOT를 최소 1개 이상 선택해야 합니다.")
    else:
        data = ProductionRegistration(
            product_item_id=product_options[product_label],
            output_lot_no=output_lot_no,
            production_no=production_no,
            production_date=production_date,
            qty=qty,
            expire_date=expire_date,
            material_rows=material_rows,
        )
        try:
            result = register_production(data)
            st.success("생산실적이 정상적으로 등록되었습니다.")
            st.write(result)
            st.info(
                """
                저장된 작업:
                1. 완제품 LOT 1건 생성
                2. 생산실적 1건 생성
                3. 선택한 원자재 LOT별 투입 이력 생성
                """
            )
        except ValueError as exc:
            st.error(str(exc))

st.caption(
    "현재 스키마에는 재고 이동 테이블이 없으므로 원자재 LOT 수량 차감은 하지 않습니다."
)
