CREATE TABLE item (
    item_id INTEGER PRIMARY KEY,
    item_code TEXT NOT NULL UNIQUE,
    item_name TEXT NOT NULL,
    item_type TEXT NOT NULL CHECK (item_type IN ('PRODUCT', 'MATERIAL')),
    unit TEXT NOT NULL,
    is_active TEXT NOT NULL DEFAULT 'Y' CHECK (is_active IN ('Y', 'N'))
);

CREATE TABLE lot (
    lot_id INTEGER PRIMARY KEY,
    lot_no TEXT NOT NULL UNIQUE,
    item_id INTEGER NOT NULL,
    lot_type TEXT NOT NULL CHECK (lot_type IN ('RECEIPT', 'PRODUCTION')),
    qty REAL NOT NULL CHECK (qty >= 0),
    received_date TEXT,
    produced_date TEXT,
    expire_date TEXT,
    FOREIGN KEY (item_id) REFERENCES item (item_id)
);

CREATE TABLE production (
    production_id INTEGER PRIMARY KEY,
    production_no TEXT NOT NULL UNIQUE,
    item_id INTEGER NOT NULL,
    output_lot_id INTEGER NOT NULL UNIQUE,
    production_date TEXT NOT NULL,
    qty REAL NOT NULL CHECK (qty > 0),
    status TEXT NOT NULL CHECK (status IN ('PLANNED', 'COMPLETED', 'CANCELED')),
    FOREIGN KEY (item_id) REFERENCES item (item_id),
    FOREIGN KEY (output_lot_id) REFERENCES lot (lot_id)
);

CREATE TABLE production_material (
    production_material_id INTEGER PRIMARY KEY,
    production_id INTEGER NOT NULL,
    material_item_id INTEGER NOT NULL,
    material_lot_id INTEGER NOT NULL,
    qty REAL NOT NULL CHECK (qty > 0),
    FOREIGN KEY (production_id) REFERENCES production (production_id),
    FOREIGN KEY (material_item_id) REFERENCES item (item_id),
    FOREIGN KEY (material_lot_id) REFERENCES lot (lot_id)
);

CREATE TABLE bom (
    bom_id INTEGER PRIMARY KEY,
    product_item_id INTEGER NOT NULL,
    material_item_id INTEGER NOT NULL,
    qty_per_unit REAL NOT NULL CHECK (qty_per_unit > 0),
    UNIQUE (product_item_id, material_item_id),
    FOREIGN KEY (product_item_id) REFERENCES item (item_id),
    FOREIGN KEY (material_item_id) REFERENCES item (item_id)
);

CREATE TABLE defect_reason_code (
    reason_code TEXT PRIMARY KEY,
    reason_name TEXT NOT NULL,
    is_active TEXT NOT NULL DEFAULT 'Y' CHECK (is_active IN ('Y', 'N'))
);

CREATE TABLE inspection (
    inspection_id INTEGER PRIMARY KEY,
    lot_id INTEGER NOT NULL UNIQUE,
    inspection_type TEXT NOT NULL CHECK (inspection_type IN ('RECEIPT', 'PRODUCTION')),
    inspection_date TEXT NOT NULL,
    checked_qty REAL NOT NULL CHECK (checked_qty >= 0),
    defect_qty REAL NOT NULL DEFAULT 0 CHECK (defect_qty >= 0),
    result TEXT NOT NULL CHECK (result IN ('PASS', 'FAIL', 'PARTIAL')),
    defect_reason TEXT,
    reason_code TEXT REFERENCES defect_reason_code (reason_code),
    FOREIGN KEY (lot_id) REFERENCES lot (lot_id)
);

CREATE TABLE production_plan (
    plan_id INTEGER PRIMARY KEY,
    plan_no TEXT NOT NULL UNIQUE,
    item_id INTEGER NOT NULL,
    planned_qty REAL NOT NULL CHECK (planned_qty > 0),
    plan_date TEXT NOT NULL,
    status TEXT NOT NULL CHECK (status IN ('OPEN', 'COMPLETED', 'CANCELED')) DEFAULT 'OPEN',
    linked_production_id INTEGER,
    FOREIGN KEY (item_id) REFERENCES item (item_id),
    FOREIGN KEY (linked_production_id) REFERENCES production (production_id)
);

CREATE TABLE user (
    user_id TEXT PRIMARY KEY,
    user_name TEXT NOT NULL,
    password_hash TEXT NOT NULL,
    role TEXT NOT NULL CHECK (role IN ('ADMIN', 'OPERATOR', 'INSPECTOR')),
    is_active TEXT NOT NULL DEFAULT 'Y' CHECK (is_active IN ('Y', 'N'))
);

CREATE TABLE shipment (
    shipment_id INTEGER PRIMARY KEY,
    shipment_no TEXT NOT NULL UNIQUE,
    customer_name TEXT,
    shipment_date TEXT NOT NULL,
    status TEXT NOT NULL CHECK (status IN ('COMPLETED', 'CANCELED')) DEFAULT 'COMPLETED'
);

CREATE TABLE shipment_item (
    shipment_item_id INTEGER PRIMARY KEY,
    shipment_id INTEGER NOT NULL,
    lot_id INTEGER NOT NULL,
    qty REAL NOT NULL CHECK (qty > 0),
    FOREIGN KEY (shipment_id) REFERENCES shipment (shipment_id),
    FOREIGN KEY (lot_id) REFERENCES lot (lot_id)
);
