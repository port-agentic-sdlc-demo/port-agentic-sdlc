"""GitHub REST helpers for Developer and Reviewer agents."""

from __future__ import annotations

import base64
import os
from typing import Any, Dict, List, Optional
from urllib.parse import urlparse

import requests


class GitHubClient:
    def __init__(self, token: str = None, repo: str = None):
        self.token = token or os.getenv("GITHUB_TOKEN") or os.getenv("GH_TOKEN")
        self.repo = repo or os.getenv("GITHUB_REPO", "port-agentic-sdlc-demo/port-agentic-sdlc")
        self.api = "https://api.github.com"
        self.dry_run = os.getenv("FACTORY_DRY_RUN", "").lower() in {"1", "true", "yes"}

    def _headers(self) -> Dict[str, str]:
        headers = {
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
        }
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        return headers

    def parse_pr_url(self, pr_url: str) -> Dict[str, Any]:
        path = urlparse(pr_url).path.strip("/").split("/")
        # owner/repo/pull/123
        if len(path) >= 4 and path[2] in {"pull", "pulls"}:
            return {"owner": path[0], "repo": path[1], "number": int(path[3]), "full_name": f"{path[0]}/{path[1]}"}
        raise ValueError(f"Unrecognized PR URL: {pr_url}")

    def get_default_branch(self) -> str:
        response = requests.get(f"{self.api}/repos/{self.repo}", headers=self._headers(), timeout=20)
        response.raise_for_status()
        return response.json().get("default_branch") or "main"

    def get_ref_sha(self, ref: str) -> str:
        response = requests.get(
            f"{self.api}/repos/{self.repo}/git/ref/heads/{ref}",
            headers=self._headers(),
            timeout=20,
        )
        response.raise_for_status()
        return response.json()["object"]["sha"]

    def create_branch(self, branch: str, from_branch: str = None) -> Dict[str, Any]:
        if self.dry_run:
            return {"dry_run": True, "branch": branch}
        base = from_branch or self.get_default_branch()
        sha = self.get_ref_sha(base)
        response = requests.post(
            f"{self.api}/repos/{self.repo}/git/refs",
            headers=self._headers(),
            json={"ref": f"refs/heads/{branch}", "sha": sha},
            timeout=20,
        )
        if response.status_code not in (200, 201):
            # Branch may already exist
            if response.status_code == 422:
                return {"ok": True, "branch": branch, "existed": True}
            return {"error": f"HTTP {response.status_code}", "body": response.text}
        return {"ok": True, "branch": branch}

    def get_file(self, path: str, ref: str = None) -> Dict[str, Any]:
        if self.dry_run and os.path.isfile(path):
            with open(path, encoding="utf-8") as handle:
                return {"path": path, "exists": True, "content": handle.read(), "dry_run": True}
        params = {"ref": ref} if ref else None
        response = requests.get(
            f"{self.api}/repos/{self.repo}/contents/{path}",
            headers=self._headers(),
            params=params,
            timeout=20,
        )
        if response.status_code == 404:
            return {"path": path, "exists": False, "content": ""}
        response.raise_for_status()
        data = response.json()
        content = base64.b64decode(data.get("content") or "").decode("utf-8")
        return {"path": path, "exists": True, "sha": data.get("sha"), "content": content}

    def put_file(self, path: str, content: str, message: str, branch: str, allowed_prefix: str) -> Dict[str, Any]:
        if not path.startswith(allowed_prefix.rstrip("/") + "/") and path != allowed_prefix.rstrip("/"):
            return {"error": f"Refusing to write {path}; must be under {allowed_prefix}"}
        if self.dry_run:
            os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
            with open(path, "w", encoding="utf-8") as handle:
                handle.write(content)
            return {"dry_run": True, "path": path, "bytes": len(content)}
        existing = self.get_file(path, ref=branch)
        payload = {
            "message": message,
            "content": base64.b64encode(content.encode("utf-8")).decode("ascii"),
            "branch": branch,
        }
        if existing.get("sha"):
            payload["sha"] = existing["sha"]
        response = requests.put(
            f"{self.api}/repos/{self.repo}/contents/{path}",
            headers=self._headers(),
            json=payload,
            timeout=30,
        )
        if response.status_code >= 400:
            return {"error": f"HTTP {response.status_code}", "body": response.text}
        return {"ok": True, "path": path, "commit": response.json().get("commit", {}).get("sha")}

    def create_pull_request(self, title: str, body: str, head: str, base: str = None) -> Dict[str, Any]:
        if self.dry_run:
            return {
                "dry_run": True,
                "html_url": f"https://github.com/{self.repo}/compare/{head}",
                "title": title,
            }
        response = requests.post(
            f"{self.api}/repos/{self.repo}/pulls",
            headers=self._headers(),
            json={"title": title, "body": body, "head": head, "base": base or self.get_default_branch()},
            timeout=30,
        )
        if response.status_code >= 400:
            return {"error": f"HTTP {response.status_code}", "body": response.text}
        data = response.json()
        return {"ok": True, "html_url": data.get("html_url"), "number": data.get("number")}

    def list_pr_files(self, pr_url: str) -> List[Dict[str, Any]]:
        parsed = self.parse_pr_url(pr_url)
        files: List[Dict[str, Any]] = []
        page = 1
        while True:
            response = requests.get(
                f"{self.api}/repos/{parsed['full_name']}/pulls/{parsed['number']}/files",
                headers=self._headers(),
                params={"per_page": 100, "page": page},
                timeout=30,
            )
            response.raise_for_status()
            batch = response.json()
            if not batch:
                break
            files.extend(
                {
                    "filename": item.get("filename"),
                    "status": item.get("status"),
                    "patch": item.get("patch"),
                    "additions": item.get("additions"),
                    "deletions": item.get("deletions"),
                }
                for item in batch
            )
            if len(batch) < 100:
                break
            page += 1
        return files

    def create_issue_comment(self, pr_url: str, body: str) -> Dict[str, Any]:
        parsed = self.parse_pr_url(pr_url)
        if self.dry_run:
            return {"dry_run": True, "comment": body[:500]}
        response = requests.post(
            f"{self.api}/repos/{parsed['full_name']}/issues/{parsed['number']}/comments",
            headers=self._headers(),
            json={"body": body},
            timeout=20,
        )
        if response.status_code >= 400:
            return {"error": f"HTTP {response.status_code}", "body": response.text}
        return {"ok": True, "html_url": response.json().get("html_url")}

    def submit_review(self, pr_url: str, body: str, event: str = "COMMENT") -> Dict[str, Any]:
        parsed = self.parse_pr_url(pr_url)
        if event not in {"APPROVE", "REQUEST_CHANGES", "COMMENT"}:
            event = "COMMENT"
        if self.dry_run:
            return {"dry_run": True, "event": event}
        response = requests.post(
            f"{self.api}/repos/{parsed['full_name']}/pulls/{parsed['number']}/reviews",
            headers=self._headers(),
            json={"body": body, "event": event},
            timeout=20,
        )
        if response.status_code >= 400:
            return {"error": f"HTTP {response.status_code}", "body": response.text}
        return {"ok": True, "html_url": response.json().get("html_url"), "state": response.json().get("state")}
