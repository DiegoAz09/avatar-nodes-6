import traceback

print("[AvatarCreator] Initializing...")

try:
    from .nodes_elevenlabs import NODE_CLASS_MAPPINGS as EL_NODES, NODE_DISPLAY_NAME_MAPPINGS as EL_NAMES
    print(f"[AvatarCreator] ElevenLabs OK: {list(EL_NODES.keys())}")
except Exception as e:
    print(f"[AvatarCreator] ERROR loading ElevenLabs: {e}")
    traceback.print_exc()
    EL_NODES = {}
    EL_NAMES = {}

try:
    from .nodes_higgsfield import NODE_CLASS_MAPPINGS as HF_NODES, NODE_DISPLAY_NAME_MAPPINGS as HF_NAMES
    print(f"[AvatarCreator] Higgsfield OK: {list(HF_NODES.keys())}")
except Exception as e:
    print(f"[AvatarCreator] ERROR loading Higgsfield: {e}")
    traceback.print_exc()
    HF_NODES = {}
    HF_NAMES = {}

NODE_CLASS_MAPPINGS = {**EL_NODES, **HF_NODES}
NODE_DISPLAY_NAME_MAPPINGS = {**EL_NAMES, **HF_NAMES}

__all__ = ["NODE_CLASS_MAPPINGS", "NODE_DISPLAY_NAME_MAPPINGS"]
print(f"[AvatarCreator] Ready. Nodes registered: {list(NODE_CLASS_MAPPINGS.keys())}")
