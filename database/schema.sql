SET NAMES utf8mb4;

CREATE DATABASE IF NOT EXISTS erp_wms
  CHARACTER SET utf8mb4
  COLLATE utf8mb4_unicode_ci;

USE erp_wms;

DROP TABLE IF EXISTS stock_ledger;
DROP TABLE IF EXISTS outbound_record;
DROP TABLE IF EXISTS inbound_record;
DROP TABLE IF EXISTS stock_balance;
DROP TABLE IF EXISTS customer;
DROP TABLE IF EXISTS staff;
DROP TABLE IF EXISTS product;
DROP TABLE IF EXISTS warehouse_location;
DROP TABLE IF EXISTS warehouse;
DROP TABLE IF EXISTS data_import_batch;

CREATE TABLE warehouse (
  warehouse_id INT UNSIGNED NOT NULL AUTO_INCREMENT,
  warehouse_code VARCHAR(32) NOT NULL,
  warehouse_name VARCHAR(128) NOT NULL,
  created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (warehouse_id),
  UNIQUE KEY uq_warehouse_code (warehouse_code)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE warehouse_location (
  location_id INT UNSIGNED NOT NULL AUTO_INCREMENT,
  warehouse_id INT UNSIGNED NOT NULL,
  location_code VARCHAR(32) NOT NULL,
  zone_code VARCHAR(8) NOT NULL,
  aisle_code VARCHAR(16) NOT NULL,
  rack_code VARCHAR(16) NOT NULL,
  position_code VARCHAR(8) NOT NULL,
  created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (location_id),
  UNIQUE KEY uq_location_code (location_code),
  KEY idx_warehouse (warehouse_id),
  KEY idx_location_zone (zone_code),
  KEY idx_location_aisle (aisle_code),
  CONSTRAINT fk_location_warehouse
    FOREIGN KEY (warehouse_id) REFERENCES warehouse (warehouse_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE product (
  product_id INT UNSIGNED NOT NULL AUTO_INCREMENT,
  sku_code VARCHAR(160) NOT NULL,
  source_product_code VARCHAR(64) NOT NULL,
  brand VARCHAR(128) NOT NULL,
  product_name VARCHAR(255) NOT NULL,
  category VARCHAR(128) NOT NULL,
  size VARCHAR(128) NOT NULL,
  function_feature VARCHAR(128) NOT NULL,
  color VARCHAR(64) NOT NULL,
  pallet_spec VARCHAR(64) NOT NULL,
  pallet_capacity INT UNSIGNED NOT NULL,
  created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (product_id),
  UNIQUE KEY uq_sku_code (sku_code),
  UNIQUE KEY uq_source_code_brand (source_product_code, brand),
  KEY idx_product_category (category),
  KEY idx_product_brand (brand)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE staff (
  staff_id INT UNSIGNED NOT NULL AUTO_INCREMENT,
  staff_name VARCHAR(64) NOT NULL,
  created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (staff_id),
  UNIQUE KEY uq_staff_name (staff_name)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE customer (
  customer_id INT UNSIGNED NOT NULL AUTO_INCREMENT,
  customer_code VARCHAR(32) NOT NULL,
  customer_name VARCHAR(128) NULL,
  created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (customer_id),
  UNIQUE KEY uq_customer_code (customer_code)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE stock_balance (
  balance_id INT UNSIGNED NOT NULL AUTO_INCREMENT,
  product_id INT UNSIGNED NOT NULL,
  location_id INT UNSIGNED NOT NULL,
  quantity INT UNSIGNED NOT NULL,
  created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (balance_id),
  UNIQUE KEY uq_product_location (product_id, location_id),
  KEY idx_stock_location (location_id),
  CONSTRAINT fk_stock_product
    FOREIGN KEY (product_id) REFERENCES product (product_id),
  CONSTRAINT fk_stock_location
    FOREIGN KEY (location_id) REFERENCES warehouse_location (location_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE inbound_record (
  inbound_id INT UNSIGNED NOT NULL AUTO_INCREMENT,
  product_id INT UNSIGNED NOT NULL,
  location_id INT UNSIGNED NOT NULL,
  staff_id INT UNSIGNED NOT NULL,
  quantity INT UNSIGNED NOT NULL,
  task VARCHAR(64) NOT NULL,
  action VARCHAR(64) NOT NULL,
  source_file VARCHAR(128) NOT NULL,
  source_row INT UNSIGNED NOT NULL,
  source_day TINYINT UNSIGNED NOT NULL,
  created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (inbound_id),
  UNIQUE KEY uq_inbound_source (source_file, source_row),
  KEY idx_inbound_product (product_id),
  KEY idx_inbound_location (location_id),
  KEY idx_inbound_staff (staff_id),
  KEY idx_inbound_day (source_day),
  CONSTRAINT fk_inbound_product
    FOREIGN KEY (product_id) REFERENCES product (product_id),
  CONSTRAINT fk_inbound_location
    FOREIGN KEY (location_id) REFERENCES warehouse_location (location_id),
  CONSTRAINT fk_inbound_staff
    FOREIGN KEY (staff_id) REFERENCES staff (staff_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE outbound_record (
  outbound_id INT UNSIGNED NOT NULL AUTO_INCREMENT,
  product_id INT UNSIGNED NOT NULL,
  location_id INT UNSIGNED NOT NULL,
  staff_id INT UNSIGNED NOT NULL,
  customer_id INT UNSIGNED NOT NULL,
  quantity INT UNSIGNED NOT NULL,
  task VARCHAR(64) NOT NULL,
  action VARCHAR(64) NOT NULL,
  source_file VARCHAR(128) NOT NULL,
  source_row INT UNSIGNED NOT NULL,
  source_day TINYINT UNSIGNED NOT NULL,
  created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (outbound_id),
  UNIQUE KEY uq_outbound_source (source_file, source_row),
  KEY idx_outbound_product (product_id),
  KEY idx_outbound_location (location_id),
  KEY idx_outbound_staff (staff_id),
  KEY idx_outbound_customer (customer_id),
  KEY idx_outbound_day (source_day),
  CONSTRAINT fk_outbound_product
    FOREIGN KEY (product_id) REFERENCES product (product_id),
  CONSTRAINT fk_outbound_location
    FOREIGN KEY (location_id) REFERENCES warehouse_location (location_id),
  CONSTRAINT fk_outbound_staff
    FOREIGN KEY (staff_id) REFERENCES staff (staff_id),
  CONSTRAINT fk_outbound_customer
    FOREIGN KEY (customer_id) REFERENCES customer (customer_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE data_import_batch (
  batch_id INT UNSIGNED NOT NULL AUTO_INCREMENT,
  batch_no VARCHAR(64) NOT NULL,
  dataset_name VARCHAR(128) NOT NULL,
  dataset_version VARCHAR(32) NOT NULL,
  imported_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  total_rows INT UNSIGNED NOT NULL,
  valid_rows INT UNSIGNED NOT NULL,
  invalid_rows INT UNSIGNED NOT NULL,
  status VARCHAR(32) NOT NULL,
  notes TEXT NULL,
  PRIMARY KEY (batch_id),
  UNIQUE KEY uq_batch_no (batch_no)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE stock_ledger (
  ledger_id INT UNSIGNED NOT NULL AUTO_INCREMENT,
  product_id INT UNSIGNED NOT NULL,
  location_id INT UNSIGNED NOT NULL,
  transaction_type VARCHAR(32) NOT NULL,
  quantity_delta INT NOT NULL,
  before_quantity INT NOT NULL,
  after_quantity INT NOT NULL,
  source_type VARCHAR(64) NOT NULL,
  source_id INT UNSIGNED NULL,
  idempotency_key VARCHAR(160) NOT NULL,
  operator_id INT UNSIGNED NULL,
  created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (ledger_id),
  UNIQUE KEY uq_ledger_idempotency (idempotency_key),
  KEY idx_ledger_product (product_id),
  KEY idx_ledger_location (location_id),
  KEY idx_ledger_type (transaction_type),
  CONSTRAINT fk_ledger_product
    FOREIGN KEY (product_id) REFERENCES product (product_id),
  CONSTRAINT fk_ledger_location
    FOREIGN KEY (location_id) REFERENCES warehouse_location (location_id),
  CONSTRAINT fk_ledger_operator
    FOREIGN KEY (operator_id) REFERENCES staff (staff_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
