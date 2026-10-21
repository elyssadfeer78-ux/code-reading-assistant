import importlib.util
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch


spec = importlib.util.spec_from_file_location("installer", Path(__file__).resolve().parents[1] / "install.py")
installer = importlib.util.module_from_spec(spec)
spec.loader.exec_module(installer)


class InstallTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)

    def test_workbuddy_user_install_is_complete_and_idempotent(self):
        planned, skill, rule = installer.plan_install(self.root, "workbuddy", True)
        self.assertFalse(rule.exists())
        installer.apply_plan(planned)
        self.assertTrue((skill / "references/assessment.md").is_file())
        self.assertTrue((skill / "references/code-reading-flow.md").is_file())
        self.assertIn("alwaysApply: true", rule.read_text(encoding="utf-8"))
        self.assertIn("默认启用代码阅读陪练", rule.read_text(encoding="utf-8"))
        self.assertIn((skill / "SKILL.md").as_posix(), rule.read_text(encoding="utf-8"))
        repeated, _, _ = installer.plan_install(self.root, "workbuddy", True)
        self.assertEqual(repeated, {})

    def test_codex_preserves_existing_bytes_and_backup(self):
        agents = self.root / "AGENTS.md"
        original = "# 现有规则\r\n只改指定目录\r\n".encode("utf-8")
        agents.write_bytes(original)
        planned, _, rule = installer.plan_install(self.root, "codex", False)
        backups = installer.apply_plan(planned)
        self.assertEqual(rule, agents)
        self.assertTrue(agents.read_bytes().startswith(original))
        self.assertEqual(len(backups), 1)
        self.assertEqual(backups[0].read_bytes(), original)

    def test_codex_honors_active_override_and_custom_home(self):
        config = self.root / "custom-profile"
        config.mkdir()
        override = config / "AGENTS.override.md"
        override.write_text("# Profile\n", encoding="utf-8")
        planned, skill, rule = installer.plan_install(self.root, "codex", True, config)
        installer.apply_plan(planned)
        self.assertEqual(rule, override)
        self.assertEqual(skill, self.root / ".agents/skills/code-reading-assistant")
        self.assertFalse((config / "AGENTS.md").exists())

    def test_modified_skill_is_not_overwritten(self):
        planned, skill, _ = installer.plan_install(self.root, "workbuddy", False)
        installer.apply_plan(planned)
        target = skill / "SKILL.md"
        target.write_text("local customization", encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "内容不同"):
            installer.plan_install(self.root, "workbuddy", False)
        self.assertEqual(target.read_text(), "local customization")

    def test_malformed_markers_abort_before_any_writes(self):
        agents = self.root / "AGENTS.md"
        agents.write_text("<!-- code-reading-assistant:start -->", encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "不完整"):
            installer.plan_install(self.root, "codex", False)
        self.assertFalse((self.root / ".agents").exists())

    def test_symlink_destination_is_rejected(self):
        outside = self.root / "outside"
        outside.mkdir()
        (self.root / ".codebuddy").symlink_to(outside, target_is_directory=True)
        with self.assertRaisesRegex(ValueError, "符号链接"):
            installer.plan_install(self.root, "workbuddy", True)
        self.assertEqual(list(outside.iterdir()), [])

    def test_partial_write_failure_rolls_back_completed_writes(self):
        original_path = self.root / "existing.md"
        original_path.write_text("original", encoding="utf-8")
        new_path = self.root / "new.md"
        real_replace = Path.replace

        def fail_second(path, target):
            if target == new_path:
                raise OSError("simulated write failure")
            return real_replace(path, target)

        with patch.object(Path, "replace", fail_second):
            with self.assertRaisesRegex(OSError, "simulated"):
                installer.apply_plan({original_path: b"changed", new_path: b"new"})
        self.assertEqual(original_path.read_text(), "original")
        self.assertFalse(new_path.exists())

    def test_unknown_edition_or_missing_rule_fails_without_writes(self):
        target = self.root / "target"
        with self.assertRaisesRegex(ValueError, "不含所选版本"):
            installer.plan_install(target, "codex", False, edition="zhihuiya")
        package = self.root / "package"
        skill = package / "code-reading-assistant"
        skill.mkdir(parents=True)
        (skill / "SKILL.md").write_text("placeholder", encoding="utf-8")
        with patch.object(installer, "PACKAGE", package):
            self.assertEqual(installer.choose_edition(), "code")
            with self.assertRaisesRegex(ValueError, "缺少默认规则"):
                installer.plan_install(target, "codex", False)
        self.assertFalse(target.exists())


if __name__ == "__main__":
    unittest.main()
