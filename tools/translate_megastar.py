from __future__ import annotations

import csv
import shutil
from pathlib import Path


BASE_DIR = Path(r"C:\Users\wang2\Desktop\智能erp仓管系统\data\raw\megastar")
SOURCE_DIR = BASE_DIR / "extracted"
OUTPUT_DIR = BASE_DIR / "中文数据"

CATEGORY = {
    "Cabinet": "文件柜",
    "Drawer": "抽屉柜",
    "Cupboard": "储物柜",
    "Office Chair": "办公椅",
    "Gaming Chair": "游戏椅",
    "Keyboard": "键盘",
    "Mouse": "鼠标",
    "Laptop": "笔记本电脑",
    "All-in-one": "一体机",
    "Notebook": "笔记本",
    "SPen": "触控笔",
    "Pencil": "铅笔",
    "Printer": "打印机",
    "Table": "桌子",
    "TV": "电视机",
}

FUNCTION = {
    "Filing": "文件收纳",
    "Sliding": "滑动式",
    "Door": "带门式",
    "Locker": "储物锁柜",
    "Leather": "皮革",
    "Adjustable": "可调节",
    "Head pillow": "头枕",
    "Ergonomic": "人体工学",
    "Bluetooth": "蓝牙",
    "Wireled": "有线",
    "Mechanical": "机械式",
    "8GB RAM": "8吉字节内存",
    "16GB RAM": "16吉字节内存",
    "32GB RAM": "32吉字节内存",
    "i5": "第5代处理器",
    "i7": "第7代处理器",
    "dot": "点阵",
    "line": "线条",
    "ruled": "横线",
    "Watercolour": "水彩",
    "Hexagonal": "六角形",
    "Soluble": "可溶性",
    "Wifi": "无线网络",
    "Laser": "激光",
    "Inkjet": "喷墨",
    "Mono": "黑白",
    "All-in-one": "一体式",
    "Auto Adjustable": "自动调节",
    "Workstation": "工作站",
    "Frame": "框架式",
    "FHD": "全高清",
    "4K": "超高清",
    "SFHD": "超级全高清",
    "S4K": "超级超高清",
}

COLOUR = {
    "Black": "黑色",
    "White": "白色",
    "Grey": "灰色",
    "Beige": "米色",
    "Pink": "粉色",
    "Navi": "藏青色",
    "Silver": "银色",
    "Mix": "混合色",
}

SIZE = {
    "A2": "二号纸",
    "A3": "三号纸",
    "A4": "四号纸",
    "A5": "五号纸",
    "L": "大号",
    "M": "中号",
    "S": "小号",
    '14"': "14英寸",
    '15"': "15英寸",
    '17"': "17英寸",
    '32"': "32英寸",
    '42"': "42英寸",
    '50"': "50英寸",
    '65"': "65英寸",
    '75"': "75英寸",
}

STAFF = {
    "Sarah": "莎拉",
    "Emily": "艾米丽",
    "Laura": "劳拉",
    "Chris": "克里斯",
    "Amy": "艾米",
    "Jane": "简",
    "John": "约翰",
    "Mike": "迈克",
    "Alex": "亚历克斯",
    "David": "大卫",
}

# 数据集中的品牌是模拟品牌，不作为业务主键。使用稳定的中文展示名，避免最终文件继续保留英文品牌名。
BRAND_NAMES = {
    name: f"品牌{index:02d}"
    for index, name in enumerate(
        [
            "QEKI", "WENO", "RGAP", "TEWOL", "AEKI", "XENO", "OGAP", "SEWOL",
            "Hcetigol", "Rerar", "Susa", "PH", "Ovonel", "Rezar", "Ynos", "Excercise",
            "Scrap", "Graph", "Music", "Aloyarc", "Gib", "Reldeats", "Nalin", "Rehtorb",
            "Sonac", "Nospe", "CITSATNAF", "TRAMA", "TRAMK", "Gnusmag", "GL", "Esnesih",
        ],
        start=1,
    )
}

COMMON_COLUMNS = {
    "Product": "商品编码",
    "Description": "商品描述",
    "Category": "商品类别",
    "Brand": "品牌",
    "Size": "规格",
    "Function": "功能特征",
    "Colour": "颜色",
    "Pallet": "托盘规格",
    "Quantity": "数量",
    "Location": "库位编码",
    "Staff": "操作员工",
    "From": "来源动作",
    "To": "去向动作",
    "Customer": "客户编号",
    "Task": "作业任务",
}

FILE_NAMES = {
    "Product_list.csv": "商品主数据.csv",
    "dc_locations.csv": "库位数据.csv",
    "list_to_check.csv": "商品校验清单.csv",
    "warehouse_stocks.csv": "仓库库存.csv",
}


def translate_value(column: str, value: str) -> str:
    if column == "Category":
        return CATEGORY.get(value, value)
    if column == "Brand":
        return BRAND_NAMES.get(value, "未命名品牌")
    if column == "Size":
        return SIZE.get(value, value)
    if column == "Function":
        return FUNCTION.get(value, value)
    if column == "Colour":
        return COLOUR.get(value, value)
    if column == "Staff":
        return STAFF.get(value, value)
    if column == "From":
        return {"Receive": "收货"}.get(value, value)
    if column == "To":
        return {"Despatch": "出库"}.get(value, value)
    if column == "Task":
        return {"Put away": "上架", "Pick": "拣货"}.get(value, value)
    return value


def translated_description(row: dict[str, str]) -> str:
    category = translate_value("Category", row.get("Category", ""))
    brand = translate_value("Brand", row.get("Brand", ""))
    size = translate_value("Size", row.get("Size", ""))
    function = translate_value("Function", row.get("Function", ""))
    colour = translate_value("Colour", row.get("Colour", ""))
    details = "、".join(item for item in (size, function, colour) if item)
    return f"{colour} {brand} {size} {category}（{function}）" if details else f"{brand} {category}"


def output_columns(input_columns: list[str]) -> list[str]:
    return [COMMON_COLUMNS[column] for column in input_columns]


def translate_file(source: Path, target: Path) -> None:
    with source.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        columns = reader.fieldnames or []
        rows = []
        for row in reader:
            translated = {}
            for column in columns:
                target_column = COMMON_COLUMNS[column]
                translated[target_column] = (
                    translated_description(row)
                    if column == "Description"
                    else translate_value(column, row.get(column, ""))
                )
            rows.append(translated)

    target.parent.mkdir(parents=True, exist_ok=True)
    with target.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=output_columns(columns), extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    if not SOURCE_DIR.exists():
        raise FileNotFoundError(f"找不到原始数据目录：{SOURCE_DIR}")
    if OUTPUT_DIR.exists():
        shutil.rmtree(OUTPUT_DIR)
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    for source in sorted(SOURCE_DIR.glob("*.csv")):
        target_name = FILE_NAMES.get(source.name)
        if target_name is None and source.name.startswith("receiving_"):
            target_name = source.stem.replace("receiving_", "收货记录_") + ".csv"
        if target_name is None and source.name.startswith("picking_"):
            target_name = source.stem.replace("picking_", "拣货记录_") + ".csv"
        if target_name is None:
            raise ValueError(f"未配置文件名映射：{source.name}")
        translate_file(source, OUTPUT_DIR / target_name)

    # 只校验业务可读字段。商品编码、库位编码、客户编号、任务编号等标识符允许包含英文片段。
    english_words = set(CATEGORY) | set(FUNCTION) | set(COLOUR) | set(STAFF) | {"Receive", "Despatch", "Put away", "Pick"}
    readable_columns = {
        "商品描述", "商品类别", "品牌", "规格", "功能特征", "颜色",
        "操作员工", "来源动作", "去向动作", "作业任务",
    }
    for target in OUTPUT_DIR.glob("*.csv"):
        with target.open("r", encoding="utf-8-sig", newline="") as handle:
            rows = list(csv.DictReader(handle))
            for row in rows:
                for column in readable_columns.intersection(row):
                    value = row[column]
                    for word in english_words:
                        if word in value:
                            raise ValueError(f"文件仍包含英文业务词：{target.name} / {column} -> {word}")

    print(f"已生成 {len(list(OUTPUT_DIR.glob('*.csv')))} 个中文 CSV 文件：{OUTPUT_DIR}")


if __name__ == "__main__":
    main()
