from pydantic import Field
from typing import Dict, ClassVar, List
from .i18n import I18nMixin, Description


class BiliBiliLiveConfig(I18nMixin):
    """Configuration for BiliBili Live platform."""

    room_ids: List[int] = Field([], alias="room_ids")
    sessdata: str = Field("", alias="sessdata")

    DESCRIPTIONS: ClassVar[Dict[str, Description]] = {
        "room_ids": Description(
            en="List of BiliBili live room IDs to monitor", zh="要监控的B站直播间ID列表"
        ),
        "sessdata": Description(
            en="SESSDATA cookie value for authenticated requests (optional)",
            zh="用于认证请求的SESSDATA cookie值（可选）",
        ),
    }


class PumpFunLiveConfig(I18nMixin):
    """Configuration for Pump.fun Live integration."""
    room_id: str = ""
    limit: int = 20
    DESCRIPTIONS: ClassVar[Dict[str, Description]] = {
        "room_id": Description(en="Pump.fun room ID", zh="Pump.fun 房间ID"),
        "limit": Description(en="Number of messages to fetch per request", zh="每次请求获取的消息数量"),
    }


class LiveConfig(I18nMixin):
    """Configuration for live streaming platforms integration."""

    bilibili_live: BiliBiliLiveConfig = Field(
        BiliBiliLiveConfig(), alias="bilibili_live"
    )
    pumpfun_live: PumpFunLiveConfig = Field(default_factory=PumpFunLiveConfig, alias="pumpfun_live")

    DESCRIPTIONS: ClassVar[Dict[str, Description]] = {
        "bilibili_live": Description(
            en="Configuration for BiliBili Live platform", zh="B站直播平台配置"
        ),
    }
