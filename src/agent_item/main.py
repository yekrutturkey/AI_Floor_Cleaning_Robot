from __future__ import annotations

import argparse
from pathlib import Path

from agent_item.services.downloader import (
    GitHubDownloadError,
    download_github_path,
)


def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="下载 GitHub 中的单个文件或整个文件夹。")

    parser.add_argument(
        "url",
        help=("GitHub 文件或文件夹 URL，例如 https://github.com/owner/repo/tree/main/data"),
    )

    parser.add_argument(
        "-o",
        "--output-dir",
        default="data/raw",
        help="本地保存目录，默认：data/raw",
    )

    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="覆盖本地已经存在的同名文件。",
    )

    parser.add_argument(
        "--ref",
        dest="ref_override",
        help=("显式指定分支名称。仅在分支名称包含斜杠时需要，例如 feature/download。"),
    )

    return parser.parse_args()


def main() -> None:
    args = parse_arguments()

    try:
        summary = download_github_path(
            url=args.url,
            output_dir=Path(args.output_dir),
            overwrite=args.overwrite,
            ref_override=args.ref_override,
        )

    except ValueError as exc:
        print(f"地址错误：{exc}")
        raise SystemExit(2) from exc

    except GitHubDownloadError as exc:
        print(f"下载失败：{exc}")
        raise SystemExit(1) from exc

    except KeyboardInterrupt:
        print("\n用户取消下载。")
        raise SystemExit(130) from None

    for path in summary.downloaded_files:
        print(f"[已下载] {path}")

    for path in summary.skipped_files:
        print(f"[已跳过] {path}，文件已经存在")

    for item in summary.unsupported_items:
        print(f"[未处理] {item}")

    print()
    print(
        "处理完成："
        f"下载 {len(summary.downloaded_files)} 个，"
        f"跳过 {len(summary.skipped_files)} 个，"
        f"未处理 {len(summary.unsupported_items)} 个。"
    )


if __name__ == "__main__":
    main()
