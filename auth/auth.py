"""
权限控制模块
"""

import os
import json
import hashlib
import bcrypt
from typing import Dict, List, Optional
from datetime import datetime

from config import USER_ROLES


class AuthManager:
    """权限管理类"""

    def __init__(self, users_file: Optional[str] = None):
        if users_file is None:
            from config import DATA_DIR
            users_file = os.path.join(DATA_DIR, 'users.json')
        self.users_file = users_file
        self._users = self._load_users()

    def _load_users(self) -> Dict:
        """加载用户数据"""
        if os.path.exists(self.users_file):
            with open(self.users_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        return self._create_default_users()

    def _create_default_users(self) -> Dict:
        """创建默认用户"""
        default_users = {
            'admin': {
                'username': 'admin',
                'password_hash': self._hash_password('admin123'),
                'role': 'admin',
                'full_name': '系统管理员',
                'created_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'last_login': None
            },
            'auditor': {
                'username': 'auditor',
                'password_hash': self._hash_password('audit123'),
                'role': 'auditor',
                'full_name': '审计人员',
                'created_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'last_login': None
            },
            'viewer': {
                'username': 'viewer',
                'password_hash': self._hash_password('view123'),
                'role': 'viewer',
                'full_name': '只读用户',
                'created_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'last_login': None
            }
        }
        self._save_users(default_users)
        return default_users

    def _hash_password(self, password: str) -> str:
        """哈希密码"""
        return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

    def _verify_password(self, password: str, password_hash: str) -> bool:
        """验证密码"""
        try:
            return bcrypt.checkpw(password.encode('utf-8'), password_hash.encode('utf-8'))
        except ValueError:
            return False

    def _save_users(self, users: Optional[Dict] = None):
        """保存用户数据"""
        if users is None:
            users = self._users
        os.makedirs(os.path.dirname(self.users_file), exist_ok=True)
        with open(self.users_file, 'w', encoding='utf-8') as f:
            json.dump(users, f, ensure_ascii=False, indent=2)

    def authenticate(self, username: str, password: str) -> Optional[Dict]:
        """用户认证"""
        if username not in self._users:
            return None

        user = self._users[username]
        if self._verify_password(password, user['password_hash']):
            user['last_login'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            self._save_users()
            return {
                'username': user['username'],
                'role': user['role'],
                'full_name': user.get('full_name', username),
                'last_login': user['last_login']
            }
        return None

    def get_user_role(self, username: str) -> Optional[str]:
        """获取用户角色"""
        if username in self._users:
            return self._users[username]['role']
        return None

    def has_permission(self, username: str, permission: str) -> bool:
        """检查用户是否有指定权限"""
        role = self.get_user_role(username)
        if role is None:
            return False

        role_permissions = {
            'admin': ['all'],
            'auditor': ['view', 'audit', 'export', 'upload'],
            'viewer': ['view']
        }

        if 'all' in role_permissions.get(role, []):
            return True
        return permission in role_permissions.get(role, [])

    def change_password(self, username: str, old_password: str, new_password: str) -> bool:
        """修改密码"""
        if username not in self._users:
            return False

        user = self._users[username]
        if not self._verify_password(old_password, user['password_hash']):
            return False

        user['password_hash'] = self._hash_password(new_password)
        self._save_users()
        return True

    def add_user(self, username: str, password: str, role: str, full_name: str = '') -> bool:
        """添加用户"""
        if username in self._users:
            return False
        if role not in USER_ROLES:
            return False

        self._users[username] = {
            'username': username,
            'password_hash': self._hash_password(password),
            'role': role,
            'full_name': full_name or username,
            'created_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'last_login': None
        }
        self._save_users()
        return True

    def delete_user(self, username: str) -> bool:
        """删除用户"""
        if username not in self._users:
            return False
        if username == 'admin':
            return False
        del self._users[username]
        self._save_users()
        return True

    def list_users(self) -> List[Dict]:
        """列出所有用户"""
        return [
            {
                'username': u['username'],
                'role': u['role'],
                'full_name': u.get('full_name', ''),
                'created_at': u.get('created_at', ''),
                'last_login': u.get('last_login', '')
            }
            for u in self._users.values()
        ]

    def get_user_info(self, username: str) -> Optional[Dict]:
        """获取用户信息"""
        if username not in self._users:
            return None
        user = self._users[username]
        return {
            'username': user['username'],
            'role': user['role'],
            'full_name': user.get('full_name', ''),
            'role_name': USER_ROLES.get(user['role'], user['role']),
            'created_at': user.get('created_at', ''),
            'last_login': user.get('last_login', '')
        }
