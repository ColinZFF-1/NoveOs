"""
书香中文网 (m.sxcnw.org) 各频道 Top10 小说批量下载脚本
使用 scrapling 库抓取，保存到 D:\noveos\RAG 按频道分类

流程：分类页 → 详情页 → 下载页 → TXT下载 → 转UTF-8保存
"""
import re
import time
from pathlib import Path
from scrapling.fetchers import FetcherSession

BASE_URL = "https://m.sxcnw.org"
RAG_DIR = Path(r"D:\noveos\RAG")

# 13个频道
CATEGORIES = [
    ("chuanyue", "穿越小说"),
    ("yanqing", "言情小说"),
    ("xuanhuan", "玄幻小说"),
    ("wuxia", "武侠小说"),
    ("wangyou", "网游小说"),
    ("jingji", "竞技小说"),
    ("dushi", "都市小说"),
    ("kehuan", "科幻小说"),
    ("fuhei", "腹黑小说"),
    ("junshi", "军事小说"),
    ("lishi", "历史小说"),
    ("kongbu", "恐怖小说"),
    ("meiwen", "美文同人"),
]


def safe_filename(name):
    """去除文件名中的非法字符，限制长度"""
    name = re.sub(r'[\\/:*?"<>|]', '_', name)
    name = name.strip().strip('.')
    if not name:
        name = "unknown"
    # 限制长度避免 Windows 路径过长
    if len(name) > 80:
        name = name[:80]
    return name


def extract_novel_id(href):
    """从 /shuku/29925.html 提取 ID"""
    m = re.search(r'/shuku/(\d+)\.html', href)
    return m.group(1) if m else None


def get_top10_from_category(session, slug, cname):
    """从分类首页获取 Top10 小说列表（人气排序，第1页即Top10）"""
    url = f"{BASE_URL}/{slug}/"
    try:
        page = session.get(url, stealthy_headers=True)
    except Exception as e:
        print(f"  获取分类页失败: {e}")
        return []

    novels = []
    items = page.css('div.wp4 div.wc3 ul li')
    for item in items[:10]:
        link = item.css('p a')
        if not link:
            continue
        href = link[0].attrib.get('href', '')
        title = link[0].text.strip() if hasattr(link[0], 'text') else ''
        if not title:
            title = link.css('::text').get() or ''
            title = title.strip()
        novel_id = extract_novel_id(href)
        if novel_id and title:
            novels.append({'id': novel_id, 'title': title, 'href': href})
    return novels


def get_download_url_via_detail(session, novel_id):
    """
    从小说详情页提取下载页链接，再从下载页提取 TXT 地址。
    因为下载页的 classid 参数不固定（如 downpage/1/ 或 downpage/7/）。
    """
    # Step 1: 获取详情页
    detail_url = f"{BASE_URL}/shuku/{novel_id}.html"
    try:
        detail = session.get(detail_url, stealthy_headers=True)
    except Exception:
        return None

    # 找到"进入下载地址列表"链接
    # 模式: <a href="/downpage/X/NNN.html">进入下载地址列表</a>
    downpage_href = None
    for a in detail.css('div.down a'):
        href = a.attrib.get('href', '')
        if '/downpage/' in href:
            downpage_href = href
            break

    if not downpage_href:
        # 尝试从 raw HTML 用正则兜底
        import re as re_mod
        html = detail.body
        if isinstance(html, bytes):
            html = html.decode('utf-8', errors='replace')
        m = re_mod.search(r'href=["\']([^"\']*downpage[^"\']*)["\']', html)
        if m:
            downpage_href = m.group(1)

    if not downpage_href:
        return None

    if downpage_href.startswith('/'):
        downpage_url = BASE_URL + downpage_href
    else:
        downpage_url = downpage_href

    # Step 2: 获取下载页
    try:
        dl_page = session.get(downpage_url, stealthy_headers=True)
    except Exception:
        return None

    # Step 3: 提取 TXT 下载链接
    for a in dl_page.css('div.xz2 ul li a'):
        href = a.attrib.get('href', '')
        if href and ('txt.sxcnw.org' in href or href.endswith('.txt')):
            if href.startswith('//'):
                return 'https:' + href
            return href

    # 正则兜底
    html2 = dl_page.body
    if isinstance(html2, bytes):
        html2 = html2.decode('utf-8', errors='replace')
    import re as re_mod2
    m = re_mod2.search(r'href=["\']([^"\']*txt\.sxcnw\.org[^"\']*\.txt)["\']', html2)
    if m:
        return m.group(1)

    return None


def decode_content(raw_bytes):
    """智能检测编码并解码为字符串"""
    if raw_bytes.startswith(b'\xef\xbb\xbf'):
        return raw_bytes[3:].decode('utf-8')
    if raw_bytes.startswith(b'\xff\xfe'):
        return raw_bytes[2:].decode('utf-16-le')
    if raw_bytes.startswith(b'\xfe\xff'):
        return raw_bytes[2:].decode('utf-16-be')

    # 该网站 TXT 文件绝大多数是 GBK
    for enc in ['gbk', 'gb18030', 'utf-8', 'gb2312']:
        try:
            return raw_bytes.decode(enc)
        except (UnicodeDecodeError, UnicodeError):
            continue
    return raw_bytes.decode('utf-8', errors='replace')


def download_novel(session, download_url, save_path):
    """下载小说 TXT，统一转存 UTF-8"""
    if save_path.exists():
        size_kb = save_path.stat().st_size / 1024
        print(f"    -> 已存在 ({size_kb:.1f} KB), 跳过")
        return 'skipped'

    if not download_url:
        return 'no_url'

    try:
        resp = session.get(download_url, stealthy_headers=True)
        content = resp.body
        if not content or len(content) == 0:
            print(f"    x 下载内容为空")
            return 'empty'

        text = decode_content(content)
        save_path.write_text(text, encoding='utf-8')
        size_kb = len(content) / 1024
        print(f"    v 下载完成 ({size_kb:.1f} KB)")
        return 'ok'
    except Exception as e:
        print(f"    x 下载失败: {e}")
        return 'error'


def main():
    print("=" * 60)
    print("书香中文网 各频道 Top10 小说批量下载")
    print("=" * 60)

    RAG_DIR.mkdir(parents=True, exist_ok=True)

    stats = {'ok': 0, 'skipped': 0, 'no_url': 0, 'empty': 0, 'error': 0}
    all_results = []  # (category, title, status)

    with FetcherSession(impersonate='chrome') as session:
        for slug, cname in CATEGORIES:
            print(f"\n{'='*50}")
            print(f"[{cname}] ({slug})")
            print(f"{'='*50}")

            cat_dir = RAG_DIR / cname
            cat_dir.mkdir(parents=True, exist_ok=True)

            # Step 1: 分类页 → Top10 列表
            novels = get_top10_from_category(session, slug, cname)
            if not novels:
                print(f"  未获取到小说列表")
                continue

            print(f"  获取到 {len(novels)} 本小说")

            # Step 2,3,4: 逐本处理
            for i, novel in enumerate(novels, 1):
                nid = novel['id']
                title = novel['title']
                print(f"  [{i}/{len(novels)}] {title} (ID:{nid})", end="")

                time.sleep(0.3)  # 详情页
                dl_url = get_download_url_via_detail(session, nid)

                time.sleep(0.3)  # 下载
                safe_t = safe_filename(title)
                save_path = cat_dir / f"{safe_t}.txt"
                status = download_novel(session, dl_url, save_path)

                stats[status] = stats.get(status, 0) + 1
                all_results.append((cname, title, status))

    # 汇总
    print(f"\n{'='*60}")
    print(f"下载完成！")
    print(f"  成功下载: {stats.get('ok', 0)} 本")
    print(f"  已存在跳过: {stats.get('skipped', 0)} 本")
    print(f"  无下载链接: {stats.get('no_url', 0)} 本")
    print(f"  下载为空: {stats.get('empty', 0)} 本")
    print(f"  下载出错: {stats.get('error', 0)} 本")
    print(f"  存放目录: {RAG_DIR}")
    print(f"{'='*60}")

    # 写汇总文件
    summary_path = RAG_DIR / "download_summary.txt"
    with open(summary_path, 'w', encoding='utf-8') as f:
        f.write("书香中文网 各频道 Top10 小说下载汇总\n")
        f.write("=" * 60 + "\n")
        for cname, title, status in all_results:
            status_cn = {'ok': '成功', 'skipped': '跳过', 'no_url': '无链接',
                         'empty': '空', 'error': '出错'}.get(status, status)
            f.write(f"[{status_cn}] {cname} - {title}\n")
        f.write("\n")
        f.write(f"成功: {stats.get('ok', 0)}, 跳过: {stats.get('skipped', 0)}, "
                f"无链接: {stats.get('no_url', 0)}, 空: {stats.get('empty', 0)}, "
                f"错误: {stats.get('error', 0)}\n")
    print(f"  汇总文件: {summary_path}")


if __name__ == '__main__':
    main()
