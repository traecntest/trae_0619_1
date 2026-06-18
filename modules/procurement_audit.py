"""
采购审计模块
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Optional

from core import BaseAuditEngine, AuditFinding, AuditResult
from utils import ThresholdAlert, TrendAnalyzer, AnomalyDetector
from config import AUDIT_RULES


class ProcurementAuditEngine(BaseAuditEngine):
    """采购审计引擎"""

    def __init__(self):
        super().__init__('采购审计', 'procurement')
        self.threshold_alert = ThresholdAlert()
        self.trend_analyzer = TrendAnalyzer()
        self.anomaly_detector = AnomalyDetector()

        rules = AUDIT_RULES.get('procurement', {})
        for key, rule in rules.items():
            self.thresholds[key] = rule.get('default_threshold', 0)

    def run_audit(self) -> AuditResult:
        """执行采购审计"""
        if self.data is None or len(self.data) == 0:
            raise ValueError("没有加载审计数据")

        result = AuditResult(self.audit_type, self.name)
        result.data = self.data.copy()

        self._check_price_fluctuation(result)
        self._check_supplier_concentration(result)
        self._check_anomaly_transactions(result)
        self._check_purchase_allocation(result)
        self._check_round_amounts(result)

        result.finalize()
        self.result = result
        return result

    def _check_price_fluctuation(self, result: AuditResult):
        """价格波动预警分析"""
        material_col = self._find_column(['物料名称', '物料编码', '物料', '产品名称', '品名'])
        price_col = self._find_column(['单价', '价格', 'unit_price', 'price'])
        date_col = self._find_column(['采购日期', '日期', 'date'])

        if not material_col or not price_col:
            return

        if date_col:
            trend_df, trend_info = self.trend_analyzer.analyze_trend(
                self.data, date_col, price_col, freq='M', group_col=material_col
            )
            result.analysis_data['price_trend'] = trend_df
        else:
            trend_df = pd.DataFrame()

        price_stats = self.data.groupby(material_col)[price_col].agg(
            ['count', 'mean', 'std', 'min', 'max', 'median']
        ).reset_index()
        price_stats['cv'] = price_stats['std'] / price_stats['mean'].replace(0, np.nan)

        threshold = self.get_threshold('price_fluctuation', 0.15)
        high_fluctuation = price_stats[price_stats['cv'] > threshold]

        result.analysis_data['price_fluctuation_stats'] = price_stats

        if len(high_fluctuation) > 0:
            affected = self.data[self.data[material_col].isin(high_fluctuation[material_col])]
            max_cv = high_fluctuation['cv'].max()
            risk_score = self._calculate_risk_score(max_cv, threshold)
            risk_level = self._determine_risk_level(risk_score)

            finding = AuditFinding(
                finding_type='价格波动异常',
                description=f"发现 {len(high_fluctuation)} 种物料采购价格波动较大，变异系数超过 {threshold:.0%} 阈值。"
                           f" 最大变异系数为 {max_cv:.2%}（{high_fluctuation.iloc[0][material_col]}）。",
                risk_level=risk_level,
                evidence={
                    'high_fluctuation_materials': high_fluctuation[material_col].tolist(),
                    'threshold': threshold,
                    'max_cv': max_cv
                },
                affected_records=affected,
                risk_score=risk_score
            )
            result.add_finding(finding)

    def _check_supplier_concentration(self, result: AuditResult):
        """供应商集中度分析"""
        supplier_col = self._find_column(['供应商', '供应商名称', '供应商编号', 'supplier'])
        amount_col = self._find_column(['采购金额', '金额', '总价', 'amount'])

        if not supplier_col or not amount_col:
            return

        high_conc, conc_info = self.threshold_alert.check_concentration(
            self.data, amount_col, supplier_col,
            concentration_threshold=self.get_threshold('supplier_concentration', 0.30)
        )

        result.analysis_data['supplier_concentration'] = pd.DataFrame([
            {'供应商': k, '金额': v}
            for k, v in conc_info.get('concentration_ratios', {}).items()
        ])

        if conc_info.get('high_concentration_groups', 0) > 0:
            threshold = self.get_threshold('supplier_concentration', 0.30)
            max_ratio = max(conc_info.get('concentration_ratios', {}).values(), default=0)
            hhi = conc_info.get('herfindahl_index', 0)
            risk_score = self._calculate_risk_score(max_ratio, threshold)
            risk_level = self._determine_risk_level(risk_score)

            finding = AuditFinding(
                finding_type='供应商集中度风险',
                description=f"发现 {conc_info['high_concentration_groups']} 家供应商采购占比超过 {threshold:.0%}。"
                           f" 最高供应商占比为 {max_ratio:.2%}，赫芬达尔指数为 {hhi:.4f}。"
                           f" 可能存在供应商过度依赖风险。",
                risk_level=risk_level,
                evidence={
                    'high_concentration_suppliers': [
                        k for k, v in conc_info.get('concentration_ratios', {}).items()
                        if v > threshold
                    ],
                    'max_ratio': max_ratio,
                    'herfindahl_index': hhi
                },
                affected_records=high_conc,
                risk_score=risk_score
            )
            result.add_finding(finding)

    def _check_anomaly_transactions(self, result: AuditResult):
        """异常交易识别"""
        amount_col = self._find_column(['采购金额', '金额', '总价', 'amount'])

        if not amount_col:
            return

        anomalies_z, info_z = self.threshold_alert.check_outliers_zscore(
            self.data, amount_col,
            z_threshold=self.get_threshold('anomaly_transaction', 3.0)
        )

        anomalies_iqr, info_iqr = self.threshold_alert.check_outliers_iqr(
            self.data, amount_col
        )

        result.analysis_data['amount_outliers'] = anomalies_z

        if len(anomalies_z) > 0:
            threshold = self.get_threshold('anomaly_transaction', 3.0)
            z_values = (self.data[amount_col] - self.data[amount_col].mean()) / self.data[amount_col].std()
            max_z = z_values.abs().max()
            risk_score = self._calculate_risk_score(len(anomalies_z), len(self.data) * 0.01)
            risk_level = self._determine_risk_level(risk_score)

            finding = AuditFinding(
                finding_type='异常大额交易',
                description=f"使用Z-score方法检测出 {len(anomalies_z)} 笔异常交易（{len(anomalies_z)/len(self.data):.2%}），"
                           f"超过 {threshold} 个标准差。最大Z值为 {max_z:.2f}。"
                           f" 涉及总金额 {anomalies_z[amount_col].sum():,.2f} 元。",
                risk_level=risk_level,
                evidence={
                    'anomaly_count': len(anomalies_z),
                    'anomaly_percentage': len(anomalies_z) / len(self.data),
                    'total_anomaly_amount': anomalies_z[amount_col].sum(),
                    'method': 'z-score'
                },
                affected_records=anomalies_z,
                risk_score=risk_score
            )
            result.add_finding(finding)

        supplier_col = self._find_column(['供应商', '供应商名称', '供应商编号', 'supplier'])
        date_col = self._find_column(['采购日期', '日期', 'date'])

        if supplier_col and date_col:
            freq_anomalies, freq_info = self.anomaly_detector.detect_frequent_transactions(
                self.data, supplier_col, date_col,
                threshold=20,
                window_days=30
            )

            if freq_info.get('frequent_entities', 0) > 0:
                risk_score = 40.0
                risk_level = 'medium'

                finding = AuditFinding(
                    finding_type='供应商频繁交易',
                    description=f"发现 {freq_info['frequent_entities']} 家供应商在30天内交易次数超过20次。"
                               f" 最频繁交易次数为 {freq_info['max_transactions_in_window']} 次。",
                    risk_level=risk_level,
                    evidence={
                        'frequent_suppliers_count': freq_info['frequent_entities'],
                        'max_transactions': freq_info['max_transactions_in_window'],
                        'window_days': 30
                    },
                    affected_records=freq_anomalies,
                    risk_score=risk_score
                )
                result.add_finding(finding)

    def _check_purchase_allocation(self, result: AuditResult):
        """采购量分配分析"""
        material_col = self._find_column(['物料名称', '物料编码', '物料', '产品名称', '品名'])
        supplier_col = self._find_column(['供应商', '供应商名称', '供应商编号', 'supplier'])
        qty_col = self._find_column(['采购数量', '数量', 'quantity', 'qty'])

        if not all([material_col, supplier_col, qty_col]):
            return

        allocation = self.data.pivot_table(
            index=material_col,
            columns=supplier_col,
            values=qty_col,
            aggfunc='sum',
            fill_value=0
        )

        allocation_pct = allocation.div(allocation.sum(axis=1), axis=0)
        single_source_threshold = self.get_threshold('purchase_allocation', 0.50)
        single_source_materials = (allocation_pct.max(axis=1) > single_source_threshold).sum()

        result.analysis_data['purchase_allocation'] = allocation_pct.reset_index()

        if single_source_materials > 0:
            total_materials = len(allocation)
            risk_score = self._calculate_risk_score(single_source_materials, total_materials * 0.10)
            risk_level = self._determine_risk_level(risk_score)

            top_supplier_pct = allocation_pct.max(axis=1)
            high_conc_materials = top_supplier_pct[top_supplier_pct > single_source_threshold]

            finding = AuditFinding(
                finding_type='采购量分配集中',
                description=f"在 {total_materials} 种物料中，有 {single_source_materials} 种物料的单一供应商"
                           f"采购占比超过 {single_source_threshold:.0%}，存在单一货源依赖风险。"
                           f" 最高单一供应商占比为 {top_supplier_pct.max():.2%}。",
                risk_level=risk_level,
                evidence={
                    'single_source_materials': single_source_materials,
                    'total_materials': total_materials,
                    'threshold': single_source_threshold,
                    'max_single_supplier_ratio': top_supplier_pct.max(),
                    'materials_list': high_conc_materials.index.tolist()[:10]
                },
                affected_records=self.data[
                    self.data[material_col].isin(high_conc_materials.index)
                ],
                risk_score=risk_score
            )
            result.add_finding(finding)

    def _check_round_amounts(self, result: AuditResult):
        """整数金额检测"""
        amount_col = self._find_column(['采购金额', '金额', '总价', 'amount'])

        if not amount_col:
            return

        threshold = self.get_threshold('round_amount', 10000)
        round_amounts, round_info = self.anomaly_detector.detect_round_numbers(
            self.data, amount_col, threshold=threshold
        )

        if len(round_amounts) > 0:
            risk_score = 35.0
            risk_level = 'medium'

            finding = AuditFinding(
                finding_type='大额整数交易',
                description=f"发现 {len(round_amounts)} 笔大额整数交易（金额 ≥ {threshold:,.0f}元且为1000的整数倍），"
                           f"占总交易数的 {len(round_amounts)/len(self.data):.2%}。"
                           f" 涉及总金额 {round_amounts[amount_col].sum():,.2f} 元。",
                risk_level=risk_level,
                evidence={
                    'round_amount_count': len(round_amounts),
                    'round_amount_total': round_amounts[amount_col].sum(),
                    'threshold': threshold
                },
                affected_records=round_amounts,
                risk_score=risk_score
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
