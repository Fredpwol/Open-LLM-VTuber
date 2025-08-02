import asyncio
import sys
import os
from loguru import logger

project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, project_root)

from src.open_llm_vtuber.live.pumpfun_live import PumpFunLivePlatform
from src.open_llm_vtuber.config_manager.utils import read_yaml, validate_config

async def main():
    logger.info("Starting Pump.fun Live client")
    config_path = os.path.join(project_root, "conf.yaml")
    config_data = read_yaml(config_path)
    config = validate_config(config_data)
    pumpfun_config = config.live_config.pumpfun_live
    platform = PumpFunLivePlatform(pumpfun_config.model_dump())
    await platform.run()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Shutting down Pump.fun Live client") 
