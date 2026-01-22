# -*- coding: utf-8 -*-
"""
OpenAPI 最小结构校验器

说明：
- 为了保持依赖最小化，这里不引入第三方 openapi-spec-validator。
- 校验目标是“可用与可调试”，满足本项目对结构正确性的最低要求。
"""

from __future__ import annotations

from typing import Any, Dict, List


def validate_openapi_minimal(doc: Dict[str, Any]) -> List[str]:
    """
    返回错误列表；空列表表示通过最小校验。
    """
    errors: List[str] = []
    if not isinstance(doc, dict):
        return ["OpenAPI 文档必须是 JSON 对象"]

    if not str(doc.get("openapi", "")).startswith("3"):
        errors.append("缺少或不支持的 openapi 版本（必须为 3.x）")

    info = doc.get("info")
    if not isinstance(info, dict):
        errors.append("缺少 info 对象")
    else:
        if not info.get("title"):
            errors.append("info.title 不能为空")
        if not info.get("version"):
            errors.append("info.version 不能为空")

    paths = doc.get("paths")
    if not isinstance(paths, dict) or not paths:
        errors.append("paths 不能为空（未生成任何接口）")
    else:
        for path, item in paths.items():
            if not isinstance(path, str) or not path.startswith("/"):
                errors.append(f"非法 path key: {path!r}（必须以 / 开头）")
            if not isinstance(item, dict):
                errors.append(f"path item 必须为对象: {path}")
                continue
            for method, op in item.items():
                if method.lower() not in {"get", "post", "put", "delete", "patch"}:
                    continue
                if not isinstance(op, dict):
                    errors.append(f"{path} {method}: operation 必须为对象")
                    continue
                if "responses" not in op or not isinstance(op.get("responses"), dict) or not op["responses"]:
                    errors.append(f"{path} {method}: responses 不能为空")

    return errors

