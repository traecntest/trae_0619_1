"""
内控风险分析系统 - 配置模块
"""

import os

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

DATA_DIR = os.path.join(BASE_DIR, 'data')
LOG_DIR = os.path.join(BASE_DIR, 'logs')
UPLOAD_DIR = os.path.join(BASE_DIR, 'uploads')
EXPORT_DIR = os.path.join(BASE_DIR, 'exports')

for _dir in [DATA_DIR, LOG_DIR, UPLOAD_DIR, EXPORT_DIR]:
    os.makedirs(_dir, exist_ok=True)

APP_TITLE = "内控风险分析系统"
APP_VERSION = "1.0.0"

SUPPORTED_FILE_TYPES = ['xlsx', 'xls', 'csv']

MAX_FILE_SIZE_MB = 100

DEFAULT_ENCODING = 'utf-8'

AUDIT_CATEGORIES = {
    'procurement': '采购审计',
    'sales': '销售审计',
    'production': '生产审计',
    'maintenance': '维修审计'
}

RISK_LEVELS = {
    'high': {'name': '高风险', 'color': '#FF4B4B', 'score_threshold': 80},
    'medium': {'name': '中风险', 'color': '#FFA500', 'score_threshold': 50},
    'low': {'name': '低风险', 'color': '#4CAF50', 'score_threshold': 20},
    'none': {'name': '无风险', 'color': '#9E9E9E', 'score_threshold': 0}
}

DATABASE_CONFIG = {
    'default': {
        'host': 'localhost',
        'port': 3306,
        'database': '',
        'username': '',
        'password': ''
    }
}

SAMPLING_CONFIG = {
    'default_method': 'stratified',
    'confidence_level': 0.95,
    'margin_of_error': 0.05,
    'min_sample_size': 30,
    'max_sample_size': 500
}

USER_ROLES = {
    'admin': '系统管理员',
    'auditor': '审计人员',
    'viewer': '只读用户'
}
