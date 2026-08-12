from typing import Dict, Any, Optional

class SlackEvent(dict):
    @staticmethod
    def from_payload(payload: Dict[str, Any]) -> Optional["SlackEvent"]:
        try:
            event = SlackEvent(payload)
            return event
        except KeyError:
            return None
    
    @property
    def text(self) -> str:
        if self.get("event", {}).get("channel_type") == "im":
            elements = self["event"]["blocks"][0]["elements"][0]["elements"]
            for el in elements:
                if el.get("type") == "text":
                    return el.get("text", "")
                
        if self.get("event",{}).get("channel_type") == "channel":
            elements = self["event"]["blocks"][0]["elements"][0]["elements"]
            text_result = next((el["text"] for el in elements if el["type"] == "text"), "")
            return text_result


        return "" 

    
    @property
    def user_id(self) -> Optional[str]:
        return self.get("event", {}).get("user","")
    
    @property
    def channel_id(self) -> Optional[str]:
        return self.get("event", {}).get("channel","")
    
    @property
    def type(self) -> str:
        """ message对应私聊，app_mention对应频道at """
        return self.get("event", {}).get("channel_type", "")
    
    @property
    def message_id(self) -> str:
        return self.get("event_id","")
    
    @property
    def pic_url(self) -> str:
        """提取 Slack 事件中的图片 URL"""
        files = self.get("event", {}).get("files", [])
        if files:
            return files[0].get("url_private", "")
        return ""
        
    
    @property
    def sender_name(self) -> str:
        return self.get("event", {}).get("user","")
    
    def __getattr__(self, key: str) -> Optional[Any]:
        return self.get(key)

    def __setattr__(self, key: str, value: Any) -> None:
        self[key] = value

    def __repr__(self) -> str:
        return f"<SlackEvent {super().__repr__()}>"
