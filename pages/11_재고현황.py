import html

import pandas as pd
import plotly.express as px
import streamlit as st

from src import queries
from src.ui import alert_badge, kpi_row, require_role, setup_page, show_dataframe


setup_page("재고 현황")
require_role("ADMIN", "OPERATOR", "INSPECTOR")
st.title("🔍재고 현황 대시보드")
st.markdown("---")

tab_stock, tab_expiring, tab_shortage = st.tabs(
    ["전체 재고 현황", "유효기한 임박", "생산계획 대비 부족 확인"]
)

with tab_stock:
    stock_df = queries.material_stock_summary()

    if not stock_df.empty:
        low_count = int((stock_df["remaining_qty"] <= 0).sum())
        kpi_row(
            [
                ("관리 원자재 수", f"{len(stock_df)} 개", "kpi-blue"),
                ("총 잔량 합계", f"{stock_df['remaining_qty'].sum():,.0f}", "kpi-green"),
                ("잔량 0 이하 품목 수", f"{low_count} 개", "kpi-red" if low_count > 0 else "kpi-teal"),
            ]
        )

    st.subheader("원자재별 재고 현황")

    if stock_df.empty:
        st.info("원자재 재고 데이터가 없습니다.")
    else:
        # 잔량 기준 정렬 후, 각 품목을 진행바(progress bar) 형태로 시각화한다.
        sorted_stock = stock_df.sort_values("remaining_qty", ascending=False).reset_index(drop=True)
        max_qty = max(sorted_stock["remaining_qty"].max(), 1)

        rows_html = []
        for _, row in sorted_stock.iterrows():
            remaining = row["remaining_qty"]
            pct = max(min(remaining / max_qty * 100, 100), 0)
            if remaining <= 0:
                bar_color = "#D8481E"
            elif pct < 30:
                bar_color = "#E0B84B"
            else:
                bar_color = "#2E8B57"
            rows_html.append(
                f"""
                <div class="stock-row">
                    <div class="stock-label">{html.escape(row['item_name'])}</div>
                    <div class="stock-bar-bg">
                        <div class="stock-bar-fill" style="width:{pct:.1f}%; background:{bar_color};"></div>
                    </div>
                    <div class="stock-value">{remaining:,.0f} {html.escape(str(row['unit']))}</div>
                </div>
                """
            )
        st.markdown("".join(rows_html), unsafe_allow_html=True)

        st.write("")
        fig_stock = px.bar(
            sorted_stock,
            x="remaining_qty",
            y="item_name",
            orientation="h",
            color="remaining_qty",
            color_continuous_scale=["#D8481E", "#E0B84B", "#2E8B57"],
            labels={"item_name": "원자재", "remaining_qty": "잔량"},
        )
        fig_stock.update_layout(
            showlegend=False,
            coloraxis_showscale=False,
            margin=dict(l=10, r=10, t=10, b=10),
            plot_bgcolor="rgba(0,0,0,0)",
            paper_bgcolor="rgba(0,0,0,0)",
            height=max(300, len(sorted_stock) * 28),
        )
        st.plotly_chart(fig_stock, use_container_width=True)

    st.caption(
        "잔량 = 총 입고량(RECEIPT LOT) - 총 생산투입량(production_material). "
        "재고 이동/폐기/조정 이력은 별도로 관리하지 않으므로 실물 재고와 차이가 있을 수 있다."
    )

with tab_expiring:
    days = st.radio(
        "임박 기준", [7, 30, 60, 90], index=1, horizontal=True, format_func=lambda d: f"{d}일 이내"
    )

    expiring_df = queries.expiring_material_lots(days=days)

    if not expiring_df.empty:
        kpi_row(
            [
                (f"{days}일 이내 만료 LOT 수", f"{len(expiring_df)} 건", "kpi-gold"),
                ("해당 잔량 합계", f"{expiring_df['remaining_qty'].sum():,.0f}", "kpi-purple"),
            ],
            columns=2,
        )

    if expiring_df.empty:
        st.success(" 해당 기간 내 유효기한이 임박한 LOT가 없습니다.")
    else:
       
        fig_exp = px.bar(
            expiring_df.sort_values("days_until_expire"),
            x="days_until_expire",
            y="lot_no",
            orientation="h",
            color="days_until_expire",
            color_continuous_scale=["#D8481E", "#E0B84B", "#2E8B57"],
            labels={"lot_no": "LOT 번호", "days_until_expire": "만료까지 남은 일수"},
            hover_data=["item_name", "remaining_qty", "expire_date"],
        )
        fig_exp.update_layout(
            margin=dict(l=10, r=10, t=10, b=10),
            plot_bgcolor="rgba(0,0,0,0)",
            paper_bgcolor="rgba(0,0,0,0)",
            height=max(300, len(expiring_df) * 28),
            coloraxis_colorbar_title="D-day",
        )
        st.plotly_chart(fig_exp, use_container_width=True)

        show_dataframe(expiring_df)

with tab_shortage:
    st.caption("특정 제품을 계획 수량만큼 생산한다고 가정했을 때, BOM 기준 원자재 부족 여부를 미리 확인합니다.")

    products = queries.active_items_for_select("PRODUCT")
    if not products:
        st.warning("등록된 제품이 없습니다.")
    else:
        product_options = {
            f"{item['item_code']} | {item['item_name']}": item["item_id"] for item in products
        }
        product_label = st.selectbox("확인할 제품", list(product_options.keys()))
        product_item_id = product_options[product_label]
        planned_qty = st.number_input("계획 생산수량", min_value=0.0, value=1000.0, step=100.0)

        bom_df = queries.bom_for_product(product_item_id)

        if bom_df.empty:
            st.info("이 제품은 등록된 BOM이 없어 부족량을 계산할 수 없습니다.")
        else:
            stock_df = queries.material_stock_summary()
            stock_by_item = dict(zip(stock_df["item_id"], stock_df["remaining_qty"]))

            rows = []
            for _, bom_row in bom_df.iterrows():
                material_item_id = int(bom_row["material_item_id"])
                required_qty = float(bom_row["qty_per_unit"]) * planned_qty
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

            kpi_row(
                [
                    ("확인 원자재 수", f"{len(result_df)} 개", "kpi-blue"),
                    ("부족 원자재 수", f"{shortage_count} 개", "kpi-red" if shortage_count > 0 else "kpi-teal"),
                ],
                columns=2,
            )

            if shortage_count > 0:
                alert_badge(f"{shortage_count}개 원자재가 부족합니다. 입고 등록이 필요합니다.", "danger")
            else:
                alert_badge("모든 원자재가 충분합니다.", "ok")

            st.write("")

            
            for _, row in result_df.iterrows():
                is_short = row["부족수량"] > 0
                card_class = "shortage-bad" if is_short else "shortage-ok"
                status_text = f" 부족 {row['부족수량']:,.1f} {row['단위']}" if is_short else "🟢 충분"
                st.markdown(
                    f"""
                    <div class="shortage-card {card_class}">
                        <b>{html.escape(row['원자재'])}</b> &nbsp;|&nbsp;
                        필요 {row['필요수량']:,.1f} {html.escape(row['단위'])} &nbsp;|&nbsp;
                        잔량 {row['현재잔량']:,.1f} {html.escape(row['단위'])} &nbsp;|&nbsp;
                        {status_text}
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

            st.write("")
            fig_shortage = px.bar(
                result_df,
                x="원자재",
                y=["필요수량", "현재잔량"],
                barmode="group",
                color_discrete_map={"필요수량": "#D8481E", "현재잔량": "#2B5F8A"},
                labels={"value": "수량", "variable": "구분"},
            )
            fig_shortage.update_layout(
                margin=dict(l=10, r=10, t=30, b=10),
                plot_bgcolor="rgba(0,0,0,0)",
                paper_bgcolor="rgba(0,0,0,0)",
                legend_title_text="",
            )
            st.plotly_chart(fig_shortage, use_container_width=True)