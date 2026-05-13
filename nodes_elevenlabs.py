import os
import wave
import requests
import tempfile


class ElevenLabsTTSNode:
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                # forceInput so this always appears as a connectable input slot
                "text": ("STRING", {"forceInput": True}),
            },
            "optional": {
                "api_key": ("STRING", {"default": "", "multiline": False}),
                "voice_id": ("STRING", {"default": "vDZzh7TACla2mhsWlFBx", "multiline": False}),
                "model_id": (
                    ["eleven_multilingual_v2", "eleven_monolingual_v1", "eleven_turbo_v2"],
                    {"default": "eleven_multilingual_v2"},
                ),
                "stability": ("FLOAT", {"default": 0.5, "min": 0.0, "max": 1.0, "step": 0.05}),
                "similarity_boost": ("FLOAT", {"default": 0.75, "min": 0.0, "max": 1.0, "step": 0.05}),
            },
        }

    RETURN_TYPES = ("STRING",)
    RETURN_NAMES = ("audio_path",)
    FUNCTION = "generate_tts"
    CATEGORY = "AvatarCreator"

    def generate_tts(self, text, api_key="", voice_id="vDZzh7TACla2mhsWlFBx",
                     model_id="eleven_multilingual_v2", stability=0.5, similarity_boost=0.75):
        api_key = api_key or os.environ.get("ELEVENLABS_API_KEY", "")
        voice_id = voice_id or os.environ.get("ELEVENLABS_VOICE_ID", "vDZzh7TACla2mhsWlFBx")

        if not api_key:
            raise ValueError("ElevenLabs API key is required. Set ELEVENLABS_API_KEY secret or pass api_key.")
        if not text.strip():
            raise ValueError("Text cannot be empty.")

        url = f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}"
        headers = {
            "Content-Type": "application/json",
            "xi-api-key": api_key,
        }
        # Request PCM 22050Hz so we can wrap it in a standard WAV container
        # (Higgsfield requires WAV audio)
        params = {"output_format": "pcm_22050"}
        payload = {
            "text": text,
            "model_id": model_id,
            "voice_settings": {
                "stability": stability,
                "similarity_boost": similarity_boost,
            },
        }

        resp = requests.post(url, json=payload, headers=headers, params=params, timeout=120)
        resp.raise_for_status()

        # Wrap raw PCM in a proper WAV container
        pcm_data = resp.content
        tmp = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
        with wave.open(tmp.name, "wb") as wf:
            wf.setnchannels(1)   # mono
            wf.setsampwidth(2)   # 16-bit
            wf.setframerate(22050)
            wf.writeframes(pcm_data)

        print(f"[ElevenLabs TTS] Audio saved to: {tmp.name} ({len(pcm_data)} PCM bytes)")
        return (tmp.name,)


NODE_CLASS_MAPPINGS = {"ElevenLabsTTSNode": ElevenLabsTTSNode}
NODE_DISPLAY_NAME_MAPPINGS = {"ElevenLabsTTSNode": "ElevenLabs TTS"}
