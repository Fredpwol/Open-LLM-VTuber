import requests
import os
from resemble import Resemble
from .tts_interface import TTSInterface
from loguru import logger

class ResembleTTS(TTSInterface):
    def __init__(self, api_key, voice_uuid, project_uuid=None):
        self.api_key = api_key or os.environ.get("RESEMBLE_API_KEY")
        self.voice_uuid = voice_uuid
        self.project_uuid = project_uuid or os.environ.get("RESEMBLE_PROJECT_UUID")
        Resemble.api_key(self.api_key)

    def generate_audio(self, text: str, file_name_no_ext=None) -> str:
        output_path = self.generate_cache_file_name(file_name_no_ext, file_extension="wav")
        logger.info(f"ResembleTTS: Generating audio for text: {text}")
        # Synthesize using the resemble SDK
        response = Resemble.v2.clips.create_sync(
            project_uuid=self.project_uuid,
            voice_uuid=self.voice_uuid,
            body=text,
        )
        audio_url = response['item']["audio_src"]  # This is a direct URL to the audio file
        r = requests.get(audio_url, stream=True)
        r.raise_for_status()
        with open(output_path, "wb") as f:
            for chunk in r.iter_content(chunk_size=8192):
                if chunk:
                    f.write(chunk)
        logger.info(f"ResembleTTS: Audio downloaded to {output_path}")
        return output_path 
