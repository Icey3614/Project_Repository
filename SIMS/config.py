# -*- coding: utf-8 -*-
"""系统配置：项目常量与默认参数。"""

# 项目专属数据库名称（MySQL 模式下自动创建）
DATABASE_NAME = "student_management"

# MySQL 检测与登录的默认值（主机/端口预填，账号密码每次启动时手动输入）
DEFAULT_MYSQL_HOST = "127.0.0.1"
DEFAULT_MYSQL_PORT = 3306

# 首次使用时自动创建的默认教师账号（登录后可在系统里修改密码）
DEFAULT_TEACHER_USERNAME = "admin"
DEFAULT_TEACHER_PASSWORD = "admin123"
DEFAULT_TEACHER_NAME = "系统管理员"
