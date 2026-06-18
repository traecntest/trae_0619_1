"""
示例数据生成器
生成各审计模块的测试数据
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import os
from config import DATA_DIR


def generate_procurement_data(n_records: int = 500, seed: int = 42) -> pd.DataFrame:
    """生成采购审计示例数据"""
    np.random.seed(seed)

    materials = ['钢材A', '钢材B', '塑料原料', '电子元件A', '电子元件B',
                 '包装材料', '润滑油', '轴承', '密封圈', '电机']
    suppliers = ['供应商甲', '供应商乙', '供应商丙', '供应商丁', '供应商戊',
                 '供应商己', '供应商庚', '供应商辛']
    departments = ['采购一部', '采购二部', '采购三部']
    buyers = ['张三', '李四', '王五', '赵六', '钱七']

    base_prices = {
        '钢材A': 5800,
        '钢材B': 4200,
        '塑料原料': 8500,
        '电子元件A': 120,
        '电子元件B': 280,
        '包装材料': 15,
        '润滑油': 320,
        '轴承': 180,
        '密封圈': 25,
        '电机': 2500
    }

    start_date = datetime(2024, 1, 1)
    end_date = datetime(2024, 12, 31)
    date_range = (end_date - start_date).days

    data = []
    for i in range(n_records):
        material = np.random.choice(materials)
        supplier = np.random.choice(suppliers)
        base_price = base_prices[material]

        price_variation = np.random.normal(0, 0.08)
        if np.random.random() < 0.05:
            price_variation += np.random.choice([-0.25, 0.25])

        unit_price = round(base_price * (1 + price_variation), 2)
        quantity = int(np.random.exponential(100)) + 1
        amount = round(unit_price * quantity, 2)

        if np.random.random() < 0.03:
            amount = round(amount / 1000) * 1000
            unit_price = round(amount / quantity, 2) if quantity > 0 else unit_price

        random_days = np.random.randint(0, date_range)
        purchase_date = start_date + timedelta(days=random_days)

        data.append({
            '采购单号': f'CG{2024}{i+1:06d}',
            '供应商': supplier,
            '物料名称': material,
            '物料编码': f'MAT{materials.index(material)+1:03d}',
            '采购数量': quantity,
            '单价': unit_price,
            '采购金额': amount,
            '采购日期': purchase_date.strftime('%Y-%m-%d'),
            '采购部门': np.random.choice(departments),
            '采购员': np.random.choice(buyers),
            '备注': ''
        })

    df = pd.DataFrame(data)

    top_supplier = '供应商甲'
    top_materials = ['钢材A', '钢材B']
    mask = (df['物料名称'].isin(top_materials)) & (df['供应商'] == top_supplier)
    df.loc[mask, '采购金额'] = df.loc[mask, '采购金额'] * 1.5
    df.loc[mask, '单价'] = df.loc[mask, '采购金额'] / df.loc[mask, '采购数量']

    return df


def generate_sales_data(n_records: int = 800, seed: int = 42) -> pd.DataFrame:
    """生成销售审计示例数据"""
    np.random.seed(seed)

    products = ['产品A', '产品B', '产品C', '产品D', '产品E', '产品F']
    customers = ['客户001', '客户002', '客户003', '客户004', '客户005',
                 '客户006', '客户007', '客户008', '客户009', '客户010',
                 '客户011', '客户012', '客户013', '客户014', '客户015']
    salespeople = ['销售甲', '销售乙', '销售丙', '销售丁', '销售戊']
    departments = ['销售一部', '销售二部', '销售三部']

    base_prices = {
        '产品A': 1200,
        '产品B': 850,
        '产品C': 2300,
        '产品D': 560,
        '产品E': 1800,
        '产品F': 3200
    }

    credit_limits = {
        '客户001': 500000,
        '客户002': 300000,
        '客户003': 800000,
        '客户004': 200000,
        '客户005': 400000,
        '客户006': 150000,
        '客户007': 600000,
        '客户008': 250000,
        '客户009': 350000,
        '客户010': 100000,
        '客户011': 450000,
        '客户012': 180000,
        '客户013': 700000,
        '客户014': 220000,
        '客户015': 380000
    }

    start_date = datetime(2024, 1, 1)
    end_date = datetime(2024, 12, 31)
    date_range = (end_date - start_date).days

    data = []
    for i in range(n_records):
        product = np.random.choice(products)
        customer = np.random.choice(customers)
        base_price = base_prices[product]

        discount_rate = np.abs(np.random.normal(0.05, 0.08))
        discount_rate = min(discount_rate, 0.5)

        if np.random.random() < 0.03:
            discount_rate = np.random.uniform(0.35, 0.55)

        unit_price = round(base_price * (1 - discount_rate), 2)
        quantity = int(np.random.exponential(50)) + 1
        original_amount = round(base_price * quantity, 2)
        discount_amount = round(original_amount - unit_price * quantity, 2)
        sales_amount = original_amount - discount_amount

        is_return = np.random.random() < 0.08
        return_qty = int(quantity * np.random.uniform(0.1, 0.5)) if is_return else 0

        random_days = np.random.randint(0, date_range)
        sale_date = start_date + timedelta(days=random_days)

        receivable_days = int(np.random.exponential(45))
        receivable_date = sale_date + timedelta(days=receivable_days)

        actual_pay_days = receivable_days + int(np.random.normal(0, 15))
        if np.random.random() < 0.1:
            actual_pay_days += int(np.random.uniform(30, 90))
        actual_pay_date = sale_date + timedelta(days=actual_pay_days) if actual_pay_days > 0 else None

        data.append({
            '销售单号': f'XS{2024}{i+1:06d}',
            '客户名称': customer,
            '产品名称': product,
            '产品编码': f'PRD{products.index(product)+1:03d}',
            '销售数量': quantity,
            '单价': unit_price,
            '销售金额': sales_amount,
            '折扣金额': discount_amount,
            '折扣率': round(discount_rate, 4),
            '信用额度': credit_limits[customer],
            '销售日期': sale_date.strftime('%Y-%m-%d'),
            '应回款日期': receivable_date.strftime('%Y-%m-%d'),
            '实际回款日期': actual_pay_date.strftime('%Y-%m-%d') if actual_pay_date else '',
            '销售部门': np.random.choice(departments),
            '销售员': np.random.choice(salespeople),
            '是否退货': '是' if is_return else '否',
            '退货数量': return_qty,
            '备注': ''
        })

    df = pd.DataFrame(data)
    return df


def generate_production_data(n_records: int = 300, seed: int = 42) -> pd.DataFrame:
    """生成生产审计示例数据"""
    np.random.seed(seed)

    products = ['产品A', '产品B', '产品C', '产品D']
    materials = ['原料1', '原料2', '原料3', '原料4', '原料5']
    workshops = ['一车间', '二车间', '三车间']
    teams = ['甲班', '乙班', '丙班']

    material_standards = {
        ('产品A', '原料1'): 2.5,
        ('产品A', '原料2'): 1.2,
        ('产品A', '原料3'): 0.8,
        ('产品B', '原料1'): 1.8,
        ('产品B', '原料2'): 2.0,
        ('产品B', '原料4'): 1.5,
        ('产品C', '原料2'): 3.0,
        ('产品C', '原料3'): 1.5,
        ('产品C', '原料5'): 0.5,
        ('产品D', '原料1'): 1.0,
        ('产品D', '原料4'): 2.5,
        ('产品D', '原料5'): 1.0,
    }

    start_date = datetime(2024, 1, 1)
    end_date = datetime(2024, 12, 31)
    date_range = (end_date - start_date).days

    data = []
    for i in range(n_records):
        product = np.random.choice(products)
        workshop = np.random.choice(workshops)
        team = np.random.choice(teams)

        plan_qty = int(np.random.exponential(200)) + 50
        actual_qty = int(plan_qty * np.random.normal(0.95, 0.08))
        actual_qty = max(0, actual_qty)

        scrap_rate = np.random.exponential(0.02)
        scrap_qty = int(actual_qty * scrap_rate)
        actual_qty -= scrap_qty

        man_hours = round(plan_qty * np.random.uniform(0.5, 1.5), 1)

        random_days = np.random.randint(0, date_range)
        prod_date = start_date + timedelta(days=random_days)

        product_materials = [(m, std) for (p, m), std in material_standards.items() if p == product]

        for material, std_qty_per_unit in product_materials:
            std_qty = round(plan_qty * std_qty_per_unit, 2)

            variance = np.random.normal(0, 0.05)
            if np.random.random() < 0.05:
                variance += np.random.choice([-0.15, 0.15])

            actual_material = round(std_qty * (1 + variance), 2)

            data.append({
                '生产单号': f'SC{2024}{i+1:06d}',
                '产品名称': product,
                '物料名称': material,
                '计划产量': plan_qty,
                '实际产量': actual_qty,
                '报废数量': scrap_qty,
                '标准用量': std_qty,
                '实际用量': actual_material,
                '工时': man_hours,
                '生产日期': prod_date.strftime('%Y-%m-%d'),
                '生产部门': workshop,
                '班组': team,
                '备注': ''
            })

    df = pd.DataFrame(data)
    return df


def generate_maintenance_data(n_records: int = 400, seed: int = 42) -> pd.DataFrame:
    """生成维修审计示例数据"""
    np.random.seed(seed)

    assets = [f'设备{str(i).zfill(3)}' for i in range(1, 51)] + [f'车辆{str(i).zfill(3)}' for i in range(1, 31)]
    repair_types = ['常规保养', '故障维修', '大修', '配件更换', '年检检修', '事故维修']
    vendors = ['维修厂A', '维修厂B', '维修厂C', '维修厂D', '特约维修站']
    departments = ['生产部', '物流部', '行政部', '设备部']

    cost_ranges = {
        '常规保养': (200, 800),
        '故障维修': (500, 3000),
        '大修': (3000, 15000),
        '配件更换': (300, 2000),
        '年检检修': (100, 500),
        '事故维修': (2000, 20000)
    }

    start_date = datetime(2024, 1, 1)
    end_date = datetime(2024, 12, 31)
    date_range = (end_date - start_date).days

    high_freq_assets = ['设备005', '设备012', '车辆007', '设备023']

    data = []
    for i in range(n_records):
        repair_type = np.random.choice(repair_types)
        cost_range = cost_ranges[repair_type]

        if np.random.random() < 0.1:
            asset = np.random.choice(high_freq_assets)
        else:
            asset = np.random.choice(assets)

        cost = round(np.random.uniform(*cost_range), 2)

        if np.random.random() < 0.03:
            cost = round(cost * np.random.uniform(1.5, 3.0), 2)

        if np.random.random() < 0.02:
            cost = round(cost / 1000) * 1000

        random_days = np.random.randint(0, date_range)
        repair_date = start_date + timedelta(days=random_days)

        data.append({
            '维修单号': f'WX{2024}{i+1:06d}',
            '车辆/设备编号': asset,
            '车辆/设备名称': f'{asset}号设备' if '设备' in asset else f'{asset}号车辆',
            '维修类型': repair_type,
            '维修费用': cost,
            '维修日期': repair_date.strftime('%Y-%m-%d'),
            '维修部门': np.random.choice(departments),
            '报修人': np.random.choice(['张三', '李四', '王五', '赵六', '钱七']),
            '维修厂家': np.random.choice(vendors),
            '故障描述': f'{repair_type}维修',
            '备注': ''
        })

    df = pd.DataFrame(data)
    return df


def generate_all_sample_data(output_dir: str = None):
    """生成所有示例数据并保存"""
    if output_dir is None:
        output_dir = DATA_DIR

    os.makedirs(output_dir, exist_ok=True)

    procurement_df = generate_procurement_data()
    procurement_path = os.path.join(output_dir, 'sample_procurement.xlsx')
    procurement_df.to_excel(procurement_path, index=False)
    print(f"采购数据已生成: {procurement_path} ({len(procurement_df)}条)")

    sales_df = generate_sales_data()
    sales_path = os.path.join(output_dir, 'sample_sales.xlsx')
    sales_df.to_excel(sales_path, index=False)
    print(f"销售数据已生成: {sales_path} ({len(sales_df)}条)")

    production_df = generate_production_data()
    production_path = os.path.join(output_dir, 'sample_production.xlsx')
    production_df.to_excel(production_path, index=False)
    print(f"生产数据已生成: {production_path} ({len(production_df)}条)")

    maintenance_df = generate_maintenance_data()
    maintenance_path = os.path.join(output_dir, 'sample_maintenance.xlsx')
    maintenance_df.to_excel(maintenance_path, index=False)
    print(f"维修数据已生成: {maintenance_path} ({len(maintenance_df)}条)")

    return {
        'procurement': procurement_path,
        'sales': sales_path,
        'production': production_path,
        'maintenance': maintenance_path
    }


if __name__ == '__main__':
    generate_all_sample_data()
