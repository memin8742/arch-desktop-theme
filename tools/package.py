#!/usr/bin/env python3
"""Validate the approved bundle and build reproducible release ZIPs (stdlib only)."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import struct
import sys
import zipfile

ROOT = Path(__file__).resolve().parents[1]
BUNDLE = ROOT / 'paket'
CONFIG = '04-ayarlar-ve-ozellikler.json'
INSTRUCTIONS = '00-CODEXE-VERILECEK-ISTEK.txt'
EXPECTED = {
    INSTRUCTIONS, CONFIG, '01-duvar-kagidi.png', '02-onayli-masaustu.png',
    '03-terminal-detayi.png', '05-acilis-ekrani.png', '06-giris-kilit-ekrani.png',
    '07-bolme-cizgileri-referansi.png', '08-bolmeli-terminal-ornek.png',
    '09-dosya-log-renk-ornekleri.png', '10-batarya-modu.png',
    '11-thunar-dosya-yoneticisi.png',
}
INSTALLER_FILES = {
    'kur.sh', 'KOLAY-KURULUM.txt', 'README.md', 'KURULUM.md', 'AGENTS.md',
    'CODEXE-VERILECEK-ISTEK.txt', 'CHANGELOG.md', 'VERSION', 'tools/package.py',
    'installer/install.py', 'installer/assets.py', 'installer/terminal.py',
    'installer/helper.py', 'installer/theme.zsh', 'installer/test_installer.py',
    'installer/linux_smoke.py', 'installer/desktop.py', 'installer/system.py',
    'installer/root_terminal.py', 'installer/icons.py',
    'installer/runtime/arch-network.py', 'installer/runtime/arch-record.py',
    'installer/runtime/arch-terminal-mark.svg', 'installer/runtime/system-summary.py',
    'installer/runtime/terminal.css', 'installer/runtime/theme.css',
    'installer/boot/arch-blue.plymouth', 'installer/boot/arch-blue.script',
    'installer/boot/arch-greeter.css', 'installer/boot/refresh.sh',
}


def require(condition, message):
    if not condition:
        raise ValueError(message)


def read_json(path):
    return json.loads(path.read_text(encoding='utf-8-sig'))


def sha256(path):
    digest = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            digest.update(block)
    return digest.hexdigest()


def version():
    result = (ROOT / 'VERSION').read_text(encoding='utf-8').strip()
    require(re.fullmatch(r'\d+\.\d+(?:\.\d+)?', result), 'VERSION geçersiz.')
    return result


def inputs():
    require(BUNDLE.is_dir(), 'paket/ bulunamadı.')
    require({p.name for p in BUNDLE.iterdir()} == EXPECTED, 'Paket tam olarak beklenen 12 dosyayı içermeli.')
    require(all((BUNDLE / name).is_file() and not (BUNDLE / name).is_symlink() for name in EXPECTED), 'Paket dosyaları normal dosya olmalı.')
    require(all((ROOT / name).is_file() and not (ROOT / name).is_symlink() for name in INSTALLER_FILES), 'Kurulum aracı dosyası eksik.')
    config = read_json(BUNDLE / CONFIG)
    text = (BUNDLE / INSTRUCTIONS).read_text(encoding='utf-8-sig')
    require('\ufffd' not in text + json.dumps(config, ensure_ascii=False), 'Bozuk UTF-8 karakteri var.')
    require(len(config['kisayollar']) == 27, '27 kısayol korunmalı.')
    require(len({row['tus'] for row in config['kisayollar']}) == 27, 'Yinelenen kısayol var.')
    for name in config['guncel_gorseller'].values():
        require(name in EXPECTED and name.endswith('.png'), 'Geçersiz görsel referansı: ' + name)
    for name in re.findall(r'\b\d{2}-[a-z0-9-]+\.(?:txt|png|json|webp)\b', text):
        require(name in EXPECTED, 'Eksik talimat referansı: ' + name)
    for path in BUNDLE.glob('*.png'):
        with path.open('rb') as stream:
            header = stream.read(24)
        require(header[:8] == b'\x89PNG\r\n\x1a\n' and header[12:16] == b'IHDR', 'Geçersiz PNG: ' + path.name)
        width, height = struct.unpack('>II', header[16:24])
        require(width > 0 and height > 0, 'Geçersiz görsel boyutu: ' + path.name)
    return config, text


def manifest(config):
    return {
        'release_version': version(),
        'source_definition_version': config['paket_surumu'],
        'bundle_directory': 'paket',
        'files': {name: {'bytes': (BUNDLE / name).stat().st_size,
                         'sha256': sha256(BUNDLE / name)} for name in sorted(EXPECTED)},
        'installer_files': {name: {'bytes': (ROOT / name).stat().st_size,
                                  'sha256': sha256(ROOT / name)} for name in sorted(INSTALLER_FILES)},
    }


def sync():
    config, text = inputs()
    current = version()
    config['yayin_surumu'] = current
    config['gorsel_sha256'] = {path.name: sha256(path) for path in sorted(BUNDLE.glob('*.png'))}
    text = re.sub(r'(KURULUM TARİFİ v|Bu klasördeki v)\d+\.?(?:\d+\.?)*',
                  lambda match: match.group(1) + current, text)
    (BUNDLE / CONFIG).write_text(json.dumps(config, ensure_ascii=False, indent=2) + '\n', encoding='utf-8-sig', newline='\n')
    (BUNDLE / INSTRUCTIONS).write_text(text, encoding='utf-8-sig', newline='\n')
    (ROOT / 'manifest.json').write_text(json.dumps(manifest(config), ensure_ascii=False, indent=2) + '\n', encoding='utf-8', newline='\n')


def check():
    config, text = inputs()
    require(config['yayin_surumu'] == version(), 'JSON yayın sürümü VERSION ile uyuşmuyor; sync çalıştırın.')
    require('v' + version() in text, 'Talimat sürümünü güncelleyin.')
    actual_images = {path.name: sha256(path) for path in sorted(BUNDLE.glob('*.png'))}
    require(config['gorsel_sha256'] == actual_images, 'Görsel özetleri uyuşmuyor; değişikliği inceleyin ve sync çalıştırın.')
    require(read_json(ROOT / 'manifest.json') == manifest(config), 'Manifest uyuşmuyor; değişikliği inceleyin ve sync çalıştırın.')
    for appearance in [config['terminal']['zemin_saydamligi'], config['thunar']['dis_gorunum']['zemin_saydamligi']]:
        require(appearance['opaklik'] == 0.8 and appearance['metin_opakligi'] == 1.0,
                'Onaylı %80 zemin/tam opak metin kuralı değişti.')
    require(config['terminal']['bolmeler']['renk_ve_malzeme']['uc_ucgenleri'] is False, 'Üçgensiz bölücü kuralı değişti.')
    require(config['terminal']['istem']['git_bilgisi'] is False, 'Git istem modülü eklenmemeli.')
    require(config['terminal']['basarisiz_komut']['etkin'] is False, 'Hata rozeti eklenmemeli.')
    print('Paket doğrulandı: v' + version() + ', 12 tasarım dosyası + Xfce kurulum aracı, 27 kısayol.')
    return config


def build():
    check()
    output = ROOT / 'dist'
    output.mkdir(exist_ok=True)
    destination = output / ('arch-desktop-theme-v' + version() + '.zip')
    sources = {name: ROOT / name for name in INSTALLER_FILES}
    sources['manifest.json'] = ROOT / 'manifest.json'
    sources.update({'paket/' + name: BUNDLE / name for name in EXPECTED})
    with zipfile.ZipFile(destination, 'w', zipfile.ZIP_DEFLATED) as archive:
        for name in sorted(sources):
            info = zipfile.ZipInfo(name, date_time=(1980, 1, 1, 0, 0, 0))
            info.create_system = 3
            info.external_attr = (0o100755 if name == 'kur.sh' else 0o100644) << 16
            info.compress_type = zipfile.ZIP_DEFLATED
            archive.writestr(info, sources[name].read_bytes())
    with zipfile.ZipFile(destination) as archive:
        require(archive.testzip() is None and set(archive.namelist()) == set(sources), 'ZIP bütünlük hatası.')
        require(all(archive.read(name) == path.read_bytes() for name, path in sources.items()), 'ZIP kaynakla uyuşmuyor.')
    checksum = output / (destination.name + '.sha256')
    checksum.write_text(sha256(destination) + '  ' + destination.name + '\n', encoding='utf-8', newline='\n')
    print('Üretildi: ' + str(destination))
    print('SHA256: ' + sha256(destination))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command', choices=['check', 'sync', 'build'])
    args = parser.parse_args()
    if args.command == 'sync':
        sync()
        check()
    elif args.command == 'check':
        check()
    else:
        build()


if __name__ == '__main__':
    try:
        main()
    except (ValueError, KeyError, OSError, json.JSONDecodeError) as error:
        print('Hata: ' + str(error), file=sys.stderr)
        sys.exit(1)
