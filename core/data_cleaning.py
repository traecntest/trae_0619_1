"""
数据清洗与标准化模块
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Tuple
import re
from datetime import datetime


class DataCleaner:
    """数据清洗与标准化类"""

    def __init__(self):
        pass

    def clean_data(self, df: pd.DataFrame, schema_type: Optional[str] = None) -> Tuple[pd.DataFrame, Dict]:
        """
        综合数据清洗流程
        返回清洗后的数据和清洗报告
        """
        report = {
            'initial_rows': len(df),
            'initial_columns': len(df.columns),
            'steps': []
        }

        df_clean = df.copy()

        df_clean = self._strip_strings(df_clean)
        report['steps'].append('去除字符串首尾空格')

        df_clean, removed_dupes = self._remove_duplicates(df_clean)
        report['duplicates_removed'] = removed_dupes
        report['steps'].append(f'去除重复行 ({removed_dupes}行)')

        if schema_type:
            df_clean = self._standardize_columns(df_clean, schema_type)
            report['steps'].append('字段名称标准化')

        df_clean = self._convert_numeric_fields(df_clean)
        report['steps'].append('数值字段类型转换')

        df_clean = self._convert_date_fields(df_clean)
        report['steps'].append('日期字段类型转换')

        report['final_rows'] = len(df_clean)
        report['final_columns'] = len(df_clean.columns)

        return df_clean, report

    def _strip_strings(self, df: pd.DataFrame) -> pd.DataFrame:
        """去除所有字符串列的首尾空格"""
        for col in df.columns:
            if df[col].dtype == 'object':
                df[col] = df[col].astype(str).str.strip()
                df[col] = df[col].replace(['nan', 'NaN', 'None', ''], np.nan)
        return df

    def _remove_duplicates(self, df: pd.DataFrame) -> Tuple[pd.DataFrame, int]:
        """去除完全重复的行"""
        initial_count = len(df)
        df_clean = df.drop_duplicates()
        removed = initial_count - len(df_clean)
        return df_clean, removed

    def _standardize_columns(self, df: pd.DataFrame, schema_type: str) -> pd.DataFrame:
        """根据数据模式标准化字段名"""
        from config import DATA_SCHEMAS

        if schema_type not in DATA_SCHEMAS:
            return df

        schema = DATA_SCHEMAS[schema_type]
        all_fields = schema.get('required_fields', []) + schema.get('optional_fields', [])

        column_mapping = {}
        for col in df.columns:
            col_clean = col.strip()
            if col_clean in all_fields:
                column_mapping[col] = col_clean
            else:
                matched = self._fuzzy_match_column(col_clean, all_fields)
                if matched:
                    column_mapping[col] = matched

        if column_mapping:
            df = df.rename(columns=column_mapping)

        return df

    def _fuzzy_match_column(self, col_name: str, target_columns: List[str]) -> Optional[str]:
        """模糊匹配列名"""
        col_lower = col_name.lower()
        for target in target_columns:
            if target.lower() == col_lower:
                return target
            if target.lower() in col_lower or col_lower in target.lower():
                if len(set(col_lower) & set(target.lower())) > len(col_lower) * 0.6:
                    return target
        return None

    def _convert_numeric_fields(self, df: pd.DataFrame) -> pd.DataFrame:
        """自动识别并转换数值字段"""
        for col in df.columns:
            if df[col].dtype == 'object':
                numeric_series = df[col].apply(self._parse_numeric)
                non_null_count = numeric_series.notna().sum()
                if non_null_count > len(df) * 0.5 and non_null_count > 0:
                    df[col] = numeric_series
        return df

    def _parse_numeric(self, value: str) -> float:
        """解析数值，处理千分位、货币符号等"""
        if pd.isna(value) or value == '':
            return np.nan
        if isinstance(value, (int, float)):
            return float(value)
        try:
            cleaned = str(value).replace(',', '').replace('¥', '').replace('￥', '').replace('$', '').replace('%', '')
            cleaned = cleaned.strip()
            return float(cleaned)
        except (ValueError, TypeError):
            return np.nan

    def _convert_date_fields(self, df: pd.DataFrame) -> pd.DataFrame:
        """自动识别并转换日期字段"""
        for col in df.columns:
            if df[col].dtype == 'object':
                date_series = df[col].apply(self._parse_date)
                non_null_count = date_series.notna().sum()
                if non_null_count > len(df) * 0.5 and non_null_count > 0:
                    df[col] = date_series
        return df

    def _parse_date(self, value: str) -> Optional[datetime]:
        """解析日期字符串"""
        if pd.isna(value) or value == '':
            return pd.NaT
        if isinstance(value, datetime):
            return value
        try:
            from dateutil import parser
            return parser.parse(str(value))
        except (ValueError, TypeError):
            pass

        date_patterns = [
            '%Y-%m-%d',
            '%Y/%m/%d',
            '%Y%m%d',
            '%Y年%m月%d日',
            '%m/%d/%Y',
            '%d/%m/%Y',
            '%Y-%m-%d %H:%M:%S',
            '%Y/%m/%d %H:%M:%S',
        ]

        for pattern in date_patterns:
            try:
                return datetime.strptime(str(value), pattern)
            except (ValueError, TypeError):
                continue

        return pd.NaT

    def validate_data(self, df: pd.DataFrame, schema_type: str) -> Dict:
        """验证数据是否符合指定模式"""
        from config import DATA_SCHEMAS

        if schema_type not in DATA_SCHEMAS:
            return {'valid': False, 'errors': ['未知的数据模式']}

        schema = DATA_SCHEMAS[schema_type]
        required_fields = schema.get('required_fields', [])

        result = {
            'valid': True,
            'missing_fields': [],
            'field_stats': {},
            'errors': []
        }

        for field in required_fields:
            if field not in df.columns:
                result['missing_fields'].append(field)
                result['valid'] = False
            else:
                non_null_count = df[field].notna().sum()
                result['field_stats'][field] = {
                    'non_null': non_null_count,
                    'null': len(df) - non_null_count,
                    'completeness': non_null_count / len(df) if len(df) > 0 else 0
                }

        if result['missing_fields']:
            result['errors'].append(f"缺少必需字段: {', '.join(result['missing_fields'])}")

        return result

    def handle_missing_values(self, df: pd.DataFrame, strategy: str = 'keep') -> pd.DataFrame:
        """处理缺失值"""
        if strategy == 'drop':
            return df.dropna()
        elif strategy == 'fill_zero':
            numeric_cols = df.select_dtypes(include=[np.number]).columns
            df[numeric_cols] = df[numeric_cols].fillna(0)
            return df
        elif strategy == 'fill_mean':
            numeric_cols = df.select_dtypes(include=[np.number]).columns
            df[numeric_cols] = df[numeric_cols].fillna(df[numeric_cols].mean())
            return df
        else:
            return df
