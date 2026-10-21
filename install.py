#!/usr/bin/env python3
"""Install the code-reading-assistant skill and its default routing rule.

本包只包含一个版本：代码阅读助手（code-reading-assistant，零外部依赖）。
安装器与 skill 源码发布在同一个仓库里：仓库布局与解压后的包内布局一致
（skill 源码位于包根的 code-reading-assistant/ 目录）。
"""

import argparse
import os
from pathlib import Path
import shutil
import tempfile


PACKAGE = Path(__file__).resolve().parent
# 版本 -> (仓库内相对路径, Skill 基础名, 仓库内规则模板相对路径)
EDITIONS = {
    "code": ("code-reading-assistant", "code-reading-assistant", "integrations/code-reading-always-on.md"),
}


def _resolve_source(edition):
    """Return (skill_dir, template_path) for the given edition."""
    rel, basename, tpl = EDITIONS[edition]
    skill = PACKAGE / rel
    if not (skill / "SKILL.md").is_file():
        skill = PACKAGE / basename
    template = PACKAGE / tpl
    if not template.is_file():
        template = PACKAGE / "integrations" / Path(tpl).name
    return skill, template


def choose_edition(requested=None):
    available = [key for key in EDITIONS if _resolve_source(key)[0].is_dir()]
    if requested is not None:
        if requested not in available:
            raise ValueError(f"本包不含所选版本 {requested}，请下载对应版本包。")
        return requested
    if not available:
        raise ValueError("本包缺少 Skill 源码。")
    return available[0]


def check_regular_path(path):
    for candidate in (path, *path.parents):
        if candidate.is_symlink():
            raise ValueError(f"拒绝通过符号链接写入：{candidate}")
    if path.exists() and not path.is_file():
        raise ValueError(f"目标不是普通文件：{path}")


def plan_install(root, platform, user_scope, codex_home=None, edition="code"):
    """Return only new/changed file bytes. All validation precedes writes."""
    edition = choose_edition(edition)
    skill_rel, skill_name, _ = EDITIONS[edition]
    source, template = _resolve_source(edition)
    if source.is_symlink() or template.is_symlink():
        raise ValueError("安装源码或规则模板不能是符号链接。")
    if not template.is_file():
        raise ValueError(f"本包缺少默认规则：{template}")
    start = f"<!-- {skill_name}:start -->"
    end = f"<!-- {skill_name}:end -->"
    root = Path(root).absolute()
    if platform == "workbuddy":
        skill_dir = root / ".codebuddy" / "skills" / skill_name
        rule_path = root / ".codebuddy" / "rules" / f"{skill_name}.md"
    elif platform == "codex":
        skill_dir = root / ".agents" / "skills" / skill_name
        rule_dir = Path(codex_home).absolute() if user_scope and codex_home else (
            root / ".codex" if user_scope else root
        )
        override = rule_dir / "AGENTS.override.md"
        check_regular_path(override)
        rule_path = override if override.exists() and override.read_bytes().strip() else rule_dir / "AGENTS.md"
    else:
        raise ValueError(f"不支持的平台：{platform}")

    check_regular_path(rule_path)
    old = rule_path.read_bytes() if rule_path.exists() else b""
    # Validate encoding without normalizing or rewriting unrelated original bytes.
    original = old.decode("utf-8")

    planned = {}
    for src in sorted(source.rglob("*")):
        if src.is_symlink():
            raise ValueError(f"安装包含符号链接：{src}")
        if not src.is_file():
            continue
        dest = skill_dir / src.relative_to(source)
        check_regular_path(dest)
        data = src.read_bytes()
        if dest.exists() and dest.read_bytes() != data:
            raise ValueError(f"同名 Skill 文件内容不同，请先人工备份和处理：{dest}")
        if not dest.exists():
            planned[dest] = data

    rule = template.read_text(encoding="utf-8")
    rule = rule.replace("__SKILL_PATH__", (skill_dir / "SKILL.md").as_posix())
    if start in original or end in original:
        if original.count(start) != 1 or original.count(end) != 1:
            raise ValueError(f"学习规则标记重复或不完整，请人工检查：{rule_path}")
        if rule.strip() not in original:
            raise ValueError(f"已有不同的学习规则，请人工核对：{rule_path}")
        updated = old
    elif platform == "workbuddy":
        if old:
            raise ValueError(f"规则文件已被其他内容占用：{rule_path}")
        description = "默认启用代码阅读陪练"
        updated = (f"---\ndescription: {description}\nalwaysApply: true\n---\n\n" + rule).encode("utf-8")
    else:
        separator = b"" if not old else (b"\n" if old.endswith(b"\n") else b"\n\n")
        updated = old + separator + rule.encode("utf-8")
    if updated != old:
        planned[rule_path] = updated
    return planned, skill_dir, rule_path


def apply_plan(planned):
    backups = []
    written = []
    try:
        for path, data in planned.items():
            path.parent.mkdir(parents=True, exist_ok=True)
            previous = path.read_bytes() if path.exists() else None
            if previous is not None:
                fd, name = tempfile.mkstemp(prefix=path.name + ".backup-", dir=path.parent)
                os.close(fd)
                backup = Path(name)
                shutil.copy2(path, backup)
                backups.append(backup)
            fd, name = tempfile.mkstemp(prefix=".learning-install-", dir=path.parent)
            temporary = Path(name)
            try:
                with os.fdopen(fd, "wb") as stream:
                    stream.write(data)
                if path.exists():
                    shutil.copymode(path, temporary)
                temporary.replace(path)
                written.append((path, previous))
            finally:
                temporary.unlink(missing_ok=True)
    except OSError:
        for path, previous in reversed(written):
            if previous is None:
                path.unlink(missing_ok=True)
            else:
                path.write_bytes(previous)
        raise
    return backups


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--edition", choices=tuple(EDITIONS), help="本包只有 code 代码阅读版。")
    parser.add_argument("--platform", choices=("workbuddy", "codex"), default="workbuddy")
    scope = parser.add_mutually_exclusive_group(required=True)
    scope.add_argument("--user", action="store_true", help="用户级安装，默认应用于该用户的代码项目")
    scope.add_argument("--project", type=Path, help="仅安装到指定项目")
    parser.add_argument("--dry-run", action="store_true", help="仅列出拟写入路径")
    args = parser.parse_args()
    root = Path.home() if args.user else args.project
    try:
        edition = choose_edition(args.edition)
        planned, skill_dir, rule_path = plan_install(
            root, args.platform, args.user, os.environ.get("CODEX_HOME"), edition
        )
        print(f"版本: {edition}\nSkill: {skill_dir}\n默认规则: {rule_path}")
        for path in planned:
            print(f"{'将写入' if args.dry_run else '待写入'}: {path}")
        if args.dry_run:
            print("预览结束，未写入任何文件。")
            return
        for backup in apply_plan(planned):
            print(f"原文件备份: {backup}")
        print("安装文件已就绪。请新建会话验证默认加载与学习关卡；这不是不可绕开的执行锁。")
    except (OSError, ValueError) as error:
        parser.exit(1, f"安装未完成：{error}\n")


if __name__ == "__main__":
    main()
