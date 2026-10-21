#!/usr/bin/env python3
"""Build the standalone preview package of code-reading-assistant.

本仓库只发布一个版本：代码阅读助手（code-reading-assistant，零外部依赖）。
仓库布局与发行包内布局一致：skill 源码位于包根的 code-reading-assistant/ 目录，
docs/、cases/、integrations/ 为配套材料；发行包内部以 Skill 基础名做顶层目录。
"""

import argparse
import hashlib
import io
from pathlib import Path
import re
import zipfile


ROOT = Path(__file__).resolve().parents[1]
# 版本 -> 仓库内 Skill 源码相对路径
SKILLS = {
    "code": "code-reading-assistant",
}
# 版本 -> 仓库根 README（打包为包内 README.md）
README_FILES = {
    "code": "README.md",
}
# 版本 -> 仓库内默认规则模板（打包为 integrations/<模板基名>）
TEMPLATE_FILES = {
    "code": "integrations/code-reading-always-on.md",
}
# 代码版配套文件（打包为 docs/ 与 cases/）
SUPPORT_FILES = (
    "docs/SKILL-README.md",
    "docs/用法与示例.md",
    "docs/优化记录-v0.4.0.md",
    "cases/01-代码模块陪读/输入任务.md",
)


def build_packages(output, root=ROOT, editions=None):
    output = Path(output)
    output.mkdir(parents=True, exist_ok=True)
    built = []
    for edition, skill_rel in SKILLS.items():
        if editions is not None and edition not in editions:
            continue
        skill = root / skill_rel
        text = (skill / "SKILL.md").read_text(encoding="utf-8")
        version = re.search(r'^  version: "(\d+\.\d+\.\d+)"$', text, re.MULTILINE)
        if version is None:
            raise ValueError(f"缺少有效版本号：{skill}")
        name = f"{Path(skill_rel).name}-v{version.group(1)}-preview"
        files = {
            "README.md": root / README_FILES[edition],
            "LICENSE": root / "LICENSE",
            "install.py": root / "install.py",
            f"integrations/{Path(TEMPLATE_FILES[edition]).name}": root / TEMPLATE_FILES[edition],
        }
        # Skill 源码：内部路径统一用基础名前缀
        for source in sorted(skill.rglob("*")):
            if source.is_symlink():
                raise ValueError(f"拒绝打包符号链接：{source}")
            if source.is_file() and source.suffix in (".md", ".yaml"):
                files[f"{Path(skill_rel).name}/{source.relative_to(skill).as_posix()}"] = source
        for path in SUPPORT_FILES:
            files[path] = root / path
        # Read inputs before opening the output so missing files cannot truncate it.
        contents = {path: source.read_bytes() for path, source in files.items()}
        archive = output / f"{name}.zip"
        buffer = io.BytesIO()
        with zipfile.ZipFile(buffer, "w", compression=zipfile.ZIP_DEFLATED) as package:
            for path, content in sorted(contents.items()):
                info = zipfile.ZipInfo(f"{name}/{path}", date_time=(2026, 10, 19, 0, 0, 0))
                info.create_system = 3
                info.external_attr = 0o100644 << 16
                info.compress_type = zipfile.ZIP_DEFLATED
                package.writestr(info, content)
        data = buffer.getvalue()
        if archive.exists() and archive.read_bytes() != data:
            raise ValueError(f"已有发行包内容不同，拒绝回填：{archive.name}。请提升对应版号，或只构建本次变更的版本。")
        if not archive.exists():
            archive.write_bytes(data)
        built.append(archive)
    sums = [f"{hashlib.sha256(path.read_bytes()).hexdigest()}  {path.name}" for path in sorted(output.glob("*.zip"))]
    (output / "SHA256SUMS.txt").write_text("\n".join(sums) + "\n", encoding="utf-8")
    return built


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=ROOT / "dist")
    parser.add_argument("--edition", choices=tuple(SKILLS), help="只构建所选版本")
    args = parser.parse_args()
    for archive in build_packages(args.output, editions=[args.edition] if args.edition else None):
        print(archive)


if __name__ == "__main__":
    main()
