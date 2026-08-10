# -*- coding: utf-8 -*-
"""登录安全：失败次数限制与临时锁定。"""
import time

MAX_ATTEMPTS = 5
LOCK_SECONDS = 300


class LoginGuard:
    def __init__(self):
        self._failures = {}  # key -> [count, lock_until]

    def remaining(self, key):
        entry = self._failures.get(key)
        if not entry:
            return MAX_ATTEMPTS
        count, lock_until = entry
        if lock_until and time.time() < lock_until:
            return 0
        return max(0, MAX_ATTEMPTS - count)

    def lock_seconds_left(self, key):
        entry = self._failures.get(key)
        if entry and entry[1] and time.time() < entry[1]:
            return int(entry[1] - time.time())
        return 0

    def record_failure(self, key):
        entry = self._failures.get(key)
        if not entry:
            entry = [1, None]
            self._failures[key] = entry
        else:
            entry[0] += 1
            if entry[0] >= MAX_ATTEMPTS:
                entry[1] = time.time() + LOCK_SECONDS
        return self.remaining(key)

    def reset(self, key):
        self._failures.pop(key, None)


# 全局共享的登录守卫（同一个程序内生效）
login_guard = LoginGuard()
