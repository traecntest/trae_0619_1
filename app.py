"""
内控风险分析系统 - 主入口
基于Streamlit的Web界面
"""

import os
import sys
import pandas as pd
import streamlit as st
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config import APP_TITLE, APP_VERSION, AUDIT_CATEGORIES, RISK_LEVELS, DATA_SCHEMAS
from core import DataIngestion, DataCleaner, ReportGenerator
from modules import (
    ProcurementAuditEngine,
    SalesAuditEngine,
    ProductionAuditEngine,
    MaintenanceAuditEngine
)
from utils import Sampler
from auth import AuthManager, AuditLogger


st.set_page_config(
    page_title=f"{APP_TITLE} v{APP_VERSION}",
    page_icon="🔍",
    layout="wide",
    initial_sidebar_state="expanded"
)

auth_manager = AuthManager()
audit_logger = AuditLogger()


def init_session_state():
    """初始化会话状态"""
    if 'authenticated' not in st.session_state:
        st.session_state.authenticated = False
    if 'username' not in st.session_state:
        st.session_state.username = ''
    if 'user_role' not in st.session_state:
        st.session_state.user_role = ''
    if 'current_page' not in st.session_state:
        st.session_state.current_page = 'home'
    if 'uploaded_data' not in st.session_state:
        st.session_state.uploaded_data = None
    if 'cleaned_data' not in st.session_state:
        st.session_state.cleaned_data = None
    if 'audit_result' not in st.session_state:
        st.session_state.audit_result = None
    if 'current_audit_type' not in st.session_state:
        st.session_state.current_audit_type = None


def login_page():
    """登录页面"""
    st.title(f"🔍 {APP_TITLE}")
    st.markdown("---")

    col1, col2, col3 = st.columns([1, 2, 1])

    with col2:
        st.markdown("### 用户登录")
        st.info("内部审计人员专用系统，请使用您的账号登录")

        username = st.text_input("用户名", key="login_username")
        password = st.text_input("密码", type="password", key="login_password")

        if st.button("登录", type="primary", use_container_width=True):
            user = auth_manager.authenticate(username, password)
            if user:
                st.session_state.authenticated = True
                st.session_state.username = user['username']
                st.session_state.user_role = user['role']
                st.session_state.full_name = user.get('full_name', username)
                audit_logger.log_login(username)
                st.success("登录成功！")
                st.rerun()
            else:
                st.error("用户名或密码错误")
                audit_logger.log_login(username, success=False)

        st.markdown("---")
        st.caption("默认账号：")
        st.caption("• 管理员：admin / admin123")
        st.caption("• 审计员：auditor / audit123")
        st.caption("• 只读用户：viewer / view123")


def sidebar():
    """侧边栏导航"""
    with st.sidebar:
        st.title(f"🔍 {APP_TITLE}")
        st.caption(f"v{APP_VERSION}")

        st.markdown("---")

        if st.session_state.authenticated:
            st.success(f"👤 {st.session_state.get('full_name', st.session_state.username)}")
            st.caption(f"角色：{st.session_state.user_role}")

            st.markdown("---")

            st.markdown("### 功能导航")

            if st.button("🏠 首页", use_container_width=True,
                         type="primary" if st.session_state.current_page == 'home' else "secondary"):
                st.session_state.current_page = 'home'
                st.rerun()

            if st.button("📊 数据接入", use_container_width=True,
                         type="primary" if st.session_state.current_page == 'data' else "secondary"):
                st.session_state.current_page = 'data'
                st.rerun()

            st.markdown("#### 审计模块")

            if st.button("🛒 采购审计", use_container_width=True,
                         type="primary" if st.session_state.current_page == 'procurement' else "secondary"):
                st.session_state.current_page = 'procurement'
                st.rerun()

            if st.button("💰 销售审计", use_container_width=True,
                         type="primary" if st.session_state.current_page == 'sales' else "secondary"):
                st.session_state.current_page = 'sales'
                st.rerun()

            if st.button("🏭 生产审计", use_container_width=True,
                         type="primary" if st.session_state.current_page == 'production' else "secondary"):
                st.session_state.current_page = 'production'
                st.rerun()

            if st.button("🔧 维修审计", use_container_width=True,
                         type="primary" if st.session_state.current_page == 'maintenance' else "secondary"):
                st.session_state.current_page = 'maintenance'
                st.rerun()

            st.markdown("#### 工具")

            if st.button("🎲 抽样工具", use_container_width=True,
                         type="primary" if st.session_state.current_page == 'sampling' else "secondary"):
                st.session_state.current_page = 'sampling'
                st.rerun()

            if st.session_state.user_role == 'admin':
                st.markdown("#### 系统管理")
                if st.button("👥 用户管理", use_container_width=True,
                             type="primary" if st.session_state.current_page == 'users' else "secondary"):
                    st.session_state.current_page = 'users'
                    st.rerun()

                if st.button("📋 操作日志", use_container_width=True,
                             type="primary" if st.session_state.current_page == 'logs' else "secondary"):
                    st.session_state.current_page = 'logs'
                    st.rerun()

            st.markdown("---")

            if st.button("🚪 退出登录", use_container_width=True):
                audit_logger.log_logout(st.session_state.username)
                st.session_state.authenticated = False
                st.session_state.username = ''
                st.session_state.user_role = ''
                st.session_state.current_page = 'home'
                st.session_state.uploaded_data = None
                st.session_state.cleaned_data = None
                st.session_state.audit_result = None
                st.rerun()


def home_page():
    """首页"""
    st.title(f"欢迎使用 {APP_TITLE}")
    st.markdown("---")

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric("审计模块", "4", "采购/销售/生产/维修")
    with col2:
        st.metric("内置审计规则", "20+", "持续更新中")
    with col3:
        st.metric("分析维度", "多维度", "价格/数量/趋势/异常")
    with col4:
        st.metric("数据接入方式", "3种", "Excel/数据库/API")

    st.markdown("---")

    st.subheader("📋 功能概览")

    col1, col2 = st.columns(2)

    with col1:
        st.markdown("""
        ### 🛒 采购审计
        - **价格波动预警**：监控物料价格异常波动
        - **供应商集中度分析**：识别单一供应商依赖风险
        - **异常交易识别**：检测大额、整数、重复等异常交易
        - **采购量分配分析**：分析多供应商采购分配合理性
        """)

        st.markdown("""
        ### 🏭 生产审计
        - **领料差异分析**：标准用量 vs 实际用量对比
        - **完工入库分析**：计划产量 vs 实际产量
        - **报废率监控**：监控报废率异常波动
        - **生产效率分析**：投入产出比分析
        """)

    with col2:
        st.markdown("""
        ### 💰 销售审计
        - **价格体系合规性**：检查售价执行一致性
        - **客户信用管理**：超信用额度预警
        - **回款周期分析**：应收账款账龄分析
        - **退货/折扣异常**：检测异常退货和折扣
        """)

        st.markdown("""
        ### 🔧 维修审计
        - **过度维修识别**：检测车辆/设备维修频次异常
        - **维修费用分析**：费用趋势和异常检测
        - **维修类型分布**：分析维修结构合理性
        """)

    st.markdown("---")

    st.subheader("🔧 通用工具")

    col1, col2, col3 = st.columns(3)

    with col1:
        st.info("""
        **🎲 自动抽样**
        - 简单随机抽样
        - 分层抽样
        - 系统抽样
        - 货币单位抽样(PPS)
        """)
        if st.button("🎲 进入抽样工具", use_container_width=True,
                     key="goto_sampling"):
            st.session_state.current_page = 'sampling'
            st.rerun()

    with col2:
        st.info("""
        **📈 趋势分析**
        - 时间趋势分析
        - 两期对比
        - 异常波动检测
        - 移动平均
        """)
        if st.button("📈 上传数据分析", use_container_width=True,
                     key="goto_data_trend"):
            st.session_state.current_page = 'data'
            st.rerun()

    with col3:
        st.info("""
        **⚠️ 异常检测**
        - Z-score异常值
        - IQR异常值
        - 本福特定律
        - 整数金额检测
        """)
        if st.button("⚠️ 上传数据分析", use_container_width=True,
                     key="goto_data_anomaly"):
            st.session_state.current_page = 'data'
            st.rerun()

    st.markdown("---")
    st.caption(f"© 2024 内控风险分析系统 v{APP_VERSION}")


def data_page():
    """数据接入页面"""
    st.title("📊 数据接入")
    st.markdown("---")

    tab1, tab2, tab3 = st.tabs(["文件上传", "数据库连接", "示例数据"])

    with tab1:
        st.subheader("📁 上传数据文件")
        st.info("支持 Excel (.xlsx, .xls) 和 CSV 格式")

        uploaded_file = st.file_uploader(
            "选择文件",
            type=['xlsx', 'xls', 'csv'],
            help="最大支持 100MB 文件"
        )

        if uploaded_file is not None:
            try:
                import tempfile
                with tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(uploaded_file.name)[1]) as tmp:
                    tmp.write(uploaded_file.getvalue())
                    tmp_path = tmp.name

                data_ingestion = DataIngestion()

                sheet_names = data_ingestion.get_sheet_names(tmp_path)
                sheet_name = None

                if sheet_names:
                    sheet_name = st.selectbox("选择工作表", sheet_names)

                if st.button("读取数据", type="primary"):
                    df = data_ingestion.read_file(tmp_path, sheet_name)
                    st.session_state.uploaded_data = df
                    st.session_state.cleaned_data = None
                    st.session_state.audit_result = None

                    audit_logger.log_data_upload(
                        st.session_state.username,
                        uploaded_file.name,
                        uploaded_file.size
                    )

                    st.success(f"数据读取成功！共 {len(df)} 行，{len(df.columns)} 列")

                os.unlink(tmp_path)
            except Exception as e:
                st.error(f"文件读取失败：{str(e)}")

    with tab2:
        st.subheader("🗄️ 数据库连接")
        st.info("支持 MySQL、PostgreSQL 等主流数据库")

        db_type = st.selectbox("数据库类型", ["MySQL", "PostgreSQL", "SQL Server", "Oracle"])
        host = st.text_input("主机地址", "localhost")
        port = st.number_input("端口", value=3306)
        database = st.text_input("数据库名")
        username = st.text_input("用户名")
        password = st.text_input("密码", type="password")
        query = st.text_area("SQL 查询语句", "SELECT * FROM table_name LIMIT 1000")

        if st.button("连接并查询", type="primary"):
            try:
                if db_type == 'MySQL':
                    conn_str = f"mysql+pymysql://{username}:{password}@{host}:{port}/{database}"
                elif db_type == 'PostgreSQL':
                    conn_str = f"postgresql://{username}:{password}@{host}:{port}/{database}"
                else:
                    st.error("暂不支持该数据库类型")
                    st.stop()

                data_ingestion = DataIngestion()
                df = data_ingestion.read_from_database(conn_str, query)
                st.session_state.uploaded_data = df
                st.session_state.cleaned_data = None
                st.session_state.audit_result = None

                st.success(f"查询成功！共返回 {len(df)} 行数据")
            except Exception as e:
                st.error(f"数据库连接失败：{str(e)}")

    with tab3:
        st.subheader("📦 示例数据")
        st.info("快速体验系统功能，使用内置示例数据")

        sample_type = st.selectbox(
            "选择示例数据类型",
            ["采购数据", "销售数据", "生产数据", "维修数据"]
        )

        sample_map = {
            "采购数据": "procurement",
            "销售数据": "sales",
            "生产数据": "production",
            "维修数据": "maintenance"
        }

        if st.button("加载示例数据", type="primary"):
            from data import (
                generate_procurement_data,
                generate_sales_data,
                generate_production_data,
                generate_maintenance_data
            )

            sample_key = sample_map[sample_type]

            if sample_key == 'procurement':
                df = generate_procurement_data()
            elif sample_key == 'sales':
                df = generate_sales_data()
            elif sample_key == 'production':
                df = generate_production_data()
            else:
                df = generate_maintenance_data()

            st.session_state.uploaded_data = df
            st.session_state.cleaned_data = None
            st.session_state.audit_result = None
            st.session_state.current_audit_type = sample_key

            st.success(f"示例数据加载成功！共 {len(df)} 行，{len(df.columns)} 列")

    if st.session_state.uploaded_data is not None:
        st.markdown("---")
        st.subheader("📋 数据预览")

        df = st.session_state.uploaded_data

        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("数据行数", len(df))
        with col2:
            st.metric("字段数量", len(df.columns))
        with col3:
            st.metric("空值数量", df.isnull().sum().sum())
        with col4:
            null_cols = df.isnull().any().sum()
            st.metric("含空值字段", null_cols)

        with st.expander("查看数据详情", expanded=True):
            st.dataframe(df.head(50), use_container_width=True)

        st.markdown("---")
        st.subheader("🧹 数据清洗与标准化")

        schema_type = st.selectbox(
            "选择数据模式（可选）",
            ["自动识别"] + list(DATA_SCHEMAS.keys()),
            help="选择对应的数据模式以进行字段标准化"
        )

        if st.button("执行数据清洗", type="primary"):
            cleaner = DataCleaner()
            schema_key = None if schema_type == "自动识别" else schema_type
            cleaned_df, report = cleaner.clean_data(df, schema_key)
            st.session_state.cleaned_data = cleaned_df

            st.success("数据清洗完成！")

            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("原始行数", report['initial_rows'])
            with col2:
                st.metric("清洗后行数", report['final_rows'])
            with col3:
                removed = report['initial_rows'] - report['final_rows']
                st.metric("去除行数", removed)

            st.write("清洗步骤：")
            for step in report['steps']:
                st.write(f"  ✓ {step}")

        if st.session_state.cleaned_data is not None:
            st.markdown("---")
            st.subheader("✅ 清洗后数据预览")
            st.dataframe(st.session_state.cleaned_data.head(50), use_container_width=True)


def display_audit_result(result):
    """展示审计结果"""
    if not result:
        return

    summary = result.summary

    st.markdown("---")
    st.subheader("📊 审计摘要")

    col1, col2, col3, col4, col5 = st.columns(5)

    risk_colors = {
        'high': '#FF4B4B',
        'medium': '#FFA500',
        'low': '#4CAF50',
        'none': '#9E9E9E'
    }

    overall_risk = summary.get('overall_risk_level', 'none')
    risk_name = RISK_LEVELS.get(overall_risk, {}).get('name', '未知')

    with col1:
        st.metric("总发现数", summary.get('total_findings', 0))
    with col2:
        st.metric("🔴 高风险", summary.get('risk_counts', {}).get('high', 0))
    with col3:
        st.metric("🟡 中风险", summary.get('risk_counts', {}).get('medium', 0))
    with col4:
        st.metric("🟢 低风险", summary.get('risk_counts', {}).get('low', 0))
    with col5:
        st.metric("整体风险等级", risk_name)
        st.markdown(f"<p style='color:{risk_colors.get(overall_risk, '#333')};font-weight:bold;'>{risk_name}</p>",
                    unsafe_allow_html=True)

    st.markdown("---")
    st.subheader("📋 疑点清单")

    if result.findings:
        for idx, finding in enumerate(result.findings, 1):
            risk_color = risk_colors.get(finding.risk_level, '#333')
            risk_name = RISK_LEVELS.get(finding.risk_level, {}).get('name', '未知')

            with st.expander(
                f"[{idx}] {finding.finding_type} - 风险等级: {risk_name} (分数: {finding.risk_score:.1f})",
                expanded=(finding.risk_level == 'high')
            ):
                st.markdown(f"**描述：** {finding.description}")

                if finding.evidence:
                    st.markdown("**证据/详情：**")
                    for key, value in finding.evidence.items():
                        if isinstance(value, list):
                            st.write(f"  - {key}: {', '.join(map(str, value[:5]))}" +
                                     (f"... (共{len(value)}项)" if len(value) > 5 else ""))
                        elif isinstance(value, (int, float)):
                            st.write(f"  - {key}: {value:,.2f}" if isinstance(value, float) else f"  - {key}: {value}")
                        else:
                            st.write(f"  - {key}: {value}")

                if finding.affected_records is not None and len(finding.affected_records) > 0:
                    st.markdown(f"**涉及记录数：** {len(finding.affected_records)}")
                    st.dataframe(finding.affected_records.head(20), use_container_width=True)
    else:
        st.info("未发现风险点")

    st.markdown("---")
    st.subheader("📤 导出报告")

    col1, col2, col3 = st.columns(3)

    with col1:
        report_gen = ReportGenerator()
        from io import BytesIO

        output = BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            summary_df = pd.DataFrame([
                ['审计类型', result.audit_type],
                ['审计名称', result.audit_name],
                ['总发现数', summary.get('total_findings', 0)],
                ['整体风险等级', risk_name],
            ], columns=['项目', '内容'])
            summary_df.to_excel(writer, sheet_name='审计摘要', index=False)

            findings_data = []
            for i, f in enumerate(result.findings, 1):
                findings_data.append({
                    '序号': i,
                    '疑点类型': f.finding_type,
                    '风险等级': f.risk_level,
                    '风险分数': f.risk_score,
                    '描述': f.description,
                    '涉及记录数': len(f.affected_records) if f.affected_records is not None else 0
                })
            pd.DataFrame(findings_data).to_excel(writer, sheet_name='疑点清单', index=False)

            if result.data is not None:
                result.data.head(1000).to_excel(writer, sheet_name='原始数据', index=False)

        excel_data = output.getvalue()
        st.download_button(
            "下载Excel报告",
            data=excel_data,
            file_name=f"审计报告_{result.audit_type}_{datetime.now().strftime('%Y%m%d')}.xlsx",
            mime='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            use_container_width=True
        )

    with col2:
        text_report = report_gen.generate_text_report(result)
        st.download_button(
            "下载文本报告",
            data=text_report,
            file_name=f"审计报告_{result.audit_type}_{datetime.now().strftime('%Y%m%d')}.txt",
            mime='text/plain',
            use_container_width=True
        )

    with col3:
        if st.button("📋 生成报告记录", use_container_width=True):
            audit_logger.log_audit_run(
                st.session_state.username,
                result.audit_type,
                summary.get('total_findings', 0)
            )
            st.success("已记录到操作日志")


def procurement_audit_page():
    """采购审计页面"""
    st.title("🛒 采购审计")
    st.markdown("---")

    st.subheader("⚙️ 审计参数设置")

    col1, col2 = st.columns(2)

    with col1:
        price_threshold = st.slider(
            "价格波动阈值（变异系数）",
            min_value=0.05,
            max_value=0.50,
            value=0.15,
            step=0.01,
            help="超过此值视为价格波动异常"
        )
        concentration_threshold = st.slider(
            "供应商集中度阈值",
            min_value=0.10,
            max_value=0.80,
            value=0.30,
            step=0.05,
            help="单一供应商占比超过此值视为集中度过高"
        )

    with col2:
        zscore_threshold = st.slider(
            "异常交易Z值阈值",
            min_value=1.5,
            max_value=5.0,
            value=3.0,
            step=0.1,
            help="标准差倍数，超过此值视为异常"
        )
        round_amount_threshold = st.number_input(
            "大额整数交易阈值（元）",
            min_value=1000,
            max_value=100000,
            value=10000,
            step=1000,
            help="金额大于此值且为1000的整数倍时标记"
        )

    st.markdown("---")

    data_source = st.radio(
        "数据源选择",
        ["使用已上传数据", "加载示例数据"],
        horizontal=True
    )

    df = None

    if data_source == "使用已上传数据":
        if st.session_state.cleaned_data is not None:
            df = st.session_state.cleaned_data
            st.info(f"使用已清洗的数据（{len(df)} 行）")
        elif st.session_state.uploaded_data is not None:
            df = st.session_state.uploaded_data
            st.warning(f"使用原始数据（{len(df)} 行），建议先清洗")
        else:
            st.warning("请先在「数据接入」页面上传数据，或选择加载示例数据")
    else:
        from data import generate_procurement_data
        df = generate_procurement_data()
        st.success(f"已加载示例采购数据（{len(df)} 行）")

    if df is not None and st.button("开始审计", type="primary", use_container_width=True):
        with st.spinner("正在执行采购审计分析..."):
            engine = ProcurementAuditEngine()
            engine.load_data(df)
            engine.set_thresholds({
                'price_fluctuation': price_threshold,
                'supplier_concentration': concentration_threshold,
                'anomaly_transaction': zscore_threshold,
                'round_amount': round_amount_threshold
            })
            result = engine.run_audit()
            st.session_state.audit_result = result
            st.session_state.current_audit_type = 'procurement'

        st.success("审计完成！")

    if st.session_state.audit_result and st.session_state.current_audit_type == 'procurement':
        display_audit_result(st.session_state.audit_result)


def sales_audit_page():
    """销售审计页面"""
    st.title("💰 销售审计")
    st.markdown("---")

    st.subheader("⚙️ 审计参数设置")

    col1, col2 = st.columns(2)

    with col1:
        price_threshold = st.slider(
            "价格合规阈值（变异系数）",
            min_value=0.02,
            max_value=0.30,
            value=0.10,
            step=0.01
        )
        credit_threshold = st.slider(
            "信用额度倍数阈值",
            min_value=0.5,
            max_value=2.0,
            value=1.0,
            step=0.1
        )

    with col2:
        collection_threshold = st.number_input(
            "回款周期阈值（天）",
            min_value=30,
            max_value=365,
            value=90,
            step=10
        )
        discount_threshold = st.slider(
            "折扣率异常阈值",
            min_value=0.10,
            max_value=0.70,
            value=0.30,
            step=0.05
        )

    st.markdown("---")

    data_source = st.radio(
        "数据源选择",
        ["使用已上传数据", "加载示例数据"],
        horizontal=True
    )

    df = None

    if data_source == "使用已上传数据":
        if st.session_state.cleaned_data is not None:
            df = st.session_state.cleaned_data
            st.info(f"使用已清洗的数据（{len(df)} 行）")
        elif st.session_state.uploaded_data is not None:
            df = st.session_state.uploaded_data
            st.warning(f"使用原始数据（{len(df)} 行），建议先清洗")
        else:
            st.warning("请先在「数据接入」页面上传数据，或选择加载示例数据")
    else:
        from data import generate_sales_data
        df = generate_sales_data()
        st.success(f"已加载示例销售数据（{len(df)} 行）")

    if df is not None and st.button("开始审计", type="primary", use_container_width=True):
        with st.spinner("正在执行销售审计分析..."):
            engine = SalesAuditEngine()
            engine.load_data(df)
            engine.set_thresholds({
                'price_compliance': price_threshold,
                'credit_management': credit_threshold,
                'collection_cycle': float(collection_threshold),
                'discount_anomaly': discount_threshold,
                'return_anomaly': 0.10
            })
            result = engine.run_audit()
            st.session_state.audit_result = result
            st.session_state.current_audit_type = 'sales'

        st.success("审计完成！")

    if st.session_state.audit_result and st.session_state.current_audit_type == 'sales':
        display_audit_result(st.session_state.audit_result)


def production_audit_page():
    """生产审计页面"""
    st.title("🏭 生产审计")
    st.markdown("---")

    st.subheader("⚙️ 审计参数设置")

    col1, col2 = st.columns(2)

    with col1:
        material_threshold = st.slider(
            "物料差异阈值",
            min_value=0.02,
            max_value=0.30,
            value=0.10,
            step=0.01
        )
        completion_threshold = st.slider(
            "完工率阈值",
            min_value=0.70,
            max_value=0.99,
            value=0.90,
            step=0.01
        )

    with col2:
        scrap_threshold = st.slider(
            "报废率阈值",
            min_value=0.01,
            max_value=0.20,
            value=0.05,
            step=0.01
        )
        efficiency_threshold = st.slider(
            "生产效率阈值",
            min_value=0.50,
            max_value=1.20,
            value=0.85,
            step=0.05
        )

    st.markdown("---")

    data_source = st.radio(
        "数据源选择",
        ["使用已上传数据", "加载示例数据"],
        horizontal=True
    )

    df = None

    if data_source == "使用已上传数据":
        if st.session_state.cleaned_data is not None:
            df = st.session_state.cleaned_data
            st.info(f"使用已清洗的数据（{len(df)} 行）")
        elif st.session_state.uploaded_data is not None:
            df = st.session_state.uploaded_data
            st.warning(f"使用原始数据（{len(df)} 行），建议先清洗")
        else:
            st.warning("请先在「数据接入」页面上传数据，或选择加载示例数据")
    else:
        from data import generate_production_data
        df = generate_production_data()
        st.success(f"已加载示例生产数据（{len(df)} 行）")

    if df is not None and st.button("开始审计", type="primary", use_container_width=True):
        with st.spinner("正在执行生产审计分析..."):
            engine = ProductionAuditEngine()
            engine.load_data(df)
            engine.set_thresholds({
                'material_variance': material_threshold,
                'completion_rate': completion_threshold,
                'scrap_rate': scrap_threshold,
                'production_efficiency': efficiency_threshold
            })
            result = engine.run_audit()
            st.session_state.audit_result = result
            st.session_state.current_audit_type = 'production'

        st.success("审计完成！")

    if st.session_state.audit_result and st.session_state.current_audit_type == 'production':
        display_audit_result(st.session_state.audit_result)


def maintenance_audit_page():
    """维修审计页面"""
    st.title("🔧 维修审计")
    st.markdown("---")

    st.subheader("⚙️ 审计参数设置")

    col1, col2 = st.columns(2)

    with col1:
        freq_threshold = st.number_input(
            "月度维修频次阈值（次/月）",
            min_value=1,
            max_value=20,
            value=3,
            step=1
        )
        cost_zscore_threshold = st.slider(
            "费用异常Z值阈值",
            min_value=1.5,
            max_value=5.0,
            value=3.0,
            step=0.1
        )

    with col2:
        cost_trend_threshold = st.slider(
            "费用波动阈值",
            min_value=0.05,
            max_value=0.50,
            value=0.20,
            step=0.05
        )
        vendor_concentration = st.slider(
            "维修供应商集中度阈值",
            min_value=0.20,
            max_value=0.80,
            value=0.50,
            step=0.05
        )

    st.markdown("---")

    data_source = st.radio(
        "数据源选择",
        ["使用已上传数据", "加载示例数据"],
        horizontal=True
    )

    df = None

    if data_source == "使用已上传数据":
        if st.session_state.cleaned_data is not None:
            df = st.session_state.cleaned_data
            st.info(f"使用已清洗的数据（{len(df)} 行）")
        elif st.session_state.uploaded_data is not None:
            df = st.session_state.uploaded_data
            st.warning(f"使用原始数据（{len(df)} 行），建议先清洗")
        else:
            st.warning("请先在「数据接入」页面上传数据，或选择加载示例数据")
    else:
        from data import generate_maintenance_data
        df = generate_maintenance_data()
        st.success(f"已加载示例维修数据（{len(df)} 行）")

    if df is not None and st.button("开始审计", type="primary", use_container_width=True):
        with st.spinner("正在执行维修审计分析..."):
            engine = MaintenanceAuditEngine()
            engine.load_data(df)
            engine.set_thresholds({
                'excessive_maintenance': float(freq_threshold),
                'maintenance_cost': cost_trend_threshold
            })
            result = engine.run_audit()
            st.session_state.audit_result = result
            st.session_state.current_audit_type = 'maintenance'

        st.success("审计完成！")

    if st.session_state.audit_result and st.session_state.current_audit_type == 'maintenance':
        display_audit_result(st.session_state.audit_result)


def sampling_page():
    """抽样工具页面"""
    st.title("🎲 自动抽样工具")
    st.markdown("---")

    if st.session_state.cleaned_data is not None:
        df = st.session_state.cleaned_data
    elif st.session_state.uploaded_data is not None:
        df = st.session_state.uploaded_data
    else:
        st.info("请先上传数据或加载示例数据后再使用抽样功能")
        return

    st.info(f"当前数据：{len(df)} 行，{len(df.columns)} 列")

    col1, col2 = st.columns(2)

    with col1:
        method = st.selectbox(
            "抽样方法",
            options=['random', 'stratified', 'systematic', 'mus'],
            format_func=lambda x: {
                'random': '简单随机抽样',
                'stratified': '分层抽样',
                'systematic': '系统抽样（等距）',
                'mus': '货币单位抽样（PPS）'
            }[x]
        )

    with col2:
        sample_size = st.number_input(
            "样本量（留空自动计算）",
            min_value=1,
            max_value=len(df),
            value=min(100, len(df)),
            step=10
        )

    stratify_col = None
    amount_col = None

    if method == 'stratified':
        stratify_col = st.selectbox(
            "分层字段",
            options=list(df.columns)
        )

    if method == 'mus':
        numeric_cols = df.select_dtypes(include='number').columns.tolist()
        if numeric_cols:
            amount_col = st.selectbox(
                "金额字段",
                options=numeric_cols
            )
        else:
            st.warning("未检测到数值列，将使用随机抽样")

    if st.button("执行抽样", type="primary"):
        sampler = Sampler()
        sample_df, info = sampler.sample(
            df,
            method=method,
            sample_size=sample_size,
            stratify_col=stratify_col,
            amount_col=amount_col
        )

        st.success("抽样完成！")

        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("总体数量", info.get('population_size', 0))
        with col2:
            st.metric("样本数量", info.get('actual_sample_size', 0))
        with col3:
            st.metric("抽样比例", f"{info.get('sampling_ratio', 0):.2%}")

        st.markdown("---")
        st.subheader("📋 样本数据")
        st.dataframe(sample_df, use_container_width=True)

        csv_data = sample_df.to_csv(index=False).encode('utf-8-sig')
        st.download_button(
            "下载样本数据",
            data=csv_data,
            file_name=f"抽样结果_{method}_{datetime.now().strftime('%Y%m%d%H%M%S')}.csv",
            mime='text/csv'
        )


def users_page():
    """用户管理页面"""
    if st.session_state.user_role != 'admin':
        st.error("您没有权限访问此页面")
        return

    st.title("👥 用户管理")
    st.markdown("---")

    users = auth_manager.list_users()

    st.subheader("用户列表")

    user_df = pd.DataFrame(users)
    if not user_df.empty:
        user_df = user_df[['username', 'full_name', 'role', 'created_at', 'last_login']]
        user_df.columns = ['用户名', '姓名', '角色', '创建时间', '最后登录']
        st.dataframe(user_df, use_container_width=True)
    else:
        st.info("暂无用户")

    st.markdown("---")
    st.subheader("添加用户")

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        new_username = st.text_input("用户名")
    with col2:
        new_fullname = st.text_input("姓名")
    with col3:
        new_role = st.selectbox("角色", ['auditor', 'viewer', 'admin'])
    with col4:
        new_password = st.text_input("初始密码", type="password")

    if st.button("添加用户", type="primary"):
        if not new_username and not new_password:
            st.warning("请填写用户名和密码")
        elif not new_username:
            st.warning("请输入用户名")
        elif not new_password:
            st.warning("请输入密码")
        else:
            if auth_manager.add_user(new_username, new_password, new_role, new_fullname):
                st.success(f"用户 {new_username} 添加成功")
                st.rerun()
            else:
                st.error("添加失败，用户名可能已存在")


def logs_page():
    """操作日志页面"""
    if st.session_state.user_role != 'admin':
        st.error("您没有权限访问此页面")
        return

    st.title("📋 操作日志")
    st.markdown("---")

    col1, col2, col3 = st.columns(3)

    with col1:
        filter_user = st.text_input("用户筛选", "")
    with col2:
        filter_operation = st.selectbox(
            "操作类型",
            ["全部", "login", "logout", "data_upload", "audit_run", "export", "config_change"]
        )
    with col3:
        limit = st.number_input("显示条数", min_value=10, max_value=1000, value=100, step=10)

    logs = audit_logger.read_logs(
        limit=int(limit),
        username=filter_user if filter_user else None,
        operation=filter_operation if filter_operation != "全部" else None
    )

    if logs:
        log_df = pd.DataFrame(logs)
        log_df = log_df[['timestamp', 'username', 'operation', 'module', 'description']]
        log_df.columns = ['时间', '用户', '操作', '模块', '描述']
        st.dataframe(log_df, use_container_width=True)

        st.metric("总记录数", len(logs))
    else:
        st.info("暂无日志记录")

    stats = audit_logger.get_statistics()
    if stats:
        st.markdown("---")
        st.subheader("📊 统计概览")

        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("总操作数", stats.get('total_operations', 0))
        with col2:
            st.metric("活跃用户数", len(stats.get('by_user', {})))
        with col3:
            st.metric("操作类型数", len(stats.get('by_operation', {})))


def main():
    """主函数"""
    init_session_state()

    if not st.session_state.authenticated:
        login_page()
    else:
        sidebar()

        page = st.session_state.current_page

        if page == 'home':
            home_page()
        elif page == 'data':
            data_page()
        elif page == 'procurement':
            procurement_audit_page()
        elif page == 'sales':
            sales_audit_page()
        elif page == 'production':
            production_audit_page()
        elif page == 'maintenance':
            maintenance_audit_page()
        elif page == 'sampling':
            sampling_page()
        elif page == 'users':
            users_page()
        elif page == 'logs':
            logs_page()
        else:
            home_page()


if __name__ == '__main__':
    main()
