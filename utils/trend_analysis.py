"""
趋势分析工具
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Tuple, Any
from datetime import datetime


class TrendAnalyzer:
    """趋势分析类"""

    def __init__(self):
        pass

    def analyze_trend(
        self,
        df: pd.DataFrame,
        date_col: str,
        value_col: str,
        freq: str = 'M',
        group_col: Optional[str] = None
    ) -> Tuple[pd.DataFrame, Dict[str, Any]]:
        """
        分析时间趋势
        freq: D(日), W(周), M(月), Q(季), Y(年)
        """
        if date_col not in df.columns or value_col not in df.columns:
            return pd.DataFrame(), {'error': '列不存在'}

        df = df.copy()
        df[date_col] = pd.to_datetime(df[date_col])

        info = {
            'date_column': date_col,
            'value_column': value_col,
            'frequency': freq,
            'date_range': {
                'start': df[date_col].min(),
                'end': df[date_col].max()
            }
        }

        if group_col and group_col in df.columns:
            trend_df = df.groupby([group_col, pd.Grouper(key=date_col, freq=freq)])[value_col].sum().reset_index()
            trend_df.columns = [group_col, 'period', 'value']

            trend_stats = []
            for group in trend_df[group_col].unique():
                group_data = trend_df[trend_df[group_col] == group]
                stats = self._calculate_trend_stats(group_data['value'])
                stats['group'] = group
                trend_stats.append(stats)

            info['group_trends'] = trend_stats
        else:
            trend_df = df.groupby(pd.Grouper(key=date_col, freq=freq))[value_col].sum().reset_index()
            trend_df.columns = ['period', 'value']

            stats = self._calculate_trend_stats(trend_df['value'])
            info['trend_stats'] = stats

        return trend_df, info

    def _calculate_trend_stats(self, values: pd.Series) -> Dict[str, Any]:
        """计算趋势统计指标"""
        values = values.dropna()
        if len(values) == 0:
            return {}

        stats = {
            'periods': len(values),
            'total': values.sum(),
            'mean': values.mean(),
            'median': values.median(),
            'std': values.std(),
            'min': values.min(),
            'max': values.max(),
            'cv': values.std() / values.mean() if values.mean() != 0 else 0
        }

        if len(values) >= 2:
            x = np.arange(len(values))
            slope, intercept = np.polyfit(x, values.values, 1)
            stats['slope'] = slope
            stats['trend_direction'] = 'increasing' if slope > 0 else 'decreasing' if slope < 0 else 'stable'
            stats['growth_rate'] = ((values.iloc[-1] - values.iloc[0]) / values.iloc[0]) if values.iloc[0] != 0 else 0

        if len(values) >= 4:
            first_half = values.iloc[:len(values)//2].mean()
            second_half = values.iloc[len(values)//2:].mean()
            stats['half_period_change'] = (second_half - first_half) / first_half if first_half != 0 else 0

        return stats

    def compare_periods(
        self,
        df: pd.DataFrame,
        date_col: str,
        value_col: str,
        period1_start: str,
        period1_end: str,
        period2_start: str,
        period2_end: str,
        group_col: Optional[str] = None
    ) -> Tuple[pd.DataFrame, Dict[str, Any]]:
        """两期对比分析"""
        if date_col not in df.columns or value_col not in df.columns:
            return pd.DataFrame(), {'error': '列不存在'}

        df = df.copy()
        df[date_col] = pd.to_datetime(df[date_col])

        period1_start = pd.to_datetime(period1_start)
        period1_end = pd.to_datetime(period1_end)
        period2_start = pd.to_datetime(period2_start)
        period2_end = pd.to_datetime(period2_end)

        df['period'] = np.where(
            (df[date_col] >= period1_start) & (df[date_col] <= period1_end),
            'period1',
            np.where(
                (df[date_col] >= period2_start) & (df[date_col] <= period2_end),
                'period2',
                'other'
            )
        )

        info = {
            'period1': {'start': period1_start, 'end': period1_end},
            'period2': {'start': period2_start, 'end': period2_end}
        }

        if group_col and group_col in df.columns:
            comparison = df[df['period'] != 'other'].pivot_table(
                index=group_col,
                columns='period',
                values=value_col,
                aggfunc='sum',
                fill_value=0
            ).reset_index()

            if 'period1' in comparison.columns and 'period2' in comparison.columns:
                comparison['absolute_change'] = comparison['period2'] - comparison['period1']
                comparison['change_rate'] = np.where(
                    comparison['period1'] != 0,
                    comparison['absolute_change'] / comparison['period1'],
                    np.nan
                )

            info['group_comparison'] = True
        else:
            period1_total = df[df['period'] == 'period1'][value_col].sum()
            period2_total = df[df['period'] == 'period2'][value_col].sum()

            comparison = pd.DataFrame([{
                'period1': period1_total,
                'period2': period2_total,
                'absolute_change': period2_total - period1_total,
                'change_rate': (period2_total - period1_total) / period1_total if period1_total != 0 else np.nan
            }])

            info['period1_total'] = period1_total
            info['period2_total'] = period2_total
            info['absolute_change'] = period2_total - period1_total
            info['change_rate'] = (period2_total - period1_total) / period1_total if period1_total != 0 else np.nan

        return comparison, info

    def detect_abnormal_trend(
        self,
        df: pd.DataFrame,
        date_col: str,
        value_col: str,
        threshold: float = 0.30,
        freq: str = 'M'
    ) -> Tuple[pd.DataFrame, Dict[str, Any]]:
        """
        检测异常波动期
        threshold: 环比变动阈值
        """
        trend_df, _ = self.analyze_trend(df, date_col, value_col, freq)

        if len(trend_df) < 2:
            return pd.DataFrame(), {'error': '数据点不足'}

        trend_df['prev_value'] = trend_df['value'].shift(1)
        trend_df['change_rate'] = (trend_df['value'] - trend_df['prev_value']) / trend_df['prev_value'].replace(0, np.nan)
        trend_df['abs_change_rate'] = trend_df['change_rate'].abs()

        abnormal = trend_df[trend_df['abs_change_rate'] > threshold]

        info = {
            'threshold': threshold,
            'total_periods': len(trend_df),
            'abnormal_periods': len(abnormal),
            'max_increase': trend_df['change_rate'].max(),
            'max_decrease': trend_df['change_rate'].min()
        }

        return abnormal, info

    def moving_average(
        self,
        df: pd.DataFrame,
        date_col: str,
        value_col: str,
        window: int = 3,
        freq: str = 'D'
    ) -> Tuple[pd.DataFrame, Dict[str, Any]]:
        """移动平均分析"""
        trend_df, _ = self.analyze_trend(df, date_col, value_col, freq)

        if len(trend_df) < window:
            return trend_df, {'error': '数据点不足'}

        trend_df[f'ma_{window}'] = trend_df['value'].rolling(window=window, center=False).mean()
        trend_df['deviation'] = (trend_df['value'] - trend_df[f'ma_{window}']) / trend_df[f'ma_{window}']

        info = {
            'window': window,
            'frequency': freq
        }

        return trend_df, info
