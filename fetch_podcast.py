#!/usr/bin/env python3
"""
fetch_podcast.py
從「游庭皓的財經皓角」podcast RSS 偵測最新一集，下載直連 MP3 → Groq Whisper
轉錄 → Claude 整理成結構化財經筆記，寫入 data.json["podcast_brief"]。

取代 fetch_youtube.py：podcast enclosure 是開放直連 MP3，機房 IP 抓取屬正常
行為、不被當機器人，因此無需 cookies/代理，比 YouTube 穩定得多。

設計要點：
- 主來源直連 SoundCloud RSS；失效時用 iTunes Lookup（PODCAST_ITUNES_ID）
  重新取得當前 feedUrl 再抓（作者換 host 也不會壞）。
- podcast_state.json 冪等快取：同一集 id 已處理過 → 直接重用，不重轉錄/重摘要。
- 任何失敗只記 log、不丟例外，不可中斷整批早報。
"""

import os
import re
import sys
import json
import html
import tempfile
import subprocess
from pathlib import Path
from email.utils import parsedate_to_datetime
from datetime import datetime, timezone, timedelta
from xml.etree import ElementTree as ET

import httpx

from config import (
    PODCAST_RSS_URL,
    PODCAST_NAME,
    PODCAST_ITUNES_ID,
    PODCAST_GROQ_MODEL,
    PODCAST_WHISPER_LANGUAGE,
    PODCAST_AUDIO_SEGMENT_MB,
    PODCAST_AUDIO_SEGMENT_SECONDS,
    PODCAST_SUMMARY_SINGLE_PASS_MAX,
    PODCAST_SUMMARY_CHUNK_CHARS,
)

ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY")
GROQ_API_KEY = os.environ.get("GROQ_API_KEY")

STATE_PATH = "podcast_state.json"
DATA_PATH = "data.json"
TPE = timezone(timedelta(hours=8))
UA = {"User-Agent": "Mozilla/5.0 (daily-design-brief podcast fetcher)"}


def log(msg: str) -> None:
    ts = datetime.now(TPE).strftime("%H:%M:%S")
    print(f"[{ts}] [podcast] {msg}", flush=True)


# ── 1. 偵測最新一集 ────────────────────────────────────────────────
def _fetch_rss_text(url: str) -> str:
    with httpx.Client(timeout=30, headers=UA, follow_redirects=True) as c:
        r = c.get(url)
        r.raise_for_status()
        return r.text


def _resolve_feed_url() -> str:
    """主來源直連 RSS；失敗時用 iTunes Lookup 取得當前 feedUrl。"""
    try:
        _fetch_rss_text(PODCAST_RSS_URL)
        return PODCAST_RSS_URL
    except Exception as e:
        log(f"[warn] 直連 RSS 失敗（{e}）→ 改用 iTunes Lookup 重新定位 feedUrl")
    try:
        with httpx.Client(timeout=30, headers=UA, follow_redirects=True) as c:
            r = c.get(f"https://itunes.apple.com/lookup?id={PODCAST_ITUNES_ID}")
            r.raise_for_status()
            feed = (r.json().get("results") or [{}])[0].get("feedUrl")
            if feed:
                log(f"iTunes 取得 feedUrl：{feed}")
                return feed
    except Exception as e:
        log(f"[warn] iTunes Lookup 也失敗：{e}")
    return PODCAST_RSS_URL  # 回退原值，交由上層 try/except 處理


def resolve_latest_episode() -> dict | None:
    """回傳最新一集 {episode_id,title,url,published,channel,mp3_url} 或 None。"""
    try:
        xml_text = _fetch_rss_text(_resolve_feed_url())
    except Exception as e:
        log(f"[warn] 取得 RSS 失敗：{e}")
        return None
    try:
        root = ET.fromstring(xml_text)
    except Exception as e:
        log(f"[warn] RSS 解析失敗：{e}")
        return None

    item = root.find(".//item")  # feed 由新到舊，第一筆即最新
    if item is None:
        log("RSS 內沒有任何集數")
        return None

    title = (item.findtext("title") or "").strip()
    link = (item.findtext("link") or "").strip()
    pub_raw = (item.findtext("pubDate") or "").strip()
    enc = item.find("enclosure")
    mp3_url = enc.get("url") if enc is not None else ""
    guid = (item.findtext("guid") or "").strip() or mp3_url

    if not mp3_url:
        log("最新集沒有 enclosure 音檔 → 跳過")
        return None

    published = ""
    try:
        published = parsedate_to_datetime(pub_raw).astimezone(TPE).strftime("%Y-%m-%d")
    except Exception:
        pass

    # episode_id：取 guid 末段做為穩定鍵
    m = re.search(r"(\d{6,})", guid)
    episode_id = m.group(1) if m else guid[-32:]

    return {
        "episode_id": episode_id,
        "title": title,
        "url": link or PODCAST_RSS_URL,
        "published": published,
        "channel": PODCAST_NAME,
        "mp3_url": mp3_url,
    }


# ── 2. 下載音檔 ────────────────────────────────────────────────────
def download_mp3(url: str, dest: str) -> bool:
    try:
        with httpx.Client(timeout=120, headers=UA, follow_redirects=True) as c:
            with c.stream("GET", url) as r:
                r.raise_for_status()
                with open(dest, "wb") as f:
                    for chunk in r.iter_bytes(chunk_size=1 << 16):
                        f.write(chunk)
        return os.path.exists(dest) and os.path.getsize(dest) > 0
    except Exception as e:
        log(f"[warn] 音檔下載失敗：{e}")
        return False


# ── 3. Groq Whisper 轉錄（含切段）─────────────────────────────────
def _whisper_one(client, path: str) -> str:
    with open(path, "rb") as f:
        resp = client.audio.transcriptions.create(
            file=(os.path.basename(path), f.read()),
            model=PODCAST_GROQ_MODEL,
            language=PODCAST_WHISPER_LANGUAGE,
            response_format="text",
        )
    return resp if isinstance(resp, str) else getattr(resp, "text", str(resp))


def transcribe(mp3_path: str, tmp: str) -> str:
    if not GROQ_API_KEY:
        log("[info] GROQ_API_KEY 未設定 — 無法轉錄")
        return ""
    try:
        from groq import Groq
    except ImportError:
        log("[warn] groq 套件未安裝 — 無法轉錄")
        return ""

    client = Groq(api_key=GROQ_API_KEY)
    size_mb = os.path.getsize(mp3_path) / (1024 * 1024)
    try:
        if size_mb <= PODCAST_AUDIO_SEGMENT_MB:
            log(f"Whisper 轉錄（{size_mb:.1f}MB，單檔）")
            return _whisper_one(client, mp3_path).strip()

        log(f"音訊 {size_mb:.1f}MB > {PODCAST_AUDIO_SEGMENT_MB}MB → ffmpeg 切段")
        # 先轉成 16kHz 單聲道縮小體積，再依秒數切段
        mono = os.path.join(tmp, "mono.mp3")
        subprocess.run(
            ["ffmpeg", "-y", "-i", mp3_path, "-ar", "16000", "-ac", "1", mono],
            check=True, capture_output=True,
        )
        src = mono if os.path.exists(mono) else mp3_path
        seg_tmpl = os.path.join(tmp, "seg%03d.mp3")
        subprocess.run(
            ["ffmpeg", "-y", "-i", src, "-f", "segment",
             "-segment_time", str(PODCAST_AUDIO_SEGMENT_SECONDS), "-c", "copy", seg_tmpl],
            check=True, capture_output=True,
        )
        segs = sorted(Path(tmp).glob("seg*.mp3"))
        parts = []
        for i, seg in enumerate(segs):
            log(f"  轉錄第 {i+1}/{len(segs)} 段")
            parts.append(_whisper_one(client, str(seg)).strip())
        return "\n".join(p for p in parts if p)
    except Exception as e:
        log(f"[warn] Whisper 轉錄失敗：{e}")
        return ""


# ── 4. Claude 摘要（主題分組格式）────────────────────────────────
SYSTEM_PROMPT = (
    "你是一位專業的財經內容編輯。使用者會給你一段節目逐字稿（可能含口語、"
    "語助詞、辨識錯誤、廣告或開場閒聊）。請忠實整理成結構清楚、可在一兩分鐘內"
    "讀完重點的筆記，用繁體中文書寫。"
    "整理時依「主題」分組（例如政策、通膨、產業、股市等），同一主題的論點收在一起；"
    "務必保留逐字稿中的具體數據（百分比、金額、指數、利率、商品、個股、時間）。"
    "只根據逐字稿內容，不要自行補充或臆測；辨識明顯有誤處可合理修正。"
    "這是對他人節目內容的摘要，不是投資建議——描述時用「主講人認為…」這類語氣。"
)

FORMAT_INSTRUCTION = (
    "請輸出以下 Markdown 結構（不要加 ``` 圍欄、不要多餘前言）：\n\n"
    "## 一句話總結\n"
    "（一句話，先講整集最重要的結論）\n\n"
    "接著用 3–6 個「主題段落」組織內容。每個主題一個 ## 標題，格式為"
    "「編號. 主題：一句副標」；標題下放 2–4 個重點，每個重點為一個項目符號，"
    "以「**粗體標籤：** 」開頭，後接 1–2 句說明，並把相關數據寫進說明裡。範例：\n\n"
    "## 1. 聯準會政策動向：華許首秀放鷹\n"
    "- **利率按兵不動但暗示升息：** 以 12:0 維持 3.5%–3.75%，點陣圖 9 位官員預估年底前至少升息一次。\n"
    "- **政策聲明簡化：** 從 300 多字縮減至約 130 字並刪除前瞻指引。\n\n"
    "最後一段結論：\n\n"
    "## 結論與後市展望\n"
    "（主講人的整體判斷與風險提醒）\n\n"
    "---\n"
    "*本筆記為節目內容摘要，非投資建議。*"
)


def _claude(client, system: str, user: str, max_tokens: int = 3000) -> str:
    resp = client.messages.create(
        model="claude-sonnet-4-5",
        max_tokens=max_tokens,
        system=system,
        messages=[{"role": "user", "content": user}],
    )
    return "".join(b.text for b in resp.content if getattr(b, "type", "") == "text").strip()


def summarize(transcript: str, title: str) -> str:
    if not ANTHROPIC_API_KEY:
        log("[info] ANTHROPIC_API_KEY 未設定 — 無法摘要")
        return ""
    try:
        import anthropic
    except ImportError:
        log("[warn] anthropic 套件未安裝 — 無法摘要")
        return ""

    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
    try:
        if len(transcript) <= PODCAST_SUMMARY_SINGLE_PASS_MAX:
            user = f"節目標題：{title}\n\n逐字稿：\n{transcript}\n\n{FORMAT_INSTRUCTION}"
            return _claude(client, SYSTEM_PROMPT, user)

        log(f"逐字稿 {len(transcript)} 字 > {PODCAST_SUMMARY_SINGLE_PASS_MAX} → map-reduce")
        chunks = [
            transcript[i:i + PODCAST_SUMMARY_CHUNK_CHARS]
            for i in range(0, len(transcript), PODCAST_SUMMARY_CHUNK_CHARS)
        ]
        partials = []
        for i, ch in enumerate(chunks):
            log(f"  條列第 {i+1}/{len(chunks)} 段")
            user = (
                f"以下是節目逐字稿的第 {i+1}/{len(chunks)} 段，請條列此段重點"
                f"（保留數據、標的與時間相關資訊，繁體中文）：\n\n{ch}"
            )
            partials.append(_claude(client, SYSTEM_PROMPT, user, max_tokens=1500))
        merged = "\n\n".join(partials)
        user = (
            f"節目標題：{title}\n\n以下是各段重點條列，請彙整成最終筆記：\n\n"
            f"{merged}\n\n{FORMAT_INSTRUCTION}"
        )
        return _claude(client, SYSTEM_PROMPT, user)
    except Exception as e:
        log(f"[warn] Claude 摘要失敗：{e}")
        return ""


# ── state / data I/O ───────────────────────────────────────────────
def load_json(path: str) -> dict:
    if os.path.exists(path):
        try:
            with open(path, encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}
    return {}


def write_brief_into_data(brief: dict) -> None:
    data = load_json(DATA_PATH)
    data["podcast_brief"] = brief
    with open(DATA_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    log(f"✅ data.json 寫入 podcast_brief（{brief.get('title','')[:30]}）")


# ── main ───────────────────────────────────────────────────────────
def main() -> None:
    force = "--force" in sys.argv
    log("偵測最新一集 …")
    info = resolve_latest_episode()
    if not info:
        return

    eid = info["episode_id"]
    state = load_json(STATE_PATH)
    if not force and eid in state:
        log(f"{eid}（{info['title'][:24]}）已在快取 → 重用，不重轉錄/摘要")
        write_brief_into_data(state[eid])
        return

    log(f"新集：{info['title'][:40]}（{info['published']}）")
    with tempfile.TemporaryDirectory() as tmp:
        mp3 = os.path.join(tmp, "episode.mp3")
        log("下載音檔 …")
        if not download_mp3(info["mp3_url"], mp3):
            log("[warn] 音檔下載失敗 → 跳過")
            return
        transcript = transcribe(mp3, tmp)

    if not transcript:
        log("[warn] 轉錄為空 → 跳過")
        return

    summary_md = summarize(transcript, info["title"])
    if not summary_md:
        log("[warn] 摘要為空 → 跳過")
        return

    brief = {
        "episode_id": eid,
        "title": info["title"],
        "url": info["url"],
        "published": info["published"],
        "channel": info["channel"],
        "transcript_source": "Podcast 音檔 · Whisper",
        "summary_md": summary_md,
    }

    state[eid] = brief
    if len(state) > 90:
        for k in list(state.keys())[:-90]:
            state.pop(k, None)
    with open(STATE_PATH, "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=2)

    write_brief_into_data(brief)
    log("完成")


if __name__ == "__main__":
    main()
