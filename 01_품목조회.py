import streamlit as st
import pandas as pd
from src import queries
from src.ui import metric_row, setup_page, show_dataframe

setup_page("품목 조회")


st.title("품목 조회")


with st.expander(" 신규 품목 등록"):
    with st.form("add_item_form", clear_on_submit=True):
        col1, col2 = st.columns(2)
        new_code = col1.text_input("품목 코드")
        new_name = col2.text_input("품목명")
        new_type = col1.selectbox("품목 유형*", ["PRODUCT", "MATERIAL"])
        new_unit = col2.text_input("단위", value="EA")
        new_active = col2.selectbox("active", ["Y", "N"])
        
        submitted = st.form_submit_button("품목 저장")
        if submitted:
            if not new_code or not new_name:
                st.error("품목 코드와 품목명은 필수 입력 항목입니다.")
            else:
                try:   
                    queries.insert_item(new_code, new_name, new_type, new_unit, new_active)
                    st.success(f"[{new_name}] 품목이 성공적으로 등록되었습니다.")
                    st.rerun() 
                except Exception as e:
                    st.error(f"등록 실패 (중복 코드 확인): {e}")

st.divider()




col_search1, col_search2 = st.columns([3, 1])
keyword = col_search1.text_input("품목 코드 또는 품목명 검색")
item_type = col_search2.selectbox("품목 유형", ["전체", "PRODUCT", "MATERIAL"])

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
    st.divider()
    st.subheader(" 품목 상세 정보 및 연관 데이터")
    
    selected_item_name = st.selectbox("상세 확인 품목 선택", df["item_name"].tolist())
    selected_row = df[df["item_name"] == selected_item_name].iloc[0]
    
    item_id = int(selected_row["item_id"])
    item_type_val = selected_row["item_type"]

  
    st.write(
        {
            "품목 ID": item_id,
            "품목 코드": selected_row["item_code"],
            "품목 유형": item_type_val,
            "단위": selected_row["unit"],
            "연결 LOT 수": int(selected_row["lot_count"]),
        }
    )


    if item_type_val == "PRODUCT":
        st.markdown(f"** {selected_item_name}의 BOM 소요 자재**")
   
        bom_df = queries.get_bom_by_parent_id(item_id) if hasattr(queries, 'get_bom_by_parent_id') else pd.DataFrame()
        if not bom_df.empty:
            show_dataframe(bom_df)
        else:
            st.info("등록된 BOM 정보가 없습니다.")
            
    elif item_type_val == "MATERIAL":
        st.markdown(f"** {selected_item_name}의 입고/보유 LOT 목록**")
     
        lots_df = queries.get_lots_by_item_id(item_id) if hasattr(queries, 'get_lots_by_item_id') else pd.DataFrame()
        if not lots_df.empty:
            show_dataframe(lots_df)
        else:
            st.info("연결된 LOT 이력이 없습니다.")

st.caption(
    "`item`은 기준정보다. 실제 입고 또는 생산으로 생긴 묶음과 수량은 `lot`에서 확인한다."
)
