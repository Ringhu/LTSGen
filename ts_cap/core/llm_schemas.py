# ts_cap/core/llm_schemas.py
from typing import List, Optional, Any
from pydantic import BaseModel, Field

class CaptionContent(BaseModel):
    zh: str = Field(..., description="中文描述")
    en: str = Field(..., description="English description")

class LocalSegment(BaseModel):
    # 我们要求 LLM 返回 segment_id，用来和 Python 端的索引对齐
    segment_id: int = Field(..., description="The ID of the segment provided in the prompt")
    description: CaptionContent = Field(..., description="Description")
    
    # start/end/type 可选，因为我们会用 Python 算好的覆盖它
    start: Optional[int] = Field(default=None)
    end: Optional[int] = Field(default=None)
    type: Optional[str] = Field(default=None)

class HierarchicalCaption(BaseModel):
    global_summary: CaptionContent = Field(..., description="Statistical summary")
    domain_summary: Optional[CaptionContent] = Field(default=None, description="Domain context summary")
    local_captions: List[LocalSegment] = Field(..., description="List of local events matching the input IDs")

    def to_record_dict(self):
        # 这里的逻辑稍后会在 samples.py 里被“增强版”逻辑替代
        # 所以这里只做最基本的序列化
        domain_dict = {"zh": "", "en": ""}
        if self.domain_summary:
            domain_dict = {"zh": self.domain_summary.zh, "en": self.domain_summary.en}

        return {
            "global": {"zh": self.global_summary.zh, "en": self.global_summary.en},
            "domain_integrated": domain_dict,
            # Local 会在 samples.py 里通过 ID 合并，这里先返回原始列表
            "local_raw": self.local_captions 
        }