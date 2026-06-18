"""
数据接入模块
支持Excel/CSV文件上传和数据库连接
"""

import os
import pandas as pd
from typing import Optional, Dict, List, Any
from datetime import datetime

from config import SUPPORTED_FILE_TYPES, DATA_SCHEMAS


class DataIngestion:
    """数据接入类，统一管理各类数据源的读取"""

    def __init__(self):
        self.supported_extensions = SUPPORTED_FILE_TYPES

    def read_file(self, file_path: str, sheet_name: Optional[str] = None) -> pd.DataFrame:
        """读取文件，自动识别文件格式"""
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"文件不存在: {file_path}")

        ext = os.path.splitext(file_path)[1].lower().lstrip('.')
        if ext not in self.supported_extensions:
            raise ValueError(f"不支持的文件格式: {ext}")

        if ext in ['xlsx', 'xls']:
            return self._read_excel(file_path, sheet_name)
        elif ext == 'csv':
            return self._read_csv(file_path)
        else:
            raise ValueError(f"未知的文件格式: {ext}")

    def _read_excel(self, file_path: str, sheet_name: Optional[str] = None) -> pd.DataFrame:
        """读取Excel文件"""
        try:
            if sheet_name:
                df = pd.read_excel(file_path, sheet_name=sheet_name, dtype=str)
            else:
                df = pd.read_excel(file_path, dtype=str)
            return df
        except Exception as e:
            raise Exception(f"读取Excel文件失败: {str(e)}")

    def _read_csv(self, file_path: str, encoding: str = 'utf-8') -> pd.DataFrame:
        """读取CSV文件"""
        try:
            try:
                df = pd.read_csv(file_path, dtype=str, encoding=encoding)
            except UnicodeDecodeError:
                df = pd.read_csv(file_path, dtype=str, encoding='gbk')
            return df
        except Exception as e:
            raise Exception(f"读取CSV文件失败: {str(e)}")

    def read_from_database(self, connection_string: str, query: str) -> pd.DataFrame:
        """从数据库读取数据"""
        try:
            from sqlalchemy import create_engine
            engine = create_engine(connection_string)
            df = pd.read_sql(query, engine)
            return df
        except Exception as e:
            raise Exception(f"数据库读取失败: {str(e)}")

    def get_sheet_names(self, file_path: str) -> List[str]:
        """获取Excel文件的所有sheet名称"""
        ext = os.path.splitext(file_path)[1].lower().lstrip('.')
        if ext in ['xlsx', 'xls']:
            xl = pd.ExcelFile(file_path)
            return xl.sheet_names
        return []

    def preview_data(self, df: pd.DataFrame, n_rows: int = 10) -> pd.DataFrame:
        """预览数据前n行"""
        return df.head(n_rows)

    def get_data_info(self, df: pd.DataFrame) -> Dict[str, Any]:
        """获取数据基本信息"""
        return {
            'rows': len(df),
            'columns': list(df.columns),
            'column_count': len(df.columns),
            'null_counts': df.isnull().sum().to_dict(),
            'dtypes': df.dtypes.astype(str).to_dict()
        }
