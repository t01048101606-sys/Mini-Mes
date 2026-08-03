import streamlit as st

from src import queries
from src.services import BomRow, replace_bom
from src.ui import require_role, setup_page, show_dataframe


setup_page("BOM 관리")
require_role("ADMIN", "OPERATOR")
st.title("BOM 관리")
st.markdown("---")

st.subheader("제품별 BOM 등록 현황")
status_df = queries.products_with_bom_status()
show_dataframe(status_df, "등록된 제품이 없습니다.")

st.markdown("---")

products = queries.active_items_for_select("PRODUCT")
materials = queries.active_items_for_select("MATERIAL")

if not products or not materials:
    st.warning("BOM을 등록하려면 제품과 원자재 품목이 모두 필요합니다.")
    st.stop()

product_options = {
    f"{item['item_code']} | {item['item_name']}": item["item_id"] for item in products
}
material_options = {
    f"{item['item_code']} | {item['item_name']} ({item['unit']})": item
    for item in materials
}
material_id_to_label = {v["item_id"]: k for k, v in material_options.items()}

st.subheader("BOM 편집")
product_label = st.selectbox("제품 선택", list(product_options.keys()))
product_item_id = product_options[product_label]

existing_rows = queries.bom_for_product_rows(product_item_id)
existing_material_ids = [row["material_item_id"] for row in existing_rows]
existing_qty_by_material = {row["material_item_id"]: row["qty_per_unit"] for row in existing_rows}

with st.form("bom_form"):
    default_labels = [
        material_id_to_label[mid] for mid in existing_material_ids if mid in material_id_to_label
    ]
    selected_labels = st.multiselect(
        "구성 원자재 선택",
        list(material_options.keys()),
        default=default_labels,
    )

    bom_rows: list[BomRow] = []
    for label in selected_labels:
        material = material_options[label]
        default_qty = existing_qty_by_material.get(material["item_id"], 1.0)
        qty_per_unit = st.number_input(
            f"{material['item_name']} 단위당 소요량 ({material['unit']})",
            min_value=0.0,
            value=float(default_qty),
            step=0.1,
            key=f"bom_qty_{material['item_id']}",
        )
        bom_rows.append(
            BomRow(material_item_id=material["item_id"], qty_per_unit=qty_per_unit)
        )

    submitted = st.form_submit_button("BOM 저장")

if submitted:
    try:
        result = replace_bom(product_item_id, bom_rows)
        st.success("BOM이 저장되었습니다.")
        st.write(result)
        st.rerun()
    except ValueError as exc:
        st.error(str(exc))

if existing_rows:
    st.markdown("---")
    st.subheader("현재 저장된 BOM")
    show_dataframe(queries.bom_for_product(product_item_id))
