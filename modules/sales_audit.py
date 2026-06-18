"""
销售审计模块
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Optional
from datetime import datetime

from core import BaseAuditEngine, AuditFinding, AuditResult
from utils import ThresholdAlert, TrendAnalyzer, AnomalyDetector
from config import AUDIT_RULES


class SalesAuditEngine(BaseAuditEngine):
    """销售审计引擎"""

    def __init__(self):
        super().__init__('销售审计', 'sales')
        self.threshold_alert = ThresholdAlert()
        self.trend_analyzer = TrendAnalyzer()
        self.anomaly_detector = AnomalyDetector()

        rules = AUDIT_RULES.get('sales', {})
        for key, rule in rules.items():
            self.thresholds[key] = rule.get('default_threshold', 0)

    def run_audit(self) -> AuditResult:
        """执行销售审计"""
        if self.data is None or len(self.data) == 0:
            raise ValueError("没有加载审计数据")

        result = AuditResult(self.audit_type, self.name)
        result.data = self.data.copy()

        self._check_price_compliance(result)
        self._check_credit_management(result)
        self._check_collection_cycle(result)
        self._check_return_anomaly(result)
        self._check_discount_anomaly(result)

        result.finalize()
        self.result = result
        return result

    def _check_price_compliance(self, result: AuditResult):
        """价格体系合规性检查"""
        product_col = self._find_column(['产品名称', '产品编码', '产品', '商品名称', '品名'])
        price_col = self._find_column(['单价', '售价', '价格', 'unit_price', 'price'])
        amount_col = self._find_column(['销售金额', '金额', '总价', 'amount'])

        if not product_col or not price_col:
            return

        price_stats = self.data.groupby(product_col)[price_col].agg(
            ['count', 'mean', 'std', 'min', 'max', 'median']
        ).reset_index()

        price_stats['range_ratio'] = (price_stats['max'] - price_stats['min']) / price_stats['mean'].replace(0, np.nan)
        price_stats['cv'] = price_stats['std'] / price_stats['mean'].replace(0, np.nan)

        threshold = self.get_threshold('price_compliance', 0.10)
        non_compliant = price_stats[price_stats['cv'] > threshold]

        result.analysis_data['price_compliance_stats'] = price_stats

        if len(non_compliant) > 0:
            max_cv = non_compliant['cv'].max()
            risk_score = self._calculate_risk_score(max_cv, threshold)
            risk_level = self._determine_risk_level(risk_score)

            affected = self.data[self.data[product_col].isin(non_compliant[product_col])]

            finding = AuditFinding(
                finding_type='价格体系不合规',
                description=f"发现 {len(non_compliant)} 种产品销售价格波动较大，变异系数超过 {threshold:.0%} 阈值。"
                           f" 最大变异系数为 {max_cv:.2%}（{non_compliant.iloc[0][product_col]}）。"
                           f" 可能存在价格执行不一致或越权定价风险。",
                risk_level=risk_level,
                evidence={
                    'non_compliant_products': non_compliant[product_col].tolist(),
                    'threshold': threshold,
                    'max_cv': max_cv
                },
                affected_records=affected,
                risk_score=risk_score
            )
            result.add_finding(finding)

    def _check_credit_management(self, result: AuditResult):
        """客户信用管理检查"""
        customer_col = self._find_column(['客户名称', '客户', '客户编号', 'customer'])
        credit_col = self._find_column(['信用额度', '信用限额', 'credit_limit', 'credit'])
        amount_col = self._find_column(['销售金额', '应收账款', '应收余额', 'amount'])
        receivable_col = self._find_column(['应收账款余额', '应收余额', '应收账款', 'receivable'])

        if not customer_col:
            return

        amount_field = receivable_col if receivable_col else amount_col

        if not amount_field:
            return

        if credit_col:
            customer_credit = self.data.groupby(customer_col).agg(
                total_amount=(amount_field, 'sum'),
                credit_limit=(credit_col, 'max')
            ).reset_index()

            customer_credit['credit_usage_ratio'] = (
                customer_credit['total_amount'] / customer_credit['credit_limit'].replace(0, np.nan)
            )

            threshold = self.get_threshold('credit_management', 1.0)
            over_credit = customer_credit[customer_credit['credit_usage_ratio'] > threshold]

            result.analysis_data['credit_usage'] = customer_credit

            if len(over_credit) > 0:
                max_ratio = over_credit['credit_usage_ratio'].max()
                risk_score = self._calculate_risk_score(max_ratio, threshold)
                risk_level = self._determine_risk_level(risk_score, risk_level_override='high' if risk_score > 60 else 'medium')

                affected = self.data[
                    self.data[customer_col].isin(over_credit[customer_col])
                ]

                finding = AuditFinding(
                    finding_type='客户超信用额度',
                    description=f"发现 {len(over_credit)} 家客户信用额度使用率超过 {threshold:.0%}。"
                               f" 最高使用率为 {max_ratio:.2%}（{over_credit.iloc[0][customer_col]}）。"
                               f" 存在坏账风险。",
                    risk_level=risk_level,
                    evidence={
                        'over_credit_customers': over_credit[customer_col].tolist(),
                        'max_credit_usage': max_ratio,
                        'threshold': threshold,
                        'total_over_amount': (
                            over_credit['total_amount'] - over_credit['credit_limit']
                        ).sum()
                    },
                    affected_records=affected,
                    risk_score=risk_score
                )
                result.add_finding(finding)
        else:
            customer_totals = self.data.groupby(customer_col)[amount_field].sum().sort_values(ascending=False)
            total_receivable = customer_totals.sum()
            top10_ratio = customer_totals.head(10).sum() / total_receivable if total_receivable > 0 else 0

            result.analysis_data['customer_concentration'] = (
                customer_totals.reset_index()
            )

            if top10_ratio > 0.5:
                risk_score = 45.0
                risk_level = 'medium'

                finding = AuditFinding(
                    finding_type='客户集中度风险',
                    description=f"前10大客户应收账款占比达 {top10_ratio:.2%}，"
                               f"超过50%警戒线，存在客户集中度过高风险。",
                    risk_level=risk_level,
                    evidence={
                        'top10_ratio': top10_ratio,
                        'top_customers': customer_totals.head(10).index.tolist()
                    },
                    affected_records=self.data[
                        self.data[customer_col].isin(customer_totals.head(10).index)
                    ],
                    risk_score=risk_score
                )
                result.add_finding(finding)

    def _check_collection_cycle(self, result: AuditResult):
        """回款周期分析"""
        customer_col = self._find_column(['客户名称', '客户', '客户编号', 'customer'])
        sale_date_col = self._find_column(['销售日期', '日期', 'sale_date', 'date'])
        due_date_col = self._find_column(['应回款日期', '到期日', '应付款日期', 'due_date'])
        actual_pay_col = self._find_column(['实际回款日期', '实际到账日期', '收款日期', 'pay_date'])
        receivable_col = self._find_column(['应收账款余额', '应收余额', '应收账款', 'receivable'])
        aging_col = self._find_column(['账龄', '账龄天数', 'aging'])

        if not customer_col:
            return

        if aging_col and receivable_col:
            aging_stats = self.data.groupby(customer_col).agg(
                avg_aging=(aging_col, 'mean'),
                max_aging=(aging_col, 'max'),
                total_receivable=(receivable_col, 'sum')
            ).reset_index()

            threshold = self.get_threshold('collection_cycle', 90)
            long_aging = aging_stats[aging_stats['avg_aging'] > threshold]

            result.analysis_data['aging_analysis'] = aging_stats

            if len(long_aging) > 0:
                max_aging = long_aging['max_aging'].max()
                risk_score = self._calculate_risk_score(
                    long_aging['total_receivable'].sum(),
                    aging_stats['total_receivable'].sum() * 0.20
                )
                risk_level = self._determine_risk_level(risk_score)

                affected = self.data[self.data[customer_col].isin(long_aging[customer_col])]

                finding = AuditFinding(
                    finding_type='长账龄应收账款',
                    description=f"发现 {len(long_aging)} 家客户平均账龄超过 {threshold} 天。"
                               f" 最长账龄 {max_aging:.0f} 天，"
                               f" 涉及长账龄应收账款合计 {long_aging['total_receivable'].sum():,.2f} 元。",
                    risk_level=risk_level,
                    evidence={
                        'long_aging_customers': long_aging[customer_col].tolist(),
                        'threshold_days': threshold,
                        'max_aging_days': max_aging,
                        'total_long_aging_amount': long_aging['total_receivable'].sum()
                    },
                    affected_records=affected,
                    risk_score=risk_score
                )
                result.add_finding(finding)

        elif sale_date_col and actual_pay_col:
            df = self.data.copy()
            df[sale_date_col] = pd.to_datetime(df[sale_date_col])
            df[actual_pay_col] = pd.to_datetime(df[actual_pay_col])

            valid_payments = df[df[actual_pay_col].notna()]
            if len(valid_payments) > 0:
                valid_payments['collection_days'] = (
                    valid_payments[actual_pay_col] - valid_payments[sale_date_col]
                ).dt.days

                collection_stats = valid_payments.groupby(customer_col)['collection_days'].agg(
                    ['mean', 'median', 'max', 'count']
                ).reset_index()

                threshold = self.get_threshold('collection_cycle', 90)
                slow_payers = collection_stats[collection_stats['mean'] > threshold]

                result.analysis_data['collection_cycle'] = collection_stats

                if len(slow_payers) > 0:
                    max_days = slow_payers['max'].max()
                    risk_score = 40.0
                    risk_level = 'medium'

                    finding = AuditFinding(
                        finding_type='回款周期异常',
                        description=f"发现 {len(slow_payers)} 家客户平均回款周期超过 {threshold} 天。"
                                   f" 最长回款周期 {max_days:.0f} 天。",
                        risk_level=risk_level,
                        evidence={
                            'slow_payers': slow_payers[customer_col].tolist(),
                            'threshold_days': threshold,
                            'max_days': max_days
                        },
                        affected_records=valid_payments[
                            valid_payments[customer_col].isin(slow_payers[customer_col])
                        ],
                        risk_score=risk_score
                    )
                    result.add_finding(finding)

    def _check_return_anomaly(self, result: AuditResult):
        """退货异常检测"""
        return_flag = self._find_column(['是否退货', '退货标记', '退货', 'is_return', 'returned'])
        return_qty_col = self._find_column(['退货数量', '退库数量', 'return_qty'])
        qty_col = self._find_column(['销售数量', '数量', 'quantity', 'qty'])
        product_col = self._find_column(['产品名称', '产品编码', '产品', '商品名称', '品名'])
        customer_col = self._find_column(['客户名称', '客户', '客户编号', 'customer'])
        amount_col = self._find_column(['销售金额', '金额', 'amount'])

        if not product_col:
            return

        if return_flag or return_qty_col:
            if return_flag:
                return_data = self.data[self.data[return_flag].isin(
                    ['是', 'Y', 'y', 'Yes', 'yes', True, 1, '1']
                )]
                return_count = len(return_data)
                total_count = len(self.data)
                return_rate = return_count / total_count if total_count > 0 else 0
            else:
                return_data = self.data[self.data[return_qty_col].fillna(0) > 0]
                return_count = len(return_data)
                total_count = len(self.data)
                return_rate = return_count / total_count if total_count > 0 else 0

            threshold = self.get_threshold('return_anomaly', 0.10)

            product_return_rate = self._calculate_return_rate(
                self.data, product_col, return_flag, return_qty_col, qty_col
            )

            high_return_products = product_return_rate[product_return_rate['return_rate'] > threshold]

            result.analysis_data['product_return_rate'] = product_return_rate

            if len(high_return_products) > 0:
                max_rate = high_return_products['return_rate'].max()
                risk_score = self._calculate_risk_score(max_rate, threshold)
                risk_level = self._determine_risk_level(risk_score)

                finding = AuditFinding(
                    finding_type='产品退货率异常',
                    description=f"发现 {len(high_return_products)} 种产品退货率超过 {threshold:.0%} 阈值。"
                               f" 最高退货率为 {max_rate:.2%}（{high_return_products.iloc[0][product_col]}）。"
                               f" 整体退货率为 {return_rate:.2%}。",
                    risk_level=risk_level,
                    evidence={
                        'high_return_products': high_return_products[product_col].tolist(),
                        'overall_return_rate': return_rate,
                        'max_return_rate': max_rate,
                        'threshold': threshold
                    },
                    affected_records=self.data[
                        self.data[product_col].isin(high_return_products[product_col])
                    ],
                    risk_score=risk_score
                )
                result.add_finding(finding)

            if customer_col:
                customer_return_rate = self._calculate_return_rate(
                    self.data, customer_col, return_flag, return_qty_col, qty_col
                )
                high_return_customers = customer_return_rate[customer_return_rate['return_rate'] > threshold]

                if len(high_return_customers) > 0:
                    finding = AuditFinding(
                        finding_type='客户退货异常',
                        description=f"发现 {len(high_return_customers)} 家客户退货率超过 {threshold:.0%} 阈值。"
                                   f" 最高退货率为 {high_return_customers['return_rate'].max():.2%}"
                                   f"（{high_return_customers.iloc[0][customer_col]}）。",
                        risk_level='medium',
                        evidence={
                            'high_return_customers': high_return_customers[customer_col].tolist(),
                            'max_return_rate': high_return_customers['return_rate'].max()
                        },
                        affected_records=self.data[
                            self.data[customer_col].isin(high_return_customers[customer_col])
                        ],
                        risk_score=35.0
                    )
                    result.add_finding(finding)

    def _calculate_return_rate(
        self,
        df: pd.DataFrame,
        group_col: str,
        return_flag: Optional[str],
        return_qty_col: Optional[str],
        qty_col: Optional[str]
    ) -> pd.DataFrame:
        """计算分组退货率"""
        if return_flag and qty_col:
            total_qty = df.groupby(group_col)[qty_col].sum()
            return_qty = df[df[return_flag].isin(
                ['是', 'Y', 'y', 'Yes', 'yes', True, 1, '1']
            )].groupby(group_col)[qty_col].sum()
            result = pd.DataFrame({'total_qty': total_qty, 'return_qty': return_qty.fillna(0)})
            result['return_rate'] = result['return_qty'] / result['total_qty'].replace(0, np.nan)
        elif return_qty_col and qty_col:
            total_qty = df.groupby(group_col)[qty_col].sum()
            return_qty = df.groupby(group_col)[return_qty_col].sum().fillna(0)
            result = pd.DataFrame({'total_qty': total_qty, 'return_qty': return_qty})
            result['return_rate'] = result['return_qty'] / result['total_qty'].replace(0, np.nan)
        else:
            total_count = df.groupby(group_col).size()
            if return_flag:
                return_count = df[df[return_flag].isin(
                    ['是', 'Y', 'y', 'Yes', 'yes', True, 1, '1']
                )].groupby(group_col).size()
            else:
                return_count = df[df[return_qty_col].fillna(0) > 0].groupby(group_col).size()
            result = pd.DataFrame({'total_count': total_count, 'return_count': return_count.fillna(0)})
            result['return_rate'] = result['return_count'] / result['total_count'].replace(0, np.nan)

        return result.reset_index().sort_values('return_rate', ascending=False)

    def _check_discount_anomaly(self, result: AuditResult):
        """折扣异常分析"""
        discount_col = self._find_column(['折扣金额', '折扣', 'discount', 'discount_amount'])
        discount_rate_col = self._find_column(['折扣率', '折扣比例', 'discount_rate'])
        amount_col = self._find_column(['销售金额', '原价金额', 'amount'])
        customer_col = self._find_column(['客户名称', '客户', '客户编号', 'customer'])
        product_col = self._find_column(['产品名称', '产品编码', '产品', '商品名称', '品名'])

        if not discount_col and not discount_rate_col:
            return

        df = self.data.copy()

        if discount_rate_col:
            df['_discount_rate'] = pd.to_numeric(df[discount_rate_col], errors='coerce')
        elif discount_col and amount_col:
            df['_discount_amount'] = pd.to_numeric(df[discount_col], errors='coerce')
            df['_original_amount'] = pd.to_numeric(df[amount_col], errors='coerce') + df['_discount_amount'].fillna(0)
            df['_discount_rate'] = df['_discount_amount'] / df['_original_amount'].replace(0, np.nan)
        else:
            return

        threshold = self.get_threshold('discount_anomaly', 0.30)
        high_discount = df[df['_discount_rate'] > threshold]

        result.analysis_data['discount_analysis'] = df[
            [col for col in df.columns if not col.startswith('_')]
        ].assign(折扣率=df['_discount_rate'].values)

        if len(high_discount) > 0:
            max_discount = df['_discount_rate'].max()
            risk_score = self._calculate_risk_score(max_discount, threshold)
            risk_level = self._determine_risk_level(risk_score)

            finding = AuditFinding(
                finding_type='异常高额折扣',
                description=f"发现 {len(high_discount)} 笔订单折扣率超过 {threshold:.0%} 阈值，"
                           f"占总订单数的 {len(high_discount)/len(df):.2%}。"
                           f" 最高折扣率为 {max_discount:.2%}。",
                risk_level=risk_level,
                evidence={
                    'high_discount_count': len(high_discount),
                    'max_discount_rate': max_discount,
                    'threshold': threshold,
                    'total_discount_amount': high_discount.get('_discount_amount', pd.Series()).sum()
                },
                affected_records=high_discount[[col for col in high_discount.columns if not col.startswith('_')]],
                risk_score=risk_score
            )
            result.add_finding(finding)

            if customer_col:
                customer_avg_discount = df.groupby(customer_col)['_discount_rate'].mean().sort_values(ascending=False)
                high_discount_customers = customer_avg_discount[customer_avg_discount > threshold * 0.7]

                if len(high_discount_customers) > 0:
                    finding = AuditFinding(
                        finding_type='客户折扣异常',
                        description=f"发现 {len(high_discount_customers)} 家客户平均折扣率偏高。"
                                   f" 最高平均折扣率为 {high_discount_customers.iloc[0]:.2%}"
                                   f"（{high_discount_customers.index[0]}）。",
                        risk_level='medium',
                        evidence={
                            'high_discount_customers': high_discount_customers.index.tolist(),
                            'max_avg_discount': high_discount_customers.max()
                        },
                        affected_records=df[
                            df[customer_col].isin(high_discount_customers.index)
                        ][[col for col in df.columns if not col.startswith('_')]],
                        risk_score=30.0
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

    def _determine_risk_level(self, risk_score: float, risk_level_override: Optional[str] = None) -> str:
        """确定风险等级，支持覆盖"""
        if risk_level_override:
            return risk_level_override
        return super()._determine_risk_level(risk_score)
