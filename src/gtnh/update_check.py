#!/usr/bin/env python3
from typing import Dict, Set

from github import Github
from github.GitRelease import GitRelease
from github.Repository import Repository
from mod_info import OTHER, UNKNOWN, GTNHModpack, ModInfo, load_gtnh_manifest
from utils import get_all_repos, get_token


class NoReleasesException(Exception):
    pass


def check_for_updates(all_repos: Dict[str, Repository], gtnh_modpack: GTNHModpack) -> None:
    print("Checking for updates")

    for mod in gtnh_modpack.github_mods:
        check_mod_for_update(all_repos, mod)


def check_mod_for_update(all_repos: Dict[str, Repository], mod: ModInfo) -> None:
    version_updated = False

    print(f"Checking {mod.name}:{mod.version} for updates")
    repo = all_repos.get(mod.name, None)
    if repo is None:
        print(f"Couldn't find repo {mod.name}")
        return

    latest_release: GitRelease = repo.get_latest_release()
    if not latest_release:
        print(f"*** No latest release found for {mod.name}")
        return

    latest_version = latest_release.tag_name

    if latest_version > mod.version:
        print(f"Update found for {mod.name} {mod.version} -> {latest_version}")
        mod.version = latest_version
        version_updated = True

    if mod.license in [UNKNOWN, OTHER]:
        try:
            repo_license = repo.get_license()
            if repo_license:
                mod.license = repo_license.license.name
        except Exception:
            pass

    if mod.repo_url is None:
        mod.repo_url = repo.html_url

    if version_updated or mod.download_url is None or mod.filename is None or mod.browser_download_url is None:
        release_assets = latest_release.get_assets()
        for asset in release_assets:
            if (
                not asset.name.endswith(".jar")
                or asset.name.endswith("dev.jar")
                or asset.name.endswith("sources.jar")
                or asset.name.endswith("api.jar")
            ):
                continue

            mod.browser_download_url = asset.browser_download_url
            mod.download_url = asset.url
            mod.tagged_at = asset.created_at
            mod.filename = asset.name


def check_for_missing_repos(all_repos: Dict[str, Repository], gtnh_modpack: GTNHModpack) -> Set[str]:
    all_repo_names = set(all_repos.keys())
    all_modpack_names = set(gtnh_modpack._github_modmap.keys())

    return all_repo_names - all_modpack_names


if __name__ == "__main__":
    g = Github(get_token())
    o = g.get_organization("GTNewHorizons")

    print("Grabbing all repository information")
    all_repos = get_all_repos(o)
    github_mods = load_gtnh_manifest()

    check_for_updates(all_repos, github_mods)
    with open("updated_mods.json", "w+") as f:
        f.write(github_mods.json(indent=2, exclude={"_github_modmap"}))

    missing_repos = check_for_missing_repos(all_repos, github_mods)
    if len(missing_repos):
        print(f"Missing Mods: {', '.join(missing_repos)}")
