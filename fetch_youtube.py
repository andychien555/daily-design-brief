#!/usr/bin/env python3
"""
fetch_youtube.py
從「游庭皓的財經皓角」頻道 /streams 解析最新一場「已結束」直播，
取逐字稿（字幕優先，太短/失敗退回 Groq Whisper），由 Claude 整理成
結構化財經筆記，並把結果寫入 data.json 的 youtube_brief 欄位。

設計要點（對應 yt-daily-brief-SPEC.md）：
- 絕不寫死單一影片 ID，永遠從頻道 /streams 動態解析最新已結束直播。（§5.1/§5.2）
- 用 youtube_state.json 做冪等快取：同一 video_id 已處理過 → 直接重用，
  不重抓逐字稿、不重呼叫 Whisper/Claude（避免非交易日 / 備援重跑浪費額度）。
- 任何失敗都只記 log、不丟例外，不可中斷整批早報。（§13）
"""

import os
import re
import sys
import json
import html
import tempfile
import subprocess
from pathlib import Path
from datetime import datetime, timezone, timedelta

from config import (
    YT_CHANNEL_STREAMS_URL,
    YT_CHANNEL_NAME,
    YT_CANDIDATE_COUNT,
    YT_PREFER_SUBTITLES,
    YT_SUBTITLE_LANGS,
    YT_SUBTITLE_MIN_CHARS,
    YT_GROQ_MODEL,
    YT_WHISPER_LANGUAGE,
    YT_AUDIO_SEGMENT_MB,
    YT_AUDIO_SEGMENT_SECONDS,
    YT_SUMMARY_SINGLE_PASS_MAX,
    YT_SUMMARY_CHUNK_CHARS,
)

ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY")
GROQ_API_KEY = os.environ.get("GROQ_API_KEY")
YT_COOKIES = os.environ.get("YT_COOKIES")  # cookies.txt 路徑（機房 IP 防封鎖）

STATE_PATH = "youtube_state.json"
DATA_PATH = "data.json"
TPE = timezone(timedelta(hours=8))


def log(msg: str) -> None:
    ts = datetime.now(TPE).strftime("%H:%M:%S")
    print(f"[{ts}] [youtube] {msg}", flush=True)


# ── yt-dlp 共用設定 ────────────────────────────────────────────────
def base_ydl_opts() -> dict:
    opts = {"quiet": True, "no_warnings": True, "skip_download": True}
    if YT_COOKIES and os.path.exists(YT_COOKIES):
        opts["cookiefile"] = YT_COOKIES
        log(f"使用 cookies：{YT_COOKIES}")
    return opts


# ── 1. 解析最新一場已結束直播 ──────────────────────────────────────
def resolve_latest_finished() -> dict | None:
    """回傳 {video_id,title,url,published,channel} 或 None。

    先以 extract_flat 取候選 entries，再對候選由新到舊逐一做完整
    extract_info 取 live_status，回傳第一個非 is_live / is_upcoming 者。
    """
    try:
        import yt_dlp
    except ImportError:
        log("[warn] yt-dlp 未安裝 — 跳過 YouTube 區塊")
        return None

    flat_opts = dict(base_ydl_opts())
    flat_opts.update({"extract_flat": True, "playlist_items": f"1:{YT_CANDIDATE_COUNT}"})

    try:
        with yt_dlp.YoutubeDL(flat_opts) as ydl:
            info = ydl.extract_info(YT_CHANNEL_STREAMS_URL, download=False)
        entries = [e for e in (info.get("entries") or []) if e and e.get("id")]
    except Exception as e:
        log(f"[warn] 解析頻道 /streams 失敗：{e}")
        return None

    if not entries:
        log("找不到任何直播候選")
        return None

    full_opts = base_ydl_opts()
    for ent in entries:
        vid = ent["id"]
        try:
            with yt_dlp.YoutubeDL(full_opts) as ydl:
                # process=False：只取 metadata（live_status/title/upload_date），
                # 不做格式選擇——帶 cookies 時登入用 client 回傳的格式會讓
                # 預設格式選擇器丟「Requested format is not available」。
                meta = ydl.extract_info(
                    f"https://www.youtube.com/watch?v={vid}", download=False, process=False
                )
        except Exception as e:
            log(f"[warn] 取 {vid} metadata 失敗：{e}（跳過此候選）")
            continue

        status = meta.get("live_status")
        if status in ("is_live", "is_upcoming"):
            log(f"{vid} 仍在直播/未開始（{status}）→ 跳過")
            continue

        upload = meta.get("upload_date") or ""
        published = ""
        if len(upload) == 8:
            published = f"{upload[:4]}-{upload[4:6]}-{upload[6:]}"
        return {
            "video_id": vid,
            "title": (meta.get("title") or "").strip(),
            "url": f"https://www.youtube.com/watch?v={vid}",
            "published": published,
            "channel": meta.get("uploader") or YT_CHANNEL_NAME,
        }

    log("候選都還在直播中或無法取得 → 略過")
    return None


# ── 2a. 字幕路徑 ───────────────────────────────────────────────────
def parse_vtt(text: str) -> str:
    """VTT → 純文字（SPEC §12）。"""
    out = []
    prev = None
    for raw in text.splitlines():
        line = raw.strip()
        if not line:
            continue
        if line == "WEBVTT" or "-->" in line:
            continue
        if line.isdigit():
            continue
        if line.startswith(("NOTE", "Kind:", "Language:")):
            continue
        line = re.sub(r"<[^>]+>", "", line)  # 移除 <c>/行內時間標籤等
        line = html.unescape(line).strip()
        if not line:
            continue
        if line == prev:  # 去連續重複行
            continue
        out.append(line)
        prev = line
    return "\n".join(out)


def fetch_subtitles(video_id: str) -> str:
    """下載字幕並回傳純文字；失敗或無字幕回 ""。"""
    try:
        import yt_dlp
    except ImportError:
        return ""

    with tempfile.TemporaryDirectory() as tmp:
        opts = base_ydl_opts()
        opts.update({
            "writesubtitles": True,
            "writeautomaticsub": True,
            "subtitlesformat": "vtt",
            "subtitleslangs": YT_SUBTITLE_LANGS,
            "outtmpl": os.path.join(tmp, "%(id)s.%(ext)s"),
            # 帶 cookies 時預設格式選擇器會丟錯；字幕下載不需要影片格式，
            # 忽略「無可用格式」讓字幕仍能寫出。
            "ignore_no_formats_error": True,
        })
        try:
            with yt_dlp.YoutubeDL(opts) as ydl:
                ydl.download([f"https://www.youtube.com/watch?v={video_id}"])
        except Exception as e:
            log(f"[warn] 字幕下載失敗：{e}")
            return ""

        # 依偏好語言順序挑檔
        for lang in YT_SUBTITLE_LANGS:
            cand = Path(tmp) / f"{video_id}.{lang}.vtt"
            if cand.exists():
                txt = parse_vtt(cand.read_text(encoding="utf-8", errors="ignore"))
                if txt:
                    log(f"取得字幕（{lang}），{len(txt)} 字")
                    return txt
        # 後援：任何 .vtt
        vtts = sorted(Path(tmp).glob(f"{video_id}*.vtt"))
        if vtts:
            txt = parse_vtt(vtts[0].read_text(encoding="utf-8", errors="ignore"))
            if txt:
                log(f"取得字幕（{vtts[0].name}），{len(txt)} 字")
                return txt
    return ""


# ── 2b. Whisper 路徑 ───────────────────────────────────────────────
def download_audio(video_id: str, tmp: str) -> str | None:
    """下載音訊轉 16kHz 單聲道 mp3，回傳檔案路徑或 None。"""
    try:
        import yt_dlp
    except ImportError:
        return None
    opts = base_ydl_opts()
    opts.update({
        "skip_download": False,
        "format": "bestaudio/best",
        "outtmpl": os.path.join(tmp, "%(id)s.%(ext)s"),
        "postprocessors": [{
            "key": "FFmpegExtractAudio",
            "preferredcodec": "mp3",
        }],
        "postprocessor_args": ["-ar", "16000", "-ac", "1"],
    })
    try:
        with yt_dlp.YoutubeDL(opts) as ydl:
            ydl.download([f"https://www.youtube.com/watch?v={video_id}"])
    except Exception as e:
        log(f"[warn] 音訊下載失敗：{e}")
        return None
    mp3 = os.path.join(tmp, f"{video_id}.mp3")
    return mp3 if os.path.exists(mp3) else None


def _whisper_one(client, path: str) -> str:
    with open(path, "rb") as f:
        resp = client.audio.transcriptions.create(
            file=(os.path.basename(path), f.read()),
            model=YT_GROQ_MODEL,
            language=YT_WHISPER_LANGUAGE,
            response_format="text",
        )
    # response_format="text" → SDK 回傳純字串（或具 .text 屬性）
    return resp if isinstance(resp, str) else getattr(resp, "text", str(resp))


def transcribe_whisper(video_id: str) -> str:
    if not GROQ_API_KEY:
        log("[info] GROQ_API_KEY 未設定 — 無法用 Whisper")
        return ""
    try:
        from groq import Groq
    except ImportError:
        log("[warn] groq 套件未安裝 — 無法用 Whisper")
        return ""

    with tempfile.TemporaryDirectory() as tmp:
        mp3 = download_audio(video_id, tmp)
        if not mp3:
            return ""
        client = Groq(api_key=GROQ_API_KEY)
        size_mb = os.path.getsize(mp3) / (1024 * 1024)
        try:
            if size_mb <= YT_AUDIO_SEGMENT_MB:
                log(f"Whisper 轉錄（{size_mb:.1f}MB，單檔）")
                return _whisper_one(client, mp3).strip()

            # 超大檔 → ffmpeg 切段逐段轉錄串接（§6.2）
            log(f"音訊 {size_mb:.1f}MB > {YT_AUDIO_SEGMENT_MB}MB，切段轉錄")
            seg_tmpl = os.path.join(tmp, "seg%03d.mp3")
            subprocess.run(
                ["ffmpeg", "-y", "-i", mp3, "-f", "segment",
                 "-segment_time", str(YT_AUDIO_SEGMENT_SECONDS), "-c", "copy", seg_tmpl],
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


# ── 3. 取逐字稿（字幕優先＋Whisper 退回）───────────────────────────
def get_transcript(video_id: str) -> tuple[str, str]:
    """回傳 (transcript, source)；source 為「字幕」「Whisper」或 ""。"""
    if YT_PREFER_SUBTITLES:
        subs = fetch_subtitles(video_id)
        if len(subs) >= YT_SUBTITLE_MIN_CHARS:
            return subs, "字幕"
        if subs:
            log(f"字幕僅 {len(subs)} 字（< {YT_SUBTITLE_MIN_CHARS}）→ 退回 Whisper")
        else:
            log("無字幕 → 退回 Whisper")
    whisper = transcribe_whisper(video_id)
    if whisper:
        return whisper, "Whisper"
    return "", ""


# ── 4. Claude 摘要 ─────────────────────────────────────────────────
SYSTEM_PROMPT = (
    "你是一位專業的財經內容編輯。使用者會給你一段直播逐字稿（可能含口語、"
    "語助詞、辨識錯誤、廣告或開場閒聊）。請忠實整理成結構清楚、可在一分鐘內"
    "讀完重點的筆記，用繁體中文書寫。只根據逐字稿內容，不要自行補充或臆測；"
    "辨識明顯有誤處可合理修正。這是對他人影片內容的摘要，不是投資建議——"
    "描述時用「主講人認為…」這類語氣。"
)

FORMAT_INSTRUCTION = (
    "請輸出以下 Markdown 結構（不要加 ``` 圍欄、不要多餘前言）：\n\n"
    "## 一句話總結\n"
    "## 本集重點\n（5–8 條，先講結論）\n"
    "## 提到的數據與標的\n（指數/利率/商品/個股/數字，沒有寫「—」）\n"
    "## 主講人的觀點與風險提醒\n"
    "---\n"
    "*本筆記為影片內容摘要，非投資建議。*"
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
        if len(transcript) <= YT_SUMMARY_SINGLE_PASS_MAX:
            user = f"影片標題：{title}\n\n逐字稿：\n{transcript}\n\n{FORMAT_INSTRUCTION}"
            return _claude(client, SYSTEM_PROMPT, user)

        # map-reduce（§6.4）
        log(f"逐字稿 {len(transcript)} 字 > {YT_SUMMARY_SINGLE_PASS_MAX} → map-reduce")
        chunks = [
            transcript[i:i + YT_SUMMARY_CHUNK_CHARS]
            for i in range(0, len(transcript), YT_SUMMARY_CHUNK_CHARS)
        ]
        partials = []
        for i, ch in enumerate(chunks):
            log(f"  條列第 {i+1}/{len(chunks)} 段")
            user = (
                f"以下是直播逐字稿的第 {i+1}/{len(chunks)} 段，請條列此段重點"
                f"（保留數據、標的與時間相關資訊，繁體中文）：\n\n{ch}"
            )
            partials.append(_claude(client, SYSTEM_PROMPT, user, max_tokens=1500))
        merged = "\n\n".join(partials)
        user = (
            f"影片標題：{title}\n\n以下是各段重點條列，請彙整成最終筆記：\n\n"
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
    data["youtube_brief"] = brief
    with open(DATA_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    log(f"✅ data.json 寫入 youtube_brief（{brief.get('title','')[:30]}）")


# ── main ───────────────────────────────────────────────────────────
def main() -> None:
    force = "--force" in sys.argv
    log("解析最新已結束直播 …")
    info = resolve_latest_finished()
    if not info:
        return  # 找不到 → 不動 data.json（保留前次或留空）

    vid = info["video_id"]
    state = load_json(STATE_PATH)

    if not force and vid in state:
        log(f"{vid} 已在快取 → 重用（不重抓/重摘要）")
        write_brief_into_data(state[vid])
        return

    transcript, source = get_transcript(vid)
    if not transcript:
        log("[warn] 取不到逐字稿（字幕無＋Whisper 失敗/關閉）→ 跳過")
        return

    summary_md = summarize(transcript, info["title"])
    if not summary_md:
        log("[warn] 摘要為空 → 跳過")
        return

    brief = {
        "video_id": vid,
        "title": info["title"],
        "url": info["url"],
        "published": info["published"],
        "channel": info["channel"],
        "transcript_source": source,
        "summary_md": summary_md,
    }

    # 更新快取（保留 90 筆上限避免無限成長）
    state[vid] = brief
    if len(state) > 90:
        for k in list(state.keys())[:-90]:
            state.pop(k, None)
    with open(STATE_PATH, "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=2)

    write_brief_into_data(brief)
    log(f"完成（來源：{source}）")


if __name__ == "__main__":
    main()
