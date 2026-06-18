"""
操作日志模块
记录所有审计操作，保证可追溯性
"""

import os
import json
import csv
from typing import Dict, List, Optional
from datetime import datetime


class AuditLogger:
    """审计日志类"""

    def __init__(self, log_file: Optional[str] = None):
        if log_file is None:
            from config import LOG_DIR
            log_file = os.path.join(LOG_DIR, 'audit_operations.log')
        self.log_file = log_file
        os.makedirs(os.path.dirname(self.log_file), exist_ok=True)

    def log_operation(
        self,
        username: str,
        operation: str,
        module: str = '',
        description: str = '',
        details: Optional[Dict] = None,
        ip: str = ''
    ):
        """记录操作日志"""
        log_entry = {
            'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'username': username,
            'operation': operation,
            'module': module,
            'description': description,
            'details': details or {},
            'ip': ip
        }

        self._write_log(log_entry)

    def _write_log(self, log_entry: Dict):
        """写入日志"""
        with open(self.log_file, 'a', encoding='utf-8') as f:
            f.write(json.dumps(log_entry, ensure_ascii=False) + '\n')

    def read_logs(
        self,
        limit: int = 100,
        username: Optional[str] = None,
        operation: Optional[str] = None,
        module: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None
    ) -> List[Dict]:
        """读取日志"""
        logs = []
        if not os.path.exists(self.log_file):
            return logs

        with open(self.log_file, 'r', encoding='utf-8') as f:
            for line in f:
                try:
                    log_entry = json.loads(line.strip())
                    if self._filter_log(log_entry, username, operation, module, start_date, end_date):
                        logs.append(log_entry)
                except json.JSONDecodeError:
                    continue

        logs = sorted(logs, key=lambda x: x['timestamp'], reverse=True)
        return logs[:limit]

    def _filter_log(
        self,
        log_entry: Dict,
        username: Optional[str],
        operation: Optional[str],
        module: Optional[str],
        start_date: Optional[str],
        end_date: Optional[str]
    ) -> bool:
        """过滤日志"""
        if username and log_entry.get('username') != username:
            return False
        if operation and log_entry.get('operation') != operation:
            return False
        if module and log_entry.get('module') != module:
            return False
        if start_date:
            if log_entry.get('timestamp', '') < start_date:
                return False
        if end_date:
            if log_entry.get('timestamp', '') > end_date + ' 23:59:59':
                return False
        return True

    def get_statistics(self, days: int = 30) -> Dict:
        """获取日志统计"""
        from datetime import timedelta

        logs = self.read_logs(limit=10000)
        if not logs:
            return {}

        stats = {
            'total_operations': len(logs),
            'by_user': {},
            'by_operation': {},
            'by_module': {}
        }

        for log in logs:
            user = log.get('username', 'unknown')
            op = log.get('operation', 'unknown')
            mod = log.get('module', 'unknown')

            stats['by_user'][user] = stats['by_user'].get(user, 0) + 1
            stats['by_operation'][op] = stats['by_operation'].get(op, 0) + 1
            stats['by_module'][mod] = stats['by_module'].get(mod, 0) + 1

        return stats

    def export_logs(self, export_path: str, file_format: str = 'csv') -> bool:
        """导出日志"""
        logs = self.read_logs(limit=100000)
        if not logs:
            return False

        try:
            if file_format == 'csv':
                with open(export_path, 'w', newline='', encoding='utf-8-sig') as f:
                    if logs:
                        writer = csv.DictWriter(f, fieldnames=logs[0].keys())
                        writer.writeheader()
                        for log in logs:
                            log['details'] = json.dumps(log.get('details', {}), ensure_ascii=False)
                            writer.writerow(log)
            elif file_format == 'json':
                with open(export_path, 'w', encoding='utf-8') as f:
                    json.dump(logs, f, ensure_ascii=False, indent=2)
            else:
                return False
            return True
        except Exception:
            return False

    def log_login(self, username: str, ip: str = '', success: bool = True):
        """记录登录"""
        self.log_operation(
            username=username,
            operation='login' if success else 'login_failed',
            module='system',
            description='用户登录' if success else '用户登录失败',
            ip=ip
        )

    def log_logout(self, username: str, ip: str = ''):
        """记录登出"""
        self.log_operation(
            username=username,
            operation='logout',
            module='system',
            description='用户登出',
            ip=ip
        )

    def log_data_upload(self, username: str, filename: str, file_size: int, module: str = ''):
        """记录数据上传"""
        self.log_operation(
            username=username,
            operation='data_upload',
            module=module,
            description=f'上传数据文件: {filename}',
            details={'filename': filename, 'file_size': file_size}
        )

    def log_audit_run(self, username: str, audit_type: str, findings_count: int):
        """记录审计执行"""
        self.log_operation(
            username=username,
            operation='audit_run',
            module=audit_type,
            description=f'执行{audit_type}审计',
            details={'findings_count': findings_count}
        )

    def log_export(self, username: str, export_type: str, module: str = ''):
        """记录导出操作"""
        self.log_operation(
            username=username,
            operation='export',
            module=module,
            description=f'导出{export_type}',
            details={'export_type': export_type}
        )

    def log_config_change(self, username: str, config_key: str, old_value: str, new_value: str):
        """记录配置变更"""
        self.log_operation(
            username=username,
            operation='config_change',
            module='system',
            description=f'修改配置: {config_key}',
            details={'key': config_key, 'old_value': old_value, 'new_value': new_value}
        )
