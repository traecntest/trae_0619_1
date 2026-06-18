"""
生产审计模块
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Optional

from core import BaseAuditEngine, AuditFinding, AuditResult
from utils import ThresholdAlert, TrendAnalyzer, AnomalyDetector
from config import AUDIT_RULES


class ProductionAuditEngine(BaseAuditEngine):
    """生产审计引擎"""

    def __init__(self):
        super().__init__('生产审计', 'production')
        self.threshold_alert = ThresholdAlert()
        self.trend_analyzer = TrendAnalyzer()
        self.anomaly_detector = AnomalyDetector()

        rules = AUDIT_RULES.get('production', {})
        for key, rule in rules.items():
            self.thresholds[key] = rule.get('default_threshold', 0)

    def run_audit(self) -> AuditResult:
        """执行生产审计"""
        if self.data is None or len(self.data) == 0:
            raise ValueError("没有加载审计数据")

        result = AuditResult(self.audit_type, self.name)
        result.data = self.data.copy()

        self._check_material_variance(result)
        self._check_completion_rate(result)
        self._check_scrap_rate(result)
        self._check_production_efficiency(result)

        result.finalize()
        self.result = result
        return result

    def _check_material_variance(self, result: AuditResult):
        """领料差异分析"""
        product_col = self._find_column(['产品名称', '产品编码', '产品', 'product'])
        material_col = self._find_column(['物料名称', '物料编码', '物料', 'material'])
        std_qty_col = self._find_column(['标准用量', '标准领料', '定额用量', 'standard_qty'])
        actual_qty_col = self._find_column(['实际用量', '实际领料', '领料数量', 'actual_qty'])

        if not all([std_qty_col, actual_qty_col]):
            return

        df = self.data.copy()
        df[std_qty_col] = pd.to_numeric(df[std_qty_col], errors='coerce')
        df[actual_qty_col] = pd.to_numeric(df[actual_qty_col], errors='coerce')

        df = df.dropna(subset=[std_qty_col, actual_qty_col])
        df = df[df[std_qty_col] > 0]

        if len(df) == 0:
            return

        df['material_variance'] = df[actual_qty_col] - df[std_qty_col]
        df['material_variance_rate'] = df['material_variance'] / df[std_qty_col]

        threshold = self.get_threshold('material_variance', 0.10)
        high_variance = df[df['material_variance_rate'].abs() > threshold]

        result.analysis_data['material_variance'] = df

        if len(high_variance) > 0:
            max_variance = df['material_variance_rate'].abs().max()
            avg_variance = df['material_variance_rate'].mean()
            risk_score = self._calculate_risk_score(len(high_variance), len(df) * 0.05)
            risk_level = self._determine_risk_level(risk_score)

            variance_summary = f"超耗" if avg_variance > 0 else "节约"

            finding = AuditFinding(
                finding_type='物料领用差异异常',
                description=f"发现 {len(high_variance)} 条记录物料领用差异率超过 ±{threshold:.0%}，"
                           f"占总记录数的 {len(high_variance)/len(df):.2%}。"
                           f" 最大差异率为 {max_variance:.2%}，"
                           f" 整体平均差异率为 {avg_variance:.2%}（{variance_summary}）。",
                risk_level=risk_level,
                evidence={
                    'high_variance_count': len(high_variance),
                    'max_variance_rate': max_variance,
                    'avg_variance_rate': avg_variance,
                    'threshold': threshold,
                    'total_variance_amount': df['material_variance'].sum()
                },
                affected_records=high_variance,
                risk_score=risk_score
            )
            result.add_finding(finding)

        if material_col:
            material_stats = df.groupby(material_col)['material_variance_rate'].agg(
                ['count', 'mean', 'std', 'max', 'min']
            ).reset_index()

            high_variance_materials = material_stats[
                material_stats['mean'].abs() > threshold * 0.5
            ]

            if len(high_variance_materials) > 0:
                result.analysis_data['material_variance_by_material'] = material_stats

                finding = AuditFinding(
                    finding_type='物料差异按物料分析',
                    description=f"发现 {len(high_variance_materials)} 种物料平均领用差异率偏高。"
                               f" 差异最大的物料：{high_variance_materials.iloc[0][material_col]}"
                               f"（{high_variance_materials.iloc[0]['mean']:.2%}）。",
                    risk_level='low',
                    evidence={
                        'high_variance_materials': high_variance_materials[material_col].tolist(),
                        'top_variance_material': high_variance_materials.iloc[0][material_col],
                        'top_variance_rate': high_variance_materials.iloc[0]['mean']
                    },
                    affected_records=df[df[material_col].isin(high_variance_materials[material_col])],
                    risk_score=25.0
                )
                result.add_finding(finding)

        if product_col:
            product_stats = df.groupby(product_col)['material_variance_rate'].agg(
                ['count', 'mean', 'std', 'max', 'min']
            ).reset_index()

            high_variance_products = product_stats[
                product_stats['mean'].abs() > threshold * 0.5
            ]

            if len(high_variance_products) > 0:
                result.analysis_data['material_variance_by_product'] = product_stats

    def _check_completion_rate(self, result: AuditResult):
        """完工入库分析"""
        product_col = self._find_column(['产品名称', '产品编码', '产品', 'product'])
        plan_qty_col = self._find_column(['计划产量', '计划数量', '生产计划量', 'plan_qty'])
        actual_qty_col = self._find_column(['实际产量', '实际数量', '完工数量', '入库数量', 'actual_qty'])
        date_col = self._find_column(['生产日期', '入库日期', '日期', 'date'])

        if not all([plan_qty_col, actual_qty_col]):
            return

        df = self.data.copy()
        df[plan_qty_col] = pd.to_numeric(df[plan_qty_col], errors='coerce')
        df[actual_qty_col] = pd.to_numeric(df[actual_qty_col], errors='coerce')

        df = df.dropna(subset=[plan_qty_col, actual_qty_col])
        df = df[df[plan_qty_col] > 0]

        if len(df) == 0:
            return

        df['completion_rate'] = df[actual_qty_col] / df[plan_qty_col]

        threshold = self.get_threshold('completion_rate', 0.90)
        low_completion = df[df['completion_rate'] < threshold]

        result.analysis_data['completion_rate'] = df

        avg_completion = df['completion_rate'].mean()

        if len(low_completion) > 0:
            risk_score = self._calculate_risk_score(1 - avg_completion, 1 - threshold)
            risk_level = self._determine_risk_level(risk_score)

            finding = AuditFinding(
                finding_type='生产完工率偏低',
                description=f"发现 {len(low_completion)} 条生产记录完工率低于 {threshold:.0%}，"
                           f"占总记录数的 {len(low_completion)/len(df):.2%}。"
                           f" 整体平均完工率为 {avg_completion:.2%}，"
                           f" 最低完工率为 {df['completion_rate'].min():.2%}。",
                risk_level=risk_level,
                evidence={
                    'low_completion_count': len(low_completion),
                    'avg_completion_rate': avg_completion,
                    'min_completion_rate': df['completion_rate'].min(),
                    'threshold': threshold
                },
                affected_records=low_completion,
                risk_score=risk_score
            )
            result.add_finding(finding)

        if date_col:
            trend_df, trend_info = self.trend_analyzer.analyze_trend(
                df, date_col, 'completion_rate', freq='W'
            )
            result.analysis_data['completion_trend'] = trend_df

    def _check_scrap_rate(self, result: AuditResult):
        """报废率监控"""
        product_col = self._find_column(['产品名称', '产品编码', '产品', 'product'])
        scrap_qty_col = self._find_column(['报废数量', '废品数量', '不合格数量', 'scrap_qty'])
        total_qty_col = self._find_column(['总产量', '投产数量', '总数量', 'total_qty', 'plan_qty'])
        actual_qty_col = self._find_column(['实际产量', '完工数量', '入库数量', 'actual_qty'])
        date_col = self._find_column(['生产日期', '报废日期', '日期', 'date'])

        if not scrap_qty_col:
            return

        df = self.data.copy()
        df[scrap_qty_col] = pd.to_numeric(df[scrap_qty_col], errors='coerce').fillna(0)

        if total_qty_col and total_qty_col in df.columns:
            df[total_qty_col] = pd.to_numeric(df[total_qty_col], errors='coerce')
        elif actual_qty_col and actual_qty_col in df.columns:
            df[total_qty_col] = pd.to_numeric(df[actual_qty_col], errors='coerce') + df[scrap_qty_col]
        else:
            return

        df = df.dropna(subset=[total_qty_col])
        df = df[df[total_qty_col] > 0]

        if len(df) == 0:
            return

        df['scrap_rate'] = df[scrap_qty_col] / df[total_qty_col]

        threshold = self.get_threshold('scrap_rate', 0.05)
        high_scrap = df[df['scrap_rate'] > threshold]

        result.analysis_data['scrap_rate'] = df

        avg_scrap_rate = df['scrap_rate'].mean()

        if len(high_scrap) > 0:
            max_scrap = df['scrap_rate'].max()
            risk_score = self._calculate_risk_score(avg_scrap_rate, threshold)
            risk_level = self._determine_risk_level(risk_score)

            finding = AuditFinding(
                finding_type='报废率超标',
                description=f"发现 {len(high_scrap)} 条记录报废率超过 {threshold:.2%} 阈值，"
                           f"占总记录数的 {len(high_scrap)/len(df):.2%}。"
                           f" 整体平均报废率为 {avg_scrap_rate:.2%}，"
                           f" 最高报废率为 {max_scrap:.2%}。"
                           f" 总报废数量：{df[scrap_qty_col].sum():,.0f}。",
                risk_level=risk_level,
                evidence={
                    'high_scrap_count': len(high_scrap),
                    'avg_scrap_rate': avg_scrap_rate,
                    'max_scrap_rate': max_scrap,
                    'threshold': threshold,
                    'total_scrap_qty': df[scrap_qty_col].sum()
                },
                affected_records=high_scrap,
                risk_score=risk_score
            )
            result.add_finding(finding)

        if product_col:
            product_scrap = df.groupby(product_col).agg(
                total_qty=(total_qty_col, 'sum'),
                scrap_qty=(scrap_qty_col, 'sum'),
                count=(scrap_qty_col, 'count')
            ).reset_index()
            product_scrap['scrap_rate'] = product_scrap['scrap_qty'] / product_scrap['total_qty']
            product_scrap = product_scrap.sort_values('scrap_rate', ascending=False)

            high_scrap_products = product_scrap[product_scrap['scrap_rate'] > threshold]

            result.analysis_data['scrap_rate_by_product'] = product_scrap

            if len(high_scrap_products) > 0:
                finding = AuditFinding(
                    finding_type='产品报废率异常',
                    description=f"发现 {len(high_scrap_products)} 种产品报废率超过 {threshold:.2%} 阈值。"
                               f" 最高报废率产品：{high_scrap_products.iloc[0][product_col]}"
                               f"（{high_scrap_products.iloc[0]['scrap_rate']:.2%}）。",
                    risk_level='medium',
                    evidence={
                        'high_scrap_products': high_scrap_products[product_col].tolist(),
                        'top_scrap_product': high_scrap_products.iloc[0][product_col],
                        'top_scrap_rate': high_scrap_products.iloc[0]['scrap_rate']
                    },
                    affected_records=df[
                        df[product_col].isin(high_scrap_products[product_col])
                    ],
                    risk_score=45.0
                )
                result.add_finding(finding)

        if date_col:
            trend_df, trend_info = self.trend_analyzer.detect_abnormal_trend(
                df, date_col, scrap_qty_col, threshold=0.30, freq='M'
            )
            result.analysis_data['scrap_trend'] = trend_df

            if len(trend_df) > 0:
                finding = AuditFinding(
                    finding_type='报废趋势异常波动',
                    description=f"检测到报废数量存在异常波动期。"
                               f" 最大环比增幅 {trend_info.get('max_increase', 0):.2%}，"
                               f" 最大环比降幅 {trend_info.get('max_decrease', 0):.2%}。",
                    risk_level='low',
                    evidence={
                        'abnormal_periods': len(trend_df),
                        'max_increase': trend_info.get('max_increase', 0),
                        'max_decrease': trend_info.get('max_decrease', 0)
                    },
                    affected_records=None,
                    risk_score=20.0
                )
                result.add_finding(finding)

    def _check_production_efficiency(self, result: AuditResult):
        """生产效率分析"""
        product_col = self._find_column(['产品名称', '产品编码', '产品', 'product'])
        output_col = self._find_column(['实际产量', '完工数量', '产量', 'output_qty'])
        hours_col = self._find_column(['工时', '生产工时', '投入工时', 'man_hours', 'hours'])
        date_col = self._find_column(['生产日期', '日期', 'date'])

        if not all([output_col, hours_col]):
            return

        df = self.data.copy()
        df[output_col] = pd.to_numeric(df[output_col], errors='coerce')
        df[hours_col] = pd.to_numeric(df[hours_col], errors='coerce')

        df = df.dropna(subset=[output_col, hours_col])
        df = df[df[hours_col] > 0]

        if len(df) == 0:
            return

        df['efficiency'] = df[output_col] / df[hours_col]

        threshold = self.get_threshold('production_efficiency', 0.85)
        avg_efficiency = df['efficiency'].mean()
        efficiency_std = df['efficiency'].std()

        if efficiency_std > 0:
            df['efficiency_zscore'] = (df['efficiency'] - avg_efficiency) / efficiency_std
            low_eff = df[df['efficiency_zscore'] < -2]
        else:
            low_eff = pd.DataFrame()

        result.analysis_data['production_efficiency'] = df

        if len(low_eff) > 0:
            min_eff = df['efficiency'].min()
            risk_score = 30.0
            risk_level = 'low'

            finding = AuditFinding(
                finding_type='生产效率异常偏低',
                description=f"发现 {len(low_eff)} 条记录生产效率显著偏低（低于均值2个标准差）。"
                           f" 平均效率为 {avg_efficiency:.4f} 单位/工时，"
                           f" 最低效率为 {min_eff:.4f} 单位/工时。",
                risk_level=risk_level,
                evidence={
                    'low_efficiency_count': len(low_eff),
                    'avg_efficiency': avg_efficiency,
                    'min_efficiency': min_eff
                },
                affected_records=low_eff,
                risk_score=risk_score
            )
            result.add_finding(finding)

        if date_col:
            trend_df, trend_info = self.trend_analyzer.analyze_trend(
                df, date_col, 'efficiency', freq='W'
            )
            result.analysis_data['efficiency_trend'] = trend_df

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
