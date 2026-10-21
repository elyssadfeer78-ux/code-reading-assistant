import hashlib
import importlib.util
from pathlib import Path
import re
import subprocess
import sys
import tempfile
import unittest
import zipfile


ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("builder", ROOT / "scripts/build_packages.py")
builder = importlib.util.module_from_spec(spec)
spec.loader.exec_module(builder)


class PackageTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory()
        cls.addClassCleanup(cls.temp.cleanup)
        cls.root = Path(cls.temp.name)
        cls.archives = builder.build_packages(cls.root / "dist")
        cls.packages = {}
        for edition, archive in zip(builder.SKILLS, cls.archives):
            with zipfile.ZipFile(archive) as package:
                package.extractall(cls.root / "extracted")
            cls.packages[edition] = cls.root / "extracted" / archive.stem

    def test_archive_is_standalone_and_contains_only_this_edition(self):
        for edition, package in self.packages.items():
            with self.subTest(edition=edition):
                own = Path(builder.SKILLS[edition]).name
                self.assertTrue((package / own / "SKILL.md").is_file())
                self.assertEqual((package / "README.md").read_bytes(), (ROOT / builder.README_FILES[edition]).read_bytes())
                skill_root = ROOT / builder.SKILLS[edition]
                for source in skill_root.rglob("*"):
                    if source.is_file():
                        self.assertEqual((package / own / source.relative_to(skill_root)).read_bytes(), source.read_bytes())
                self.assertFalse(any(path.suffix in (".docx", ".pdf", ".pyc") for path in package.rglob("*")))
        code = self.packages["code"]
        self.assertTrue((code / "docs/用法与示例.md").is_file())
        self.assertTrue((code / "docs/优化记录-v0.4.0.md").is_file())
        self.assertTrue((code / "cases/01-代码模块陪读/输入任务.md").is_file())
        for directory in (code / "code-reading-assistant", code / "integrations"):
            for path in directory.rglob("*"):
                if path.is_file():
                    # 代码版不应混入科研版专属产物（Skill 标识、科研状态、刊会/参赛等）
                    self.assertNotRegex(path.read_text(encoding="utf-8"), r"zhihuiya|mcp_pending|刊会|参赛")

    def test_extracted_default_install_dry_run_repeat_and_wrong_edition(self):
        for edition, package in self.packages.items():
            for platform in ("codex", "workbuddy"):
                with self.subTest(edition=edition, platform=platform):
                    target = self.root / "projects" / edition / platform
                    command = [sys.executable, str(package / "install.py"), "--platform", platform, "--project", str(target)]
                    preview = subprocess.run(command + ["--dry-run"], capture_output=True, text=True, encoding="utf-8")
                    self.assertEqual(preview.returncode, 0, preview.stderr)
                    self.assertFalse(target.exists())
                    first = subprocess.run(command, capture_output=True, text=True, encoding="utf-8")
                    self.assertEqual(first.returncode, 0, first.stderr)
                    self.assertIn(f"版本: {edition}", first.stdout)
                    skill_parent = ".agents" if platform == "codex" else ".codebuddy"
                    skill_basename = Path(builder.SKILLS[edition]).name
                    self.assertTrue((target / skill_parent / "skills" / skill_basename / "SKILL.md").exists())
                    before = {p: p.read_bytes() for p in target.rglob("*") if p.is_file()}
                    repeated = subprocess.run(command, capture_output=True, text=True, encoding="utf-8")
                    self.assertEqual(repeated.returncode, 0, repeated.stderr)
                    self.assertNotIn("待写入", repeated.stdout)
                    wrong = subprocess.run(command + ["--edition", "zhihuiya"], capture_output=True, text=True, encoding="utf-8")
                    self.assertNotEqual(wrong.returncode, 0)
                    self.assertTrue(("不含所选版本" in wrong.stderr) or ("invalid choice" in wrong.stderr), wrong.stderr)
                    self.assertEqual(before, {p: p.read_bytes() for p in target.rglob("*") if p.is_file()})

    def test_packaged_markdown_links_resolve_inside_package(self):
        for package in self.packages.values():
            for document in package.rglob("*.md"):
                for link in re.findall(r"\[[^\]]*\]\(([^)]+)\)", document.read_text(encoding="utf-8")):
                    if "://" in link or link.startswith("#"):
                        continue
                    target = (document.parent / link.split("#")[0]).resolve()
                    with self.subTest(document=document.name, link=link):
                        target.relative_to(package.resolve())
                        self.assertTrue(target.exists(), str(target))

    def test_rebuild_is_identical_and_preserves_existing_historical_archives(self):
        output = self.root / "dist"
        previous = {p.name: p.read_bytes() for p in self.archives}
        history = output / "code-reading-assistant-v0.1.0-preview.zip"
        history.write_bytes(b"historical fixture")
        builder.build_packages(output)
        self.assertEqual(history.read_bytes(), b"historical fixture")
        self.assertEqual(previous, {p.name: p.read_bytes() for p in self.archives})
        sums = (output / "SHA256SUMS.txt").read_text(encoding="utf-8")
        for path in (*self.archives, history):
            self.assertIn(f"{hashlib.sha256(path.read_bytes()).hexdigest()}  {path.name}", sums)

    def test_existing_release_protection(self):
        output = self.root / "single-release"
        archives = builder.build_packages(output, editions=["code"])
        self.assertEqual(len(archives), 1)
        self.assertIn("code-reading-assistant", archives[0].name)
        archives[0].write_bytes(b"existing published content")
        with self.assertRaisesRegex(ValueError, "拒绝回填"):
            builder.build_packages(output, editions=["code"])
        self.assertEqual(archives[0].read_bytes(), b"existing published content")


if __name__ == "__main__":
    unittest.main()
