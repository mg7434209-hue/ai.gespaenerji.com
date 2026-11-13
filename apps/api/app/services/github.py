"""GitHub'da tek dosyalık değişiklikle PR açan küçük istemci (onaylı yönetim).

Yalnız `services/actions.py` kullanır. Belirteç JARVIS_GITHUB_TOKEN'dır; hata
`GitHubError` olarak döner ve belirteç hiçbir iletiye yazılmaz.
"""
import base64
from typing import Callable, Optional

import httpx

from app.config import settings

API = "https://api.github.com"


class GitHubError(RuntimeError):
    pass


def configured() -> bool:
    return bool(settings.jarvis_github_token)


def _client() -> httpx.Client:
    return httpx.Client(base_url=API, timeout=30.0, headers={
        "Authorization": f"Bearer {settings.jarvis_github_token}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
        "User-Agent": "gespa-os-jarvis",
    })


def _ok(r: httpx.Response, what: str) -> dict:
    if r.status_code >= 300:
        hint = {401: "belirteç geçersiz", 403: "belirtecin bu repoya yazma izni yok",
                404: "repo ya da dosya bulunamadı (belirteç bu repoyu görmüyor olabilir)",
                422: "GitHub isteği reddetti (dal zaten var olabilir)"}.get(r.status_code, "")
        raise GitHubError(f"{what}: HTTP {r.status_code}" + (f" — {hint}" if hint else ""))
    return r.json() if r.content else {}


def open_file_pr(repo: str, path: str, branch: str, edit: Callable[[str], str], *,
                 title: str, body: str, message: str,
                 client: Optional[httpx.Client] = None) -> str:
    """`path` dosyasını varsayılan dalın GÜNCEL hâlinden okur, `edit` ile değiştirir,
    yeni dalda commit'ler ve PR açar. PR adresini döndürür. `edit` ValueError atarsa
    hiçbir şey yazılmaz."""
    if not configured() and client is None:
        raise GitHubError("JARVIS_GITHUB_TOKEN tanımlı değil")
    c = client or _client()
    try:
        base = _ok(c.get(f"/repos/{repo}"), "repo okunamadı")["default_branch"]
        head = _ok(c.get(f"/repos/{repo}/git/ref/heads/{base}"), "dal okunamadı")["object"]["sha"]
        meta = _ok(c.get(f"/repos/{repo}/contents/{path}", params={"ref": head}), "dosya okunamadı")
        raw = c.get(f"/repos/{repo}/contents/{path}", params={"ref": head},
                    headers={"Accept": "application/vnd.github.raw"})
        if raw.status_code != 200:
            raise GitHubError(f"dosya içeriği okunamadı: HTTP {raw.status_code}")
        new = edit(raw.text)  # ValueError → çağırana
        if new == raw.text:
            raise ValueError("dosyada değişecek bir şey yok (değer zaten böyle)")
        _ok(c.post(f"/repos/{repo}/git/refs", json={"ref": f"refs/heads/{branch}", "sha": head}), "dal açılamadı")
        _ok(c.put(f"/repos/{repo}/contents/{path}", json={
            "message": message, "branch": branch, "sha": meta["sha"],
            "content": base64.b64encode(new.encode("utf-8")).decode("ascii"),
        }), "dosya yazılamadı")
        pr = _ok(c.post(f"/repos/{repo}/pulls", json={"title": title, "head": branch, "base": base, "body": body}),
                 "PR açılamadı")
        return pr["html_url"]
    except httpx.HTTPError as e:
        raise GitHubError(f"GitHub'a ulaşılamadı ({type(e).__name__})")
    finally:
        if client is None:
            c.close()
