#!/usr/bin/env python3
"""Appearance-only installer. Back up each touched target before changing it."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import tarfile
import tempfile
import time

ROOT = Path(__file__).resolve().parents[1]
HOME = Path.home()
CONFIG = Path(os.environ.get('XDG_CONFIG_HOME', HOME / '.config'))
DATA = Path(os.environ.get('XDG_DATA_HOME', HOME / '.local/share'))
STATE = Path(os.environ.get('XDG_STATE_HOME', HOME / '.local/state')) / 'vkde'
DATA_ITEMS = ['plasma/plasmoids/luisbocanegra.panel.colorizer',
              'plasma/plasmoids/org.simonqvq.redmiclock',
              'plasma/desktoptheme/We10XOS-dark',
              'plasma/look-and-feel/com.github.yeyushengfan258.We10XOS-dark',
              'color-schemes/We10XOSDark.colors', 'icons/Fluent-dark',
              'konsole/AuthorGlass.profile', 'konsole/AuthorGlass.colorscheme']
CONFIG_ITEMS = ['Kvantum/We10XOS-dark', 'Kvantum/kvantum.kvconfig',
                'kdeglobals', 'kwinrc', 'breezeblurred6rc', 'konsolerc', 'plasmarc',
                'plasma-org.kde.plasma.desktop-appletsrc']

def run(*args, **kwargs):
    kwargs.setdefault('timeout', 30)
    return subprocess.run(args, check=True, text=True, **kwargs)

def targets():
    return {'data/' + x: DATA / x for x in DATA_ITEMS} | {'config/' + x: CONFIG / x for x in CONFIG_ITEMS}

def remove(path):
    if path.is_symlink() or path.is_file():
        path.unlink()
    elif path.is_dir():
        shutil.rmtree(path)

def copy(src, dst):
    dst.parent.mkdir(parents=True, exist_ok=True)
    if src.is_dir() and not src.is_symlink():
        shutil.copytree(src, dst, symlinks=True)
    else:
        shutil.copy2(src, dst, follow_symlinks=False)

def backup():
    folder = STATE / ('backup-' + time.strftime('%Y%m%d-%H%M%S') + '-' + str(os.getpid()))
    folder.mkdir(parents=True, mode=0o700)
    existing = []
    for key, path in targets().items():
        if path.exists() or path.is_symlink():
            copy(path, folder / key)
            existing.append(key)
    (folder / 'manifest.json').write_text(json.dumps({'existing': existing}))
    return folder

def restore(folder, live=True):
    # A known target list avoids arbitrary deletion from manifest contents.
    existing = json.loads((folder / 'manifest.json').read_text())['existing']
    if not set(existing).issubset(targets()):
        raise ValueError('Invalid backup manifest')
    if live:
        run('systemctl', '--user', 'stop', 'plasma-plasmashell.service')
    try:
        for key, path in targets().items():
            remove(path)
            if key in existing:
                copy(folder / key, path)
    finally:
        if live:
            run('systemctl', '--user', 'start', 'plasma-plasmashell.service')
            run('qdbus6', 'org.kde.KWin', '/KWin', 'org.kde.KWin.reconfigure')

def write(file, group, key, value):
    run('kwriteconfig6', '--file', file, '--group', group, '--key', key, value)

def decoration():
    versions = {'kwin': '6.7.5', 'qt6-base': '6.12.0', 'kdecoration': '6.7.5',
                'kcoreaddons': '6.30.0', 'kconfig': '6.30.0', 'ki18n': '6.30.0',
                'kcolorscheme': '6.30.0', 'kguiaddons': '6.30.0', 'kiconthemes': '6.30.0'}
    if os.uname().machine != 'x86_64' or not shutil.which('pacman'):
        print('Breeze Blurred binary skipped: unsupported platform. Using Breeze.')
        return 'org.kde.breeze'
    for package, expected in versions.items():
        result = subprocess.run(['pacman', '-Q', package], text=True, capture_output=True)
        if result.returncode or result.stdout.split()[1].rsplit('-', 1)[0] != expected:
            print('Breeze Blurred binary skipped: ABI differs from the tested build. Using Breeze.')
            return 'org.kde.breeze'
    plugin = Path('/usr/lib/qt6/plugins/org.kde.kdecoration3/org.kde.breezeblurred6.so')
    with tempfile.TemporaryDirectory(prefix='vkde-decoration-') as temp:
        temp = Path(temp)
        with tarfile.open(ROOT / 'assets/breeze-blurred6.tar.gz') as archive:
            archive.extractall(temp, filter='data')
        source = temp / 'BreezeBlurred6/org.kde.breezeblurred6.so'
        digest = hashlib.sha256(source.read_bytes()).digest()
        if plugin.exists():
            if hashlib.sha256(plugin.read_bytes()).digest() != digest:
                print('Existing custom decoration differs; leaving its binary intact. Using Breeze.')
                return 'org.kde.breeze'
        else:
            # Only this new plugin file is installed system-wide; stock Breeze is untouched.
            run('sudo', 'install', '-Dm755', str(source), str(plugin), timeout=None)
    return 'org.kde.breezeblurred6'

def apply():
    write('kdeglobals', 'KDE', 'widgetStyle', 'kvantum')
    write('kdeglobals', 'General', 'ColorScheme', 'We10XOSDark')
    write('kdeglobals', 'Icons', 'Theme', 'Fluent-dark')
    write('kdeglobals', 'KDE', 'LookAndFeelPackage', 'com.github.yeyushengfan258.We10XOS-dark')
    write('Kvantum/kvantum.kvconfig', 'General', 'theme', 'We10XOS-dark')
    write('konsolerc', 'Desktop Entry', 'DefaultProfile', 'AuthorGlass.profile')
    write('kwinrc', 'Plugins', 'blurEnabled', 'true')
    library = decoration()
    if library == 'org.kde.breezeblurred6':
        (CONFIG / 'breezeblurred6rc').write_text('[Glass]\nOpacity=0.8\nBlur=true\nTintColor=#333333\n[Windeco]\nDrawBackgroundGradient=false\n[Common]\nShadowSize=ShadowMedium\nShadowStrength=180\n')
    write('kwinrc', 'org.kde.kdecoration2', 'library', library)
    write('kwinrc', 'org.kde.kdecoration2', 'theme', '')
    script = (ROOT / 'presets/layout.js').read_text()
    for name in ['top', 'bottom']:
        script = script.replace('__' + name.upper() + '__', json.dumps(json.loads((ROOT / f'presets/{name}.json').read_text())))
    pins = [name for name in ['org.kde.dolphin.desktop', 'org.kde.konsole.desktop', 'firefox.desktop']
            if (Path('/usr/share/applications') / name).exists() or (DATA / 'applications' / name).exists()]
    script = script.replace('__PINS__', json.dumps(['applications:' + p for p in pins]))
    result = run('qdbus6', 'org.kde.plasmashell', '/PlasmaShell', 'org.kde.PlasmaShell.evaluateScript', script, capture_output=True)
    if 'Error' in result.stdout or 'Error' in result.stderr:
        raise RuntimeError('Plasma layout script failed: ' + result.stdout + result.stderr)
    run('qdbus6', 'org.kde.KWin', '/KWin', 'org.kde.KWin.reconfigure')
    run('qdbus6', 'org.kde.KWin', '/Effects', 'org.kde.kwin.Effects.loadEffect', 'blur')
    info = run('qdbus6', 'org.kde.KWin', '/KWin', 'org.kde.KWin.supportInformation', capture_output=True).stdout
    if library == 'org.kde.breezeblurred6' and 'Plugin: org.kde.breezeblurred6' not in info:
        print('Custom decoration did not load; reverting decoration to Breeze.')
        write('kwinrc', 'org.kde.kdecoration2', 'library', 'org.kde.breeze')
        run('qdbus6', 'org.kde.KWin', '/KWin', 'org.kde.KWin.reconfigure')
    run('systemctl', '--user', 'restart', 'plasma-plasmashell.service')

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--dry-run', action='store_true')
    parser.add_argument('--assets-only', action='store_true')
    parser.add_argument('--restore', type=Path)
    args = parser.parse_args()
    if args.restore:
        restore(args.restore.resolve())
        print('Restored previous appearance and layout.')
        return
    for line in (ROOT / 'assets/SHA256SUMS').read_text().splitlines():
        digest, relative = line.split('  ', 1)
        if hashlib.sha256((ROOT / relative).read_bytes()).hexdigest() != digest:
            raise ValueError('Asset checksum mismatch: ' + relative)
    if args.dry_run:
        print('Would install 9 appearance assets; replace panels with top bar + centered native Dock.')
        print('Backup directory:', STATE)
        print('Runtime dependencies: kvantum, python-dbus, python-gobject, qt6-tools; existing Plasma 6 required.')
        print('Wallpaper, display settings, cursor, login, input method and lock settings are preserved.')
        return
    if os.geteuid() == 0:
        raise RuntimeError('Run as your desktop user, not root')
    if not args.assets_only:
        for command in ['kwriteconfig6', 'qdbus6', 'systemctl']:
            if not shutil.which(command):
                raise RuntimeError('Missing command: ' + command)
        run('qdbus6', 'org.kde.plasmashell', '/PlasmaShell', 'org.kde.PlasmaShell.dumpCurrentLayoutJS', capture_output=True)
        run('systemctl', '--user', 'is-active', 'plasma-plasmashell.service', capture_output=True)
    folder = backup()
    print('Backup:', folder, flush=True)
    try:
        with tempfile.TemporaryDirectory(prefix='vkde-') as temp:
            temp = Path(temp)
            with tarfile.open(ROOT / 'assets/desktop.tar.gz') as archive:
                archive.extractall(temp, filter='data')
            for key, destination in targets().items():
                source = temp / key
                if source.exists():
                    remove(destination)
                    copy(source, destination)
        if not args.assets_only:
            apply()
        print('Installed. Existing Qt applications may need to be reopened to pick up the theme.')
        print('Restore: ./install.sh --restore', folder)
    except Exception:
        restore(folder, live=not args.assets_only)
        raise

if __name__ == '__main__':
    main()
