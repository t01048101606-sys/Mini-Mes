import pandas as pd
import streamlit as st

from src import queries
from src.ui import metric_row, page_title, setup_page, show_dataframe


setup_page("LOT 조회")
st.title("LOT 조회")



items = queries.active_items_for_select()
item_options = {"전체": None}
for item in items:
    item_options[f"{item['item_code']} | {item['item_name']}"] = item["item_id"]

col1, col2, col3 = st.columns(3)
keyword = col1.text_input("LOT 번호 검색")
lot_type = col2.selectbox("LOT 유형", ["전체", "RECEIPT", "PRODUCTION"])
item_label = col3.selectbox("품목", list(item_options.keys()))

df = queries.lots(keyword=keyword, lot_type=lot_type, item_id=item_options[item_label])

if not df.empty:
    
    receipt_qty = df[df["lot_type"] == "RECEIPT"]["qty"].sum()
    prod_qty = df[df["lot_type"] == "PRODUCTION"]["qty"].sum()

    metric_row(
        [
            ("LOT 총 건수", f"{len(df)} 건"),
            ("전체 수량", f"{df['qty'].sum():,.0f}"),
            ("원자재 입고 수량", f"{receipt_qty:,.0f}"),
            ("생산 완제품 수량", f"{prod_qty:,.0f}"),
        ]
    )

st.subheader("LOT와 품목 JOIN 결과")
show_dataframe(df)

if not df.empty:
    st.divider()
    st.subheader(" LOT 상세 정보 및 이력 관리")

    selected_lot = st.selectbox("상세 확인 LOT 선택", df["lot_no"].tolist())
    selected_row = df[df["lot_no"] == selected_lot].iloc[0]

    col_info, col_action = st.columns([2, 1])

    with col_info:
        
        st.write(
            {
                "LOT ID": int(selected_row["lot_id"]),
                "LOT 번호": selected_row["lot_no"],
                "품목": selected_row["item_name"],
                "품목 유형": selected_row["item_type"],
                "LOT 유형": selected_row["lot_type"],
                "수량": float(selected_row["qty"]),
                "입고일": selected_row["received_date"] or "-",
                "생산일": selected_row["produced_date"] or "-",
                "유효기한": selected_row["expire_date"] or "-",
            }
        )

    with col_action:
        
        if pd.notna(selected_row.get("expire_date")):
            
            today = pd.Timestamp.now().strftime("%Y-%m-%d")
            if str(selected_row["expire_date"]) < today:
                st.error(" 해당 LOT는 유효기한이 만료되었습니다")
            else:
                st.success(" 유효기한 내 정상 LOT입니다.")

        
        current_type = selected_row["lot_type"]
        if current_type == "PRODUCTION":
            st.info(" 정방향 추적을 실행하세요")
            
        elif current_type == "RECEIPT":
            st.info(" 역방향 추적을 실행하세요")
            

st.caption(
    "`lot_type = 'RECEIPT'` =  원자재 입고 LOT `lot_type = 'PRODUCTION'` =>  생산 결과 완제품 LOT."
)
