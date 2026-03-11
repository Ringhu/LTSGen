# ts_cap/wrappers/registry.py
from .base import BaseWrapper, WrapperConfig
from .ltsf_wrappers import LTSFWrapper
from .nab_wrapper import NABWrapper
from .ucr_wrapper import UCRWrapper
from .fred_wrapper import FREDWrapper


def get_wrapper(dataset: str, input_path: str, **kwargs) -> BaseWrapper:
    cfg = WrapperConfig(
        input_path=input_path,
        dataset_name=dataset,
        task=kwargs.get("task", "forecasting"),

        time_col=kwargs.get("time_col"),
        series_cols=kwargs.get("series_cols"),
        target_col=kwargs.get("target_col"),
        target_series_index=kwargs.get("target_series_index"),

        window_mode=kwargs.get("window_mode", "sliding"),
        window_len=int(kwargs.get("window_len", 512)),
        stride=int(kwargs.get("stride", 256)),
        max_windows=kwargs.get("max_windows"),

        ucr_name=kwargs.get("ucr_name"),
        ucr_split=kwargs.get("ucr_split", "test"),
        ucr_label_semantics=kwargs.get("ucr_label_semantics", "readme"),

        llm_enabled=kwargs.get("llm_enabled", False),
    )

    ds = (dataset or "").lower()

    if ds == "fred":
        return FREDWrapper(cfg)

    if ds == "ucr2018":
        return UCRWrapper(cfg)

    if ds == "nab":
        return NABWrapper(cfg)

    return LTSFWrapper(cfg)
