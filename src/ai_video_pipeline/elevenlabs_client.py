#!/usr/bin/env python
"""Minimal ElevenLabs REST client: text-to-speech synthesis and voice lookup.

Requires ELEVENLABS_API_KEY in the environment. No SDK dependency.
"""
from __future__ import annotations

import os
from pathlib import Path

import requests

BASE_URL = "https://api.elevenlabs.io"
DEFAULT_MODEL = "eleven_multilingual_v2"


class ElevenLabsError(RuntimeError):
    pass


def _headers(json_body: bool = True) -> dict:
    key = os.environ.get("ELEVENLABS_API_KEY")
    if not key:
        raise ElevenLabsError("ELEVENLABS_API_KEY is not set")
    headers = {"xi-api-key": key}
    if json_body:
        headers["Content-Type"] = "application/json"
    return headers


def list_voices() -> list[dict]:
    resp = requests.get(f"{BASE_URL}/v1/voices", headers=_headers(json_body=False), timeout=30)
    if resp.status_code >= 400:
        raise ElevenLabsError(f"list_voices failed ({resp.status_code}): {resp.text[:500]}")
    return resp.json().get("voices", [])


def synthesize(
    text: str,
    voice_id: str,
    dest: Path,
    model_id: str = DEFAULT_MODEL,
    stability: float = 0.5,
    similarity_boost: float = 0.75,
) -> Path:
    """Synthesize `text` with `voice_id` and write MP3 bytes to `dest`."""
    body = {
        "text": text,
        "model_id": model_id,
        "voice_settings": {"stability": stability, "similarity_boost": similarity_boost},
    }
    resp = requests.post(
        f"{BASE_URL}/v1/text-to-speech/{voice_id}", headers=_headers(), json=body, timeout=60
    )
    if resp.status_code >= 400:
        raise ElevenLabsError(f"synthesis failed ({resp.status_code}): {resp.text[:500]}")
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_bytes(resp.content)
    return dest
