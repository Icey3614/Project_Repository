# -*- coding: utf-8 -*-
"""成绩统计与排名计算（与存储方式无关）。"""

SUBJECTS = {
    "语文": "chinese_score",
    "数学": "math_score",
    "英语": "english_score",
}

PASS_LINE = 90  # 满分 150 分，及格线取 60%（90 分）


def compute_statistics(students, scores, year, class_name=None):
    """统计指定学年（可限定班级）的排名与科目汇总。"""
    pool = []
    for s in students:
        if class_name and (s.get("class_name") or "") != class_name:
            continue
        score = next(
            (
                r
                for r in scores
                if r["student_id"] == s["student_id"] and r["year"] == year
            ),
            None,
        )
        if score is None:
            continue
        values = {}
        total = 0.0
        has_any = False
        for label, key in SUBJECTS.items():
            value = score.get(key)
            if value is None:
                values[label] = None
            else:
                values[label] = float(value)
                total += float(value)
                has_any = True
        if not has_any:
            continue
        pool.append(
            {
                "student": s,
                **values,
                "total": round(total, 1),
                "avg": round(total / len(SUBJECTS), 1),
            }
        )

    # 排名（按总分降序，同分并列）
    pool.sort(key=lambda x: x["total"], reverse=True)
    rank = 0
    prev = None
    for index, item in enumerate(pool, start=1):
        if prev is None or item["total"] != prev:
            rank = index
        item["rank"] = rank
        prev = item["total"]

    # 科目汇总
    summary = {}
    for label in SUBJECTS:
        values = [x[label] for x in pool if x[label] is not None]
        if values:
            summary[label] = {
                "avg": round(sum(values) / len(values), 1),
                "max": max(values),
                "min": min(values),
                "pass_count": sum(1 for v in values if v >= PASS_LINE),
                "pass_rate": round(
                    sum(1 for v in values if v >= PASS_LINE) / len(values) * 100, 1
                ),
                "count": len(values),
            }
        else:
            summary[label] = None
    return {"rows": pool, "summary": summary, "count": len(pool)}
