"""
异常检测工具
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Tuple, Any


class AnomalyDetector:
    """异常检测类"""

    def __init__(self):
        pass

    def detect_round_numbers(
        self,
        df: pd.DataFrame,
        amount_col: str,
        threshold: float = 10000.0
    ) -> Tuple[pd.DataFrame, Dict[str, Any]]:
        """
        检测整数金额
        threshold: 金额阈值，超过此金额且为整数的标记为异常
        """
        if amount_col not in df.columns:
            return pd.DataFrame(), {'error': f'列 {amount_col} 不存在'}

        result = df.copy()
        result['_is_round'] = (
            (result[amount_col] >= threshold) &
            (result[amount_col] % 1000 == 0)
        )

        anomalies = result[result['_is_round']].drop(columns=['_is_round'])

        info = {
            'amount_column': amount_col,
            'threshold': threshold,
            'total_records': len(df),
            'anomaly_count': len(anomalies),
            'anomaly_percentage': len(anomalies) / len(df) if len(df) > 0 else 0,
            'anomaly_total_amount': anomalies[amount_col].sum() if len(anomalies) > 0 else 0
        }

        return anomalies, info

    def detect_duplicate_transactions(
        self,
        df: pd.DataFrame,
        key_columns: List[str],
        amount_col: Optional[str] = None,
        tolerance: Optional[float] = 0.01
    ) -> Tuple[pd.DataFrame, Dict[str, Any]]:
        """
        检测重复交易
        """
        if not all(col in df.columns for col in key_columns):
            return pd.DataFrame(), {'error': '关键字段不存在'}

        duplicates = df[df.duplicated(subset=key_columns, keep=False)]

        info = {
            'key_columns': key_columns,
            'total_records': len(df),
            'duplicate_groups': len(duplicates) // 2 if len(duplicates) > 0 else 0,
            'duplicate_count': len(duplicates)
        }

        if amount_col and amount_col in df.columns:
            info['duplicate_total_amount'] = duplicates[amount_col].sum()

        return duplicates.sort_values(key_columns), info

    def detect_benford_law(
        self,
        df: pd.DataFrame,
        amount_col: str
    ) -> Tuple[pd.DataFrame, Dict[str, Any]]:
        """
        Benford定律检测（本福特定律）
        用于检测数据是否符合自然数字分布
        """
        if amount_col not in df.columns:
            return pd.DataFrame(), {'error': f'列 {amount_col} 不存在'}

        amounts = df[amount_col].dropna()
        amounts = amounts[amounts > 0]

        if len(amounts) == 0:
            return pd.DataFrame(), {'error': '没有有效金额数据'}

        first_digits = amounts.astype(str).str[0].astype(int)
        first_digits = first_digits[first_digits > 0]

        if len(first_digits) == 0:
            return pd.DataFrame(), {'error': '没有有效首位数字'}

        actual_dist = first_digits.value_counts().sort_index() / len(first_digits)

        benford_dist = pd.Series(
            {i: np.log10(1 + 1/i) for i in range(1, 10)}
        )

        comparison = pd.DataFrame({
            'digit': range(1, 10),
            'actual': actual_dist.reindex(range(1, 10), fill_value=0),
            'expected': benford_dist,
            'difference': actual_dist.reindex(range(1, 10), fill_value=0) - benford_dist
        })

        chi_square = ((comparison['difference'] ** 2 / comparison['expected']).sum()) * len(first_digits)

        info = {
            'amount_column': amount_col,
            'total_records': len(amounts),
            'chi_square': chi_square,
            'benford_compliant': chi_square < 15.51,
            'max_deviation_digit': comparison.loc[comparison['difference'].abs().idxmax(), 'digit'],
            'max_deviation': comparison['difference'].abs().max()
        }

        return comparison, info

    def detect_frequent_transactions(
        self,
        df: pd.DataFrame,
        entity_col: str,
        date_col: str,
        threshold: int = 10,
        window_days: int = 30
    ) -> Tuple[pd.DataFrame, Dict[str, Any]]:
        """
        检测频繁交易
        在指定时间窗口内交易次数超过阈值的实体
        """
        if entity_col not in df.columns or date_col not in df.columns:
            return pd.DataFrame(), {'error': '列不存在'}

        df = df.copy()
        df[date_col] = pd.to_datetime(df[date_col])

        df_sorted = df.sort_values([entity_col, date_col])

        transaction_counts = []

        for entity in df_sorted[entity_col].unique():
            entity_df = df_sorted[df_sorted[entity_col] == entity].copy()
            entity_df = entity_df.sort_values(date_col)

            dates = entity_df[date_col].values
            for i in range(len(dates)):
                window_end = dates[i] + pd.Timedelta(days=window_days)
                count_in_window = ((dates >= dates[i]) & (dates <= window_end)).sum()
                transaction_counts.append({
                    entity_col: entity,
                    'start_date': dates[i],
                    'end_date': window_end,
                    'transaction_count': count_in_window
                })

        count_df = pd.DataFrame(transaction_counts)
        frequent = count_df[count_df['transaction_count'] > threshold]

        frequent_entities = frequent[entity_col].unique()
        result = df[df[entity_col].isin(frequent_entities)]

        info = {
            'entity_column': entity_col,
            'date_column': date_col,
            'threshold': threshold,
            'window_days': window_days,
            'total_entities': df[entity_col].nunique(),
            'frequent_entities': len(frequent_entities),
            'max_transactions_in_window': count_df['transaction_count'].max() if len(count_df) > 0 else 0
        }

        return result, info

    def detect_anomaly_isolation_forest(
        self,
        df: pd.DataFrame,
        numeric_cols: List[str],
        contamination: float = 0.05
    ) -> Tuple[pd.DataFrame, Dict[str, Any]]:
        """
        使用孤立森林算法检测异常
        """
        try:
            from sklearn.ensemble import IsolationForest
        except ImportError:
            return pd.DataFrame(), {'error': 'scikit-learn未安装'}

        numeric_cols = [col for col in numeric_cols if col in df.columns]
        if not numeric_cols:
            return pd.DataFrame(), {'error': '没有可用的数值列'}

        df_clean = df[numeric_cols].dropna()
        if len(df_clean) == 0:
            return pd.DataFrame(), {'error': '没有有效数据'}

        iso_forest = IsolationForest(
            contamination=contamination,
            random_state=42,
            n_estimators=100
        )

        predictions = iso_forest.fit_predict(df_clean)
        scores = iso_forest.decision_function(df_clean)

        result = df.loc[df_clean.index].copy()
        result['_anomaly'] = predictions == -1
        result['_anomaly_score'] = scores

        anomalies = result[result['_anomaly']].copy()

        info = {
            'numeric_columns': numeric_cols,
            'contamination': contamination,
            'total_records': len(df_clean),
            'anomaly_count': len(anomalies),
            'anomaly_percentage': len(anomalies) / len(df_clean) if len(df_clean) > 0 else 0
        }

        anomalies = anomalies.drop(columns=['_anomaly', '_anomaly_score'])

        return anomalies, info
