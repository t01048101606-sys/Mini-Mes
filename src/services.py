from __future__ import annotations

from dataclasses import dataclass
from datetime import date
import sqlite3

from src.db import get_connection
from src.auth import hash_password, verify_password
from src.queries import (
    lot_no_exists,
    production_no_exists,
    material_lots_with_balance,
    inspection_lot_exists,
    lot_qty,
    bom_for_product_rows,
    item_code_exists,
    item_by_id,
    defect_reason_code_exists,
    plan_no_exists,
    production_plan_by_id,
    user_id_exists,
    user_by_id,
    finished_goods_lots_with_balance,
    shipment_no_exists,
)


@dataclass
class ProductionRegistration:
    product_item_id: int
    output_lot_no: str
    production_no: str
    production_date: date
    qty: float
    expire_date: date | None
    material_rows: list[dict]


def validate_registration(data: ProductionRegistration) -> list[str]:
    errors: list[str] = []

    if not data.output_lot_no.strip():
        errors.append("완제품 LOT 번호를 입력하세요.")
    if not data.production_no.strip():
        errors.append("생산번호를 입력하세요.")
    if data.qty <= 0:
        errors.append("생산수량은 0보다 커야 합니다.")
    if not data.material_rows:
        errors.append("투입할 원자재 LOT를 1개 이상 선택하세요.")

    material_lot_ids = [row["material_lot_id"] for row in data.material_rows]
    if len(material_lot_ids) != len(set(material_lot_ids)):
        errors.append("동일한 원자재 LOT를 중복 선택할 수 없습니다.")

    # 잔량 초과 검증 — 검증 시점의 최신 잔량을 다시 조회해서 비교한다.
    balance_by_lot = {row["lot_id"]: row["remaining_qty"] for row in material_lots_with_balance()}
    for row in data.material_rows:
        if row["qty"] <= 0:
            errors.append("원자재 투입수량은 모두 0보다 커야 합니다.")
            continue
        remaining = balance_by_lot.get(row["material_lot_id"])
        if remaining is None:
            errors.append(f"LOT ID {row['material_lot_id']}는 더 이상 사용할 수 없습니다.")
        elif row["qty"] > remaining:
            errors.append(
                f"LOT ID {row['material_lot_id']}의 잔량({remaining:,.0f})보다 "
                f"투입수량({row['qty']:,.0f})이 많습니다."
            )

    if lot_no_exists(data.output_lot_no.strip()):
        errors.append("이미 존재하는 완제품 LOT 번호입니다.")
    if production_no_exists(data.production_no.strip()):
        errors.append("이미 존재하는 생산번호입니다.")

    return errors


def register_production(data: ProductionRegistration) -> dict:
    errors = validate_registration(data)
    if errors:
        raise ValueError("\n".join(errors))

    connection = get_connection()
    try:
        # 잔량 재검증(SELECT)과 실제 저장(INSERT) 사이의 경쟁을 막기 위해
        # 쓰기 트랜잭션을 명시적으로 먼저 연다.
        connection.execute("BEGIN IMMEDIATE")
        cursor = connection.cursor()

        # 트랜잭션 안에서 잔량을 한 번 더 확인 (validate_registration 이후
        # 다른 세션이 먼저 재고를 써버렸을 가능성 차단)
        for row in data.material_rows:
            remaining = cursor.execute(
                """
                SELECT l.qty - COALESCE(SUM(pm.qty), 0)
                FROM lot AS l
                LEFT JOIN production_material AS pm ON pm.material_lot_id = l.lot_id
                WHERE l.lot_id = ?
                GROUP BY l.lot_id, l.qty
                """,
                (row["material_lot_id"],),
            ).fetchone()
            if remaining is None or row["qty"] > remaining[0]:
                raise ValueError(
                    f"LOT ID {row['material_lot_id']}의 재고가 부족합니다. "
                    "다른 작업에서 먼저 사용되었을 수 있습니다."
                )

        cursor.execute(
            """
            INSERT INTO lot (lot_no, item_id, lot_type, qty, received_date, produced_date, expire_date)
            VALUES (?, ?, 'PRODUCTION', ?, NULL, ?, ?)
            """,
            (
                data.output_lot_no.strip(),
                data.product_item_id,
                data.qty,
                str(data.production_date),
                str(data.expire_date) if data.expire_date else None,
            ),
        )
        output_lot_id = cursor.lastrowid

        cursor.execute(
            """
            INSERT INTO production (production_no, item_id, output_lot_id, production_date, qty, status)
            VALUES (?, ?, ?, ?, ?, 'COMPLETED')
            """,
            (
                data.production_no.strip(),
                data.product_item_id,
                output_lot_id,
                str(data.production_date),
                data.qty,
            ),
        )
        production_id = cursor.lastrowid

        for row in data.material_rows:
            cursor.execute(
                """
                INSERT INTO production_material (production_id, material_item_id, material_lot_id, qty)
                VALUES (?, ?, ?, ?)
                """,
                (production_id, row["material_item_id"], row["material_lot_id"], row["qty"]),
            )

        connection.commit()
        return {
            "production_id": production_id,
            "production_no": data.production_no.strip(),
            "output_lot_id": output_lot_id,
            "output_lot_no": data.output_lot_no.strip(),
            "material_count": len(data.material_rows),
        }
    except sqlite3.IntegrityError as exc:
        connection.rollback()
        raise ValueError("데이터베이스 제약조건을 만족하지 못해 저장하지 못했습니다.") from exc
    except sqlite3.OperationalError as exc:
        connection.rollback()
        raise ValueError("다른 작업이 진행 중입니다. 잠시 후 다시 시도해주세요.") from exc
    except ValueError:
        connection.rollback()
        raise
    finally:
        connection.close()


@dataclass
class InspectionRegistration:
    lot_id: int
    inspection_type: str
    inspection_date: date
    checked_qty: float
    defect_qty: float
    result: str
    reason_code: str | None = None
    defect_reason: str | None = None


def validate_inspection(data: InspectionRegistration) -> list[str]:
    errors: list[str] = []

    if data.checked_qty <= 0:
        errors.append("검사수량은 0보다 커야 합니다.")
    if data.defect_qty < 0:
        errors.append("불량수량은 0 이상이어야 합니다.")
    if data.defect_qty > data.checked_qty:
        errors.append("불량수량은 검사수량보다 클 수 없습니다.")

    if data.result not in ("PASS", "FAIL", "PARTIAL"):
        errors.append("검사 결과 값이 올바르지 않습니다.")
    elif data.result == "PASS" and data.defect_qty > 0:
        errors.append("합격(PASS) 판정에는 불량수량이 0이어야 합니다.")
    elif data.result == "FAIL" and data.defect_qty != data.checked_qty:
        errors.append("불합격(FAIL) 판정은 불량수량이 검사수량과 같아야 합니다.")
    elif data.result == "PARTIAL" and not (0 < data.defect_qty < data.checked_qty):
        errors.append("부분불량(PARTIAL) 판정은 불량수량이 0과 검사수량 사이여야 합니다.")

    lot_total_qty = lot_qty(data.lot_id)
    if lot_total_qty is None:
        errors.append("존재하지 않는 LOT입니다.")
    elif data.checked_qty > lot_total_qty:
        errors.append(
            f"검사수량({data.checked_qty:,.0f})이 LOT 수량({lot_total_qty:,.0f})보다 많습니다."
        )

    if inspection_lot_exists(data.lot_id):
        errors.append("이미 검사 이력이 존재하는 LOT입니다.")

    if data.reason_code and not defect_reason_code_exists(data.reason_code):
        errors.append("존재하지 않는 불량 사유 코드입니다.")

    return errors


def register_inspection(data: InspectionRegistration) -> dict:
    errors = validate_inspection(data)
    if errors:
        raise ValueError("\n".join(errors))

    connection = get_connection()
    try:
        # 생산등록과 동일하게 쓰기 트랜잭션을 먼저 열어
        # 검증(SELECT)과 저장(INSERT) 사이의 경쟁을 막는다.
        connection.execute("BEGIN IMMEDIATE")
        cursor = connection.cursor()

        existing = cursor.execute(
            "SELECT inspection_id FROM inspection WHERE lot_id = ?",
            (data.lot_id,),
        ).fetchone()
        if existing is not None:
            raise ValueError(
                "이미 검사 이력이 존재하는 LOT입니다. (다른 작업에서 먼저 등록되었을 수 있습니다.)"
            )

        cursor.execute(
            """
            INSERT INTO inspection
                (lot_id, inspection_type, inspection_date, checked_qty, defect_qty, result, reason_code, defect_reason)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                data.lot_id,
                data.inspection_type,
                str(data.inspection_date),
                data.checked_qty,
                data.defect_qty,
                data.result,
                data.reason_code,
                data.defect_reason,
            ),
        )
        inspection_id = cursor.lastrowid

        connection.commit()
        return {
            "inspection_id": inspection_id,
            "lot_id": data.lot_id,
            "result": data.result,
            "defect_qty": data.defect_qty,
        }
    except sqlite3.IntegrityError as exc:
        connection.rollback()
        raise ValueError("데이터베이스 제약조건을 만족하지 못해 저장하지 못했습니다.") from exc
    except sqlite3.OperationalError as exc:
        connection.rollback()
        raise ValueError("다른 작업이 진행 중입니다. 잠시 후 다시 시도해주세요.") from exc
    except ValueError:
        connection.rollback()
        raise
    finally:
        connection.close()
@dataclass
class BomRow:
    material_item_id: int
    qty_per_unit: float


def validate_bom(product_item_id: int, rows: list[BomRow]) -> list[str]:
    errors: list[str] = []

    if not rows:
        errors.append("BOM에는 원자재를 1개 이상 등록해야 합니다.")

    material_ids = [row.material_item_id for row in rows]
    if len(material_ids) != len(set(material_ids)):
        errors.append("동일한 원자재를 중복 등록할 수 없습니다.")

    for row in rows:
        if row.qty_per_unit <= 0:
            errors.append("단위당 소요량은 모두 0보다 커야 합니다.")
            break

    return errors


def replace_bom(product_item_id: int, rows: list[BomRow]) -> dict:
    """제품의 BOM을 통째로 교체한다 (기존 항목 삭제 후 재삽입)."""
    errors = validate_bom(product_item_id, rows)
    if errors:
        raise ValueError("\n".join(errors))

    connection = get_connection()
    try:
        connection.execute("BEGIN IMMEDIATE")
        cursor = connection.cursor()

        cursor.execute("DELETE FROM bom WHERE product_item_id = ?", (product_item_id,))

        for row in rows:
            cursor.execute(
                """
                INSERT INTO bom (product_item_id, material_item_id, qty_per_unit)
                VALUES (?, ?, ?)
                """,
                (product_item_id, row.material_item_id, row.qty_per_unit),
            )

        connection.commit()
        return {"product_item_id": product_item_id, "material_count": len(rows)}
    except sqlite3.IntegrityError as exc:
        connection.rollback()
        raise ValueError("데이터베이스 제약조건을 만족하지 못해 저장하지 못했습니다.") from exc
    except sqlite3.OperationalError as exc:
        connection.rollback()
        raise ValueError("다른 작업이 진행 중입니다. 잠시 후 다시 시도해주세요.") from exc
    except ValueError:
        connection.rollback()
        raise
    finally:
        connection.close()


@dataclass
class ReceiptRegistration:
    material_item_id: int
    lot_no: str
    received_date: date
    qty: float
    expire_date: date | None = None


def validate_receipt(data: ReceiptRegistration) -> list[str]:
    errors: list[str] = []

    if not data.lot_no.strip():
        errors.append("입고 LOT 번호를 입력하세요.")
    if data.qty <= 0:
        errors.append("입고수량은 0보다 커야 합니다.")
    if data.lot_no.strip() and lot_no_exists(data.lot_no.strip()):
        errors.append("이미 존재하는 LOT 번호입니다.")

    return errors


def register_receipt(data: ReceiptRegistration) -> dict:
    errors = validate_receipt(data)
    if errors:
        raise ValueError("\n".join(errors))

    connection = get_connection()
    try:
        # 생산등록과 동일하게 쓰기 트랜잭션을 먼저 열어
        # 검증(SELECT)과 저장(INSERT) 사이의 경쟁을 막는다.
        connection.execute("BEGIN IMMEDIATE")
        cursor = connection.cursor()

        existing = cursor.execute(
            "SELECT lot_id FROM lot WHERE lot_no = ?", (data.lot_no.strip(),)
        ).fetchone()
        if existing is not None:
            raise ValueError(
                "이미 존재하는 LOT 번호입니다. (다른 작업에서 먼저 등록되었을 수 있습니다.)"
            )

        cursor.execute(
            """
            INSERT INTO lot (lot_no, item_id, lot_type, qty, received_date, produced_date, expire_date)
            VALUES (?, ?, 'RECEIPT', ?, ?, NULL, ?)
            """,
            (
                data.lot_no.strip(),
                data.material_item_id,
                data.qty,
                str(data.received_date),
                str(data.expire_date) if data.expire_date else None,
            ),
        )
        lot_id = cursor.lastrowid

        connection.commit()
        return {
            "lot_id": lot_id,
            "lot_no": data.lot_no.strip(),
            "qty": data.qty,
        }
    except sqlite3.IntegrityError as exc:
        connection.rollback()
        raise ValueError("데이터베이스 제약조건을 만족하지 못해 저장하지 못했습니다.") from exc
    except sqlite3.OperationalError as exc:
        connection.rollback()
        raise ValueError("다른 작업이 진행 중입니다. 잠시 후 다시 시도해주세요.") from exc
    except ValueError:
        connection.rollback()
        raise
    finally:
        connection.close()


@dataclass
class ItemRegistration:
    item_code: str
    item_name: str
    item_type: str
    unit: str


def validate_item_registration(data: ItemRegistration) -> list[str]:
    errors: list[str] = []

    if not data.item_code.strip():
        errors.append("품목 코드를 입력하세요.")
    if not data.item_name.strip():
        errors.append("품목명을 입력하세요.")
    if not data.unit.strip():
        errors.append("단위를 입력하세요.")
    if data.item_type not in ("PRODUCT", "MATERIAL"):
        errors.append("품목 유형이 올바르지 않습니다.")
    if data.item_code.strip() and item_code_exists(data.item_code.strip()):
        errors.append("이미 존재하는 품목 코드입니다.")

    return errors


def register_item(data: ItemRegistration) -> dict:
    errors = validate_item_registration(data)
    if errors:
        raise ValueError("\n".join(errors))

    connection = get_connection()
    try:
        connection.execute("BEGIN IMMEDIATE")
        cursor = connection.cursor()

        existing = cursor.execute(
            "SELECT item_id FROM item WHERE item_code = ?", (data.item_code.strip(),)
        ).fetchone()
        if existing is not None:
            raise ValueError(
                "이미 존재하는 품목 코드입니다. (다른 작업에서 먼저 등록되었을 수 있습니다.)"
            )

        cursor.execute(
            """
            INSERT INTO item (item_code, item_name, item_type, unit, is_active)
            VALUES (?, ?, ?, ?, 'Y')
            """,
            (data.item_code.strip(), data.item_name.strip(), data.item_type, data.unit.strip()),
        )
        item_id = cursor.lastrowid

        connection.commit()
        return {
            "item_id": item_id,
            "item_code": data.item_code.strip(),
            "item_name": data.item_name.strip(),
        }
    except sqlite3.IntegrityError as exc:
        connection.rollback()
        raise ValueError("데이터베이스 제약조건을 만족하지 못해 저장하지 못했습니다.") from exc
    except sqlite3.OperationalError as exc:
        connection.rollback()
        raise ValueError("다른 작업이 진행 중입니다. 잠시 후 다시 시도해주세요.") from exc
    except ValueError:
        connection.rollback()
        raise
    finally:
        connection.close()


@dataclass
class ItemUpdate:
    item_id: int
    item_name: str
    unit: str
    is_active: str


def validate_item_update(data: ItemUpdate) -> list[str]:
    errors: list[str] = []

    if not data.item_name.strip():
        errors.append("품목명을 입력하세요.")
    if not data.unit.strip():
        errors.append("단위를 입력하세요.")
    if data.is_active not in ("Y", "N"):
        errors.append("사용여부 값이 올바르지 않습니다.")
    if item_by_id(data.item_id) is None:
        errors.append("존재하지 않는 품목입니다.")

    return errors


def update_item(data: ItemUpdate) -> dict:
    errors = validate_item_update(data)
    if errors:
        raise ValueError("\n".join(errors))

    connection = get_connection()
    try:
        connection.execute("BEGIN IMMEDIATE")
        cursor = connection.cursor()

        cursor.execute(
            """
            UPDATE item
            SET item_name = ?, unit = ?, is_active = ?
            WHERE item_id = ?
            """,
            (data.item_name.strip(), data.unit.strip(), data.is_active, data.item_id),
        )

        connection.commit()
        return {
            "item_id": data.item_id,
            "item_name": data.item_name.strip(),
            "is_active": data.is_active,
        }
    except sqlite3.IntegrityError as exc:
        connection.rollback()
        raise ValueError("데이터베이스 제약조건을 만족하지 못해 저장하지 못했습니다.") from exc
    except sqlite3.OperationalError as exc:
        connection.rollback()
        raise ValueError("다른 작업이 진행 중입니다. 잠시 후 다시 시도해주세요.") from exc
    except ValueError:
        connection.rollback()
        raise
    finally:
        connection.close()


@dataclass
class DefectReasonCodeRegistration:
    reason_code: str
    reason_name: str


def validate_defect_reason_code(data: DefectReasonCodeRegistration) -> list[str]:
    errors: list[str] = []

    if not data.reason_code.strip():
        errors.append("사유 코드를 입력하세요.")
    if not data.reason_name.strip():
        errors.append("사유명을 입력하세요.")
    if data.reason_code.strip() and defect_reason_code_exists(data.reason_code.strip()):
        errors.append("이미 존재하는 사유 코드입니다.")

    return errors


def register_defect_reason_code(data: DefectReasonCodeRegistration) -> dict:
    errors = validate_defect_reason_code(data)
    if errors:
        raise ValueError("\n".join(errors))

    connection = get_connection()
    try:
        connection.execute("BEGIN IMMEDIATE")
        cursor = connection.cursor()

        existing = cursor.execute(
            "SELECT reason_code FROM defect_reason_code WHERE reason_code = ?",
            (data.reason_code.strip(),),
        ).fetchone()
        if existing is not None:
            raise ValueError("이미 존재하는 사유 코드입니다.")

        cursor.execute(
            """
            INSERT INTO defect_reason_code (reason_code, reason_name, is_active)
            VALUES (?, ?, 'Y')
            """,
            (data.reason_code.strip(), data.reason_name.strip()),
        )

        connection.commit()
        return {"reason_code": data.reason_code.strip(), "reason_name": data.reason_name.strip()}
    except sqlite3.IntegrityError as exc:
        connection.rollback()
        raise ValueError("데이터베이스 제약조건을 만족하지 못해 저장하지 못했습니다.") from exc
    except sqlite3.OperationalError as exc:
        connection.rollback()
        raise ValueError("다른 작업이 진행 중입니다. 잠시 후 다시 시도해주세요.") from exc
    except ValueError:
        connection.rollback()
        raise
    finally:
        connection.close()


def set_defect_reason_code_active(reason_code: str, is_active: str) -> dict:
    if is_active not in ("Y", "N"):
        raise ValueError("사용여부 값이 올바르지 않습니다.")

    connection = get_connection()
    try:
        connection.execute("BEGIN IMMEDIATE")
        cursor = connection.cursor()
        cursor.execute(
            "UPDATE defect_reason_code SET is_active = ? WHERE reason_code = ?",
            (is_active, reason_code),
        )
        connection.commit()
        return {"reason_code": reason_code, "is_active": is_active}
    except sqlite3.OperationalError as exc:
        connection.rollback()
        raise ValueError("다른 작업이 진행 중입니다. 잠시 후 다시 시도해주세요.") from exc
    finally:
        connection.close()


@dataclass
class ProductionPlanRegistration:
    plan_no: str
    item_id: int
    planned_qty: float
    plan_date: date


def validate_production_plan(data: ProductionPlanRegistration) -> list[str]:
    errors: list[str] = []

    if not data.plan_no.strip():
        errors.append("계획번호를 입력하세요.")
    if data.planned_qty <= 0:
        errors.append("계획수량은 0보다 커야 합니다.")
    if data.plan_no.strip() and plan_no_exists(data.plan_no.strip()):
        errors.append("이미 존재하는 계획번호입니다.")

    return errors


def register_production_plan(data: ProductionPlanRegistration) -> dict:
    errors = validate_production_plan(data)
    if errors:
        raise ValueError("\n".join(errors))

    connection = get_connection()
    try:
        connection.execute("BEGIN IMMEDIATE")
        cursor = connection.cursor()

        existing = cursor.execute(
            "SELECT plan_id FROM production_plan WHERE plan_no = ?", (data.plan_no.strip(),)
        ).fetchone()
        if existing is not None:
            raise ValueError("이미 존재하는 계획번호입니다.")

        cursor.execute(
            """
            INSERT INTO production_plan (plan_no, item_id, planned_qty, plan_date, status)
            VALUES (?, ?, ?, ?, 'OPEN')
            """,
            (data.plan_no.strip(), data.item_id, data.planned_qty, str(data.plan_date)),
        )
        plan_id = cursor.lastrowid

        connection.commit()
        return {"plan_id": plan_id, "plan_no": data.plan_no.strip()}
    except sqlite3.IntegrityError as exc:
        connection.rollback()
        raise ValueError("데이터베이스 제약조건을 만족하지 못해 저장하지 못했습니다.") from exc
    except sqlite3.OperationalError as exc:
        connection.rollback()
        raise ValueError("다른 작업이 진행 중입니다. 잠시 후 다시 시도해주세요.") from exc
    except ValueError:
        connection.rollback()
        raise
    finally:
        connection.close()


def cancel_production_plan(plan_id: int) -> dict:
    plan = production_plan_by_id(plan_id)
    if plan is None:
        raise ValueError("존재하지 않는 생산계획입니다.")
    if plan["status"] != "OPEN":
        raise ValueError("진행 중(OPEN)인 계획만 취소할 수 있습니다.")

    connection = get_connection()
    try:
        connection.execute("BEGIN IMMEDIATE")
        cursor = connection.cursor()
        cursor.execute(
            "UPDATE production_plan SET status = 'CANCELED' WHERE plan_id = ? AND status = 'OPEN'",
            (plan_id,),
        )
        if cursor.rowcount == 0:
            raise ValueError("이미 처리된 계획입니다. (다른 작업에서 먼저 변경되었을 수 있습니다.)")
        connection.commit()
        return {"plan_id": plan_id, "status": "CANCELED"}
    except sqlite3.OperationalError as exc:
        connection.rollback()
        raise ValueError("다른 작업이 진행 중입니다. 잠시 후 다시 시도해주세요.") from exc
    except ValueError:
        connection.rollback()
        raise
    finally:
        connection.close()


def complete_production_plan(plan_id: int, production_id: int) -> dict:
    """생산계획을 실제 생산실적과 연결하고 COMPLETED로 표시한다."""
    connection = get_connection()
    try:
        connection.execute("BEGIN IMMEDIATE")
        cursor = connection.cursor()
        cursor.execute(
            """
            UPDATE production_plan
            SET status = 'COMPLETED', linked_production_id = ?
            WHERE plan_id = ? AND status = 'OPEN'
            """,
            (production_id, plan_id),
        )
        connection.commit()
        return {"plan_id": plan_id, "linked_production_id": production_id}
    except sqlite3.OperationalError as exc:
        connection.rollback()
        raise ValueError("다른 작업이 진행 중입니다. 잠시 후 다시 시도해주세요.") from exc
    finally:
        connection.close()


@dataclass
class UserRegistration:
    user_id: str
    user_name: str
    password: str
    role: str


def validate_user_registration(data: UserRegistration) -> list[str]:
    errors: list[str] = []

    if not data.user_id.strip():
        errors.append("아이디를 입력하세요.")
    if not data.user_name.strip():
        errors.append("이름을 입력하세요.")
    if len(data.password) < 4:
        errors.append("비밀번호는 4자 이상이어야 합니다.")
    if data.role not in ("ADMIN", "OPERATOR", "INSPECTOR"):
        errors.append("권한 값이 올바르지 않습니다.")
    if data.user_id.strip() and user_id_exists(data.user_id.strip()):
        errors.append("이미 존재하는 아이디입니다.")

    return errors


def register_user(data: UserRegistration) -> dict:
    errors = validate_user_registration(data)
    if errors:
        raise ValueError("\n".join(errors))

    connection = get_connection()
    try:
        connection.execute("BEGIN IMMEDIATE")
        cursor = connection.cursor()

        existing = cursor.execute(
            "SELECT user_id FROM user WHERE user_id = ?", (data.user_id.strip(),)
        ).fetchone()
        if existing is not None:
            raise ValueError("이미 존재하는 아이디입니다.")

        cursor.execute(
            """
            INSERT INTO user (user_id, user_name, password_hash, role, is_active)
            VALUES (?, ?, ?, ?, 'Y')
            """,
            (
                data.user_id.strip(),
                data.user_name.strip(),
                hash_password(data.password),
                data.role,
            ),
        )

        connection.commit()
        return {"user_id": data.user_id.strip(), "user_name": data.user_name.strip()}
    except sqlite3.IntegrityError as exc:
        connection.rollback()
        raise ValueError("데이터베이스 제약조건을 만족하지 못해 저장하지 못했습니다.") from exc
    except sqlite3.OperationalError as exc:
        connection.rollback()
        raise ValueError("다른 작업이 진행 중입니다. 잠시 후 다시 시도해주세요.") from exc
    except ValueError:
        connection.rollback()
        raise
    finally:
        connection.close()


def set_user_active(user_id: str, is_active: str) -> dict:
    if is_active not in ("Y", "N"):
        raise ValueError("사용여부 값이 올바르지 않습니다.")

    connection = get_connection()
    try:
        connection.execute("BEGIN IMMEDIATE")
        cursor = connection.cursor()
        cursor.execute(
            "UPDATE user SET is_active = ? WHERE user_id = ?", (is_active, user_id)
        )
        connection.commit()
        return {"user_id": user_id, "is_active": is_active}
    except sqlite3.OperationalError as exc:
        connection.rollback()
        raise ValueError("다른 작업이 진행 중입니다. 잠시 후 다시 시도해주세요.") from exc
    finally:
        connection.close()


def authenticate_user(user_id: str, password: str) -> dict | None:
    """아이디/비밀번호가 맞고 활성 상태인 사용자면 정보를 반환하고, 아니면 None."""
    user = user_by_id(user_id.strip())
    if user is None:
        return None
    if user["is_active"] != "Y":
        return None
    if not verify_password(password, user["password_hash"]):
        return None
    return {"user_id": user["user_id"], "user_name": user["user_name"], "role": user["role"]}


@dataclass
class ShipmentRegistration:
    shipment_no: str
    customer_name: str | None
    shipment_date: date
    shipment_rows: list[dict]  # [{"lot_id": int, "qty": float}, ...]


def validate_shipment(data: ShipmentRegistration) -> list[str]:
    errors: list[str] = []

    if not data.shipment_no.strip():
        errors.append("출하번호를 입력하세요.")
    if not data.shipment_rows:
        errors.append("출하할 완제품 LOT를 1개 이상 선택하세요.")

    lot_ids = [row["lot_id"] for row in data.shipment_rows]
    if len(lot_ids) != len(set(lot_ids)):
        errors.append("동일한 LOT를 중복 선택할 수 없습니다.")

    balance_by_lot = {row["lot_id"]: row for row in finished_goods_lots_with_balance()}
    for row in data.shipment_rows:
        if row["qty"] <= 0:
            errors.append("출하수량은 모두 0보다 커야 합니다.")
            continue
        lot_info = balance_by_lot.get(row["lot_id"])
        if lot_info is None:
            errors.append(f"LOT ID {row['lot_id']}는 더 이상 출하할 수 없습니다 (잔량 없음).")
            continue
        if row["qty"] > lot_info["remaining_qty"]:
            errors.append(
                f"{lot_info['lot_no']}의 잔량({lot_info['remaining_qty']:,.0f})보다 "
                f"출하수량({row['qty']:,.0f})이 많습니다."
            )
        if lot_info["inspection_result"] == "FAIL":
            errors.append(f"{lot_info['lot_no']}는 불합격(FAIL) 판정된 LOT라 출하할 수 없습니다.")

    if data.shipment_no.strip() and shipment_no_exists(data.shipment_no.strip()):
        errors.append("이미 존재하는 출하번호입니다.")

    return errors


def register_shipment(data: ShipmentRegistration) -> dict:
    errors = validate_shipment(data)
    if errors:
        raise ValueError("\n".join(errors))

    connection = get_connection()
    try:
        connection.execute("BEGIN IMMEDIATE")
        cursor = connection.cursor()

        existing_no = cursor.execute(
            "SELECT shipment_id FROM shipment WHERE shipment_no = ?",
            (data.shipment_no.strip(),),
        ).fetchone()
        if existing_no is not None:
            raise ValueError("이미 존재하는 출하번호입니다.")

        # 트랜잭션 내에서 잔량과 검사결과를 다시 한 번 확인
        for row in data.shipment_rows:
            check = cursor.execute(
                """
                SELECT
                    l.qty - COALESCE((
                        SELECT SUM(si.qty) FROM shipment_item AS si WHERE si.lot_id = l.lot_id
                    ), 0) AS remaining_qty,
                    (SELECT result FROM inspection WHERE lot_id = l.lot_id) AS inspection_result
                FROM lot AS l
                WHERE l.lot_id = ?
                """,
                (row["lot_id"],),
            ).fetchone()
            if check is None or row["qty"] > check["remaining_qty"]:
                raise ValueError(
                    f"LOT ID {row['lot_id']}의 잔량이 부족합니다. "
                    "다른 작업에서 먼저 사용되었을 수 있습니다."
                )
            if check["inspection_result"] == "FAIL":
                raise ValueError(f"LOT ID {row['lot_id']}는 불합격 판정되어 출하할 수 없습니다.")

        cursor.execute(
            """
            INSERT INTO shipment (shipment_no, customer_name, shipment_date, status)
            VALUES (?, ?, ?, 'COMPLETED')
            """,
            (data.shipment_no.strip(), data.customer_name, str(data.shipment_date)),
        )
        shipment_id = cursor.lastrowid

        for row in data.shipment_rows:
            cursor.execute(
                """
                INSERT INTO shipment_item (shipment_id, lot_id, qty)
                VALUES (?, ?, ?)
                """,
                (shipment_id, row["lot_id"], row["qty"]),
            )

        connection.commit()
        return {
            "shipment_id": shipment_id,
            "shipment_no": data.shipment_no.strip(),
            "line_count": len(data.shipment_rows),
        }
    except sqlite3.IntegrityError as exc:
        connection.rollback()
        raise ValueError("데이터베이스 제약조건을 만족하지 못해 저장하지 못했습니다.") from exc
    except sqlite3.OperationalError as exc:
        connection.rollback()
        raise ValueError("다른 작업이 진행 중입니다. 잠시 후 다시 시도해주세요.") from exc
    except ValueError:
        connection.rollback()
        raise
    finally:
        connection.close()