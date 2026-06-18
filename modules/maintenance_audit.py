"""
维修审计模块
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Optional

from core import BaseAuditEngine, AuditFinding, AuditResult
from utils import ThresholdAlert, TrendAnalyzer, AnomalyDetector
from config import AUDIT_RULES


class MaintenanceAuditEngine(BaseAuditEngine):
    """维修审计引擎"""

    def __init__(self):
        super().__init__('维修审计', 'maintenance')
        self.threshold_alert = ThresholdAlert()
        self.trend_analyzer = TrendAnalyzer()
        self.anomaly_detector = AnomalyDetector()

        rules = AUDIT_RULES.get('maintenance', {})
        for key, rule in rules.items():
            self.thresholds[key] = rule.get('default_threshold', 0)

    def run_audit(self) -> AuditResult:
        """执行维修审计"""
        if self.data is None or len(self.data) == 0:
            raise ValueError("没有加载审计数据")

        result = AuditResult(self.audit_type, self.name)
        result.data = self.data.copy()

        self._check_excessive_maintenance(result)
        self._check_maintenance_cost(result)
        self._check_maintenance_type_distribution(result)

        result.finalize()
        self.result = result
        return result

    def _check_excessive_maintenance(self, result: AuditResult):
        """过度维修识别"""
        asset_col = self._find_column(['车辆/设备编号', '设备编号', '车辆编号', '资产编号', '设备', '车辆'])
        date_col = self._find_column(['维修日期', '日期', 'date'])
        cost_col = self._find_column(['维修费用', '费用', '金额', 'cost', 'amount'])
        type_col = self._find_column(['维修类型', '维修类别', '维修项目', 'type'])

        if not asset_col or not date_col:
            return

        df = self.data.copy()
        df[date_col] = pd.to_datetime(df[date_col])

        df['year_month'] = df[date_col].dt.to_period('M')
        monthly_counts = df.groupby([asset_col, 'year_month']).size().reset_index(name='count')

        threshold = self.get_threshold('excessive_maintenance', 3)
        excessive = monthly_counts[monthly_counts['count'] > threshold]

        result.analysis_data['monthly_maintenance_counts'] = monthly_counts

        if len(excessive) > 0:
            excessive_assets = excessive[asset_col].unique()
            max_count = excessive['count'].max()
            risk_score = self._calculate_risk_score(len(excessive_assets), len(df[asset_col].unique()) * 0.05)
            risk_level = self._determine_risk_level(risk_score)

            affected = df[df[asset_col].isin(excessive_assets)]

            finding = AuditFinding(
                finding_type='过度维修识别',
                description=f"发现 {len(excessive_assets)} 台车辆/设备存在月度维修频次过高的情况（>{threshold}次/月）。"
                           f" 最高月维修频次为 {max_count} 次。"
                           f" 可能存在过度维修或维修管理不善的风险。",
                risk_level=risk_level,
                evidence={
                    'excessive_assets_count': len(excessive_assets),
                    'max_monthly_count': max_count,
                    'threshold_monthly': threshold,
                    'excessive_assets': excessive_assets.tolist()[:10]
                },
                affected_records=affected,
                risk_score=risk_score
            )
            result.add_finding(finding)

        if cost_col:
            df[cost_col] = pd.to_numeric(df[cost_col], errors='coerce')
            asset_cost_stats = df.groupby(asset_col)[cost_col].agg(
                ['count', 'sum', 'mean', 'max']
            ).reset_index()
            asset_cost_stats.columns = [asset_col, '维修次数', '累计费用', '平均费用', '单次最高费用']

            result.analysis_data['asset_maintenance_cost'] = asset_cost_stats

            high_cost_assets = asset_cost_stats.nlargest(10, '累计费用')

            if len(high_cost_assets) > 0:
                finding = AuditFinding(
                    finding_type='高费用资产',
                    description=f"维修费用最高的10台资产累计维修费 {high_cost_assets['累计费用'].sum():,.2f} 元，"
                               f"最高单台累计 {high_cost_assets.iloc[0]['累计费用']:,.2f} 元"
                               f"（{high_cost_assets.iloc[0][asset_col]}）。",
                    risk_level='low',
                    evidence={
                        'top10_total_cost': high_cost_assets['累计费用'].sum(),
                        'top_asset': high_cost_assets.iloc[0][asset_col],
                        'top_asset_cost': high_cost_assets.iloc[0]['累计费用']
                    },
                    affected_records=df[df[asset_col].isin(high_cost_assets[asset_col])],
                    risk_score=20.0
                )
                result.add_finding(finding)

    def _check_maintenance_cost(self, result: AuditResult):
        """维修费用分析"""
        cost_col = self._find_column(['维修费用', '费用', '金额', 'cost', 'amount'])
        date_col = self._find_column(['维修日期', '日期', 'date'])
        type_col = self._find_column(['维修类型', '维修类别', '维修项目', 'type'])

        if not cost_col:
            return

        df = self.data.copy()
        df[cost_col] = pd.to_numeric(df[cost_col], errors='coerce')
        df = df.dropna(subset=[cost_col])

        if len(df) == 0:
            return

        anomalies, info = self.threshold_alert.check_outliers_zscore(
            df, cost_col, z_threshold=3.0
        )

        result.analysis_data['cost_outliers'] = anomalies

        if len(anomalies) > 0:
            threshold = 3.0
            max_cost = df[cost_col].max()
            risk_score = self._calculate_risk_score(len(anomalies), len(df) * 0.02)
            risk_level = self._determine_risk_level(risk_score)

            finding = AuditFinding(
                finding_type='高额维修费用',
                description=f"检测出 {len(anomalies)} 笔异常高额维修费用（占比 {len(anomalies)/len(df):.2%}）。"
                           f" 最高单笔费用 {max_cost:,.2f} 元，"
                           f" 异常费用合计 {anomalies[cost_col].sum():,.2f} 元。",
                risk_level=risk_level,
                evidence={
                    'anomaly_count': len(anomalies),
                    'anomaly_total_cost': anomalies[cost_col].sum(),
                    'max_single_cost': max_cost,
                    'method': 'z-score'
                },
                affected_records=anomalies,
                risk_score=risk_score
            )
            result.add_finding(finding)

        if date_col:
            df[date_col] = pd.to_datetime(df[date_col])
            trend_df, trend_info = self.trend_analyzer.analyze_trend(
                df, date_col, cost_col, freq='M'
            )
            result.analysis_data['cost_trend'] = trend_df

            if 'trend_stats' in trend_info:
                stats = trend_info['trend_stats']
                if stats.get('growth_rate', 0) > 0.20:
                    finding = AuditFinding(
                        finding_type='维修费用增长趋势',
                        description=f"维修费用呈现明显上升趋势，期间增长率达 {stats['growth_rate']:.2%}。"
                                   f" 需关注费用增长合理性。",
                        risk_level='medium',
                        evidence={
                            'growth_rate': stats.get('growth_rate', 0),
                            'trend_direction': stats.get('trend_direction', 'stable')
                        },
                        affected_records=None,
                        risk_score=35.0
                    )
                    result.add_finding(finding)

        if type_col:
            type_stats = df.groupby(type_col)[cost_col].agg(
                ['count', 'sum', 'mean']
            ).reset_index()
            type_stats['cost_ratio'] = type_stats['sum'] / type_stats['sum'].sum()
            type_stats = type_stats.sort_values('sum', ascending=False)

            result.analysis_data['maintenance_by_type'] = type_stats

            top_type_ratio = type_stats.iloc[0]['cost_ratio'] if len(type_stats) > 0 else 0
            if top_type_ratio > 0.40:
                finding = AuditFinding(
                    finding_type='维修类型集中',
                    description=f"维修费用高度集中于「{type_stats.iloc[0][type_col]}」类型，"
                               f"占总费用的 {top_type_ratio:.2%}。",
                    risk_level='low',
                    evidence={
                        'top_type': type_stats.iloc[0][type_col],
                        'top_type_ratio': top_type_ratio
                    },
                    affected_records=df[df[type_col] == type_stats.iloc[0][type_col]],
                    risk_score=15.0
                )
                result.add_finding(finding)

    def _check_maintenance_type_distribution(self, result: AuditResult):
        """维修类型分布分析"""
        type_col = self._find_column(['维修类型', '维修类别', '维修项目', 'type'])
        vendor_col = self._find_column(['维修厂家', '承修单位', '供应商', 'vendor'])
        cost_col = self._find_column(['维修费用', '费用', '金额', 'cost', 'amount'])

        if not type_col:
            return

        df = self.data.copy()
        type_counts = df[type_col].value_counts().reset_index()
        type_counts.columns = [type_col, '次数']
        type_counts['占比'] = type_counts['次数'] / type_counts['次数'].sum()

        result.analysis_data['maintenance_type_distribution'] = type_counts

        if vendor_col and cost_col:
            df[cost_col] = pd.to_numeric(df[cost_col], errors='coerce')
            vendor_stats = df.groupby(vendor_col)[cost_col].agg(
                ['count', 'sum', 'mean']
            ).reset_index()
            vendor_stats['cost_ratio'] = vendor_stats['sum'] / vendor_stats['sum'].sum()
            vendor_stats = vendor_stats.sort_values('sum', ascending=False)

            result.analysis_data['maintenance_by_vendor'] = vendor_stats

            top_vendor_ratio = vendor_stats.iloc[0]['cost_ratio'] if len(vendor_stats) > 0 else 0
            if top_vendor_ratio > 0.50:
                finding = AuditFinding(
                    finding_type='维修供应商集中',
                    description=f"维修费用高度集中于「{vendor_stats.iloc[0][vendor_col]}」，"
                               f"占总费用的 {top_vendor_ratio:.2%}，可能存在供应商依赖风险。",
                    risk_level='medium',
                    evidence={
                        'top_vendor': vendor_stats.iloc[0][vendor_col],
                        'top_vendor_ratio': top_vendor_ratio
                    },
                    affected_records=df[df[vendor_col] == vendor_stats.iloc[0][vendor_col]],
                    risk_score=40.0
                )
                result.add_finding(finding)

    def _find_column(self, possible_names: List[str]) -> Optional[str]:
        """查找可能的列名"""
        if self.data is None:
            return None
        for name in possible_names:
            if name in self.data.columns:
                return name
            for col in self.data.columns:
                if name.lower() in col.lower() or col.lower() in name.lower():
                    if len(set(name.lower()) & set(col.lower())) > len(name.lower()) * 0.5:
                        return col
        return None
