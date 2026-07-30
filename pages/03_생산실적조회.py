import pandas as pd
import streamlit as st

from src import queries
from src.ui import metric_row, page_title, setup_page, show_dataframe


setup_page("생산실적 조회")
st.title("생산실적 조회")



col_search, col_check = st.columns([3, 1])
keyword = col_search.text_input("생산번호, 품목명, 완제품 LOT 검색", placeholder="검색어 입력...")

use_date_filter = col_check.checkbox("생산일자 필터 사용")
date_from, date_to = None, None

if use_date_filter:
    col_d1, col_d2 = st.columns(2)
    date_from = col_d1.date_input("시작일")
    date_to = col_d2.date_input("종료일")


df = queries.productions(keyword=keyword, date_from=date_from, date_to=date_to)

if not df.empty:
    metric_row(
        [
            ("생산실적 수", f"{len(df)} 건"),
            ("총 생산수량", f"{df['production_qty'].sum():,.0f} EA"),
            ("발행 완제품 LOT 수", f"{df['output_lot_no'].nunique()} 개"),
        ]
    )

    st.subheader("생산 이벤트와 결과 LOT")
    show_dataframe(df)

   
    st.divider()
    st.subheader(" 생산실적 상세 및 원자재 투입 명세")

    selected_no = st.selectbox("원자재 투입 확인 생산번호 선택", df["production_no"].tolist())
    selected_row = df[df["production_no"] == selected_no].iloc[0]
    production_id = int(selected_row["production_id"])
    prod_qty = float(selected_row["production_qty"])

    
    col_info1, col_info2 = st.columns(2)
    with col_info1:
        st.markdown(f"**• 생산 ID:** `{production_id}`")
        st.markdown(f"**• 생산번호:** `{selected_row['production_no']}`")
        st.markdown(f"**• 생산 품목:** {selected_row['product_name']} (`{selected_row['product_code']}`)")
        st.markdown(f"**• 생산 수량:** {prod_qty:,.0f} EA")
        
    with col_info2:
        st.markdown(f"**• 완제품 LOT 번호:** `{selected_row['output_lot_no']}`")
        st.markdown(f"**• 생산일자:** {selected_row['production_date']}")
        workcenter = selected_row["workcenter_name"] if "workcenter_name" in selected_row else "-"
        st.markdown(f"**• 작업장/공정:** {workcenter}")

    st.write("")
    st.markdown(f" **[{selected_no}] 생산 시 투입된 원자재 LOT 목록**")
    
   
    mat_df = queries.production_materials(production_id)

    if not mat_df.empty:
        
        if "used_qty" in mat_df.columns and prod_qty > 0:
            mat_df["단위 소요량(개당)"] = (mat_df["used_qty"] / prod_qty).round(4)

        
        display_cols = [c for c in mat_df.columns if c != "production_no"]
        show_dataframe(mat_df[display_cols])
    else:
        st.info("해당 생산실적에 등록된 원자재 투입 이력이 없습니다.")
else:
    st.warning("조회된 생산실적 데이터가 없습니다.")

st.caption(
    "`production.qty`는 생산 수량이고, `production.output_lot_id`는 생산 결과로 만들어진 완제품 LOT를 말함."
)
