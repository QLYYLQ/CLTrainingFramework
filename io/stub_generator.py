"""
IO 类型存根自动生成器

此模块用于生成 IO.load() 方法的类型存根文件，使 IDE 能够根据文件后缀推断返回类型。

使用方式：
    python -m CLTrainingFramework.io

    或在代码中：
    from CLTrainingFramework.io import generate_io_stubs
    generate_io_stubs()
"""

from pathlib import Path
from typing import Optional

from CLTrainingFramework.io.Protocol import _SuffixRegistry as IORegistry


# 内置返回类型映射（handler 类名 -> 返回类型字符串）
DEFAULT_RETURN_TYPES: dict[str, str] = {
    "BaseImage": "PIL.Image.Image",
    "BaseText": "str",
    "JsonText": "dict[str, Any]",
    "YamlText": "dict[str, Any]",
    "BaseVideo": "torchvision.io.VideoReader",
}

# 导入语句映射（返回类型 -> 需要的 import）
TYPE_IMPORTS: dict[str, str] = {
    "PIL.Image.Image": "from PIL.Image import Image as PILImage",
    "torchvision.io.VideoReader": "from torchvision.io import VideoReader",
}

# 类型字符串在 stub 中的表示（返回类型 -> stub 中使用的名称）
TYPE_STUB_NAMES: dict[str, str] = {
    "PIL.Image.Image": "PILImage",
    "torchvision.io.VideoReader": "VideoReader",
}


def _get_handler_return_type(handler_class) -> str:
    """
    获取 handler 类的返回类型。

    优先使用 handler 类的 return_type 属性，否则从 DEFAULT_RETURN_TYPES 查找。
    """
    # 优先使用类上定义的 return_type 属性
    if hasattr(handler_class, "return_type"):
        return handler_class.return_type

    # 从默认映射查找
    class_name = handler_class.__name__
    return DEFAULT_RETURN_TYPES.get(class_name, "Any")


def _collect_suffix_info() -> dict[str, dict]:
    """
    从 IORegistry 收集所有后缀信息。

    Returns:
        {
            suffix: {
                "handler": handler_class,
                "return_type": "PIL.Image.Image",
                "modality": "Image",
                "is_collision": False,
            }
        }
    """
    suffix_info: dict[str, dict] = {}
    collision_suffixes = IORegistry.collision_suffix

    for modality, registry in IORegistry.items():
        base_io = registry.get("BaseIO")
        base_suffixes = set(registry.get("base_suffixes", []))
        custom_handlers = registry.get("Custom", {})

        # 处理 base suffixes
        if base_io:
            for suffix in base_suffixes:
                suffix_lower = suffix.lstrip(".").lower()
                if suffix_lower not in custom_handlers:
                    suffix_info[suffix_lower] = {
                        "handler": base_io,
                        "return_type": _get_handler_return_type(base_io),
                        "modality": modality,
                        "is_collision": suffix_lower in collision_suffixes,
                    }

        # 处理 custom handlers
        for suffix, handler in custom_handlers.items():
            if handler:
                suffix_lower = suffix.lstrip(".").lower()
                suffix_info[suffix_lower] = {
                    "handler": handler,
                    "return_type": _get_handler_return_type(handler),
                    "modality": modality,
                    "is_collision": suffix_lower in collision_suffixes,
                }

    return suffix_info


def _group_by_modality(suffix_info: dict[str, dict]) -> dict[str, set[str]]:
    """
    按模态分组返回类型。

    Returns:
        {
            "Image": {"PIL.Image.Image"},
            "Text": {"str", "dict[str, Any]"},
            "Video": {"torchvision.io.VideoReader"},
        }
    """
    groups: dict[str, set[str]] = {}

    for suffix, info in suffix_info.items():
        modality = info["modality"]
        return_type = info["return_type"]
        if modality not in groups:
            groups[modality] = set()
        groups[modality].add(return_type)

    return groups


def _generate_modality_overload(modality: str, return_types: set[str]) -> list[str]:
    """生成基于 modality 参数的 @overload 块。"""
    # 构建返回类型
    if len(return_types) == 1:
        return_type = next(iter(return_types))
        stub_type = TYPE_STUB_NAMES.get(return_type, return_type)
    else:
        # 多个返回类型，使用 Union
        type_strs = [TYPE_STUB_NAMES.get(t, t) for t in sorted(return_types)]
        stub_type = f"Union[{', '.join(type_strs)}]"

    lines = [
        f"    # modality=\"{modality}\"",
        "    @overload",
        "    def load(",
        "        self,",
        "        path: Union[str, PathLike[str]],",
        f'        modality: Literal["{modality}"],',
        "        collision_dict: Optional[dict[str, str]] = None,",
        "        **kwargs: Any,",
        f"    ) -> {stub_type}: ...",
        "",
    ]
    return lines


def _generate_stub_content(suffix_info: dict[str, dict]) -> str:
    """生成完整的 stub 文件内容。"""
    modality_groups = _group_by_modality(suffix_info)

    # 收集所有返回类型以确定需要的 imports
    all_return_types: set[str] = set()
    for return_types in modality_groups.values():
        all_return_types.update(return_types)

    # 收集需要的 imports
    imports_needed: set[str] = set()
    for return_type in all_return_types:
        if return_type in TYPE_IMPORTS:
            imports_needed.add(TYPE_IMPORTS[return_type])

    # 文件头
    lines = [
        '"""',
        "Auto-generated stub file for IO.load() type hints.",
        "",
        "Generated by: python -m CLTrainingFramework.io",
        "Do not edit manually - regenerate after registering new handlers.",
        "",
        "Usage:",
        '    image = IO.load("test.png", modality="Image")  # -> PILImage',
        '    text = IO.load("file.txt", modality="Text")    # -> str',
        '    data = IO.load("config.json", modality="Text") # -> Union[str, dict]',
        '    video = IO.load("clip.mp4", modality="Video")  # -> VideoReader',
        '"""',
        "",
        "from typing import overload, Union, Optional, Any, Literal",
        "from os import PathLike",
    ]

    # 添加类型 imports
    for imp in sorted(imports_needed):
        lines.append(imp)

    lines.extend([
        "",
        "",
        "class IO:",
        '    """',
        "    IO Router with type inference based on modality parameter.",
        "",
        "    When modality is specified, returns the corresponding type.",
        "    Without modality, returns Any (suffix-based auto-detection at runtime).",
        '    """',
        "",
        "    def __init__(self, modality: Optional[str] = None) -> None: ...",
        "",
    ])

    # 按模态生成 overloads
    modality_order = ["Image", "Text", "Video"]

    # 先按预定义顺序生成
    for modality in modality_order:
        if modality in modality_groups:
            lines.extend(_generate_modality_overload(modality, modality_groups[modality]))

    # 生成其他未在预定义顺序中的模态
    for modality, return_types in modality_groups.items():
        if modality not in modality_order:
            lines.extend(_generate_modality_overload(modality, return_types))

    # 通用 fallback（不指定 modality 时）
    lines.extend([
        "    # Fallback when modality is not specified (auto-detection)",
        "    @overload",
        "    def load(",
        "        self,",
        "        path: Union[str, PathLike[str]],",
        "        modality: None = None,",
        "        collision_dict: Optional[dict[str, str]] = None,",
        "        **kwargs: Any,",
        "    ) -> Any: ...",
        "",
        "    # Implementation signature",
        "    def load(",
        "        self,",
        "        path: Union[str, PathLike[str]],",
        "        modality: Optional[str] = None,",
        "        collision_dict: Optional[dict[str, str]] = None,",
        "        **kwargs: Any,",
        "    ) -> Any: ...",
        "",
        "    def write(",
        "        self,",
        "        path: Union[str, PathLike[str]],",
        "        data: Any,",
        "        modality: Optional[str] = None,",
        "        collision_dict: Optional[dict[str, str]] = None,",
        "        **kwargs: Any,",
        "    ) -> None: ...",
        "",
        "    def get_io(",
        "        self,",
        "        path: Union[str, PathLike[str]],",
        "        modality: Optional[str] = None,",
        "        collision_dict: Optional[dict[str, str]] = None,",
        "    ) -> Any: ...",
        "",
        "    def delete_cache(self, name: str) -> None: ...",
        "",
    ])

    return "\n".join(lines)


def generate_io_stubs(output_dir: Optional[Path] = None) -> Path:
    """
    生成 IO 类的类型存根文件。

    Args:
        output_dir: 输出目录，默认为 io 包所在目录

    Returns:
        生成的 stub 文件路径
    """
    if output_dir is None:
        output_dir = Path(__file__).parent

    output_dir = Path(output_dir)
    output_file = output_dir / "Mapping.pyi"

    # 收集信息并生成内容
    suffix_info = _collect_suffix_info()
    content = _generate_stub_content(suffix_info)

    # 写入文件
    output_file.write_text(content, encoding="utf-8")

    return output_file


def print_registry_summary() -> None:
    """打印当前注册表摘要（用于调试）。"""
    suffix_info = _collect_suffix_info()
    modality_groups = _group_by_modality(suffix_info)

    print("IORegistry Summary:")
    print("-" * 40)
    for modality, return_types in modality_groups.items():
        # 统计该模态下的后缀数量
        suffixes = [s for s, info in suffix_info.items() if info["modality"] == modality]
        print(f"  {modality}: {len(suffixes)} suffixes")
        print(f"    Return types: {', '.join(sorted(return_types))}")

    collision = IORegistry.collision_suffix
    if collision:
        print(f"\nCollision suffixes: {collision}")