"""
审计引擎基类
所有审计模块都继承自此基类
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Any, Optional, Tuple
from abc import ABC, abstractmethod
from datetime import datetime


class AuditFinding:
    """审计发现（疑点）"""

    def __init__(
        self,
        finding_type: str,
        description: str,
        risk_level: str = 'medium',
        evidence: Optional[Dict] = None,
        affected_records: Optional[pd.DataFrame] = None,
        risk_score: float = 0.0
    ):
        self.finding_type = finding_type
        self.description = description
        self.risk_level = risk_level
        self.evidence = evidence or {}
        self.affected_records = affected_records
        self.risk_score = risk_score
        self.created_at = datetime.now()

    def to_dict(self) -> Dict[str, Any]:
        return {
            'finding_type': self.finding_type,
            'description': self.description,
            'risk_level': self.risk_level,
            'risk_score': self.risk_score,
            'evidence': self.evidence,
            'affected_count': len(self.affected_records) if self.affected_records is not None else 0,
            'created_at': self.created_at.strftime('%Y-%m-%d %H:%M:%S')
        }


class AuditResult:
    """审计结果"""

    def __init__(self, audit_type: str, audit_name: str):
        self.audit_type = audit_type
        self.audit_name = audit_name
        self.findings: List[AuditFinding] = []
        self.summary: Dict[str, Any] = {}
        self.data: Optional[pd.DataFrame] = None
        self.analysis_data: Dict[str, pd.DataFrame] = {}
        self.start_time = datetime.now()
        self.end_time: Optional[datetime] = None

    def add_finding(self, finding: AuditFinding):
        self.findings.append(finding)

    def finalize(self):
        self.end_time = datetime.now()
        self._generate_summary()

    def _generate_summary(self):
        risk_counts = {'high': 0, 'medium': 0, 'low': 0, 'none': 0}
        total_score = 0.0

        for finding in self.findings:
            risk_counts[finding.risk_level] = risk_counts.get(finding.risk_level, 0) + 1
            total_score += finding.risk_score

        self.summary = {
            'total_findings': len(self.findings),
            'risk_counts': risk_counts,
            'average_risk_score': total_score / len(self.findings) if self.findings else 0,
            'overall_risk_level': self._calculate_overall_risk(risk_counts, total_score),
            'duration_seconds': (self.end_time - self.start_time).total_seconds() if self.end_time else 0
        }

    def _calculate_overall_risk(self, risk_counts: Dict, total_score: float) -> str:
        if risk_counts.get('high', 0) > 0:
            return 'high'
        elif risk_counts.get('medium', 0) > 2:
            return 'high'
        elif risk_counts.get('medium', 0) > 0:
            return 'medium'
        elif risk_counts.get('low', 0) > 0:
            return 'low'
        return 'none'

    def to_dict(self) -> Dict[str, Any]:
        return {
            'audit_type': self.audit_type,
            'audit_name': self.audit_name,
            'summary': self.summary,
            'findings': [f.to_dict() for f in self.findings],
            'start_time': self.start_time.strftime('%Y-%m-%d %H:%M:%S'),
            'end_time': self.end_time.strftime('%Y-%m-%d %H:%M:%S') if self.end_time else None
        }


class BaseAuditEngine(ABC):
    """审计引擎基类"""

    def __init__(self, name: str, audit_type: str):
        self.name = name
        self.audit_type = audit_type
        self.data: Optional[pd.DataFrame] = None
        self.thresholds: Dict[str, float] = {}
        self.result: Optional[AuditResult] = None

    def load_data(self, data: pd.DataFrame):
        """加载审计数据"""
        self.data = data.copy()

    def set_thresholds(self, thresholds: Dict[str, float]):
        """设置审计阈值"""
        self.thresholds.update(thresholds)

    def get_threshold(self, key: str, default: float = 0.0) -> float:
        """获取阈值"""
        return self.thresholds.get(key, default)

    @abstractmethod
    def run_audit(self) -> AuditResult:
        """执行审计，返回审计结果"""
        pass

    def _calculate_risk_score(self, value: float, threshold: float, higher_is_riskier: bool = True) -> float:
        """
        计算风险分数 (0-100)
        基于实际值与阈值的比例
        """
        if threshold == 0:
            return 100 if value > 0 else 0

        ratio = value / threshold if higher_is_riskier else threshold / value

        if ratio <= 0.5:
            return 0
        elif ratio <= 1.0:
            return (ratio - 0.5) * 100
        elif ratio <= 2.0:
            return 50 + (ratio - 1.0) * 50
        else:
            return 100

    def _determine_risk_level(self, risk_score: float) -> str:
        """根据风险分数确定风险等级"""
        if risk_score >= 80:
            return 'high'
        elif risk_score >= 50:
            return 'medium'
        elif risk_score >= 20:
            return 'low'
        return 'none'
