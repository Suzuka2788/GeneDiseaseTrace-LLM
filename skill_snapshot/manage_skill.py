"""Local, guarded skill snapshots and deployment; standard library only."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import tempfile
from uuid import uuid4
import zipfile

ROOT = Path(__file__).resolve().parent


def write_json(path, value):
    path = Path(path)
    temporary = path.with_name(path.name + '.tmp')
    temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n', encoding='utf-8', newline='\n')
    temporary.replace(path)


def package_info(path):
    path = Path(path).resolve()
    if not path.exists():
        return None
    files = {}
    for entry in sorted(path.rglob('*')):
        if entry.is_symlink() or entry.is_junction():
            raise ValueError(f'Linked package content needs manual review: {entry}')
        if entry.is_file() and '__pycache__' not in entry.parts and entry.suffix != '.pyc':
            files[entry.relative_to(path).as_posix()] = hashlib.sha256(entry.read_bytes()).hexdigest()
    text = (path / 'SKILL.md').read_text(encoding='utf-8')
    front = re.match(r'\A---\r?\n(.*?)\r?\n---(?:\r?\n|$)', text, re.S)
    if not front:
        raise ValueError(f'Missing skill frontmatter: {path}')
    name = re.search(r'^name:\s*[\'"]?([a-z0-9-]+)[\'"]?\s*$', front.group(1), re.M)
    version = re.search(r'^  version:\s*[\'"]?(\d+\.\d+\.\d+)[\'"]?\s*$', front.group(1), re.M)
    if not name or not version:
        raise ValueError('Expected a skill name and metadata.version in MAJOR.MINOR.PATCH format.')
    digest = hashlib.sha256(json.dumps(files, sort_keys=True, separators=(',', ':')).encode('utf-8')).hexdigest()
    return dict(path=str(path), name=name.group(1), version=version.group(1), sha256=digest, files=files)


def plan_install(source, installed, tracked_digest):
    if source is None:
        raise ValueError('Maintenance source is missing.')
    if installed is None:
        return 'install_missing'
    if source['name'] != installed['name']:
        raise ValueError('Source and installed skill names differ.')
    if tracked_digest is None or installed['sha256'] != tracked_digest:
        raise ValueError('Installed copy has unregistered changes; archive and reconcile before installing.')
    source_version = tuple(map(int, source['version'].split('.')))
    installed_version = tuple(map(int, installed['version'].split('.')))
    if source_version < installed_version:
        raise ValueError('Downgrade refused: source version is older than installed version.')
    if source_version == installed_version:
        if source['sha256'] != installed['sha256']:
            raise ValueError('Same version with different content refused; increment version and reconcile.')
        return 'up_to_date'
    return 'upgrade'


def snapshot(info, archive_root, origin):
    if info is None:
        return None
    archive_root = Path(archive_root).resolve()
    source = Path(info['path']).resolve()
    if archive_root.is_relative_to(source):
        raise ValueError('Archives must be outside the skill package.')
    if package_info(source) != info:
        raise ValueError('Package changed during snapshot planning; retry after reviewing changes.')
    target = archive_root / info['version'] / (info['sha256'] + '.zip')
    metadata = {k: v for k, v in info.items() if k != 'path'}
    metadata.update(origin=origin, original_path=str(source))
    target.parent.mkdir(parents=True, exist_ok=True)
    if not target.exists():
        with zipfile.ZipFile(target, 'x', compression=zipfile.ZIP_DEFLATED) as z:
            for relative in info['files']:
                z.write(source / relative, relative)
            z.writestr('_snapshot.json', json.dumps(metadata, ensure_ascii=False, indent=2))
    with zipfile.ZipFile(target) as z:
        saved = json.loads(z.read('_snapshot.json'))
        if saved['sha256'] != info['sha256'] or saved['files'] != info['files']:
            raise ValueError(f'Existing archive metadata mismatch: {target}')
        if set(z.namelist()) != set(info['files']) | {'_snapshot.json'}:
            raise ValueError(f'Archive file set mismatch: {target}')
        for name, digest in info['files'].items():
            if hashlib.sha256(z.read(name)).hexdigest() != digest:
                raise ValueError(f'Archive content mismatch: {target} / {name}')
    return str(target)


def git(*args):
    result = subprocess.run(['git', '-C', str(ROOT), *args], capture_output=True, text=True, encoding='utf-8')
    if result.returncode:
        raise ValueError(result.stderr.strip() or 'Git command failed.')
    return result.stdout.strip()


def verify_release(source):
    relative = Path(source['path']).relative_to(ROOT).as_posix()
    if git('status', '--porcelain', '--untracked-files=all', '--', relative):
        raise ValueError('Source package has uncommitted changes.')
    tag = source['name'] + '/v' + source['version']
    if git('rev-parse', f'{tag}:{relative}') != git('rev-parse', f'HEAD:{relative}'):
        raise ValueError('Version tag and current source package differ; do not move an existing tag.')


def install_package(source, installed, destination, archive_root):
    destination = Path(destination).absolute()
    archive_root = Path(archive_root).resolve()
    if destination.name != source['name'] or destination.is_symlink() or destination.is_junction():
        raise ValueError('Unexpected or linked installation target.')
    if destination.resolve() == Path(source['path']).resolve():
        raise ValueError('Maintenance source cannot also be the installation target.')
    if archive_root.is_relative_to(destination.resolve()):
        raise ValueError('Backup directory must be outside the installation.')
    if package_info(source['path']) != source or package_info(destination) != installed:
        raise ValueError('Source or installation changed after inspection; no files replaced.')
    snapshot(source, archive_root, 'maintenance_source')
    snapshot(installed, archive_root, 'previous_installation')
    archive_root.mkdir(parents=True, exist_ok=True)
    backup = archive_root / 'install-backups' / str(uuid4()) / source['name']
    assert backup.resolve().is_relative_to(archive_root)
    with tempfile.TemporaryDirectory(prefix='stage-', dir=archive_root) as stage_dir:
        assert Path(stage_dir).resolve().is_relative_to(archive_root)
        staged = Path(stage_dir) / source['name']
        shutil.copytree(source['path'], staged, ignore=shutil.ignore_patterns('__pycache__', '*.pyc'))
        if package_info(staged)['sha256'] != source['sha256']:
            raise ValueError('Staged package differs from source.')
        if package_info(source['path']) != source or package_info(destination) != installed:
            raise ValueError('Source or installation changed while staging; no files replaced.')
        destination.parent.mkdir(parents=True, exist_ok=True)
        if installed:
            backup.parent.mkdir(parents=True, exist_ok=True)
            destination.rename(backup)
        try:
            staged.rename(destination)
            if os.name == 'nt':
                # TemporaryDirectory has a private ACL on Windows. Once deployed,
                # inherit access from the intended installation parent instead.
                subprocess.run(['icacls', str(destination), '/reset', '/T'],
                               check=True, capture_output=True)
            if package_info(destination)['sha256'] != source['sha256']:
                raise ValueError('Installed verification failed.')
        except Exception:
            # A transactional rollback preserves unexpected files for inspection.
            if destination.exists():
                failed = archive_root / 'failed-installs' / str(uuid4()) / source['name']
                assert failed.resolve().is_relative_to(archive_root)
                failed.parent.mkdir(parents=True, exist_ok=True)
                destination.rename(failed)
            if installed:
                backup.rename(destination)
            raise
    return str(backup) if installed else None


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command', choices=['status', 'snapshot', 'install'])
    parser.add_argument('--apply', action='store_true', help='Execute installation; default is preview only.')
    args = parser.parse_args()
    if args.apply and args.command != 'install':
        parser.error('--apply is only valid for install')
    registry_path = ROOT / 'registry.json'
    registry = json.loads(registry_path.read_text(encoding='utf-8'))
    source_path = (ROOT / registry['source']).resolve()
    if not source_path.is_relative_to(ROOT) or source_path == ROOT:
        raise ValueError('Maintenance source must be a package inside this repository.')
    source = package_info(source_path)
    installed = package_info(registry['installed_path'])
    archive_root = (ROOT / registry['archive_root']).resolve()
    tracked = registry['installed_baseline_sha256']
    status = dict(source=source, installed=installed, canonical_source=str(source_path),
        installed_matches_registry=bool(installed and installed['sha256'] == tracked),
        copies_identical=bool(source and installed and source['sha256'] == installed['sha256']),
        semantic_review=registry['semantic_review'], git_status=git('status', '--short'))
    if args.command == 'status':
        print(json.dumps(status, ensure_ascii=False, indent=2))
        return
    if args.command == 'snapshot':
        print(json.dumps(dict(source=snapshot(source, archive_root, 'maintenance_source'),
                              installed=snapshot(installed, archive_root, 'installed_copy')),
                         ensure_ascii=False, indent=2))
        return
    action = plan_install(source, installed, tracked)
    verify_release(source)
    if not args.apply or action == 'up_to_date':
        print(json.dumps(dict(action=action, applied=False, source_version=source['version'],
            installed_version=installed['version'] if installed else None), ensure_ascii=False))
        return
    backup = install_package(source, installed, registry['installed_path'], archive_root)
    registry['installed_baseline_sha256'] = source['sha256']
    registry['installed_baseline_version'] = source['version']
    write_json(registry_path, registry)
    print(json.dumps(dict(action=action, applied=True, version=source['version'], backup=backup), ensure_ascii=False))


if __name__ == '__main__':
    try:
        main()
    except (ValueError, OSError, zipfile.BadZipFile, subprocess.CalledProcessError) as error:
        raise SystemExit(str(error)) from error
