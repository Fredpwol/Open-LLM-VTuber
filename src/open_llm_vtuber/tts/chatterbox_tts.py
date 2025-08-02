import os
from loguru import logger
from .tts_interface import TTSInterface

class TTSEngine(TTSInterface):
    def __init__(self, model_path: str = None, voice: str = "default", exaggeration: float = 0.5, cfg: float = 0.3, seed: int = 0, temperature: float = 1.0, output_format: str = "wav", device: str = "cuda", audio_prompt_path: str = None):
        self.voice = voice
        self.exaggeration = exaggeration
        self.cfg = cfg
        self.output_format = output_format
        self.device = device
        self.audio_prompt_path = audio_prompt_path
        self.new_audio_dir = "cache"
        self.file_extension = output_format
        if not os.path.exists(self.new_audio_dir):
            os.makedirs(self.new_audio_dir)
        # Load Chatterbox model
        try:
            from chatterbox.tts import ChatterboxTTS
            self.model = ChatterboxTTS.from_pretrained(device=self.device)
            logger.info(f"Chatterbox TTS model loaded on device: {self.device}")
        except Exception as e:
            import traceback
            print(traceback.format_exc())
            logger.critical(f"Failed to load Chatterbox TTS: {e}")
            self.model = None

    def generate_audio(self, text, file_name_no_ext=None):
        if self.model is None:
            logger.critical("Chatterbox TTS model is not loaded.")
            return None
        file_name = self.generate_cache_file_name(file_name_no_ext, self.file_extension)
        try:
            import torchaudio as ta
            # Prepare kwargs for Chatterbox
            kwargs = {
                "exaggeration": self.exaggeration,
                "cfg_weight": self.cfg,
            }
            if self.audio_prompt_path:
                kwargs["audio_prompt_path"] = self.audio_prompt_path
            wav = self.model.generate(text, **kwargs)
            ta.save(file_name, wav, self.model.sr)
            logger.info(f"Chatterbox TTS audio saved to {file_name}")
            return file_name
        except Exception as e:
            logger.critical(f"Chatterbox TTS failed: {e}")
            return None 
