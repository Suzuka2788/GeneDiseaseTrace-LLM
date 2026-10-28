import importlib.util
import json
from pathlib import Path
import tempfile
import subprocess
import unittest
from unittest.mock import patch
import zipfile

spec = importlib.util.spec_from_file_location('skill_management', Path(__file__).parents[1] / 'manage_skill.py')
management = importlib.util.module_from_spec(spec)
spec.loader.exec_module(management)


class ManagementTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)

    def tearDown(self):
        self.temporary.cleanup()

    def package(self, parent, version, body='rules'):
        path = self.root / parent / 'example-skill'
        path.mkdir(parents=True)
        (path / 'SKILL.md').write_text(
            f'---\nname: example-skill\ndescription: Example\nmetadata:\n  version: "{version}"\n---\n{body}\n', encoding='utf-8')
        return management.package_info(path)

    def test_rejects_downgrade_and_same_version_changes(self):
        installed = self.package('installed', '1.1.0')
        old = self.package('old', '1.0.0')
        changed = self.package('changed', '1.1.0', 'different')
        for source in [old, changed]:
            with self.assertRaises(ValueError):
                management.plan_install(source, installed, installed['sha256'])

    def test_rejects_unregistered_installed_edits(self):
        installed = self.package('installed', '1.1.0')
        source = self.package('source', '1.2.0')
        with self.assertRaisesRegex(ValueError, 'unregistered'):
            management.plan_install(source, installed, 'old-digest')

    def test_identical_package_is_noop(self):
        installed = self.package('installed', '1.1.0')
        source = self.package('source', '1.1.0')
        self.assertEqual(management.plan_install(source, installed, installed['sha256']), 'up_to_date')

    def test_snapshots_detect_tampering(self):
        source = self.package('source', '1.1.0')
        archive = management.snapshot(source, self.root / 'archives', 'test')
        with zipfile.ZipFile(archive, 'w') as z:
            z.writestr('_snapshot.json', json.dumps(dict(source, files={})))
        with self.assertRaises(ValueError):
            management.snapshot(source, self.root / 'archives', 'test')

    def test_upgrade_removes_obsolete_files_and_preserves_old_install(self):
        installed = self.package('installed', '1.1.0')
        (Path(installed['path']) / 'obsolete.md').write_text('old-only', encoding='utf-8')
        installed = management.package_info(installed['path'])
        source = self.package('source', '1.2.0')
        self.assertEqual(management.plan_install(source, installed, installed['sha256']), 'upgrade')
        backup = management.install_package(source, installed, installed['path'], self.root / 'archives')
        self.assertEqual(management.package_info(installed['path'])['sha256'], source['sha256'])
        self.assertFalse((Path(installed['path']) / 'obsolete.md').exists())
        self.assertEqual(management.package_info(backup)['sha256'], installed['sha256'])

    def test_rejects_changed_source_after_planning(self):
        installed = self.package('installed', '1.1.0')
        source = self.package('source', '1.2.0')
        (Path(source['path']) / 'SKILL.md').write_text('changed', encoding='utf-8')
        with self.assertRaises(ValueError):
            management.install_package(source, installed, installed['path'], self.root / 'archives')
        self.assertEqual(management.package_info(installed['path'])['sha256'], installed['sha256'])

    def test_failed_replacement_restores_previous_install(self):
        installed = self.package('installed', '1.1.0')
        source = self.package('source', '1.2.0')
        destination = Path(installed['path'])
        real_rename = Path.rename

        def fail_staged_replacement(path, target):
            if path.parent.name.startswith('stage-') and Path(target) == destination:
                raise OSError('Simulated replacement failure')
            return real_rename(path, target)

        with patch.object(Path, 'rename', fail_staged_replacement):
            with self.assertRaisesRegex(OSError, 'replacement failure'):
                management.install_package(source, installed, destination, self.root / 'archives')
        self.assertEqual(management.package_info(destination)['sha256'], installed['sha256'])

    @unittest.skipUnless(management.os.name == 'nt', 'Windows ACL transaction')
    def test_permission_inheritance_failure_restores_previous_install(self):
        installed = self.package('installed', '1.1.0')
        source = self.package('source', '1.2.0')
        with patch.object(management.subprocess, 'run',
                          side_effect=subprocess.CalledProcessError(1, ['icacls'])):
            with self.assertRaises(subprocess.CalledProcessError):
                management.install_package(source, installed, installed['path'], self.root / 'archives')
        self.assertEqual(management.package_info(installed['path'])['sha256'], installed['sha256'])


if __name__ == '__main__':
    unittest.main()
