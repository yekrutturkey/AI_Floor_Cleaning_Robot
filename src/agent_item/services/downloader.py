from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path, PurePosixPath
from typing import Any
from urllib.parse import quote, unquote, urlparse

import httpx


GITHUB_API_BASE = "https://api.github.com"
GITHUB_API_VERSION = "2026-03-10"


class GitHubDownloadError(RuntimeError):
    """GitHub 文件或目录下载失败。"""


@dataclass(frozen=True)
class GitHubTarget:
    """从 GitHub URL 中解析出的目标信息。"""

    owner: str
    repo: str
    ref: str
    path: str


@dataclass
class DownloadSummary:
    """记录本次下载结果。"""

    downloaded_files: list[Path] = field(default_factory=list)
    skipped_files: list[Path] = field(default_factory=list)
    unsupported_items: list[str] = field(default_factory=list)


def parse_github_url(
    url: str,
    *,
    ref_override: str | None = None,
) -> GitHubTarget:
    """
    解析 GitHub 文件或文件夹 URL。

    支持的 URL 示例：

    文件夹：
    https://github.com/owner/repo/tree/main/data

    文件：
    https://github.com/owner/repo/blob/main/data/example.txt

    Raw 文件：
    https://raw.githubusercontent.com/owner/repo/main/data/example.txt
    """
    parsed_url = urlparse(url)
    hostname = parsed_url.hostname or ""

    path_parts = [unquote(part) for part in parsed_url.path.split("/") if part]

    if hostname in {"github.com", "www.github.com"}:
        return _parse_normal_github_url(
            path_parts,
            ref_override=ref_override,
        )

    if hostname == "raw.githubusercontent.com":
        return _parse_raw_github_url(
            path_parts,
            ref_override=ref_override,
        )

    raise ValueError("不支持该 URL。请输入 github.com 或 raw.githubusercontent.com 地址。")


def _parse_normal_github_url(
    path_parts: list[str],
    *,
    ref_override: str | None,
) -> GitHubTarget:
    if len(path_parts) < 4:
        raise ValueError("GitHub 地址不完整。请打开具体文件或文件夹，不要使用仓库首页地址。")

    owner = path_parts[0]
    repo = path_parts[1].removesuffix(".git")
    page_type = path_parts[2]

    if page_type not in {"tree", "blob"}:
        raise ValueError("该地址不是 GitHub 文件或文件夹地址。URL 中应包含 /tree/ 或 /blob/。")

    ref, repository_path = _split_ref_and_path(
        path_parts[3:],
        ref_override=ref_override,
    )

    if page_type == "blob" and not repository_path:
        raise ValueError("文件 URL 中缺少文件路径。")

    return GitHubTarget(
        owner=owner,
        repo=repo,
        ref=ref,
        path=repository_path,
    )


def _parse_raw_github_url(
    path_parts: list[str],
    *,
    ref_override: str | None,
) -> GitHubTarget:
    if len(path_parts) < 4:
        raise ValueError("Raw GitHub 地址不完整。")

    owner = path_parts[0]
    repo = path_parts[1].removesuffix(".git")

    ref, repository_path = _split_ref_and_path(
        path_parts[2:],
        ref_override=ref_override,
    )

    if not repository_path:
        raise ValueError("Raw GitHub 地址中缺少文件路径。")

    return GitHubTarget(
        owner=owner,
        repo=repo,
        ref=ref,
        path=repository_path,
    )


def _split_ref_and_path(
    remaining_parts: list[str],
    *,
    ref_override: str | None,
) -> tuple[str, str]:
    if not remaining_parts:
        raise ValueError("GitHub URL 中缺少分支名称。")

    if ref_override is None:
        # 普通 main、master、develop 等单段分支名称
        ref = remaining_parts[0]
        repository_parts = remaining_parts[1:]
    else:
        # 支持 feature/download 等带斜杠的分支名称
        ref_parts = [part for part in ref_override.split("/") if part]

        if remaining_parts[: len(ref_parts)] != ref_parts:
            raise ValueError(f"URL 中的分支与 --ref {ref_override!r} 不匹配。")

        ref = ref_override
        repository_parts = remaining_parts[len(ref_parts) :]

    repository_path = "/".join(repository_parts)

    return ref, repository_path


def download_github_path(
    url: str,
    output_dir: str | Path,
    *,
    overwrite: bool = False,
    ref_override: str | None = None,
    token: str | None = None,
) -> DownloadSummary:
    """
    下载 GitHub 中的单个文件或整个文件夹。

    文件夹会递归下载，并保留内部目录结构。

    Args:
        url:
            GitHub 文件或文件夹 URL。
        output_dir:
            本地保存目录。
        overwrite:
            本地文件存在时是否覆盖。
        ref_override:
            分支名称中包含斜杠时显式指定，例如 feature/download。
        token:
            GitHub Token。未传入时读取 GITHUB_TOKEN 环境变量。

    Returns:
        DownloadSummary：下载、跳过和不支持项目的汇总。
    """
    target = parse_github_url(
        url,
        ref_override=ref_override,
    )

    destination_root = Path(output_dir).resolve()
    destination_root.mkdir(parents=True, exist_ok=True)

    github_token = token or os.getenv("GITHUB_TOKEN")

    headers = {
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": GITHUB_API_VERSION,
        "User-Agent": "agent-item-github-downloader",
    }

    if github_token:
        headers["Authorization"] = f"Bearer {github_token}"

    timeout = httpx.Timeout(
        connect=30.0,
        read=120.0,
        write=30.0,
        pool=30.0,
    )

    summary = DownloadSummary()

    with httpx.Client(
        headers=headers,
        timeout=timeout,
        follow_redirects=True,
    ) as client:
        content = _get_repository_content(
            client=client,
            target=target,
            repository_path=target.path,
        )

        if isinstance(content, list):
            _download_directory(
                client=client,
                target=target,
                entries=content,
                selected_root_path=target.path,
                destination_root=destination_root,
                overwrite=overwrite,
                summary=summary,
            )
        elif content.get("type") == "file":
            destination = _safe_destination(
                destination_root,
                PurePosixPath(content["name"]),
            )

            _download_file_entry(
                client=client,
                entry=content,
                destination=destination,
                overwrite=overwrite,
                summary=summary,
            )
        else:
            item_type = str(content.get("type", "unknown"))
            raise GitHubDownloadError(f"暂不支持该 GitHub 项目类型：{item_type}")

    return summary


def _get_repository_content(
    *,
    client: httpx.Client,
    target: GitHubTarget,
    repository_path: str,
) -> dict[str, Any] | list[dict[str, Any]]:
    endpoint = (
        f"{GITHUB_API_BASE}/repos/"
        f"{quote(target.owner, safe='')}/"
        f"{quote(target.repo, safe='')}/contents"
    )

    if repository_path:
        encoded_path = quote(repository_path, safe="/")
        endpoint = f"{endpoint}/{encoded_path}"

    response = client.get(
        endpoint,
        params={"ref": target.ref},
    )

    if response.is_error:
        _raise_api_error(
            response=response,
            target=target,
            repository_path=repository_path,
        )

    payload = response.json()

    if not isinstance(payload, (dict, list)):
        raise GitHubDownloadError("GitHub API 返回了无法识别的数据格式。")

    return payload


def _download_directory(
    *,
    client: httpx.Client,
    target: GitHubTarget,
    entries: list[dict[str, Any]],
    selected_root_path: str,
    destination_root: Path,
    overwrite: bool,
    summary: DownloadSummary,
) -> None:
    for entry in entries:
        item_type = entry.get("type")
        repository_path = entry.get("path")

        if not isinstance(repository_path, str):
            summary.unsupported_items.append(str(entry))
            continue

        if item_type == "file":
            relative_path = _relative_repository_path(
                repository_path=repository_path,
                selected_root_path=selected_root_path,
            )

            destination = _safe_destination(
                destination_root,
                relative_path,
            )

            _download_file_entry(
                client=client,
                entry=entry,
                destination=destination,
                overwrite=overwrite,
                summary=summary,
            )

        elif item_type == "dir":
            child_content = _get_repository_content(
                client=client,
                target=target,
                repository_path=repository_path,
            )

            if not isinstance(child_content, list):
                raise GitHubDownloadError(
                    f"预期 {repository_path} 是目录，但 GitHub API 返回的不是目录列表。"
                )

            _download_directory(
                client=client,
                target=target,
                entries=child_content,
                selected_root_path=selected_root_path,
                destination_root=destination_root,
                overwrite=overwrite,
                summary=summary,
            )

        else:
            summary.unsupported_items.append(f"{repository_path} ({item_type})")


def _download_file_entry(
    *,
    client: httpx.Client,
    entry: dict[str, Any],
    destination: Path,
    overwrite: bool,
    summary: DownloadSummary,
) -> None:
    if destination.exists() and not overwrite:
        summary.skipped_files.append(destination)
        return

    download_url = entry.get("download_url")

    if not isinstance(download_url, str) or not download_url:
        summary.unsupported_items.append(str(entry.get("path", entry.get("name", "unknown"))))
        return

    destination.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    temporary_path = destination.with_name(f"{destination.name}.part")

    temporary_path.unlink(missing_ok=True)

    try:
        with client.stream("GET", download_url) as response:
            response.raise_for_status()

            with temporary_path.open("wb") as file:
                for chunk in response.iter_bytes():
                    file.write(chunk)

        temporary_path.replace(destination)
        summary.downloaded_files.append(destination)

    except httpx.HTTPError as exc:
        temporary_path.unlink(missing_ok=True)

        raise GitHubDownloadError(
            f"下载文件失败：{entry.get('path', destination.name)}；原因：{exc}"
        ) from exc

    except OSError as exc:
        temporary_path.unlink(missing_ok=True)

        raise GitHubDownloadError(f"写入本地文件失败：{destination}；原因：{exc}") from exc


def _relative_repository_path(
    *,
    repository_path: str,
    selected_root_path: str,
) -> PurePosixPath:
    complete_path = PurePosixPath(repository_path)

    if not selected_root_path:
        return complete_path

    root_path = PurePosixPath(selected_root_path)

    try:
        return complete_path.relative_to(root_path)
    except ValueError as exc:
        raise GitHubDownloadError(
            f"仓库路径 {repository_path!r} 不属于目标目录 {selected_root_path!r}。"
        ) from exc


def _safe_destination(
    destination_root: Path,
    relative_path: PurePosixPath,
) -> Path:
    """
    防止异常路径写出目标目录，例如 ../../other。
    """
    local_parts = [part for part in relative_path.parts if part not in {"", "."}]

    destination = destination_root.joinpath(*local_parts).resolve()

    if not destination.is_relative_to(destination_root):
        raise GitHubDownloadError(f"检测到不安全的文件路径：{relative_path}")

    return destination


def _raise_api_error(
    *,
    response: httpx.Response,
    target: GitHubTarget,
    repository_path: str,
) -> None:
    try:
        response_data = response.json()
        message = response_data.get(
            "message",
            response.text,
        )
    except ValueError:
        message = response.text

    if response.status_code in {403, 429} and response.headers.get("x-ratelimit-remaining") == "0":
        raise GitHubDownloadError(
            "GitHub API 请求次数已经用完。可以稍后重试，或者配置 GITHUB_TOKEN。"
        )

    if response.status_code == 404:
        raise GitHubDownloadError(
            "GitHub 中没有找到目标。请检查："
            f"仓库 {target.owner}/{target.repo}、"
            f"分支 {target.ref}、"
            f"路径 {repository_path!r}。"
            "私有仓库还需要配置 GITHUB_TOKEN。"
        )

    raise GitHubDownloadError(
        f"GitHub API 请求失败，状态码：{response.status_code}；原因：{message}"
    )
