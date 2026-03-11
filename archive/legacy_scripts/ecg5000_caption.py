# ecg5000_caption.py

import numpy as np
import pandas as pd

from ts_classification_caption import run_ts_classification_caption_pipeline
from ts_dataset_config import DATASET_VAR_INFO


def load_ecg5000_from_tsv(
    train_path: str,
    test_path: str,
    label_first: bool = True,
) -> tuple[np.ndarray, np.ndarray]:
    """
    读取 UCR ECG5000 TRAIN/TEST tsv 文件，返回 X, y.

    - 如果 label_first=True：假定第 1 列是标签，其余是 140 个时间步；
    - label_first=False：假定最后一列是标签，其前面全是时间步。
    """
    def _load_one(path: str):
        df = pd.read_csv(path, sep=r"\s+|\t+|,", header=None, engine="python")
        arr = df.to_numpy(dtype=float)
        if label_first:
            y = arr[:, 0].astype(int)
            X = arr[:, 1:]
        else:
            y = arr[:, -1].astype(int)
            X = arr[:, :-1]
        return X, y

    X_tr, y_tr = _load_one(train_path)
    X_te, y_te = _load_one(test_path)

    X = np.concatenate([X_tr, X_te], axis=0)  # (N, 140)
    y = np.concatenate([y_tr, y_te], axis=0)  # (N,)
    return X, y


def main():
    # 1) 读数据（根据你手里的版本设置 label_first=True/False）
    X, y = load_ecg5000_from_tsv(
        train_path="/cluster/home/user1/hulining/TSDataset/LTSGen/dataset/classification/UCRArchive_2018/ECG5000/ECG5000_TRAIN.tsv",
        test_path="/cluster/home/user1/hulining/TSDataset/LTSGen/dataset/classification/UCRArchive_2018/ECG5000/ECG5000_TEST.tsv",
        label_first=True,      # 如果你发现不对，就改成 False
    )

    # 2) 变成 (N, L, C) 形式：单变量，C=1
    X = X[:, :, None]   # (N, 140, 1)
    var_names = ["ecg"]

    # 3) 可选：类别名映射
    class_name_map = {
        1: "正常心搏",
        2: "R 峰异常",
        3: "心房异常",
        4: "室性早搏",
        5: "其他异常",
    }

    # 4) 跑通用分类 caption pipeline
    run_ts_classification_caption_pipeline(
        X=X,
        y=y,
        var_names=var_names,
        dataset_name="ECG5000",
        target_col="ecg",
        output_jsonl="ecg5000_captions.jsonl",
        class_name_map=class_name_map,
        max_samples=None,   # 或者先设 100，看看效果
    )


if __name__ == "__main__":
    main()
