"""
阈值告警工具
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Tuple, Any


class ThresholdAlert:
    """阈值告警类"""

    def __init__(self):
        pass

    def check_above_threshold(
        self,
        df: pd.DataFrame,
        value_col: str,
        threshold: float,
        group_col: Optional[str] = None
    ) -> Tuple[pd.DataFrame, Dict[str, Any]]:
        """检查高于阈值的记录"""
        if value_col not in df.columns:
            return pd.DataFrame(), {'error': f'列 {value_col} 不存在'}

        info = {
            'value_column': value_col,
            'threshold': threshold,
            'total_records': len(df),
            'check_type': 'above'
        }

        if group_col and group_col in df.columns:
            group_stats = df.groupby(group_col)[value_col].agg(['count', 'mean', 'max', 'sum'])
            above_groups = group_stats[group_stats['mean'] > threshold]
            info['groups_above_threshold'] = len(above_groups)
            info['total_groups'] = len(group_stats)
            result = df[df[group_col].isin(above_groups.index)]
        else:
            result = df[df[value_col] > threshold]
            info['records_above_threshold'] = len(result)
            info['percentage'] = len(result) / len(df) if len(df) > 0 else 0

        return result.copy(), info

    def check_below_threshold(
        self,
        df: pd.DataFrame,
        value_col: str,
        threshold: float,
        group_col: Optional[str] = None
    ) -> Tuple[pd.DataFrame, Dict[str, Any]]:
        """检查低于阈值的记录"""
        if value_col not in df.columns:
            return pd.DataFrame(), {'error': f'列 {value_col} 不存在'}

        info = {
            'value_column': value_col,
            'threshold': threshold,
            'total_records': len(df),
            'check_type': 'below'
        }

        if group_col and group_col in df.columns:
            group_stats = df.groupby(group_col)[value_col].agg(['count', 'mean', 'min', 'sum'])
            below_groups = group_stats[group_stats['mean'] < threshold]
            info['groups_below_threshold'] = len(below_groups)
            info['total_groups'] = len(group_stats)
            result = df[df[group_col].isin(below_groups.index)]
        else:
            result = df[df[value_col] < threshold]
            info['records_below_threshold'] = len(result)
            info['percentage'] = len(result) / len(df) if len(df) > 0 else 0

        return result.copy(), info

    def check_outliers_zscore(
        self,
        df: pd.DataFrame,
        value_col: str,
        z_threshold: float = 3.0,
        group_col: Optional[str] = None
    ) -> Tuple[pd.DataFrame, Dict[str, Any]]:
        """使用Z-score检测异常值"""
        if value_col not in df.columns:
            return pd.DataFrame(), {'error': f'列 {value_col} 不存在'}

        result = df.copy()
        info = {
            'value_column': value_col,
            'z_threshold': z_threshold,
            'total_records': len(df),
            'method': 'z-score'
        }

        if group_col and group_col in df.columns:
            result['_zscore'] = result.groupby(group_col)[value_col].transform(
                lambda x: (x - x.mean()) / x.std() if x.std() > 0 else 0
            )
        else:
            mean_val = result[value_col].mean()
            std_val = result[value_col].std()
            if std_val > 0:
                result['_zscore'] = (result[value_col] - mean_val) / std_val
            else:
                result['_zscore'] = 0

        outliers = result[result['_zscore'].abs() > z_threshold]
        info['outlier_count'] = len(outliers)
        info['outlier_percentage'] = len(outliers) / len(df) if len(df) > 0 else 0

        outliers = outliers.drop(columns=['_zscore'])

        return outliers, info

    def check_outliers_iqr(
        self,
        df: pd.DataFrame,
        value_col: str,
        iqr_factor: float = 1.5,
        group_col: Optional[str] = None
    ) -> Tuple[pd.DataFrame, Dict[str, Any]]:
        """使用IQR方法检测异常值"""
        if value_col not in df.columns:
            return pd.DataFrame(), {'error': f'列 {value_col} 不存在'}

        result = df.copy()
        info = {
            'value_column': value_col,
            'iqr_factor': iqr_factor,
            'total_records': len(df),
            'method': 'IQR'
        }

        def iqr_filter(series):
            q1 = series.quantile(0.25)
            q3 = series.quantile(0.75)
            iqr = q3 - q1
            lower = q1 - iqr_factor * iqr
            upper = q3 + iqr_factor * iqr
            return ~((series < lower) | (series > upper))

        if group_col and group_col in df.columns:
            mask = result.groupby(group_col)[value_col].transform(iqr_filter)
        else:
            q1 = result[value_col].quantile(0.25)
            q3 = result[value_col].quantile(0.75)
            iqr = q3 - q1
            lower = q1 - iqr_factor * iqr
            upper = q3 + iqr_factor * iqr
            mask = ~((result[value_col] < lower) | (result[value_col] > upper))

        outliers = result[~mask]
        info['outlier_count'] = len(outliers)
        info['outlier_percentage'] = len(outliers) / len(df) if len(df) > 0 else 0

        return outliers, info

    def check_concentration(
        self,
        df: pd.DataFrame,
        value_col: str,
        group_col: str,
        concentration_threshold: float = 0.30
    ) -> Tuple[pd.DataFrame, Dict[str, Any]]:
        """
        集中度分析
        识别占比超过阈值的组
        """
        if value_col not in df.columns or group_col not in df.columns:
            return pd.DataFrame(), {'error': '列不存在'}

        group_totals = df.groupby(group_col)[value_col].sum().sort_values(ascending=False)
        total = group_totals.sum()

        if total == 0:
            return pd.DataFrame(), {'error': '总金额为0'}

        concentration = group_totals / total
        cumulative_concentration = concentration.cumsum()

        info = {
            'group_column': group_col,
            'value_column': value_col,
            'threshold': concentration_threshold,
            'total_amount': total,
            'total_groups': len(group_totals),
            'concentration_ratios': concentration.to_dict(),
            'cumulative_concentration': cumulative_concentration.to_dict()
        }

        high_concentration = concentration[concentration > concentration_threshold]
        info['high_concentration_groups'] = len(high_concentration)
        info['herfindahl_index'] = (concentration ** 2).sum()

        result = df[df[group_col].isin(high_concentration.index)]

        return result.copy(), info
