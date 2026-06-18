"""
系统测试脚本
验证各模块功能是否正常
"""

import os
import sys
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from data import (
    generate_procurement_data,
    generate_sales_data,
    generate_production_data,
    generate_maintenance_data
)
from core import DataIngestion, DataCleaner, ReportGenerator
from modules import (
    ProcurementAuditEngine,
    SalesAuditEngine,
    ProductionAuditEngine,
    MaintenanceAuditEngine
)
from utils import Sampler, ThresholdAlert, TrendAnalyzer, AnomalyDetector
from auth import AuthManager, AuditLogger


def test_data_generation():
    """测试数据生成"""
    print("=" * 50)
    print("测试1: 示例数据生成")
    print("=" * 50)

    try:
        procurement_df = generate_procurement_data(100)
        print(f"✓ 采购数据生成成功: {len(procurement_df)} 条")

        sales_df = generate_sales_data(100)
        print(f"✓ 销售数据生成成功: {len(sales_df)} 条")

        production_df = generate_production_data(50)
        print(f"✓ 生产数据生成成功: {len(production_df)} 条")

        maintenance_df = generate_maintenance_data(100)
        print(f"✓ 维修数据生成成功: {len(maintenance_df)} 条")

        return procurement_df, sales_df, production_df, maintenance_df
    except Exception as e:
        print(f"✗ 数据生成失败: {e}")
        import traceback
        traceback.print_exc()
        return None, None, None, None


def test_data_cleaning(df):
    """测试数据清洗"""
    print("\n" + "=" * 50)
    print("测试2: 数据清洗")
    print("=" * 50)

    try:
        cleaner = DataCleaner()
        cleaned_df, report = cleaner.clean_data(df)

        print(f"✓ 数据清洗完成")
        print(f"  原始行数: {report['initial_rows']}")
        print(f"  清洗后行数: {report['final_rows']}")
        print(f"  清洗步骤: {len(report['steps'])} 步")
        for step in report['steps']:
            print(f"    - {step}")

        return cleaned_df
    except Exception as e:
        print(f"✗ 数据清洗失败: {e}")
        import traceback
        traceback.print_exc()
        return None


def test_procurement_audit(df):
    """测试采购审计"""
    print("\n" + "=" * 50)
    print("测试3: 采购审计模块")
    print("=" * 50)

    try:
        engine = ProcurementAuditEngine()
        engine.load_data(df)
        result = engine.run_audit()

        print(f"✓ 采购审计完成")
        print(f"  审计类型: {result.audit_type}")
        print(f"  发现疑点: {result.summary['total_findings']} 个")
        print(f"  高风险: {result.summary['risk_counts']['high']} 个")
        print(f"  中风险: {result.summary['risk_counts']['medium']} 个")
        print(f"  低风险: {result.summary['risk_counts']['low']} 个")
        print(f"  整体风险等级: {result.summary['overall_risk_level']}")
        print(f"  分析数据: {list(result.analysis_data.keys())}")

        for finding in result.findings:
            print(f"    - [{finding.risk_level}] {finding.finding_type}: {finding.risk_score:.1f}分")

        return result
    except Exception as e:
        print(f"✗ 采购审计失败: {e}")
        import traceback
        traceback.print_exc()
        return None


def test_sales_audit(df):
    """测试销售审计"""
    print("\n" + "=" * 50)
    print("测试4: 销售审计模块")
    print("=" * 50)

    try:
        engine = SalesAuditEngine()
        engine.load_data(df)
        result = engine.run_audit()

        print(f"✓ 销售审计完成")
        print(f"  发现疑点: {result.summary['total_findings']} 个")
        print(f"  高风险: {result.summary['risk_counts']['high']} 个")
        print(f"  中风险: {result.summary['risk_counts']['medium']} 个")
        print(f"  低风险: {result.summary['risk_counts']['low']} 个")

        for finding in result.findings:
            print(f"    - [{finding.risk_level}] {finding.finding_type}: {finding.risk_score:.1f}分")

        return result
    except Exception as e:
        print(f"✗ 销售审计失败: {e}")
        import traceback
        traceback.print_exc()
        return None


def test_production_audit(df):
    """测试生产审计"""
    print("\n" + "=" * 50)
    print("测试5: 生产审计模块")
    print("=" * 50)

    try:
        engine = ProductionAuditEngine()
        engine.load_data(df)
        result = engine.run_audit()

        print(f"✓ 生产审计完成")
        print(f"  发现疑点: {result.summary['total_findings']} 个")
        print(f"  高风险: {result.summary['risk_counts']['high']} 个")
        print(f"  中风险: {result.summary['risk_counts']['medium']} 个")
        print(f"  低风险: {result.summary['risk_counts']['low']} 个")

        for finding in result.findings:
            print(f"    - [{finding.risk_level}] {finding.finding_type}: {finding.risk_score:.1f}分")

        return result
    except Exception as e:
        print(f"✗ 生产审计失败: {e}")
        import traceback
        traceback.print_exc()
        return None


def test_maintenance_audit(df):
    """测试维修审计"""
    print("\n" + "=" * 50)
    print("测试6: 维修审计模块")
    print("=" * 50)

    try:
        engine = MaintenanceAuditEngine()
        engine.load_data(df)
        result = engine.run_audit()

        print(f"✓ 维修审计完成")
        print(f"  发现疑点: {result.summary['total_findings']} 个")
        print(f"  高风险: {result.summary['risk_counts']['high']} 个")
        print(f"  中风险: {result.summary['risk_counts']['medium']} 个")
        print(f"  低风险: {result.summary['risk_counts']['low']} 个")

        for finding in result.findings:
            print(f"    - [{finding.risk_level}] {finding.finding_type}: {finding.risk_score:.1f}分")

        return result
    except Exception as e:
        print(f"✗ 维修审计失败: {e}")
        import traceback
        traceback.print_exc()
        return None


def test_utils(df):
    """测试工具库"""
    print("\n" + "=" * 50)
    print("测试7: 通用工具库")
    print("=" * 50)

    try:
        sampler = Sampler()
        sample_df, sample_info = sampler.sample(df, method='random', sample_size=20)
        print(f"✓ 随机抽样: {sample_info['actual_sample_size']} 个样本")

        sample_df, sample_info = sampler.sample(df, method='stratified', sample_size=30)
        print(f"✓ 分层抽样: {sample_info['actual_sample_size']} 个样本")

        sample_df, sample_info = sampler.sample(df, method='systematic', sample_size=25)
        print(f"✓ 系统抽样: {sample_info['actual_sample_size']} 个样本")

        alert = ThresholdAlert()
        amount_col = None
        for col in ['采购金额', '销售金额', '维修费用', '金额']:
            if col in df.columns:
                amount_col = col
                break

        if amount_col:
            outliers, info = alert.check_outliers_zscore(df, amount_col, z_threshold=2.0)
            print(f"✓ Z-score异常检测: {info['outlier_count']} 个异常值")

        trend = TrendAnalyzer()
        date_col = None
        for col in ['采购日期', '销售日期', '生产日期', '维修日期', '日期']:
            if col in df.columns:
                date_col = col
                break

        if date_col and amount_col:
            trend_df, trend_info = trend.analyze_trend(df, date_col, amount_col, freq='M')
            print(f"✓ 趋势分析: {len(trend_df)} 个周期")

        detector = AnomalyDetector()
        if amount_col:
            round_nums, round_info = detector.detect_round_numbers(df, amount_col, threshold=5000)
            print(f"✓ 整数金额检测: {round_info['anomaly_count']} 笔")

        return True
    except Exception as e:
        print(f"✗ 工具库测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_report_generator(result):
    """测试报告生成"""
    print("\n" + "=" * 50)
    print("测试8: 报告生成")
    print("=" * 50)

    try:
        report_gen = ReportGenerator()

        text_report = report_gen.generate_text_report(result)
        print(f"✓ 文本报告生成: {len(text_report)} 字符")

        summary = report_gen.generate_summary_report(result)
        print(f"✓ 摘要报告生成: {len(summary['findings'])} 个发现")

        return True
    except Exception as e:
        print(f"✗ 报告生成失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_auth():
    """测试权限管理"""
    print("\n" + "=" * 50)
    print("测试9: 权限管理")
    print("=" * 50)

    try:
        auth = AuthManager()

        user = auth.authenticate('admin', 'admin123')
        print(f"✓ 管理员认证: {'成功' if user else '失败'}")

        user = auth.authenticate('auditor', 'audit123')
        print(f"✓ 审计员认证: {'成功' if user else '失败'}")

        user = auth.authenticate('viewer', 'view123')
        print(f"✓ 只读用户认证: {'成功' if user else '失败'}")

        has_perm = auth.has_permission('admin', 'all')
        print(f"✓ 管理员权限检查: {has_perm}")

        has_perm = auth.has_permission('auditor', 'audit')
        print(f"✓ 审计员权限检查: {has_perm}")

        has_perm = auth.has_permission('viewer', 'audit')
        print(f"✓ 只读用户权限检查(无权限): {not has_perm}")

        users = auth.list_users()
        print(f"✓ 用户列表: {len(users)} 个用户")

        return True
    except Exception as e:
        print(f"✗ 权限管理测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_audit_log():
    """测试操作日志"""
    print("\n" + "=" * 50)
    print("测试10: 操作日志")
    print("=" * 50)

    try:
        logger = AuditLogger()

        logger.log_login('test_user', '127.0.0.1')
        logger.log_data_upload('test_user', 'test.xlsx', 10240, 'procurement')
        logger.log_audit_run('test_user', 'procurement', 5)
        logger.log_export('test_user', 'excel', 'procurement')

        logs = logger.read_logs(limit=10)
        print(f"✓ 日志记录: {len(logs)} 条")

        stats = logger.get_statistics()
        print(f"✓ 日志统计: {stats.get('total_operations', 0)} 次操作")

        return True
    except Exception as e:
        print(f"✗ 操作日志测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """主测试函数"""
    print("\n" + "=" * 60)
    print("内控风险分析系统 - 功能测试")
    print("=" * 60)

    procurement_df, sales_df, production_df, maintenance_df = test_data_generation()

    if procurement_df is None:
        print("\n❌ 测试终止：数据生成失败")
        return

    cleaned_df = test_data_cleaning(procurement_df)

    test_utils(procurement_df)

    procurement_result = test_procurement_audit(procurement_df)
    sales_result = test_sales_audit(sales_df)
    production_result = test_production_audit(production_df)
    maintenance_result = test_maintenance_audit(maintenance_df)

    if procurement_result:
        test_report_generator(procurement_result)

    test_auth()
    test_audit_log()

    print("\n" + "=" * 60)
    print("测试完成！")
    print("=" * 60)


if __name__ == '__main__':
    main()
