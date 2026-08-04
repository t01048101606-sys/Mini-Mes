INSERT INTO item (item_code, item_name, item_type, unit, is_active) VALUES
    ('RM-NOODLE', '면발', 'MATERIAL', 'G', 'Y'),
    ('RM-SOUP', '스프', 'MATERIAL', 'G', 'Y'),
    ('RM-VEG', '건더기', 'MATERIAL', 'G', 'Y');


INSERT INTO item (item_code, item_name, item_type, unit, is_active) VALUES
    ('FG-SHIN', '신라면', 'PRODUCT', 'EA', 'Y');


INSERT INTO bom (product_item_id, material_item_id, qty_per_unit)
SELECT (SELECT item_id FROM item WHERE item_code = 'FG-SHIN'),
       (SELECT item_id FROM item WHERE item_code = 'RM-NOODLE'), 120;

INSERT INTO bom (product_item_id, material_item_id, qty_per_unit)
SELECT (SELECT item_id FROM item WHERE item_code = 'FG-SHIN'),
       (SELECT item_id FROM item WHERE item_code = 'RM-SOUP'), 15;

INSERT INTO bom (product_item_id, material_item_id, qty_per_unit)
SELECT (SELECT item_id FROM item WHERE item_code = 'FG-SHIN'),
       (SELECT item_id FROM item WHERE item_code = 'RM-VEG'), 5;


INSERT INTO defect_reason_code (reason_code, reason_name, is_active) VALUES
    ('PKG_DAMAGE', '포장 손상', 'Y'),
    ('FOREIGN_OBJ', '이물 혼입', 'Y'),
    ('WEIGHT_OUT', '중량 기준 미달/초과', 'Y'),
    ('EXPIRE_MISPRINT', '유효기한 인쇄 오류', 'Y');


INSERT INTO lot (lot_no, item_id, lot_type, qty, received_date)
SELECT 'RM-20260101-0001', item_id, 'RECEIPT', 200000, '2026-01-01'
FROM item WHERE item_code = 'RM-NOODLE';

INSERT INTO lot (lot_no, item_id, lot_type, qty, received_date)
SELECT 'RM-20260101-0002', item_id, 'RECEIPT', 25000, '2026-01-01'
FROM item WHERE item_code = 'RM-SOUP';

INSERT INTO lot (lot_no, item_id, lot_type, qty, received_date)
SELECT 'RM-20260101-0003', item_id, 'RECEIPT', 8000, '2026-01-01'
FROM item WHERE item_code = 'RM-VEG';


INSERT INTO production_plan (plan_no, item_id, planned_qty, plan_date, status)
SELECT 'PLAN-20260102-0001', item_id, 1000, '2026-01-02', 'OPEN'
FROM item WHERE item_code = 'FG-SHIN';


INSERT INTO lot (lot_no, item_id, lot_type, qty, produced_date, expire_date)
SELECT 'FG-20260103-0001', item_id, 'PRODUCTION', 1000, '2026-01-03', '2026-07-03'
FROM item WHERE item_code = 'FG-SHIN';


INSERT INTO production (production_no, item_id, output_lot_id, production_date, qty, status)
SELECT 'PRD-20260103-0001',
       (SELECT item_id FROM item WHERE item_code = 'FG-SHIN'),
       (SELECT lot_id FROM lot WHERE lot_no = 'FG-20260103-0001'),
       '2026-01-03', 1000, 'COMPLETED';

UPDATE production_plan
SET status = 'COMPLETED',
    linked_production_id = (SELECT production_id FROM production WHERE production_no = 'PRD-20260103-0001')
WHERE plan_no = 'PLAN-20260102-0001';


INSERT INTO production_material (production_id, material_item_id, material_lot_id, qty)
SELECT
    (SELECT production_id FROM production WHERE production_no = 'PRD-20260103-0001'),
    (SELECT item_id FROM item WHERE item_code = 'RM-NOODLE'),
    (SELECT lot_id FROM lot WHERE lot_no = 'RM-20260101-0001'),
    120000;

INSERT INTO production_material (production_id, material_item_id, material_lot_id, qty)
SELECT
    (SELECT production_id FROM production WHERE production_no = 'PRD-20260103-0001'),
    (SELECT item_id FROM item WHERE item_code = 'RM-SOUP'),
    (SELECT lot_id FROM lot WHERE lot_no = 'RM-20260101-0002'),
    15000;

INSERT INTO production_material (production_id, material_item_id, material_lot_id, qty)
SELECT
    (SELECT production_id FROM production WHERE production_no = 'PRD-20260103-0001'),
    (SELECT item_id FROM item WHERE item_code = 'RM-VEG'),
    (SELECT lot_id FROM lot WHERE lot_no = 'RM-20260101-0003'),
    5000;


INSERT INTO inspection (lot_id, inspection_type, inspection_date, checked_qty, defect_qty, result)
SELECT lot_id, 'PRODUCTION', '2026-01-03', 1000, 0, 'PASS'
FROM lot WHERE lot_no = 'FG-20260103-0001';


INSERT INTO shipment (shipment_no, customer_name, shipment_date, status)
VALUES ('SHP-20260104-0001', '이마트', '2026-01-04', 'COMPLETED');

INSERT INTO shipment_item (shipment_id, lot_id, qty)
SELECT
    (SELECT shipment_id FROM shipment WHERE shipment_no = 'SHP-20260104-0001'),
    (SELECT lot_id FROM lot WHERE lot_no = 'FG-20260103-0001'),
    700;
