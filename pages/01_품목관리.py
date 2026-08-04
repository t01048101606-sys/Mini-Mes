import streamlit as st

from src import queries
from src.services import ItemRegistration, ItemUpdate, register_item, update_item
from src.ui import metric_row, require_role, setup_page, show_dataframe


setup_page("품목 조회")
require_role("ADMIN", "OPERATOR", "INSPECTOR")
st.title("🛡️⚙️🔍품목 관리")

st.markdown("---")

user_role = st.session_state.get("user_role")
can_edit_items = user_role in ("ADMIN", "OPERATOR")

tab_search, tab_create, tab_edit = st.tabs(["조회", "신규 등록", "수정 / 단종"])

with tab_search:
    keyword = st.text_input("품목 코드 또는 품목명 검색")
    item_type = st.selectbox("품목 유형", ["전체", "PRODUCT", "MATERIAL"])

    df = queries.items(keyword=keyword, item_type=item_type)
    type_counts = queries.item_type_counts()

    if not type_counts.empty:
        count_map = dict(zip(type_counts["item_type"], type_counts["item_count"]))
        metric_row(
            [
                ("전체 품목", int(type_counts["item_count"].sum())),
                ("제품", count_map.get("PRODUCT", 0)),
                ("원자재", count_map.get("MATERIAL", 0)),
            ]
        )

    st.subheader("조회 결과")
    show_dataframe(df)

    if not df.empty:
        selected_item_id = st.selectbox(
            "상세 확인 품목",
            df["item_id"].tolist(),
            format_func=lambda item_id: df.loc[df["item_id"] == item_id, "item_name"].iloc[0],
        )
        selected_row = df[df["item_id"] == selected_item_id].iloc[0]
        st.write(
            {
                "품목 ID": int(selected_row["item_id"]),
                "품목 코드": selected_row["item_code"],
                "품목 유형": selected_row["item_type"],
                "단위": selected_row["unit"],
                "연결 LOT 수": int(selected_row["lot_count"]),
            }
        )


with tab_create:
    if not can_edit_items:
        st.info("이 탭은 ADMIN/OPERATOR 권한만 이용할 수 있습니다.")
    else:
        st.caption("새 제품 또는 원자재 품목을 등록합니다. 등록 후에는 코드와 유형을 바꿀 수 없습니다.")

        if "last_item_created" in st.session_state:
            st.success("품목이 등록되었습니다.")
            st.write(st.session_state.pop("last_item_created"))

        with st.form("item_create_form"):
            new_item_code = st.text_input("품목 코드")
            new_item_name = st.text_input("품목명")
            new_item_type = st.selectbox("품목 유형", ["PRODUCT", "MATERIAL"])
            new_unit = st.text_input("단위", value="EA")

            create_submitted = st.form_submit_button("품목 등록", type="primary")

        if create_submitted:
            data = ItemRegistration(
                item_code=new_item_code,
                item_name=new_item_name,
                item_type=new_item_type,
                unit=new_unit,
            )
            try:
                result = register_item(data)
                st.session_state["last_item_created"] = result
                st.rerun()
            except ValueError as exc:
                st.error(str(exc))

with tab_edit:
    if not can_edit_items:
        st.info("이 탭은 ADMIN/OPERATOR 권한만 이용할 수 있습니다.")
    else:
        st.caption("품목명, 단위, 사용여부(단종 처리)를 수정합니다. 코드와 유형은 수정할 수 없습니다.")

        if "last_item_updated" in st.session_state:
            st.success("품목 정보가 수정되었습니다.")
            st.write(st.session_state.pop("last_item_updated"))

        all_items = queries.all_items_for_select()
        if not all_items:
            st.info("등록된 품목이 없습니다.")
        else:
            edit_options = {
                f"{item['item_code']} | {item['item_name']} "
                f"({'사용' if item['is_active'] == 'Y' else '단종'})": item["item_id"]
                for item in all_items
            }
            edit_label = st.selectbox("수정할 품목", list(edit_options.keys()))
            edit_item_id = edit_options[edit_label]
            current = queries.item_by_id(edit_item_id)

            with st.form("item_edit_form"):
                st.text_input("품목 코드 (수정 불가)", value=current["item_code"], disabled=True)
                st.text_input("품목 유형 (수정 불가)", value=current["item_type"], disabled=True)
                edit_item_name = st.text_input("품목명", value=current["item_name"])
                edit_unit = st.text_input("단위", value=current["unit"])
                edit_is_active = st.selectbox(
                    "사용여부",
                    ["Y", "N"],
                    index=0 if current["is_active"] == "Y" else 1,
                    format_func=lambda v: "사용" if v == "Y" else "단종",
                )

                edit_submitted = st.form_submit_button("수정 저장", type="primary")

            if edit_submitted:
                data = ItemUpdate(
                    item_id=edit_item_id,
                    item_name=edit_item_name,
                    unit=edit_unit,
                    is_active=edit_is_active,
                )
                try:
                    result = update_item(data)
                    st.session_state["last_item_updated"] = result
                    st.rerun()
                except ValueError as exc:
                    st.error(str(exc))