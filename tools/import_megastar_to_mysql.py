from __future__ import annotations

import json
import re
from pathlib import Path

import pandas as pd


BASE_DIR = Path(__file__).resolve().parents[1]
DATA_DIR = BASE_DIR / "data" / "raw" / "megastar" / "中文数据"
OUTPUT_FILE = BASE_DIR / "database" / "megastar_import.sql"
REPORT_FILE = BASE_DIR / "database" / "import_report.json"

BATCH_SIZE = 500


def read_csv(name: str) -> pd.DataFrame:
    path = DATA_DIR / name
    if not path.exists():
        raise FileNotFoundError(f"找不到数据文件：{path}")
    return pd.read_csv(path, dtype=str, keep_default_na=False)


def clean_text(value: object) -> str:
    return str(value).strip()


def to_positive_int(value: object, field: str, source: str) -> int:
    text = clean_text(value)
    try:
        number = int(float(text))
    except ValueError as exc:
        raise ValueError(f"{source} 的 {field} 不是有效数字：{text}") from exc
    if number <= 0:
        raise ValueError(f"{source} 的 {field} 必须大于 0：{text}")
    return number


def sql_text(value: object) -> str:
    if value is None:
        return "NULL"
    text = clean_text(value)
    if text == "":
        return "NULL"
    return "'" + text.replace("\\", "\\\\").replace("'", "''") + "'"


def sql_number(value: object) -> str:
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return "NULL"
    return str(int(value))


def insert_sql(
    table: str,
    columns: list[str],
    rows: list[tuple[object, ...]],
    batch_size: int = BATCH_SIZE,
) -> list[str]:
    if not rows:
        return []

    lines: list[str] = []
    column_sql = ", ".join(columns)
    for start in range(0, len(rows), batch_size):
        batch = rows[start : start + batch_size]
        values = []
        for row in batch:
            rendered = []
            for value in row:
                if isinstance(value, (int, float)) and not isinstance(value, bool):
                    rendered.append(sql_number(value))
                else:
                    rendered.append(sql_text(value))
            values.append("(" + ", ".join(rendered) + ")")
        lines.append(
            f"INSERT INTO {table} ({column_sql}) VALUES\n  " + ",\n  ".join(values) + ";"
        )
    return lines


def build_location_dataframe() -> pd.DataFrame:
    df = read_csv("库位数据.csv")
    df["库位编码"] = df["库位编码"].map(clean_text)
    if df["库位编码"].duplicated().any():
        duplicate = df.loc[df["库位编码"].duplicated(), "库位编码"].iloc[0]
        raise ValueError(f"库位编码重复：{duplicate}")
    if not (df["库位编码"].str.len() == 5).all():
        raise ValueError("存在非 5 位库位编码，无法解析库区/巷道/货架/储位")

    df["库区编码"] = df["库位编码"].str[0]
    df["巷道编码"] = df["库位编码"].str[:2]
    df["货架编码"] = df["库位编码"].str[:4]
    df["储位编码"] = df["库位编码"].str[4]
    df = df.sort_values("库位编码").reset_index(drop=True)
    df["location_id"] = df.index + 1
    return df


def build_product_dataframe() -> pd.DataFrame:
    df = read_csv("商品主数据.csv")
    text_columns = [
        "商品编码", "商品描述", "商品类别", "品牌", "规格",
        "功能特征", "颜色", "托盘规格", "数量",
    ]
    for column in text_columns:
        df[column] = df[column].map(clean_text)

    key_columns = ["商品编码", "品牌"]
    if df[key_columns].duplicated().any():
        duplicated = df.loc[df.duplicated(key_columns, keep=False), key_columns]
        raise ValueError(f"商品编码 + 品牌仍然重复：\n{duplicated.to_string(index=False)}")

    df["托盘容量"] = df.apply(
        lambda row: to_positive_int(row["数量"], "数量", "商品主数据"),
        axis=1,
    )
    df["SKU编码"] = "MS-" + df["商品编码"] + "-" + df["品牌"]
    df = df.sort_values(["商品编码", "品牌"]).reset_index(drop=True)
    df["product_id"] = df.index + 1
    return df


def build_staff_dataframe(inbound: pd.DataFrame, outbound: pd.DataFrame) -> pd.DataFrame:
    names = sorted(set(inbound["操作员工"]) | set(outbound["操作员工"]))
    df = pd.DataFrame({"员工姓名": names})
    df["staff_id"] = df.index + 1
    return df


def build_customer_dataframe(outbound: pd.DataFrame) -> pd.DataFrame:
    codes = sorted(outbound["客户编号"].drop_duplicates().tolist())
    df = pd.DataFrame({"客户编号": codes})
    df["customer_id"] = df.index + 1
    return df


def load_inbound_files() -> pd.DataFrame:
    frames = []
    for day in range(1, 6):
        filename = f"收货记录_{day}.csv"
        df = read_csv(filename)
        df["来源文件"] = filename
        df["来源行号"] = range(1, len(df) + 1)
        df["来源天"] = day
        frames.append(df)
    return pd.concat(frames, ignore_index=True)


def load_outbound_files() -> pd.DataFrame:
    frames = []
    for day in range(1, 6):
        filename = f"拣货记录_{day}.csv"
        df = read_csv(filename)
        df["来源文件"] = filename
        df["来源行号"] = range(1, len(df) + 1)
        df["来源天"] = day
        frames.append(df)
    return pd.concat(frames, ignore_index=True)


def clean_common_columns(df: pd.DataFrame) -> pd.DataFrame:
    columns = [
        "商品编码", "商品描述", "商品类别", "品牌", "规格",
        "功能特征", "颜色", "托盘规格", "数量", "库位编码",
        "操作员工", "来源文件", "作业任务",
    ]
    for column in columns:
        if column in df.columns:
            df[column] = df[column].map(clean_text)
    return df


def validate_product_attributes(
    df: pd.DataFrame,
    product: pd.DataFrame,
    name: str,
) -> None:
    columns = [
        "商品编码", "品牌", "商品描述", "商品类别", "规格",
        "功能特征", "颜色", "托盘规格",
    ]
    merged = df[columns].merge(
        product[columns],
        on=columns,
        how="left",
        indicator=True,
    )
    missing = int((merged["_merge"] == "left_only").sum())
    if missing:
        raise ValueError(f"{name} 有 {missing} 行无法匹配商品主数据属性")


def main() -> None:
    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)

    locations = build_location_dataframe()
    products = build_product_dataframe()
    inbound_raw = load_inbound_files()
    outbound_raw = load_outbound_files()
    inbound_raw = clean_common_columns(inbound_raw)
    outbound_raw = clean_common_columns(outbound_raw)

    inbound_raw["来源动作"] = inbound_raw["来源动作"].map(clean_text)
    outbound_raw["去向动作"] = outbound_raw["去向动作"].map(clean_text)
    outbound_raw["客户编号"] = outbound_raw["客户编号"].map(clean_text)

    staff = build_staff_dataframe(inbound_raw, outbound_raw)
    customers = build_customer_dataframe(outbound_raw)

    validate_product_attributes(inbound_raw, products, "收货记录")
    validate_product_attributes(outbound_raw, products, "拣货记录")

    product_key = products[["product_id", "商品编码", "品牌"]]
    location_key = locations[["location_id", "库位编码"]]
    staff_key = staff[["staff_id", "员工姓名"]]
    customer_key = customers[["customer_id", "客户编号"]]

    stock = read_csv("仓库库存.csv")
    stock = clean_common_columns(stock)
    validate_product_attributes(stock, products, "仓库库存")
    stock = stock.merge(product_key, on=["商品编码", "品牌"], how="left", validate="many_to_one")
    stock = stock.merge(location_key, on="库位编码", how="left", validate="many_to_one")
    if stock[["product_id", "location_id"]].isna().any().any():
        raise ValueError("仓库库存存在无法匹配的商品或库位")
    if stock.duplicated(["product_id", "location_id"]).any():
        raise ValueError("仓库库存存在重复的商品 + 库位组合")
    stock["库存数量"] = stock.apply(
        lambda row: to_positive_int(row["数量"], "数量", "仓库库存"),
        axis=1,
    )

    inbound = inbound_raw.merge(
        product_key,
        on=["商品编码", "品牌"],
        how="left",
        validate="many_to_one",
    ).merge(
        location_key,
        on="库位编码",
        how="left",
        validate="many_to_one",
    ).merge(
        staff_key,
        left_on="操作员工",
        right_on="员工姓名",
        how="left",
        validate="many_to_one",
    )
    if inbound[["product_id", "location_id", "staff_id"]].isna().any().any():
        raise ValueError("收货记录存在无法匹配的商品、库位或员工")
    inbound["收货数量"] = inbound.apply(
        lambda row: to_positive_int(row["数量"], "数量", row["来源文件"]),
        axis=1,
    )

    outbound = outbound_raw.merge(
        product_key,
        on=["商品编码", "品牌"],
        how="left",
        validate="many_to_one",
    ).merge(
        location_key,
        on="库位编码",
        how="left",
        validate="many_to_one",
    ).merge(
        staff_key,
        left_on="操作员工",
        right_on="员工姓名",
        how="left",
        validate="many_to_one",
    ).merge(
        customer_key,
        on="客户编号",
        how="left",
        validate="many_to_one",
    )
    if outbound[["product_id", "location_id", "staff_id", "customer_id"]].isna().any().any():
        raise ValueError("拣货记录存在无法匹配的商品、库位、员工或客户")
    outbound["拣货数量"] = outbound.apply(
        lambda row: to_positive_int(row["数量"], "数量", row["来源文件"]),
        axis=1,
    )

    warehouse_rows = [
        (1, "MEGA", "Mega Star 配送中心"),
    ]
    location_rows = [
        (row.location_id, 1, row.库位编码, row.库区编码, row.巷道编码, row.货架编码, row.储位编码)
        for row in locations.itertuples(index=False)
    ]
    product_rows = [
        (
            row.product_id,
            row.SKU编码,
            row.商品编码,
            row.品牌,
            row.商品描述,
            row.商品类别,
            row.规格,
            row.功能特征,
            row.颜色,
            row.托盘规格,
            row.托盘容量,
        )
        for row in products.itertuples(index=False)
    ]
    staff_rows = [(row.staff_id, row.员工姓名) for row in staff.itertuples(index=False)]
    customer_rows = [(row.customer_id, row.客户编号, None) for row in customers.itertuples(index=False)]
    stock_rows = [
        (int(row.product_id), int(row.location_id), int(row.库存数量))
        for row in stock.itertuples(index=False)
    ]
    inbound_rows = [
        (
            int(row.product_id),
            int(row.location_id),
            int(row.staff_id),
            int(row.收货数量),
            row.作业任务,
            row.来源动作,
            row.来源文件,
            int(row.来源行号),
            int(row.来源天),
        )
        for row in inbound.itertuples(index=False)
    ]
    outbound_rows = [
        (
            int(row.product_id),
            int(row.location_id),
            int(row.staff_id),
            int(row.customer_id),
            int(row.拣货数量),
            row.作业任务,
            row.去向动作,
            row.来源文件,
            int(row.来源行号),
            int(row.来源天),
        )
        for row in outbound.itertuples(index=False)
    ]

    total_rows = (
        len(products) + len(locations) + len(staff) + len(customers)
        + len(stock) + len(inbound) + len(outbound)
    )
    batch_rows = [
        (
            "MEGASTAR-20260908-001",
            "Mega Star Distribution Centre",
            "1.0",
            total_rows,
            total_rows,
            0,
            "IMPORTED",
            "商品唯一键为源商品编码+品牌；商品主数据数量映射为托盘容量；历史收货和拣货不写入库存流水。",
        )
    ]

    sql_lines = [
        "SET NAMES utf8mb4;",
        "USE erp_wms;",
        "START TRANSACTION;",
    ]
    sql_lines.extend(
        insert_sql(
            "warehouse",
            ["warehouse_id", "warehouse_code", "warehouse_name"],
            warehouse_rows,
        )
    )
    sql_lines.extend(
        insert_sql(
            "warehouse_location",
            [
                "location_id", "warehouse_id", "location_code", "zone_code",
                "aisle_code", "rack_code", "position_code",
            ],
            location_rows,
        )
    )
    sql_lines.extend(
        insert_sql(
            "product",
            [
                "product_id", "sku_code", "source_product_code", "brand",
                "product_name", "category", "size", "function_feature", "color",
                "pallet_spec", "pallet_capacity",
            ],
            product_rows,
        )
    )
    sql_lines.extend(insert_sql("staff", ["staff_id", "staff_name"], staff_rows))
    sql_lines.extend(
        insert_sql(
            "customer",
            ["customer_id", "customer_code", "customer_name"],
            customer_rows,
        )
    )
    sql_lines.extend(
        insert_sql(
            "stock_balance",
            ["product_id", "location_id", "quantity"],
            stock_rows,
        )
    )
    sql_lines.extend(
        insert_sql(
            "inbound_record",
            [
                "product_id", "location_id", "staff_id", "quantity",
                "task", "action", "source_file", "source_row", "source_day",
            ],
            inbound_rows,
        )
    )
    sql_lines.extend(
        insert_sql(
            "outbound_record",
            [
                "product_id", "location_id", "staff_id", "customer_id",
                "quantity", "task", "action", "source_file", "source_row",
                "source_day",
            ],
            outbound_rows,
        )
    )
    sql_lines.extend(
        insert_sql(
            "data_import_batch",
            [
                "batch_no", "dataset_name", "dataset_version", "total_rows",
                "valid_rows", "invalid_rows", "status", "notes",
            ],
            batch_rows,
            batch_size=1,
        )
    )
    sql_lines.append("COMMIT;")

    OUTPUT_FILE.write_text("\n".join(sql_lines) + "\n", encoding="utf-8")

    report = {
        "warehouse": len(warehouse_rows),
        "warehouse_location": len(location_rows),
        "product": len(product_rows),
        "staff": len(staff_rows),
        "customer": len(customer_rows),
        "stock_balance": len(stock_rows),
        "inbound_record": len(inbound_rows),
        "outbound_record": len(outbound_rows),
        "total_rows": total_rows,
        "validation": {
            "product_unique_key": "source_product_code + brand",
            "product_master_quantity_meaning": "pallet_capacity",
            "stock_quantity_meaning": "actual unit quantity",
            "transaction_quantity_meaning": "actual unit quantity",
            "historical_transactions_write_stock_ledger": False,
        },
    }
    REPORT_FILE.write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
