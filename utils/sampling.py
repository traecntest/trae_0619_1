"""
自动抽样工具
支持多种抽样方法：随机抽样、分层抽样、系统抽样、货币单位抽样
"""

import pandas as pd
import numpy as np
from typing import Optional, Dict, Any, Tuple
from config import SAMPLING_CONFIG


class Sampler:
    """抽样工具类"""

    def __init__(self):
        self.config = SAMPLING_CONFIG

    def sample(
        self,
        df: pd.DataFrame,
        method: str = 'stratified',
        sample_size: Optional[int] = None,
        stratify_col: Optional[str] = None,
        amount_col: Optional[str] = None,
        random_state: int = 42
    ) -> Tuple[pd.DataFrame, Dict[str, Any]]:
        """
        执行抽样
        返回抽样结果和抽样信息
        """
        if len(df) == 0:
            return df.copy(), {'error': '数据为空'}

        if sample_size is None:
            sample_size = self._calculate_sample_size(len(df))

        sample_size = min(sample_size, len(df))

        info = {
            'method': method,
            'population_size': len(df),
            'sample_size': sample_size,
            'sampling_ratio': sample_size / len(df) if len(df) > 0 else 0
        }

        if method == 'random':
            sample_df = self._random_sampling(df, sample_size, random_state)
        elif method == 'stratified':
            sample_df, stratify_info = self._stratified_sampling(
                df, sample_size, stratify_col, random_state
            )
            info.update(stratify_info)
        elif method == 'systematic':
            sample_df = self._systematic_sampling(df, sample_size)
        elif method == 'mus':
            sample_df, mus_info = self._monetary_unit_sampling(
                df, sample_size, amount_col, random_state
            )
            info.update(mus_info)
        else:
            raise ValueError(f"不支持的抽样方法: {method}")

        info['actual_sample_size'] = len(sample_df)

        return sample_df, info

    def _random_sampling(self, df: pd.DataFrame, sample_size: int, random_state: int) -> pd.DataFrame:
        """简单随机抽样"""
        return df.sample(n=sample_size, random_state=random_state)

    def _stratified_sampling(
        self,
        df: pd.DataFrame,
        sample_size: int,
        stratify_col: Optional[str],
        random_state: int
    ) -> Tuple[pd.DataFrame, Dict[str, Any]]:
        """分层抽样"""
        if stratify_col is None or stratify_col not in df.columns:
            numeric_cols = df.select_dtypes(include=[np.number]).columns
            if len(numeric_cols) > 0:
                stratify_col = numeric_cols[0]
                df['_stratum'] = pd.qcut(df[stratify_col], q=min(5, len(df)), duplicates='drop')
                stratify_col = '_stratum'
            else:
                return self._random_sampling(df, sample_size, random_state), {'warning': '无分层字段，使用随机抽样'}

        strata_counts = df[stratify_col].value_counts()
        total = len(df)

        samples = []
        strata_info = {'strata': {}}

        for stratum_value, count in strata_counts.items():
            stratum_size = max(1, int(sample_size * count / total))
            stratum_df = df[df[stratify_col] == stratum_value]
            stratum_sample = stratum_df.sample(n=min(stratum_size, len(stratum_df)), random_state=random_state)
            samples.append(stratum_sample)
            strata_info['strata'][str(stratum_value)] = {
                'population': count,
                'sampled': len(stratum_sample)
            }

        result = pd.concat(samples).sort_index()

        if '_stratum' in result.columns:
            result = result.drop(columns=['_stratum'])

        return result, strata_info

    def _systematic_sampling(self, df: pd.DataFrame, sample_size: int) -> pd.DataFrame:
        """系统抽样（等距抽样）"""
        interval = len(df) // sample_size
        if interval == 0:
            return df.copy()

        start = np.random.randint(0, interval)
        indices = np.arange(start, len(df), interval)[:sample_size]
        return df.iloc[indices]

    def _monetary_unit_sampling(
        self,
        df: pd.DataFrame,
        sample_size: int,
        amount_col: Optional[str],
        random_state: int
    ) -> Tuple[pd.DataFrame, Dict[str, Any]]:
        """货币单位抽样（PPS抽样）"""
        if amount_col is None or amount_col not in df.columns:
            numeric_cols = df.select_dtypes(include=[np.number]).columns
            if len(numeric_cols) > 0:
                amount_col = numeric_cols[0]
            else:
                return self._random_sampling(df, sample_size, random_state), {'warning': '无金额字段，使用随机抽样'}

        df_sorted = df.sort_values(amount_col).reset_index(drop=True)
        amounts = df_sorted[amount_col].abs().fillna(0)
        total_amount = amounts.sum()

        if total_amount == 0:
            return self._random_sampling(df, sample_size, random_state), {'warning': '总金额为0，使用随机抽样'}

        interval = total_amount / sample_size
        start = np.random.uniform(0, interval)

        selected_indices = set()
        cumulative = 0

        for i, amt in enumerate(amounts):
            cumulative += amt
            while cumulative >= start and len(selected_indices) < sample_size:
                selected_indices.add(i)
                start += interval

        sample_df = df_sorted.iloc[list(selected_indices)].sort_index()

        info = {
            'amount_column': amount_col,
            'total_amount': total_amount,
            'interval': interval
        }

        return sample_df, info

    def _calculate_sample_size(self, population_size: int) -> int:
        """根据总体规模计算样本量"""
        if population_size <= 30:
            return population_size

        from scipy import stats

        z = stats.norm.ppf((1 + self.config['confidence_level']) / 2)
        e = self.config['margin_of_error']
        p = 0.5

        n0 = (z ** 2 * p * (1 - p)) / (e ** 2)
        n = n0 / (1 + (n0 - 1) / population_size)

        sample_size = int(np.ceil(n))
        sample_size = max(sample_size, self.config['min_sample_size'])
        sample_size = min(sample_size, self.config['max_sample_size'], population_size)

        return sample_size

    def get_sample_methods(self) -> Dict[str, str]:
        """获取可用的抽样方法"""
        return {
            'random': '简单随机抽样',
            'stratified': '分层抽样',
            'systematic': '系统抽样（等距）',
            'mus': '货币单位抽样（PPS）'
        }
