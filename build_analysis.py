#!/usr/bin/env python3
"""Build storage analysis JSON and generate report."""
import json, os

home = os.path.expanduser('~')
local = os.path.join(home, 'AppData', 'Local')
roaming = os.path.join(home, 'AppData', 'Roaming')

analysis = {
    'system': {
        'os': 'Windows',
        'build': 'Windows 11 Pro 10.0.26100',
        'user': os.environ.get('USERNAME', 'Administrator'),
        'home': home,
        'disks': [
            {'name': 'C:', 'total': '249 GB', 'used': '157 GB', 'free': '92 GB'},
            {'name': 'D:', 'total': '69 GB', 'used': '8 GB', 'free': '61 GB'},
            {'name': 'E:', 'total': '156 GB', 'used': '25 GB', 'free': '130 GB'},
        ],
        'primary_disk': 'C:'
    },
    'top5': [
        {'name': 'pagefile.sys', 'size': '约 31 GB', 'type': '系统虚拟内存'},
        {'name': 'AppData（合计）', 'size': '约 105 GB', 'type': '应用数据（缓存+配置+数据）'},
        {'name': 'hiberfil.sys', 'size': '约 6 GB', 'type': '系统休眠文件'},
        {'name': 'E: Program Files', 'size': '约 14.4 GB', 'type': '应用本体'},
        {'name': 'E: Steam', 'size': '约 5.5 GB', 'type': '游戏平台'},
    ],
    'green': [
        {
            'name': 'Windows 临时文件',
            'path': os.path.join(local, 'Temp'),
            'size': '约 5.9 GB',
            'description': '系统和应用的临时文件，清理不影响任何功能。可通过磁盘清理或设置中"临时文件"项安全删除。',
            'trash_paths': [os.path.join(local, 'Temp')],
        },
        {
            'name': 'pip 下载缓存',
            'path': os.path.join(local, 'pip'),
            'size': '约 1.5 GB',
            'description': 'Python pip 的下载缓存。清理后 pip install 会重新下载，不影响已安装的包。',
            'trash_paths': [os.path.join(local, 'pip', 'cache')],
        },
        {
            'name': 'npm 缓存',
            'path': os.path.join(local, 'npm-cache'),
            'size': '约 0.7 GB',
            'description': 'Node.js npm 的包缓存。清理后 npm install 重新下载即可。建议用 npm cache clean --force。',
            'trash_paths': [os.path.join(local, 'npm-cache')],
        },
        {
            'name': '用户缓存 (.cache)',
            'path': os.path.join(home, '.cache'),
            'size': '约 1.0 GB',
            'description': '各类 CLI 工具的用户缓存数据，全部可再生。',
            'trash_paths': [os.path.join(home, '.cache')],
        },
        {
            'name': 'Chromium 浏览器快照',
            'path': os.path.join(home, '.chromium-browser-snapshots'),
            'size': '约 0.7 GB',
            'description': 'Playwright/Puppeteer 下载的 Chromium 浏览器。删除后运行 npx playwright install 可重新下载。',
            'trash_paths': [os.path.join(home, '.chromium-browser-snapshots')],
        },
        {
            'name': 'Node 缓存目录',
            'path': os.path.join(home, 'node_cache'),
            'size': '约 1.9 GB',
            'description': 'Node.js 相关工具的缓存数据，可再生。',
            'trash_paths': [os.path.join(home, 'node_cache')],
        },
        {
            'name': 'E盘回收站',
            'path': 'E:/$RECYCLE.BIN',
            'size': '约 0.4 GB',
            'description': 'E 盘回收站内容。右键桌面回收站图标，选择清空回收站即可。',
            'trash_paths': ['E:/$RECYCLE.BIN'],
        },
        {
            'name': 'D盘 noveos 旧备份',
            'path': 'D:/noveos.backup.20260601',
            'size': '约 2.6 GB',
            'description': 'D:noveos 项目的旧备份目录。确认不再需要后可安全删除。',
            'trash_paths': ['D:/noveos.backup.20260601', 'D:/noveos - ����'],
        },
    ],
    'yellow': [
        {
            'name': '豆包 (Doubao) 应用数据',
            'path': os.path.join(local, 'Doubao'),
            'size': '约 1.4 GB',
            'description': '豆包 AI 助手的本地缓存和模型数据。在豆包 App 内清除缓存最安全。',
            'open_note': '目录为 App 内部格式，不建议手动删文件。在豆包 App 内「设置 → 清除缓存」操作。',
        },
        {
            'name': 'Chrome 用户数据',
            'path': os.path.join(local, 'Google'),
            'size': '约 1.4 GB',
            'description': 'Chrome 浏览器的缓存和历史数据。在 Chrome 内清除浏览数据最安全。',
            'open_note': 'Chrome「设置 → 隐私与安全 → 清除浏览数据」→ 选"缓存的图片和文件"。',
        },
        {
            'name': '腾讯应用数据 (QQ/微信)',
            'path': os.path.join(roaming, 'Tencent'),
            'size': '约 3.8 GB',
            'description': 'QQ 和微信的聊天记录、图片缓存、文件缓存。可通过各 App 内置的清理功能处理。',
            'open_note': '微信 PC 端「设置 → 文件管理 → 打开文件夹」手动清理。QQ「系统设置 → 文件管理」清理。',
        },
        {
            'name': 'Trae IDE 数据',
            'path': os.path.join(roaming, 'TRAE SOLO CN'),
            'size': '约 3.1 GB',
            'description': 'Trae CN IDE 的扩展和缓存。如果不再使用可卸载该 IDE。',
            'open_note': '含扩展安装包和缓存。在 Trae 内禁用/卸载不用的扩展可回收部分空间。',
        },
        {
            'name': '直播伴侣数据 (webcast_mate)',
            'path': os.path.join(roaming, 'webcast_mate'),
            'size': '约 1.7 GB',
            'description': '直播伴侣工具的本地素材和缓存。不需要的旧素材可直接删除。',
        },
        {
            'name': '企业微信文件',
            'path': os.path.join(home, 'Documents', 'WXWork'),
            'size': '约 1.2 GB',
            'description': '企业微信的聊天文件和图片缓存。在企业微信设置中清理。',
            'open_note': '企业微信「设置 → 文件管理」中可查看和清理缓存文件。',
        },
        {
            'name': 'Playwright 浏览器',
            'path': os.path.join(local, 'ms-playwright'),
            'size': '约 1.6 GB',
            'description': 'Playwright 自动化测试的浏览器二进制文件。如不再用 Playwright 可删，否则保留。',
            'trash_paths': [os.path.join(local, 'ms-playwright')],
        },
        {
            'name': 'Steam 游戏 (E盘)',
            'path': 'E:/Steam',
            'size': '约 5.5 GB',
            'description': 'Steam 平台和已安装游戏。通过 Steam 客户端卸载不玩的游戏。',
            'open_note': 'Steam 库中右键游戏 → 管理 → 卸载。',
        },
    ],
    'red': [
        {
            'name': 'pagefile.sys（虚拟内存）',
            'path': 'C:/pagefile.sys',
            'size': '约 31 GB',
            'description': 'Windows 系统管理的虚拟内存页面文件，不建议手动删除。',
            'indirect_release': '设置 → 系统 → 关于 → 高级系统设置 → 性能设置 → 高级 → 虚拟内存 → 自定义大小。物理内存充足（≥32GB）可将初始值调至 4GB、最大值 8GB。',
        },
        {
            'name': 'hiberfil.sys（休眠文件）',
            'path': 'C:/hiberfil.sys',
            'size': '约 6 GB',
            'description': '系统休眠文件。如果不使用休眠功能，可以安全关闭以释放空间。',
            'indirect_release': '以管理员身份运行 cmd，执行 powercfg -h off 即可关闭休眠并自动删除此文件。注意：关闭后快速启动也会失效。',
        },
        {
            'name': 'Microsoft 系统目录',
            'path': os.path.join(local, 'Microsoft'),
            'size': '约 2.4 GB',
            'description': 'Windows 和 Office 的核心数据目录，不建议手动修改。',
            'indirect_release': '通过「设置 → 系统 → 存储 → 临时文件」让系统自动清理其可清理的子项。',
        },
    ],
    'summary': {
        'overview': 'C 盘 157 GB 已用，最大占用是虚拟内存 pagefile.sys（31 GB），其次 AppData 应用数据约 105 GB。识别出约 15 GB 可自动清理的缓存+约 20 GB 需人工判断的应用数据。',
        'total_releasable': '约 15.7 GB（绿灯）+ 约 19.7 GB（橙灯）',
        'priority': [
            '优先清理绿灯 8 项（约 15.7 GB）——全部是缓存/临时文件，安全无风险',
            '检查橙灯应用数据（腾讯/企业微信/豆包等约 19.7 GB）——可能有大量不需要的旧文件',
            '关闭休眠：powercfg -h off（释放 6 GB hiberfil.sys）',
            '调整虚拟内存：物理内存充足可将 pagefile 从 31 GB 降至 4-8 GB',
        ],
        'long_term': [
            '每月运行磁盘清理 (cleanmgr.exe)，勾选所有可清理项',
            'Chrome/Edge 设置自动清理：设置 → 隐私 → 定期清除浏览数据',
            '微信/QQ：定期在 App 内清理群聊文件和缓存',
            'npm/pip 缓存：定期执行 npm cache clean --force 和 pip cache purge',
            '大文件可视化：安装 WizTree（免费）扫描整盘，一眼看到大文件分布',
        ],
        'tier_stats': {
            'green': '约 15.7 GB',
            'yellow': '约 19.7 GB',
            'red': '约 39.4 GB',
        },
    },
}

# Save
out_path = r'd:\noveos\storage_analysis.json'
with open(out_path, 'w', encoding='utf-8') as f:
    json.dump(analysis, f, ensure_ascii=False, indent=2)
print(f'Analysis saved to {out_path}')
print(f'Green: {len(analysis["green"])}, Yellow: {len(analysis["yellow"])}, Red: {len(analysis["red"])}')
