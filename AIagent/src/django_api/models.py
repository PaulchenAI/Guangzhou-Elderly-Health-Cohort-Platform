# -*- coding: utf-8 -*-
"""
Django API 数据模型

定义 API 端点描述和配置数据类
"""

from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional


@dataclass
class DjangoAPIConfig:
    """Django API 配置"""
    base_url: str = "http://localhost:8000"
    username: str = ""
    password: str = ""
    timeout: int = 30
    # RAG 检索配置
    enable_rag: bool = True
    keyword_filter_threshold: int = 20
    top_k: int = 10
    similarity_threshold: float = 0.5


@dataclass
class APIEndpoint:
    """API 端点描述"""
    path: str
    method: str
    operation_id: str
    summary: str = ""
    description: str = ""
    tags: List[str] = field(default_factory=list)
    parameters: List[Dict[str, Any]] = field(default_factory=list)
    request_body: Optional[Dict[str, Any]] = None
    responses: Dict[str, Any] = field(default_factory=dict)
    
    def to_ai_description(self, include_schema: bool = False) -> str:
        """
        将 API 端点转换为 AI 可理解的文本描述
        用于 RAG 向量化和 LLM 理解
        
        Args:
            include_schema: 是否包含详细的请求/响应 Schema
        """
        lines = []
        
        # 基本信息
        lines.append(f"【{self.method.upper()}】{self.path}")
        # 显式包含 operation_id，便于 AI/检索与测试断言
        lines.append(f"操作ID：{self.operation_id}")
        lines.append(f"功能：{self.summary or self.description or self.operation_id}")
        
        # 分类标签
        if self.tags:
            lines.append(f"分类：{', '.join(self.tags)}")
        
        # 参数信息
        if self.parameters:
            lines.append("参数：")
            for param in self.parameters:
                param_name = param.get("name", "")
                param_in = param.get("in", "query")
                param_desc = param.get("description", "")
                param_required = param.get("required", False)
                required_mark = "*" if param_required else ""
                lines.append(f"  - {param_name}{required_mark}({param_in}): {param_desc}")
        
        # 请求体（解析具体字段）
        if self.request_body:
            lines.append("请求体：")
            body_schema = self._extract_schema(self.request_body)
            if body_schema:
                lines.append(self._format_schema(body_schema, indent=2, include_details=include_schema))
            else:
                lines.append("  JSON 数据")
        
        # 响应体（解析具体字段）
        if self.responses and include_schema:
            success_response = self.responses.get("200") or self.responses.get("201")
            if success_response:
                lines.append("响应：")
                resp_schema = self._extract_schema(success_response)
                if resp_schema:
                    lines.append(self._format_schema(resp_schema, indent=2, include_details=True))
        
        return "\n".join(lines)
    
    @classmethod
    def set_schema_components(cls, components: Dict[str, Any]):
        """设置 OpenAPI schema 的 components/schemas，用于解析 $ref"""
        cls._schema_components = components
    
    @classmethod
    def get_schema_components(cls) -> Dict[str, Any]:
        """获取 schema components"""
        return getattr(cls, '_schema_components', {})
    
    def _extract_schema(self, obj: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """从 OpenAPI 对象中提取 schema"""
        if not obj:
            return None
        # content -> application/json -> schema
        content = obj.get("content", {})
        json_content = content.get("application/json", {})
        return json_content.get("schema")
    
    def _resolve_ref(self, schema: Dict[str, Any]) -> Dict[str, Any]:
        """解析 $ref 引用，返回实际的 schema"""
        if "$ref" not in schema:
            return schema
        
        ref_path = schema["$ref"]
        # 格式: #/components/schemas/TypeName
        if ref_path.startswith("#/components/schemas/"):
            type_name = ref_path.split("/")[-1]
            components = self.get_schema_components()
            if type_name in components:
                return components[type_name]
        
        return schema
    
    def _format_schema(self, schema: Dict[str, Any], indent: int = 0, include_details: bool = False, depth: int = 0) -> str:
        """格式化 schema 为可读文本"""
        if not schema or depth > 2:  # 限制递归深度
            return ""
        
        lines = []
        prefix = "  " * indent
        
        # 解析 $ref 引用
        if "$ref" in schema:
            resolved = self._resolve_ref(schema)
            if resolved != schema:
                return self._format_schema(resolved, indent, include_details, depth + 1)
            else:
                ref_name = schema["$ref"].split("/")[-1]
                return f"{prefix}类型: {ref_name}"
        
        schema_type = schema.get("type", "object")
        
        if schema_type == "object":
            properties = schema.get("properties", {})
            required_fields = schema.get("required", [])
            
            if properties:
                for prop_name, prop_schema in properties.items():
                    required_mark = "*" if prop_name in required_fields else ""
                    prop_type = prop_schema.get("type", "any")
                    prop_desc = prop_schema.get("description", prop_schema.get("title", ""))
                    
                    # 处理 $ref
                    if "$ref" in prop_schema:
                        ref_name = prop_schema["$ref"].split("/")[-1]
                        lines.append(f"{prefix}- {prop_name}{required_mark}: {ref_name} {prop_desc}")
                    # 简化嵌套对象
                    elif prop_type == "array":
                        items = prop_schema.get("items", {})
                        if "$ref" in items:
                            item_type = items["$ref"].split("/")[-1]
                        else:
                            item_type = items.get("type", "object")
                        lines.append(f"{prefix}- {prop_name}{required_mark}: array[{item_type}] {prop_desc}")
                    elif prop_type == "object":
                        lines.append(f"{prefix}- {prop_name}{required_mark}: object {prop_desc}")
                    else:
                        lines.append(f"{prefix}- {prop_name}{required_mark}: {prop_type} {prop_desc}")
            else:
                lines.append(f"{prefix}object")
        
        elif schema_type == "array":
            items = schema.get("items", {})
            if "$ref" in items:
                item_type = items["$ref"].split("/")[-1]
                lines.append(f"{prefix}array[{item_type}]")
                # 展开数组元素的字段（如果有）
                if include_details and depth < 2:
                    resolved_items = self._resolve_ref(items)
                    if resolved_items != items and resolved_items.get("properties"):
                        lines.append(f"{prefix}  元素字段:")
                        props = resolved_items.get("properties", {})
                        for prop_name, prop_schema in list(props.items())[:8]:  # 限制显示数量
                            prop_type = prop_schema.get("type", "any")
                            prop_desc = prop_schema.get("description", prop_schema.get("title", ""))[:30]
                            lines.append(f"{prefix}    - {prop_name}: {prop_type} {prop_desc}")
            else:
                item_type = items.get("type", "object")
                lines.append(f"{prefix}array[{item_type}]")
        
        else:
            lines.append(f"{prefix}{schema_type}")
        
        return "\n".join(lines)
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "path": self.path,
            "method": self.method,
            "operation_id": self.operation_id,
            "summary": self.summary,
            "description": self.description,
            "tags": self.tags,
            "parameters": self.parameters,
            "request_body": self.request_body,
            "responses": self.responses,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "APIEndpoint":
        """从字典创建"""
        return cls(
            path=data.get("path", ""),
            method=data.get("method", "GET"),
            operation_id=data.get("operation_id", ""),
            summary=data.get("summary", ""),
            description=data.get("description", ""),
            tags=data.get("tags", []),
            parameters=data.get("parameters", []),
            request_body=data.get("request_body"),
            responses=data.get("responses", {}),
        )
