"""
审计规则配置
"""

AUDIT_RULES = {
    'procurement': {
        'price_fluctuation': {
            'name': '价格波动预警',
            'description': '监控同一物料采购价格的异常波动',
            'default_threshold': 0.15,
            'unit': '比例',
            'risk_level': 'medium'
        },
        'supplier_concentration': {
            'name': '供应商集中度分析',
            'description': '分析单一供应商占比，识别过度依赖风险',
            'default_threshold': 0.30,
            'unit': '比例',
            'risk_level': 'medium'
        },
        'anomaly_transaction': {
            'name': '异常交易识别',
            'description': '识别单笔金额异常、频繁交易等异常模式',
            'default_threshold': 3.0,
            'unit': '标准差倍数',
            'risk_level': 'high'
        },
        'purchase_allocation': {
            'name': '采购量分配分析',
            'description': '分析各供应商采购量分配是否合理',
            'default_threshold': 0.50,
            'unit': '比例',
            'risk_level': 'medium'
        },
        'round_amount': {
            'name': '整数金额检测',
            'description': '检测大额整数交易，关注舞弊风险',
            'default_threshold': 10000,
            'unit': '元',
            'risk_level': 'high'
        }
    },
    'sales': {
        'price_compliance': {
            'name': '价格体系合规性',
            'description': '检查销售价格是否在定价体系范围内',
            'default_threshold': 0.10,
            'unit': '偏差比例',
            'risk_level': 'medium'
        },
        'credit_management': {
            'name': '客户信用管理',
            'description': '分析客户信用额度使用和超信用情况',
            'default_threshold': 1.0,
            'unit': '信用额度倍数',
            'risk_level': 'high'
        },
        'collection_cycle': {
            'name': '回款周期分析',
            'description': '分析客户应收账款回款周期异常',
            'default_threshold': 90,
            'unit': '天',
            'risk_level': 'medium'
        },
        'return_anomaly': {
            'name': '退货异常检测',
            'description': '识别异常高频退货、大额退货',
            'default_threshold': 0.10,
            'unit': '退货率',
            'risk_level': 'medium'
        },
        'discount_anomaly': {
            'name': '折扣异常分析',
            'description': '分析异常折扣比例和折扣审批',
            'default_threshold': 0.30,
            'unit': '折扣率',
            'risk_level': 'high'
        }
    },
    'production': {
        'material_variance': {
            'name': '领料差异分析',
            'description': '分析实际领料与标准用量差异',
            'default_threshold': 0.10,
            'unit': '差异比例',
            'risk_level': 'medium'
        },
        'completion_rate': {
            'name': '完工入库分析',
            'description': '分析生产完工率和及时入库情况',
            'default_threshold': 0.90,
            'unit': '完工率',
            'risk_level': 'low'
        },
        'scrap_rate': {
            'name': '报废率监控',
            'description': '监控生产报废率异常波动',
            'default_threshold': 0.05,
            'unit': '报废率',
            'risk_level': 'medium'
        },
        'production_efficiency': {
            'name': '生产效率分析',
            'description': '分析投入产出比和生产效率趋势',
            'default_threshold': 0.85,
            'unit': '效率值',
            'risk_level': 'low'
        }
    },
    'maintenance': {
        'excessive_maintenance': {
            'name': '过度维修识别',
            'description': '识别同一车辆/设备维修频次和费用异常',
            'default_threshold': 3,
            'unit': '次/月',
            'risk_level': 'medium'
        },
        'maintenance_cost': {
            'name': '维修费用分析',
            'description': '分析维修费用趋势和异常',
            'default_threshold': 0.20,
            'unit': '波动比例',
            'risk_level': 'medium'
        }
    }
}

DATA_SCHEMAS = {
    'procurement_purchase': {
        'required_fields': ['采购单号', '供应商', '物料名称', '采购数量', '单价', '采购金额', '采购日期'],
        'optional_fields': ['物料编码', '采购部门', '采购员', '审批人', '合同号', '备注'],
        'date_fields': ['采购日期'],
        'numeric_fields': ['采购数量', '单价', '采购金额']
    },
    'sales_order': {
        'required_fields': ['销售单号', '客户名称', '产品名称', '销售数量', '单价', '销售金额', '销售日期'],
        'optional_fields': ['产品编码', '销售部门', '销售员', '信用额度', '折扣金额', '备注'],
        'date_fields': ['销售日期'],
        'numeric_fields': ['销售数量', '单价', '销售金额', '折扣金额', '信用额度']
    },
    'sales_receivable': {
        'required_fields': ['客户名称', '应收账款余额', '账龄', '销售日期'],
        'optional_fields': ['销售单号', '应回款日期', '实际回款日期', '已回款金额'],
        'date_fields': ['销售日期', '应回款日期', '实际回款日期'],
        'numeric_fields': ['应收账款余额', '已回款金额']
    },
    'production_material': {
        'required_fields': ['生产单号', '产品名称', '物料名称', '标准用量', '实际用量', '领料日期'],
        'optional_fields': ['物料编码', '生产部门', '领料人', '批次号', '备注'],
        'date_fields': ['领料日期'],
        'numeric_fields': ['标准用量', '实际用量']
    },
    'production_output': {
        'required_fields': ['生产单号', '产品名称', '计划产量', '实际产量', '报废数量', '生产日期'],
        'optional_fields': ['产品编码', '生产部门', '班组', '工时', '备注'],
        'date_fields': ['生产日期'],
        'numeric_fields': ['计划产量', '实际产量', '报废数量', '工时']
    },
    'maintenance_order': {
        'required_fields': ['维修单号', '车辆/设备编号', '维修类型', '维修费用', '维修日期'],
        'optional_fields': ['车辆/设备名称', '维修部门', '报修人', '维修厂家', '故障描述', '备注'],
        'date_fields': ['维修日期'],
        'numeric_fields': ['维修费用']
    }
}
