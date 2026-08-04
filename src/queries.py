from __future__ import annotations

import sqlite3

from src.db import fetch_all, fetch_dataframe, fetch_one


def table_counts():
    return fetch_dataframe(
        """
        SELECT 'item' AS table_name, COUNT(*) AS row_count FROM item
        UNION ALL
        SELECT 'lot' AS table_name, COUNT(*) AS row_count FROM lot
        UNION ALL
        SELECT 'production' AS table_name, COUNT(*) AS row_count FROM production
        UNION ALL
        SELECT 'production_material' AS table_name, COUNT(*) AS row_count FROM production_material
        UNION ALL
        SELECT 'bom' AS table_name, COUNT(*) AS row_count FROM bom
        UNION ALL
        SELECT 'inspection' AS table_name, COUNT(*) AS row_count FROM inspection
        UNION ALL
        SELECT 'shipment' AS table_name, COUNT(*) AS row_count FROM shipment
        """
    )


def table_list():
    return fetch_dataframe(
        """
        SELECT name AS table_name
        FROM sqlite_master
        WHERE type = 'table'
        ORDER BY name
        """
    )


def items(keyword: str = "", item_type: str = "전체"):
    params: list[str] = []
    where = ["1 = 1"]

    if keyword:
        where.append("(i.item_code LIKE ? OR i.item_name LIKE ?)")
        params.extend([f"%{keyword}%", f"%{keyword}%"])

    if item_type != "전체":
        where.append("i.item_type = ?")
        params.append(item_type)

    return fetch_dataframe(
        f"""
        SELECT
            i.item_id,
            i.item_code,
            i.item_name,
            i.item_type,
            i.unit,
            i.is_active,
            COUNT(DISTINCT l.lot_id) AS lot_count,
            COUNT(DISTINCT pm.production_material_id) AS material_use_count
        FROM item AS i
        LEFT JOIN lot AS l
            ON i.item_id = l.item_id
        LEFT JOIN production_material AS pm
            ON i.item_id = pm.material_item_id
        WHERE {' AND '.join(where)}
        GROUP BY
            i.item_id,
            i.item_code,
            i.item_name,
            i.item_type,
            i.unit,
            i.is_active
        ORDER BY i.item_type, i.item_code
        """,
        tuple(params),
    )


def item_type_counts():
    return fetch_dataframe(
        """
        SELECT item_type, COUNT(*) AS item_count
        FROM item
        GROUP BY item_type
        ORDER BY item_type
        """
    )


def lots(keyword: str = "", lot_type: str = "전체", item_id: int | None = None):
    params: list[object] = []
    where = ["1 = 1"]

    if keyword:
        where.append("l.lot_no LIKE ?")
        params.append(f"%{keyword}%")

    if lot_type != "전체":
        where.append("l.lot_type = ?")
        params.append(lot_type)

    if item_id:
        where.append("l.item_id = ?")
        params.append(item_id)

    return fetch_dataframe(
        f"""
        SELECT
            l.lot_id,
            l.lot_no,
            i.item_code,
            i.item_name,
            i.item_type,
            l.lot_type,
            l.qty,
            l.received_date,
            l.produced_date,
            l.expire_date
        FROM lot AS l
        JOIN item AS i
            ON l.item_id = i.item_id
        WHERE {' AND '.join(where)}
        ORDER BY
            COALESCE(l.received_date, l.produced_date),
            l.lot_no
        """,
        tuple(params),
    )


def lots_for_select(lot_type: str | None = None):
    params: tuple = ()
    where = ""
    if lot_type:
        where = "WHERE l.lot_type = ?"
        params = (lot_type,)

    return fetch_all(
        f"""
        SELECT
            l.lot_id,
            l.lot_no,
            l.item_id,
            i.item_name,
            l.lot_type,
            l.qty
        FROM lot AS l
        JOIN item AS i
            ON l.item_id = i.item_id
        {where}
        ORDER BY l.lot_no
        """,
        params,
    )


def active_items_for_select(item_type: str | None = None):
    params: tuple = ()
    where = "WHERE is_active = 'Y'"
    if item_type:
        where += " AND item_type = ?"
        params = (item_type,)

    return fetch_all(
        f"""
        SELECT item_id, item_code, item_name, item_type, unit
        FROM item
        {where}
        ORDER BY item_code
        """,
        params,
    )


def productions(keyword: str = "", date_from=None, date_to=None):
    params: list[object] = []
    where = ["1 = 1"]

    if keyword:
        where.append("(p.production_no LIKE ? OR output_lot.lot_no LIKE ? OR product.item_name LIKE ?)")
        params.extend([f"%{keyword}%", f"%{keyword}%", f"%{keyword}%"])

    if date_from:
        where.append("p.production_date >= ?")
        params.append(str(date_from))

    if date_to:
        where.append("p.production_date <= ?")
        params.append(str(date_to))

    return fetch_dataframe(
        f"""
        SELECT
            p.production_id,
            p.production_no,
            p.production_date,
            product.item_code AS product_code,
            product.item_name AS product_name,
            output_lot.lot_no AS output_lot_no,
            p.qty AS production_qty,
            p.status,
            COUNT(pm.production_material_id) AS material_row_count
        FROM production AS p
        JOIN item AS product
            ON p.item_id = product.item_id
        JOIN lot AS output_lot
            ON p.output_lot_id = output_lot.lot_id
        LEFT JOIN production_material AS pm
            ON p.production_id = pm.production_id
        WHERE {' AND '.join(where)}
        GROUP BY
            p.production_id,
            p.production_no,
            p.production_date,
            product.item_code,
            product.item_name,
            output_lot.lot_no,
            p.qty,
            p.status
        ORDER BY p.production_date, p.production_no
        """,
        tuple(params),
    )


def production_materials(production_id: int):
    return fetch_dataframe(
        """
        SELECT
            p.production_no,
            material.item_code AS material_code,
            material.item_name AS material_name,
            material_lot.lot_no AS material_lot_no,
            material_lot.qty AS material_lot_qty,
            pm.qty AS used_qty
        FROM production_material AS pm
        JOIN production AS p
            ON pm.production_id = p.production_id
        JOIN item AS material
            ON pm.material_item_id = material.item_id
        JOIN lot AS material_lot
            ON pm.material_lot_id = material_lot.lot_id
        WHERE pm.production_id = ?
        ORDER BY material.item_code, material_lot.lot_no
        """,
        (production_id,),
    )


def production_detail(production_id: int):
    return fetch_one(
        """
        SELECT
            p.production_id,
            p.production_no,
            p.production_date,
            product.item_code AS product_code,
            product.item_name AS product_name,
            output_lot.lot_no AS output_lot_no,
            output_lot.qty AS output_lot_qty,
            output_lot.expire_date AS output_expire_date,
            p.qty AS production_qty,
            p.status
        FROM production AS p
        JOIN item AS product
            ON p.item_id = product.item_id
        JOIN lot AS output_lot
            ON p.output_lot_id = output_lot.lot_id
        WHERE p.production_id = ?
        """,
        (production_id,),
    )


def forward_trace(material_lot_id: int):
    return fetch_dataframe(
        """
        SELECT
            material_lot.lot_no AS material_lot_no,
            material_item.item_name AS material_name,
            pm.qty AS used_qty,
            p.production_no,
            p.production_date,
            p.qty AS production_qty,
            output_lot.lot_no AS output_lot_no,
            output_item.item_name AS output_item_name,
            output_lot.qty AS output_lot_qty
        FROM production_material AS pm
        JOIN lot AS material_lot
            ON pm.material_lot_id = material_lot.lot_id
        JOIN item AS material_item
            ON pm.material_item_id = material_item.item_id
        JOIN production AS p
            ON pm.production_id = p.production_id
        JOIN lot AS output_lot
            ON p.output_lot_id = output_lot.lot_id
        JOIN item AS output_item
            ON p.item_id = output_item.item_id
        WHERE pm.material_lot_id = ?
        ORDER BY p.production_date, p.production_no
        """,
        (material_lot_id,),
    )


def reverse_trace(output_lot_id: int):
    return fetch_dataframe(
        """
        SELECT
            output_lot.lot_no AS output_lot_no,
            output_item.item_name AS output_item_name,
            p.production_no,
            p.production_date,
            p.qty AS production_qty,
            material_lot.lot_no AS material_lot_no,
            material_item.item_name AS material_name,
            pm.qty AS used_qty,
            material_lot.qty AS material_lot_qty
        FROM production AS p
        JOIN lot AS output_lot
            ON p.output_lot_id = output_lot.lot_id
        JOIN item AS output_item
            ON p.item_id = output_item.item_id
        JOIN production_material AS pm
            ON p.production_id = pm.production_id
        JOIN lot AS material_lot
            ON pm.material_lot_id = material_lot.lot_id
        JOIN item AS material_item
            ON pm.material_item_id = material_item.item_id
        WHERE p.output_lot_id = ?
        ORDER BY material_item.item_code, material_lot.lot_no
        """,
        (output_lot_id,),
    )


def production_by_date():
    return fetch_dataframe(
        """
        SELECT production_date, SUM(qty) AS production_qty, COUNT(*) AS production_count
        FROM production
        GROUP BY production_date
        ORDER BY production_date
        """
    )


def production_by_item():
    return fetch_dataframe(
        """
        SELECT
            i.item_code,
            i.item_name,
            SUM(p.qty) AS production_qty,
            COUNT(*) AS production_count
        FROM production AS p
        JOIN item AS i
            ON p.item_id = i.item_id
        GROUP BY i.item_id, i.item_code, i.item_name
        ORDER BY production_qty DESC, i.item_code
        """
    )


def used_material_lot_counts():
     return fetch_dataframe(
         """
         SELECT
             l.lot_no,
             i.item_name,
             l.lot_type,
             COUNT(pm.production_material_id) AS material_use_count
         FROM lot AS l
         JOIN item AS i
             ON l.item_id = i.item_id
         LEFT JOIN production_material AS pm
             ON l.lot_id = pm.material_lot_id
         GROUP BY l.lot_id, l.lot_no, i.item_name, l.lot_type
         ORDER BY material_use_count DESC, l.lot_no
         """
     )

def lot_use_counts():
    return fetch_dataframe(
        """
        SELECT
            l.lot_no,
            i.item_name,
            l.lot_type,
            COUNT(pm.production_material_id) AS material_use_count
        FROM production_material AS pm
        JOIN lot AS l
            ON pm.material_lot_id = l.lot_id
        JOIN item AS i
            ON l.item_id = i.item_id
        WHERE l.lot_type = 'RECEIPT'
          AND i.item_type = 'MATERIAL'
        GROUP BY l.lot_id, l.lot_no, i.item_name, l.lot_type
        ORDER BY material_use_count DESC, l.lot_no
        """
    )

def material_lots_with_balance():
    return fetch_all(
        """
        SELECT
            l.lot_id,
            l.lot_no,
            l.item_id,
            i.item_name,
            l.qty AS original_qty,
            l.qty - COALESCE(SUM(pm.qty), 0) AS remaining_qty
        FROM lot AS l
        JOIN item AS i ON l.item_id = i.item_id
        LEFT JOIN production_material AS pm ON pm.material_lot_id = l.lot_id
        WHERE l.lot_type = 'RECEIPT'
        GROUP BY l.lot_id, l.lot_no, l.item_id, i.item_name, l.qty
        HAVING remaining_qty > 0
        ORDER BY l.lot_no
        """
    )


def next_id(table_name: str, id_column: str) -> int:
    row = fetch_one(f"SELECT COALESCE(MAX({id_column}), 0) + 1 AS next_id FROM {table_name}")
    return int(row["next_id"])


def lot_no_exists(lot_no: str) -> bool:
    row = fetch_one("SELECT lot_id FROM lot WHERE lot_no = ?", (lot_no,))
    return row is not None


def production_no_exists(production_no: str) -> bool:
    row = fetch_one("SELECT production_id FROM production WHERE production_no = ?", (production_no,))
    return row is not None


def uninspected_lots(lot_type: str | None = None):
    params: list[str] = []
    where = ["insp.inspection_id IS NULL"]

    if lot_type:
        where.append("l.lot_type = ?")
        params.append(lot_type)

    return fetch_all(
        f"""
        SELECT
            l.lot_id,
            l.lot_no,
            l.item_id,
            i.item_name,
            l.lot_type,
            l.qty
        FROM lot AS l
        JOIN item AS i
            ON l.item_id = i.item_id
        LEFT JOIN inspection AS insp
            ON insp.lot_id = l.lot_id
        WHERE {' AND '.join(where)}
        ORDER BY l.lot_no
        """,
        tuple(params),
    )


def inspections(keyword: str = "", result_filter: str = "전체", inspection_type: str = "전체"):
    params: list[str] = []
    where = ["1 = 1"]

    if keyword:
        where.append("(l.lot_no LIKE ? OR i.item_name LIKE ?)")
        params.extend([f"%{keyword}%", f"%{keyword}%"])

    if result_filter != "전체":
        where.append("insp.result = ?")
        params.append(result_filter)

    if inspection_type != "전체":
        where.append("insp.inspection_type = ?")
        params.append(inspection_type)

    return fetch_dataframe(
        f"""
        SELECT
            insp.inspection_id,
            l.lot_no,
            i.item_code,
            i.item_name,
            insp.inspection_type,
            insp.inspection_date,
            insp.checked_qty,
            insp.defect_qty,
            insp.result,
            c.reason_name AS defect_reason_code_name,
            insp.defect_reason
        FROM inspection AS insp
        JOIN lot AS l
            ON insp.lot_id = l.lot_id
        JOIN item AS i
            ON l.item_id = i.item_id
        LEFT JOIN defect_reason_code AS c
            ON insp.reason_code = c.reason_code
        WHERE {' AND '.join(where)}
        ORDER BY insp.inspection_date DESC, insp.inspection_id DESC
        """,
        tuple(params),
    )


def defect_rate_by_item():
    return fetch_dataframe(
        """
        SELECT
            i.item_code,
            i.item_name,
            SUM(insp.checked_qty) AS total_checked_qty,
            SUM(insp.defect_qty) AS total_defect_qty,
            ROUND(SUM(insp.defect_qty) * 100.0 / NULLIF(SUM(insp.checked_qty), 0), 2) AS defect_rate_pct,
            COUNT(*) AS inspection_count
        FROM inspection AS insp
        JOIN lot AS l
            ON insp.lot_id = l.lot_id
        JOIN item AS i
            ON l.item_id = i.item_id
        GROUP BY i.item_id, i.item_code, i.item_name
        ORDER BY defect_rate_pct DESC
        """
    )


def inspection_lot_exists(lot_id: int) -> bool:
    row = fetch_one("SELECT inspection_id FROM inspection WHERE lot_id = ?", (lot_id,))
    return row is not None


def lot_qty(lot_id: int) -> float | None:
    row = fetch_one("SELECT qty FROM lot WHERE lot_id = ?", (lot_id,))
    return float(row["qty"]) if row is not None else None


def active_defect_reason_codes():
    return fetch_all(
        """
        SELECT reason_code, reason_name
        FROM defect_reason_code
        WHERE is_active = 'Y'
        ORDER BY reason_code
        """
    )


def all_defect_reason_codes():
    return fetch_dataframe(
        """
        SELECT reason_code, reason_name, is_active
        FROM defect_reason_code
        ORDER BY reason_code
        """
    )


def defect_reason_code_exists(reason_code: str) -> bool:
    row = fetch_one(
        "SELECT reason_code FROM defect_reason_code WHERE reason_code = ?", (reason_code,)
    )
    return row is not None


def defect_rate_by_reason():
    return fetch_dataframe(
        """
        SELECT
            COALESCE(c.reason_name, '(코드 미지정)') AS reason_name,
            COUNT(*) AS inspection_count,
            SUM(insp.defect_qty) AS total_defect_qty
        FROM inspection AS insp
        LEFT JOIN defect_reason_code AS c
            ON insp.reason_code = c.reason_code
        WHERE insp.defect_qty > 0
        GROUP BY c.reason_code, c.reason_name
        ORDER BY total_defect_qty DESC
        """
    )


def production_plans(keyword: str = "", status_filter: str = "전체"):
    params: list[str] = []
    where = ["1 = 1"]

    if keyword:
        where.append("(p.plan_no LIKE ? OR i.item_name LIKE ?)")
        params.extend([f"%{keyword}%", f"%{keyword}%"])

    if status_filter != "전체":
        where.append("p.status = ?")
        params.append(status_filter)

    return fetch_dataframe(
        f"""
        SELECT
            p.plan_id,
            p.plan_no,
            i.item_code,
            i.item_name,
            p.planned_qty,
            p.plan_date,
            p.status,
            p.linked_production_id
        FROM production_plan AS p
        JOIN item AS i
            ON p.item_id = i.item_id
        WHERE {' AND '.join(where)}
        ORDER BY p.plan_date DESC, p.plan_id DESC
        """,
        tuple(params),
    )


def open_production_plans_for_select():
    return fetch_all(
        """
        SELECT
            p.plan_id,
            p.plan_no,
            p.item_id,
            i.item_name,
            i.item_code,
            p.planned_qty,
            p.plan_date
        FROM production_plan AS p
        JOIN item AS i
            ON p.item_id = i.item_id
        WHERE p.status = 'OPEN'
        ORDER BY p.plan_date, p.plan_no
        """
    )


def plan_no_exists(plan_no: str) -> bool:
    row = fetch_one("SELECT plan_id FROM production_plan WHERE plan_no = ?", (plan_no,))
    return row is not None


def production_plan_by_id(plan_id: int):
    return fetch_one(
        """
        SELECT plan_id, plan_no, item_id, planned_qty, plan_date, status, linked_production_id
        FROM production_plan
        WHERE plan_id = ?
        """,
        (plan_id,),
    )


def user_by_id(user_id: str):
    return fetch_one(
        "SELECT user_id, user_name, password_hash, role, is_active FROM user WHERE user_id = ?",
        (user_id,),
    )


def user_id_exists(user_id: str) -> bool:
    row = fetch_one("SELECT user_id FROM user WHERE user_id = ?", (user_id,))
    return row is not None


def all_users():
    return fetch_dataframe(
        """
        SELECT user_id, user_name, role, is_active
        FROM user
        ORDER BY user_id
        """
    )


def finished_goods_lots_with_balance():
    return fetch_all(
        """
        SELECT
            l.lot_id,
            l.lot_no,
            l.item_id,
            i.item_name,
            l.qty AS original_qty,
            l.qty - COALESCE(SUM(si.qty), 0) AS remaining_qty,
            insp.result AS inspection_result
        FROM lot AS l
        JOIN item AS i
            ON l.item_id = i.item_id
        LEFT JOIN shipment_item AS si
            ON si.lot_id = l.lot_id
        LEFT JOIN inspection AS insp
            ON insp.lot_id = l.lot_id
        WHERE l.lot_type = 'PRODUCTION'
        GROUP BY l.lot_id, l.lot_no, l.item_id, i.item_name, l.qty, insp.result
        HAVING remaining_qty > 0
        ORDER BY l.lot_no
        """
    )


def shipment_no_exists(shipment_no: str) -> bool:
    row = fetch_one("SELECT shipment_id FROM shipment WHERE shipment_no = ?", (shipment_no,))
    return row is not None


def shipments(keyword: str = "", date_from=None, date_to=None):
    params: list[object] = []
    where = ["1 = 1"]

    if keyword:
        where.append("(s.shipment_no LIKE ? OR COALESCE(s.customer_name, '') LIKE ?)")
        params.extend([f"%{keyword}%", f"%{keyword}%"])

    if date_from:
        where.append("s.shipment_date >= ?")
        params.append(str(date_from))

    if date_to:
        where.append("s.shipment_date <= ?")
        params.append(str(date_to))

    return fetch_dataframe(
        f"""
        SELECT
            s.shipment_id,
            s.shipment_no,
            s.customer_name,
            s.shipment_date,
            s.status,
            COUNT(si.shipment_item_id) AS line_count,
            SUM(si.qty) AS total_qty
        FROM shipment AS s
        LEFT JOIN shipment_item AS si
            ON si.shipment_id = s.shipment_id
        WHERE {' AND '.join(where)}
        GROUP BY s.shipment_id, s.shipment_no, s.customer_name, s.shipment_date, s.status
        ORDER BY s.shipment_date DESC, s.shipment_no DESC
        """,
        tuple(params),
    )


def shipment_items(shipment_id: int):
    return fetch_dataframe(
        """
        SELECT
            l.lot_no,
            i.item_code,
            i.item_name,
            si.qty
        FROM shipment_item AS si
        JOIN lot AS l
            ON si.lot_id = l.lot_id
        JOIN item AS i
            ON l.item_id = i.item_id
        WHERE si.shipment_id = ?
        ORDER BY i.item_code, l.lot_no
        """,
        (shipment_id,),
    )


def item_by_id(item_id: int) -> sqlite3.Row | None:
    return fetch_one(
        "SELECT item_id, item_code, item_name, item_type, unit, is_active FROM item WHERE item_id = ?",
        (item_id,),
    )


def item_code_exists(item_code: str) -> bool:
    row = fetch_one("SELECT item_id FROM item WHERE item_code = ?", (item_code,))
    return row is not None


def all_items_for_select():
    return fetch_all(
        """
        SELECT item_id, item_code, item_name, item_type, unit, is_active
        FROM item
        ORDER BY item_type, item_code
        """
    )


def material_stock_summary():
    return fetch_dataframe(
        """
        SELECT
            i.item_id,
            i.item_code,
            i.item_name,
            i.unit,
            COALESCE(receipt.total_qty, 0) AS total_received_qty,
            COALESCE(used.total_qty, 0) AS total_used_qty,
            COALESCE(receipt.total_qty, 0) - COALESCE(used.total_qty, 0) AS remaining_qty
        FROM item AS i
        LEFT JOIN (
            SELECT item_id, SUM(qty) AS total_qty
            FROM lot
            WHERE lot_type = 'RECEIPT'
            GROUP BY item_id
        ) AS receipt ON receipt.item_id = i.item_id
        LEFT JOIN (
            SELECT ml.item_id, SUM(pm.qty) AS total_qty
            FROM production_material AS pm
            JOIN lot AS ml ON pm.material_lot_id = ml.lot_id
            GROUP BY ml.item_id
        ) AS used ON used.item_id = i.item_id
        WHERE i.item_type = 'MATERIAL' AND i.is_active = 'Y'
        ORDER BY i.item_code
        """
    )


def expiring_material_lots(days: int = 30):
    return fetch_dataframe(
        """
        SELECT
            l.lot_no,
            i.item_code,
            i.item_name,
            l.qty - COALESCE(SUM(pm.qty), 0) AS remaining_qty,
            l.expire_date,
            CAST(julianday(l.expire_date) - julianday('now') AS INTEGER) AS days_until_expire
        FROM lot AS l
        JOIN item AS i
            ON l.item_id = i.item_id
        LEFT JOIN production_material AS pm
            ON pm.material_lot_id = l.lot_id
        WHERE l.lot_type = 'RECEIPT'
          AND l.expire_date IS NOT NULL
          AND l.expire_date <= date('now', ?)
        GROUP BY l.lot_id, l.lot_no, i.item_code, i.item_name, l.expire_date
        HAVING remaining_qty > 0
        ORDER BY l.expire_date
        """,
        (f"+{days} day",),
    )
def material_lots_with_balance_for_item(item_id: int):
    return fetch_all(
        """
        SELECT
            l.lot_id,
            l.lot_no,
            l.item_id,
            i.item_name,
            l.qty AS original_qty,
            l.qty - COALESCE(SUM(pm.qty), 0) AS remaining_qty
        FROM lot AS l
        JOIN item AS i ON l.item_id = i.item_id
        LEFT JOIN production_material AS pm ON pm.material_lot_id = l.lot_id
        WHERE l.lot_type = 'RECEIPT' AND l.item_id = ?
        GROUP BY l.lot_id, l.lot_no, l.item_id, i.item_name, l.qty
        HAVING remaining_qty > 0
        ORDER BY l.lot_no
        """,
        (item_id,),
    )


def bom_for_product(product_item_id: int):
    return fetch_dataframe(
        """
        SELECT
            b.bom_id,
            b.material_item_id,
            m.item_code AS material_code,
            m.item_name AS material_name,
            m.unit AS material_unit,
            b.qty_per_unit
        FROM bom AS b
        JOIN item AS m
            ON b.material_item_id = m.item_id
        WHERE b.product_item_id = ?
        ORDER BY m.item_code
        """,
        (product_item_id,),
    )


def bom_for_product_rows(product_item_id: int):
    return fetch_all(
        """
        SELECT material_item_id, qty_per_unit
        FROM bom
        WHERE product_item_id = ?
        ORDER BY material_item_id
        """,
        (product_item_id,),
    )


def products_with_bom_status():
    return fetch_dataframe(
        """
        SELECT
            i.item_id AS product_item_id,
            i.item_code,
            i.item_name,
            COUNT(b.bom_id) AS material_count
        FROM item AS i
        LEFT JOIN bom AS b
            ON i.item_id = b.product_item_id
        WHERE i.item_type = 'PRODUCT'
        GROUP BY i.item_id, i.item_code, i.item_name
        ORDER BY i.item_code
        """
    )


def recent_activity(limit: int = 8):
    return fetch_dataframe(
        """
        SELECT
            'PRODUCTION' AS event_type,
            p.production_no AS ref_no,
            p.production_date AS event_date,
            i.item_name AS item_name,
            p.qty AS qty
        FROM production AS p
        JOIN item AS i ON p.item_id = i.item_id
        UNION ALL
        SELECT
            'RECEIPT' AS event_type,
            l.lot_no AS ref_no,
            l.received_date AS event_date,
            i.item_name AS item_name,
            l.qty AS qty
        FROM lot AS l
        JOIN item AS i ON l.item_id = i.item_id
        WHERE l.lot_type = 'RECEIPT'
        UNION ALL
        SELECT
            'SHIPMENT' AS event_type,
            s.shipment_no AS ref_no,
            s.shipment_date AS event_date,
            COALESCE(s.customer_name, '출하처 미지정') AS item_name,
            (SELECT SUM(qty) FROM shipment_item WHERE shipment_id = s.shipment_id) AS qty
        FROM shipment AS s
        ORDER BY event_date DESC, ref_no DESC
        LIMIT ?
        """,
        (limit,),
    )