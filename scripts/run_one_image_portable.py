import importlib.util
import os
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent.parent
SERVICE_SCRIPT = BASE_DIR / "service" / "tomato_dl_merge_service.py"
IMAGE_PATH = Path(r"C:\Users\Administrator\AppData\Local\Temp\0099.jpg")
QUESTION = "请判断这张番茄图片当前成熟状态，并给出是否建议采摘和后续管理建议。"

os.environ.setdefault("TOMATO_MODEL_DIR", str(BASE_DIR / "models" / "merge"))
os.environ.setdefault("TOMATO_YOLO_WEIGHTS", str(BASE_DIR / "models" / "yolo" / "yolo11n_best.pt"))
os.environ.setdefault("TOMATO_HF_HOME", str(BASE_DIR / "runtime" / "hf-cache"))
os.environ.setdefault("TOMATO_HF_MODULES_CACHE", str(BASE_DIR / "runtime" / "hf-modules"))
os.environ.setdefault("YOLO_CONFIG_DIR", str(BASE_DIR / "runtime" / "yolo-config"))


def load_module():
    spec = importlib.util.spec_from_file_location("tomato_portable_service", SERVICE_SCRIPT)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def main():
    module = load_module()
    image_summary = module.analyze_image(IMAGE_PATH)
    detection_summary = module.detector.predict(IMAGE_PATH)
    prompt = module.build_merge_prompt(QUESTION, IMAGE_PATH, image_summary, detection_summary)
    answer = module.expert_model.chat(prompt)

    print("=== 图片路径 ===")
    print(IMAGE_PATH)
    print()
    print("=== 深度学习模型检测统计 ===")
    print(detection_summary["counts"])
    print()
    print("=== 深度学习模型检测详情 ===")
    if detection_summary["detections"]:
        for item in detection_summary["detections"]:
            print(item)
    else:
        print("未检测到明确目标")
    print()
    print("=== 图片摘要 ===")
    print(image_summary)
    print()
    print("=== merge 模型回答 ===")
    print(answer)


if __name__ == "__main__":
    main()
