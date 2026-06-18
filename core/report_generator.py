"""
报告生成模块
生成审计报告
"""

import pandas as pd
from typing import Dict, List, Any
from datetime import datetime
import io
import json


class ReportGenerator:
    """审计报告生成器"""

    def __init__(self):
        pass

    def generate_summary_report(self, audit_result) -> Dict[str, Any]:
        """生成汇总报告"""
        return audit_result.to_dict()

    def export_to_excel(self, audit_result, file_path: str):
        """导出审计结果到Excel"""
        with pd.ExcelWriter(file_path, engine='openpyxl') as writer:
            summary_df = self._summary_to_dataframe(audit_result)
            summary_df.to_excel(writer, sheet_name='审计摘要', index=False)

            findings_df = self._findings_to_dataframe(audit_result)
            findings_df.to_excel(writer, sheet_name='疑点清单', index=False)

            for sheet_name, data in audit_result.analysis_data.items():
                if isinstance(data, pd.DataFrame) and len(data) > 0:
                    data.to_excel(writer, sheet_name=sheet_name[:31], index=False)

            if audit_result.data is not None:
                audit_result.data.to_excel(writer, sheet_name='原始数据', index=False)

    def _summary_to_dataframe(self, audit_result) -> pd.DataFrame:
        """将摘要转换为DataFrame"""
        summary = audit_result.summary
        data = [
            ['审计类型', audit_result.audit_type],
            ['审计名称', audit_result.audit_name],
            ['开始时间', audit_result.start_time.strftime('%Y-%m-%d %H:%M:%S')],
            ['结束时间', audit_result.end_time.strftime('%Y-%m-%d %H:%M:%S') if audit_result.end_time else ''],
            ['总发现数', summary.get('total_findings', 0)],
            ['高风险项', summary.get('risk_counts', {}).get('high', 0)],
            ['中风险项', summary.get('risk_counts', {}).get('medium', 0)],
            ['低风险项', summary.get('risk_counts', {}).get('low', 0)],
            ['整体风险等级', summary.get('overall_risk_level', 'none')],
            ['平均风险分数', round(summary.get('average_risk_score', 0), 2)],
            ['数据行数', len(audit_result.data) if audit_result.data is not None else 0],
        ]
        return pd.DataFrame(data, columns=['项目', '内容'])

    def _findings_to_dataframe(self, audit_result) -> pd.DataFrame:
        """将疑点清单转换为DataFrame"""
        rows = []
        for idx, finding in enumerate(audit_result.findings, 1):
            rows.append({
                '序号': idx,
                '疑点类型': finding.finding_type,
                '风险等级': finding.risk_level,
                '风险分数': finding.risk_score,
                '描述': finding.description,
                '涉及记录数': finding.affected_records is not None and len(finding.affected_records) or 0,
                '证据': json.dumps(finding.evidence, ensure_ascii=False) if finding.evidence else ''
            })
        return pd.DataFrame(rows)

    def generate_text_report(self, audit_result) -> str:
        """生成文本格式报告"""
        lines = []
        lines.append("=" * 60)
        lines.append(f"内控风险分析报告")
        lines.append("=" * 60)
        lines.append("")
        lines.append(f"审计类型: {audit_result.audit_type}")
        lines.append(f"审计名称: {audit_result.audit_name}")
        lines.append(f"生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        lines.append("")
        lines.append("-" * 40)
        lines.append("一、审计摘要")
        lines.append("-" * 40)

        summary = audit_result.summary
        lines.append(f"  发现疑点总数: {summary.get('total_findings', 0)}")
        lines.append(f"  高风险项: {summary.get('risk_counts', {}).get('high', 0)}")
        lines.append(f"  中风险项: {summary.get('risk_counts', {}).get('medium', 0)}")
        lines.append(f"  低风险项: {summary.get('risk_counts', {}).get('low', 0)}")
        lines.append(f"  整体风险等级: {summary.get('overall_risk_level', 'none')}")
        lines.append("")
        lines.append("-" * 40)
        lines.append("二、疑点明细")
        lines.append("-" * 40)

        for idx, finding in enumerate(audit_result.findings, 1):
            lines.append(f"")
            lines.append(f"  [{idx}] {finding.finding_type}")
            lines.append(f"      风险等级: {finding.risk_level}")
            lines.append(f"      风险分数: {finding.risk_score:.2f}")
            lines.append(f"      描述: {finding.description}")
            if finding.affected_records is not None:
                lines.append(f"      涉及记录数: {len(finding.affected_records)}")

        lines.append("")
        lines.append("=" * 60)
        lines.append("报告结束")
        lines.append("=" * 60)

        return "\n".join(lines)

    def export_findings_to_csv(self, audit_result, file_path: str):
        """导出疑点清单到CSV"""
        df = self._findings_to_dataframe(audit_result)
        df.to_csv(file_path, index=False, encoding='utf-8-sig')
