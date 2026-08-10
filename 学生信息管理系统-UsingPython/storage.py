# -*- coding: utf-8 -*-
"""存储抽象层：定义统一的数据接口、字段校验与密码哈希。

系统支持两种存储方式：
- MySQL 数据库（mysql_storage.MySqlStorage）
- Excel 表格（excel_storage.ExcelStorage）

GUI 只依赖本模块的接口编程，因此两种存储方式可以无缝切换。
"""
import hashlib
import secrets
from i18n import tr


class StorageError(Exception):
    """存储层错误（连接失败、文件读写失败等）。"""


# ---------------------------------------------------------------- 密码

def hash_password(password):
    """生成带随机盐的 SHA-256 密码哈希，格式：盐$摘要。"""
    salt = secrets.token_hex(16)
    digest = hashlib.sha256((salt + password).encode("utf-8")).hexdigest()
    return f"{salt}${digest}"


def verify_password(password, stored):
    """校验明文密码与存储的哈希是否一致。"""
    try:
        salt, digest = stored.split("$", 1)
    except ValueError:
        return False
    return hashlib.sha256((salt + password).encode("utf-8")).hexdigest() == digest


# ---------------------------------------------------------------- 数据校验

def last_six_id(id_card):
    """取身份证号后 6 位（用于生成初始密码）。"""
    text = str(id_card or "").strip()
    return text[-6:] if len(text) >= 6 else text


def default_student_password(student_id, id_card):
    """学生初始密码：学号 + 身份证后 6 位。"""
    return f"{str(student_id).strip()}{last_six_id(id_card)}"


def default_teacher_password(employee_id, id_card):
    """教师初始密码：工号 + 身份证后 6 位。"""
    return f"{str(employee_id).strip()}{last_six_id(id_card)}"


def mask_id_card(id_card):
    """身份证号脱敏：保留前 6 位与后 4 位，中间打码。"""
    text = str(id_card or "").strip()
    if len(text) != 18:
        return text
    return f"{text[:6]}********{text[-4:]}"


def validate_new_password(password):
    """用户自行设置的新密码强度校验，返回错误信息或 None。"""
    if not password or len(password) < 6:
        return tr('密码长度至少为 6 位')
    if not any(c.isalpha() for c in password) or not any(c.isdigit() for c in password):
        return tr('密码需同时包含字母和数字')
    return None


def _validate_id_card(id_card):
    idc = str(id_card or "").strip()
    if len(idc) != 18:
        return tr('身份证号应为 18 位')
    if not (idc[:17].isdigit() and (idc[-1].isdigit() or idc[-1] in "xX")):
        return tr('身份证号格式不正确')
    return None


def validate_student(
    student_id, name, gender, age, enroll_year, id_card="", class_name=""
):
    """校验学生字段，返回错误信息列表（为空表示通过）。"""
    errors = []
    if not student_id or not str(student_id).strip():
        errors.append(tr('学号不能为空'))
    if not name or not str(name).strip():
        errors.append(tr('姓名不能为空'))
    if gender not in ("男", "女"):
        errors.append(tr('性别只能填写“男”或“女”'))
    if str(age).strip() != "":
        try:
            if not (0 <= int(age) <= 150):
                errors.append(tr('年龄应为 0~150 之间的整数'))
        except (TypeError, ValueError):
            errors.append(tr('年龄应为整数'))
    if str(enroll_year).strip() == "":
        errors.append(tr('入学年份不能为空'))
    else:
        try:
            if not (1980 <= int(enroll_year) <= 2100):
                errors.append(tr('入学年份应为 1980~2100 之间的整数（如 2025）'))
        except (TypeError, ValueError):
            errors.append(tr('入学年份应为整数（如 2025）'))
    id_error = _validate_id_card(id_card)
    if id_error:
        errors.append(id_error)
    if len(str(class_name or "").strip()) > 50:
        errors.append(tr('班级名称过长（最多 50 字）'))
    return errors


def validate_teacher(username, employee_id, id_card, role):
    """校验教师账号字段，返回错误信息列表（为空表示通过）。"""
    errors = []
    if not username or not str(username).strip():
        errors.append(tr('教师账号不能为空'))
    if not employee_id or not str(employee_id).strip():
        errors.append(tr('工号不能为空'))
    id_error = _validate_id_card(id_card)
    if id_error:
        errors.append(id_error)
    if role not in ("teacher", "admin"):
        errors.append(tr('角色只能是“教师”或“管理员”'))
    return errors


def validate_score(year, chinese, math, english):
    """校验某一年度的成绩，返回错误信息列表（为空表示通过）。"""
    errors = []
    if str(year).strip() == "":
        errors.append(tr('年份不能为空'))
    else:
        try:
            if not (1980 <= int(year) <= 2100):
                errors.append(tr('年份应为 1980~2100 之间的整数（如 2025）'))
        except (TypeError, ValueError):
            errors.append(tr('年份应为整数（如 2025）'))
    for label, value in ((tr('语文'), chinese), (tr('数学'), math), (tr('英语'), english)):
        if str(value).strip() != "":
            try:
                if not (0 <= float(value) <= 150):
                    errors.append(tr('{}成绩应为 0~150 之间的数字').format(label))
            except (TypeError, ValueError):
                errors.append(tr('{}成绩应为数字').format(label))
    return errors


# ---------------------------------------------------------------- 统一接口

class Storage:
    """数据存储统一接口，两种实现都遵循该接口。"""

    mode = tr('基础存储')

    # ---- 学生 ----

    def get_student(self, student_id):
        raise NotImplementedError

    def student_login(self, student_id, password):
        raise NotImplementedError

    def list_students(self, keyword=None):
        raise NotImplementedError

    def list_deleted_students(self):
        raise NotImplementedError

    def add_student(
        self, student_id, name, gender, age, enroll_year, id_card,
        password=None, class_name="",
    ):
        raise NotImplementedError

    def update_student(
        self, student_id, name, gender, age, enroll_year, id_card, class_name=""
    ):
        raise NotImplementedError

    def change_student_password(self, student_id, old_password, new_password):
        raise NotImplementedError

    def restore_student(self, student_id):
        raise NotImplementedError

    def purge_student(self, student_id):
        raise NotImplementedError

    def delete_student(self, student_id):
        raise NotImplementedError

    # ---- 分年度成绩 ----

    def get_scores(self, student_id):
        raise NotImplementedError

    def get_all_scores(self):
        raise NotImplementedError

    def get_score(self, student_id, year):
        raise NotImplementedError

    def add_score(self, student_id, year, chinese, math, english):
        raise NotImplementedError

    def update_score(self, student_id, year, chinese, math, english):
        raise NotImplementedError

    def delete_score(self, student_id, year):
        raise NotImplementedError

    # ---- 教师账号 ----

    def teacher_login(self, username, password):
        raise NotImplementedError

    def admin_login(self, username, password):
        raise NotImplementedError

    def change_teacher_password(self, username, old_password, new_password):
        raise NotImplementedError

    def add_teacher(
        self,
        username,
        real_name,
        password,
        role="teacher",
        employee_id="",
        id_card="",
    ):
        raise NotImplementedError

    def list_teachers(self):
        raise NotImplementedError

    def update_teacher(
        self, username, real_name, role, new_password=None,
        employee_id=None, id_card=None,
    ):
        raise NotImplementedError

    def delete_teacher(self, username):
        raise NotImplementedError

    # ---- 日志与导出 ----

    def add_log(self, operator, role, action, target="", detail=""):
        raise NotImplementedError

    def list_logs(self, limit=500):
        raise NotImplementedError

    def clear_logs(self):
        """清空全部操作日志（仅管理员调用）。"""
        raise NotImplementedError

    def export_to_excel(self, path):
        raise NotImplementedError

    def describe(self):
        """返回存储方式描述，用于窗口标题等。"""
        return self.mode
