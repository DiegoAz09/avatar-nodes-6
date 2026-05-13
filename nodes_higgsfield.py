import io
import os
import time
import traceback

import numpy as np
import requests
from PIL import Image


BASE_URL = "https://cloud.higgsfield.ai"
POLL_INTERVAL = 5
MAX_POLLS = 120


class HiggsfieldAvatarNode:
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "image": ("IMAGE",),
                "audio_path": ("STRING", {"forceInput": True}),
            },
            "optional": {
                "api_key": ("STRING", {"default": "", "multiline": False}),
                "prompt": (
                    "STRING",
                    {
                        "default": "Professional presenter, looking directly at camera, natural movements",
                        "multiline": True,
                    },
                ),
                "quality": (["mid", "high"], {"default": "mid"}),
                "duration": ("INT", {"default": 10, "min": 5, "max": 15}),
            },
        }

    RETURN_TYPES = ("STRING",)
    RETURN_NAMES = ("video_url",)
    FUNCTION = "generate_avatar"
    CATEGORY = "AvatarCreator"

    def _upload_file(self, data_bytes, filename, content_type):
        """Upload file to a public host, trying multiple services as fallbacks."""
        services = [
            ("file.io", self._upload_fileio),
            ("0x0.st", self._upload_0x0),
            ("transfer.sh", self._upload_transfersh),
        ]
        for name, fn in services:
            try:
                print(f"[Higgsfield] Uploading {filename} ({len(data_bytes)} bytes) via {name}...")
                url = fn(data_bytes, filename, content_type)
                print(f"[Higgsfield] Uploaded via {name}: {url}")
                return url
            except Exception as e:
                print(f"[Higgsfield] {name} failed: {e}")
        raise RuntimeError("All file upload services failed")

    def _upload_fileio(self, data_bytes, filename, content_type):
        resp = requests.post(
            "https://file.io/?expires=1d",
            files={"file": (filename, data_bytes, content_type)},
            timeout=60,
        )
        resp.raise_for_status()
        data = resp.json()
        if not data.get("success"):
            raise RuntimeError(f"file.io error: {data}")
        return data["link"]

    def _upload_0x0(self, data_bytes, filename, content_type):
        resp = requests.post(
            "https://0x0.st",
            files={"-": (filename, data_bytes, content_type)},
            timeout=60,
        )
        resp.raise_for_status()
        return resp.text.strip()

    def _upload_transfersh(self, data_bytes, filename, content_type):
        resp = requests.put(
            f"https://transfer.sh/{filename}",
            data=data_bytes,
            headers={"Content-Type": content_type, "Max-Days": "1"},
            timeout=120,
        )
        resp.raise_for_status()
        return resp.text.strip()

    def generate_avatar(self, image, audio_path, api_key="",
                        prompt="Professional presenter, looking directly at camera, natural movements",
                        quality="mid", duration=10):
        try:
            api_key = api_key or os.environ.get("HIGGSFIELD_API_KEY", "")
            print(f"[Higgsfield] API key present: {bool(api_key)}")
            print(f"[Higgsfield] Audio path: {audio_path}")
            print(f"[Higgsfield] Audio file exists: {os.path.isfile(audio_path) if audio_path else False}")

            if not api_key:
                raise ValueError("Higgsfield API key required. Set HIGGSFIELD_API_KEY secret.")
            if not audio_path or not os.path.isfile(audio_path):
                raise ValueError(f"Audio file not found: '{audio_path}'")

            # ── Convert image tensor → JPEG bytes ────────────────────────────
            print("[Higgsfield] Converting image...")
            img_np = (image[0].cpu().numpy() * 255).astype(np.uint8)
            img_pil = Image.fromarray(img_np)
            buf = io.BytesIO()
            img_pil.save(buf, format="JPEG", quality=95)
            image_bytes = buf.getvalue()
            print(f"[Higgsfield] Image size: {len(image_bytes)} bytes")

            # ── Read WAV audio ────────────────────────────────────────────────
            with open(audio_path, "rb") as f:
                audio_bytes = f.read()
            print(f"[Higgsfield] Audio size: {len(audio_bytes)} bytes")

            # ── Upload files to public host ───────────────────────────────────
            image_url = self._upload_file(image_bytes, "expert.jpg", "image/jpeg")
            audio_url = self._upload_file(audio_bytes, "voice.wav", "audio/wav")

            # ── Submit generation ─────────────────────────────────────────────
            headers = {
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            }
            payload = {
                "input_image": image_url,
                "input_audio": audio_url,
                "prompt": prompt,
                "quality": quality,
                "duration": int(duration),
            }
            print(f"[Higgsfield] Submitting to {BASE_URL}/v1/speak/higgsfield ...")
            print(f"[Higgsfield] Payload: {payload}")

            resp = requests.post(
                f"{BASE_URL}/v1/speak/higgsfield",
                json=payload,
                headers=headers,
                timeout=60,
            )
            print(f"[Higgsfield] Response status: {resp.status_code}")
            print(f"[Higgsfield] Response body: {resp.text[:500]}")
            resp.raise_for_status()
            result = resp.json()

            request_id = (
                result.get("id")
                or result.get("request_id")
                or result.get("generation_id")
            )
            print(f"[Higgsfield] Generation ID: {request_id}")

            # ── Poll until complete ───────────────────────────────────────────
            for attempt in range(MAX_POLLS):
                time.sleep(POLL_INTERVAL)
                poll = requests.get(
                    f"{BASE_URL}/v1/generations/{request_id}",
                    headers={"Authorization": f"Bearer {api_key}"},
                    timeout=30,
                )
                print(f"[Higgsfield] Poll {attempt+1}: {poll.status_code} — {poll.text[:200]}")
                poll.raise_for_status()
                data = poll.json()
                status = str(data.get("status", "")).lower()

                if status in ("completed", "done", "succeeded", "success"):
                    video_url = (
                        data.get("video_url")
                        or data.get("output_url")
                        or data.get("url")
                        or (data.get("result") or {}).get("url")
                    )
                    print(f"[Higgsfield] Done! Video URL: {video_url}")
                    return (video_url,)

                if status in ("failed", "error", "cancelled"):
                    raise RuntimeError(f"Higgsfield generation failed: {data}")

            raise TimeoutError("Higgsfield generation did not complete within 10 minutes.")

        except Exception as e:
            print(f"[Higgsfield ERROR] {type(e).__name__}: {e}")
            print(traceback.format_exc())
            raise


NODE_CLASS_MAPPINGS = {"HiggsfieldAvatarNode": HiggsfieldAvatarNode}
NODE_DISPLAY_NAME_MAPPINGS = {"HiggsfieldAvatarNode": "Higgsfield Avatar"}
