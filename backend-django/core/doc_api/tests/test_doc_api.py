import json
import os
import random
from pathlib import Path

import pytest
import requests


def test_doc_api_summary(client):
    resp = client.get("/api/core/doc-api/summary")
    assert resp.status_code == 200
    data = resp.json()
    assert "endpoint_count" in data
    assert isinstance(data["endpoint_count"], int)
    assert data["endpoint_count"] > 0


def test_doc_api_endpoints_list(client):
    resp = client.get("/api/core/doc-api/endpoints?page=1&page_size=3")
    assert resp.status_code == 200
    data = resp.json()
    assert data["page"] == 1
    assert data["page_size"] == 3
    assert "total" in data
    assert isinstance(data["items"], list)
    assert len(data["items"]) > 0
    first = data["items"][0]
    assert "operation_id" in first
    assert "method" in first
    assert "path" in first


def test_doc_api_endpoint_detail(client):
    list_resp = client.get("/api/core/doc-api/endpoints?page=1&page_size=1")
    assert list_resp.status_code == 200
    items = list_resp.json()["items"]
    assert items
    operation_id = items[0]["operation_id"]

    detail_resp = client.get(f"/api/core/doc-api/endpoints/{operation_id}")
    assert detail_resp.status_code == 200
    detail = detail_resp.json()
    assert detail["operation_id"] == operation_id
    assert "responses" in detail


def test_doc_api_search_by_operation_id(client):
    payload = {"keyword": "PER_BASE_0001", "page": 1, "page_size": 10}
    resp = client.post(
        "/api/core/doc-api/endpoints/search",
        data=json.dumps(payload),
        content_type="application/json",
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] >= 1
    assert any(item["operation_id"] == "PER_BASE_0001" for item in data["items"])


def _load_openapi_spec() -> dict:
    repo_root = Path(__file__).resolve().parents[4]
    spec_path = repo_root / "docs" / "his" / "openapi.json"
    return json.loads(spec_path.read_text(encoding="utf-8"))


def _load_env_file(env_path: Path) -> dict:
    try:
        text = env_path.read_text(encoding="utf-8")
    except OSError:
        return {}

    values: dict[str, str] = {}
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("export "):
            line = line[len("export ") :].strip()
        if "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip()
        if (
            len(value) >= 2
            and ((value[0] == value[-1] == '"') or (value[0] == value[-1] == "'"))
        ):
            value = value[1:-1]
        values[key] = value
    return values


def _pick_random_operation(spec: dict, seed: int) -> tuple[str, str, dict]:
    get_candidates: list[tuple[str, str, dict]] = []
    other_candidates: list[tuple[str, str, dict]] = []
    paths = spec.get("paths", {})
    for p, item in paths.items():
        if not isinstance(item, dict):
            continue
        for m, op in item.items():
            if not isinstance(op, dict):
                continue
            method = str(m).upper()
            if method not in {"GET", "POST", "PUT", "DELETE", "PATCH"}:
                continue
            if method == "GET":
                get_candidates.append((p, method, op))
                continue
            else:
                request_body = op.get("requestBody") or {}
                content = request_body.get("content") or {}
                app_json = content.get("application/json") or {}
                if "example" not in app_json and not app_json.get("examples"):
                    continue
            other_candidates.append((p, method, op))

    candidates = other_candidates or get_candidates
    if not candidates:
        raise AssertionError("openapi.json 未找到任何可测试的 paths")

    rng = random.Random(seed)
    return rng.choice(candidates)


def _build_request_json(operation: dict) -> object:
    request_body = operation.get("requestBody") or {}
    content = request_body.get("content") or {}
    app_json = content.get("application/json") or {}

    if "example" in app_json:
        return app_json["example"]

    examples = app_json.get("examples") or {}
    if isinstance(examples, dict) and examples:
        first = next(iter(examples.values()))
        if isinstance(first, dict) and "value" in first:
            return first["value"]

    return {}


def _build_query_params(operation: dict, body: object | None) -> dict | None:
    parameters = operation.get("parameters") or []
    if not isinstance(parameters, list) or not parameters:
        return None

    body_values = {}
    if isinstance(body, dict):
        body_values = body.get("payload") if isinstance(body.get("payload"), dict) else body

    params: dict[str, object] = {}
    for p in parameters:
        if not isinstance(p, dict):
            continue
        if p.get("in") != "query":
            continue
        name = p.get("name")
        if not name:
            continue
        required = bool(p.get("required"))
        if name in body_values:
            params[str(name)] = body_values[name]
            continue
        if not required:
            continue
        schema = p.get("schema") or {}
        t = schema.get("type")
        if t == "integer":
            params[str(name)] = 0
        elif t == "number":
            params[str(name)] = 0
        else:
            params[str(name)] = "1"

    return params or None


def _build_auth_headers_candidates(
    auth_header: str,
    auth_value: str | None,
    doc_token: str | None,
    his_token: str | None,
) -> list[dict]:
    candidates: list[dict] = []

    if auth_value:
        candidates.append({auth_header: auth_value})
    else:
        if doc_token:
            candidates.append({auth_header: doc_token})
            candidates.append({auth_header: f"Bearer {doc_token}"})
            candidates.append({"token": doc_token})
            candidates.append({"X-Token": doc_token})
        if his_token:
            candidates.append({auth_header: his_token})
            header_value = his_token if " " in his_token else f"Bearer {his_token}"
            candidates.append({auth_header: header_value})
            candidates.append({"token": his_token})
            candidates.append({"X-Token": his_token})

    unique: list[dict] = []
    seen: set[tuple[tuple[str, str], ...]] = set()
    for hdr in candidates:
        key = tuple(sorted((str(k), str(v)) for k, v in hdr.items()))
        if key not in seen:
            seen.add(key)
            unique.append(hdr)
    return unique


def _summarize_response(resp: requests.Response) -> str:
    try:
        payload = resp.json()
    except ValueError:
        text = (resp.text or "").replace("\n", " ")
        return text[:500]

    if isinstance(payload, dict):
        for k in ("errorDetail", "errors", "data"):
            if k in payload and payload[k] is not None:
                try:
                    v = json.dumps(payload[k], ensure_ascii=False)
                except TypeError:
                    v = str(payload[k])
                return f"{k}={v[:500]}"
        for k in ("success", "succ", "code", "status"):
            if k in payload:
                return f"{k}={payload[k]}"
        for k in ("msg", "message", "error", "errorMsg", "errorMessage", "detail"):
            if k in payload and isinstance(payload[k], str):
                return payload[k][:500]
        keys = ",".join(sorted(payload.keys()))
        return f"json_keys={keys}"

    return str(payload)[:500]


def _is_auth_error_response(resp: requests.Response) -> bool:
    if resp.status_code in {401, 403}:
        return True

    try:
        payload = resp.json()
    except ValueError:
        return False

    if not isinstance(payload, dict):
        return False

    err = payload.get("errorDetail")
    if isinstance(err, dict):
        code = str(err.get("code") or "")
        message = str(err.get("message") or "")
        detail_msg = str(err.get("detailMsg") or "")
        if code == "ES0300":
            return True
        combined = f"{message} {detail_msg}"
        if "安全验证错误" in combined:
            return True
        if "Token/AccessKey" in combined:
            return True

    message = str(payload.get("message") or payload.get("msg") or "")
    if "Token/AccessKey" in message:
        return True

    return False


def _env_truthy(name: str) -> bool:
    return os.environ.get(name, "").strip().lower() in {"1", "true", "yes", "y", "on"}


def _iter_operations(spec: dict) -> list[tuple[str, str, dict]]:
    out: list[tuple[str, str, dict]] = []
    paths = spec.get("paths", {})
    if not isinstance(paths, dict):
        return out
    for p, item in paths.items():
        if not isinstance(item, dict):
            continue
        for m, op in item.items():
            if not isinstance(op, dict):
                continue
            method = str(m).upper()
            if method not in {"GET", "POST", "PUT", "DELETE", "PATCH"}:
                continue
            out.append((str(p), method, op))
    return out


def _pick_preflight_operation(spec: dict) -> tuple[str, str, dict]:
    operations = _iter_operations(spec)
    if not operations:
        raise AssertionError("openapi.json 未找到任何可测试的 paths")
    get_ops = [(p, m, op) for p, m, op in operations if m == "GET"]
    post_ops = [(p, m, op) for p, m, op in operations if m != "GET"]
    candidates = get_ops or post_ops
    candidates.sort(key=lambda t: (t[0], t[1], str((t[2] or {}).get("operationId") or "")))
    return candidates[0]


def _call_his_operation(
    *,
    base_url: str,
    path: str,
    method: str,
    operation: dict,
    headers: dict | None,
    timeout: float,
) -> requests.Response:
    url = base_url.rstrip("/") + path
    params = None
    body = None
    if method == "GET":
        params = {}
    else:
        body = _build_request_json(operation)
        params = _build_query_params(operation, body)
    return requests.request(
        method=method,
        url=url,
        headers=headers or {},
        params=params,
        json=body,
        timeout=timeout,
    )


def test_his_url_reachable():
    repo_root = Path(__file__).resolve().parents[4]
    dotenv = _load_env_file(repo_root / "backend-django" / ".env")

    his_base_url = (
        os.environ.get("HIS_BASE_URL")
        or os.environ.get("DOC_API_URL")
        or dotenv.get("DOC_API_URL")
    )
    if not his_base_url:
        pytest.skip("未设置 HIS_BASE_URL/DOC_API_URL，跳过真实 HIS 联调测试")

    timeout = float(os.environ.get("HIS_TIMEOUT_SECONDS", "10"))
    try:
        resp = requests.get(his_base_url.rstrip("/") + "/", timeout=timeout)
    except requests.RequestException as e:
        raise AssertionError(f"HIS URL 不可达 url={his_base_url} err={type(e).__name__}:{e}") from e

    assert resp is not None


def test_his_token_preflight_acceptance():
    if not _env_truthy("HIS_VALIDATE_TOKEN"):
        pytest.skip("未设置 HIS_VALIDATE_TOKEN=1，跳过 token 预检测试")

    repo_root = Path(__file__).resolve().parents[4]
    dotenv = _load_env_file(repo_root / "backend-django" / ".env")

    his_base_url = (
        os.environ.get("HIS_BASE_URL")
        or os.environ.get("DOC_API_URL")
        or dotenv.get("DOC_API_URL")
    )
    if not his_base_url:
        pytest.skip("未设置 HIS_BASE_URL/DOC_API_URL，跳过真实 HIS 联调测试")

    token = os.environ.get("DOC_API_TOKEN") or dotenv.get("DOC_API_TOKEN")
    if not token:
        pytest.skip("未设置 DOC_API_TOKEN，跳过 token 预检测试")

    timeout = float(os.environ.get("HIS_TIMEOUT_SECONDS", "10"))
    spec = _load_openapi_spec()
    path, method, operation = _pick_preflight_operation(spec)
    operation_id = operation.get("operationId")

    unauth = _call_his_operation(
        base_url=his_base_url,
        path=path,
        method=method,
        operation=operation,
        headers={},
        timeout=timeout,
    )

    headers_candidates = _build_auth_headers_candidates(
        auth_header=os.environ.get("HIS_AUTH_HEADER", "Authorization"),
        auth_value=os.environ.get("HIS_AUTH_VALUE"),
        doc_token=token,
        his_token=os.environ.get("HIS_TOKEN"),
    )
    if not headers_candidates:
        pytest.skip("未设置可用的鉴权参数，跳过 token 预检测试")

    responses: list[tuple[dict, requests.Response]] = []
    for headers in headers_candidates:
        resp = _call_his_operation(
            base_url=his_base_url,
            path=path,
            method=method,
            operation=operation,
            headers=headers,
            timeout=timeout,
        )
        responses.append((headers, resp))

    status_line = ", ".join(f"{','.join(sorted(h.keys())) or '-'}={r.status_code}" for h, r in responses)

    if any(r.status_code == 200 for _, r in responses):
        return

    non_auth = [r for _, r in responses if not _is_auth_error_response(r) and r.status_code < 500]
    if non_auth:
        return

    unauth_detail = _summarize_response(unauth)
    best = next((r for _, r in responses if r.status_code < 500), responses[-1][1])
    best_detail = _summarize_response(best)
    raise AssertionError(
        f"HIS token 预检失败（鉴权未通过）op={operation_id} method={method} path={path} "
        f"unauth_status={unauth.status_code} unauth_resp={unauth_detail} "
        f"auth_statuses=[{status_line}] auth_resp={best_detail}"
    )


def test_his_openapi_random_endpoint_returns_success():
    repo_root = Path(__file__).resolve().parents[4]
    dotenv = _load_env_file(repo_root / "backend-django" / ".env")

    his_base_url = (
        os.environ.get("HIS_BASE_URL")
        or os.environ.get("DOC_API_URL")
        or dotenv.get("DOC_API_URL")
    )
    if not his_base_url:
        pytest.skip("未设置 HIS_BASE_URL/DOC_API_URL，跳过真实 HIS 联调测试")

    auth_header = os.environ.get("HIS_AUTH_HEADER", "Authorization")
    auth_value = os.environ.get("HIS_AUTH_VALUE")
    doc_token = os.environ.get("DOC_API_TOKEN") or dotenv.get("DOC_API_TOKEN")
    his_token = os.environ.get("HIS_TOKEN")

    headers_candidates = _build_auth_headers_candidates(
        auth_header=auth_header,
        auth_value=auth_value,
        doc_token=doc_token,
        his_token=his_token,
    )
    if not headers_candidates:
        pytest.skip("未设置 HIS_AUTH_VALUE/HIS_TOKEN/DOC_API_TOKEN，跳过真实 HIS 联调测试")

    seed = int(os.environ.get("HIS_OPENAPI_RANDOM_SEED", "1"))
    timeout = float(os.environ.get("HIS_TIMEOUT_SECONDS", "10"))

    spec = _load_openapi_spec()
    strict = os.environ.get("HIS_STRICT", "").strip().lower() in {"1", "true", "yes"}

    pre_path, pre_method, pre_operation = _pick_preflight_operation(spec)
    pre_operation_id = pre_operation.get("operationId")
    pre_responses: list[tuple[dict, requests.Response]] = []
    for headers in headers_candidates:
        resp = _call_his_operation(
            base_url=his_base_url,
            path=pre_path,
            method=pre_method,
            operation=pre_operation,
            headers=headers,
            timeout=timeout,
        )
        pre_responses.append((headers, resp))

    if not any(r.status_code == 200 for _, r in pre_responses):
        pre_non_auth = [
            r for _, r in pre_responses if not _is_auth_error_response(r) and r.status_code < 500
        ]
        if not pre_non_auth and not strict:
            pre_status_line = ", ".join(
                f"{','.join(sorted(h.keys())) or '-'}={r.status_code}" for h, r in pre_responses
            )
            best = next((r for _, r in pre_responses if r.status_code < 500), pre_responses[-1][1])
            best_detail = _summarize_response(best)
            pytest.skip(
                f"HIS token 预检未通过，跳过随机接口联调 op={pre_operation_id} "
                f"method={pre_method} path={pre_path} statuses=[{pre_status_line}] resp={best_detail}"
            )

    path, method, operation = _pick_random_operation(spec, seed=seed)
    url = his_base_url.rstrip("/") + path

    params = None
    body = None
    if method == "GET":
        params = {}
    else:
        body = _build_request_json(operation)
        params = _build_query_params(operation, body)

    last_resp = None
    responses: list[tuple[dict, requests.Response]] = []
    for headers in headers_candidates:
        resp = requests.request(
            method=method,
            url=url,
            headers=headers,
            params=params,
            json=body,
            timeout=timeout,
        )
        responses.append((headers, resp))
        last_resp = resp
        if resp.status_code == 200:
            break

    assert last_resp is not None
    if last_resp.status_code != 200:
        operation_id = operation.get("operationId")
        header_sets = sorted({",".join(sorted(str(k) for k in h.keys())) for h, _ in responses})
        status_line = ", ".join(
            f"{','.join(sorted(h.keys())) or '-'}={r.status_code}" for h, r in responses
        )

        if not strict:
            if all(_is_auth_error_response(r) or r.status_code >= 500 for _, r in responses):
                best = next((r for _, r in responses if r.status_code < 500), last_resp)
                best_detail = _summarize_response(best)
                pytest.skip(
                    f"HIS 鉴权未就绪或服务异常，跳过联调测试 op={operation_id} "
                    f"method={method} path={path} statuses=[{status_line}] resp={best_detail}"
                )

        best = next((r for _, r in responses if r.status_code < 500), last_resp)
        detail = _summarize_response(best)
        raise AssertionError(
            f"HIS 非200 status={last_resp.status_code} op={operation_id} "
            f"method={method} path={path} headers={header_sets} "
            f"params={'y' if params else 'n'} body={'y' if body else 'n'} "
            f"statuses=[{status_line}] resp={detail}"
        )

    try:
        payload = last_resp.json()
    except ValueError:
        payload = None

    if isinstance(payload, dict) and "success" in payload:
        assert payload["success"] is True
