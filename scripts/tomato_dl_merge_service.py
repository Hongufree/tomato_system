import os
import sys
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent.parent
MODELS_DIR = BASE_DIR / "models"
RUNTIME_DIR = BASE_DIR / "runtime"
YOLO_RUNTIME_DIR = RUNTIME_DIR / "ultralytics_runtime"

MERGE_MODEL_DIR = Path(os.getenv("TOMATO_MODEL_DIR", str(MODELS_DIR / "merge"))).expanduser()
YOLO_WEIGHTS = Path(os.getenv("TOMATO_YOLO_WEIGHTS", str(MODELS_DIR / "yolo" / "yolo11n_best.pt"))).expanduser()
HF_HOME = Path(os.getenv("TOMATO_HF_HOME", str(RUNTIME_DIR / "hf-cache"))).expanduser()
HF_MODULES_CACHE = Path(os.getenv("TOMATO_HF_MODULES_CACHE", str(RUNTIME_DIR / "hf-modules"))).expanduser()
YOLO_CONFIG_DIR = Path(os.getenv("YOLO_CONFIG_DIR", str(RUNTIME_DIR / "yolo-config"))).expanduser()

HF_HOME.mkdir(parents=True, exist_ok=True)
HF_MODULES_CACHE.mkdir(parents=True, exist_ok=True)
YOLO_CONFIG_DIR.mkdir(parents=True, exist_ok=True)
os.environ["HF_HOME"] = str(HF_HOME)
os.environ["TRANSFORMERS_CACHE"] = str(HF_HOME)
os.environ["HF_MODULES_CACHE"] = str(HF_MODULES_CACHE)
os.environ["YOLO_CONFIG_DIR"] = str(YOLO_CONFIG_DIR)

if str(YOLO_RUNTIME_DIR) not in sys.path:
    sys.path.insert(0, str(YOLO_RUNTIME_DIR))

import torch
from fastapi import FastAPI, HTTPException, Query
from PIL import Image, UnidentifiedImageError
from pydantic import BaseModel
from transformers import AutoModel, AutoTokenizer
from ultralytics import YOLO

app = FastAPI(title="Tomato DL+Merge Service")


class GenerateResponse(BaseModel):
    generated_text: str


class TomatoExpertModel:
    def __init__(self) -> None:
        self.tokenizer = None
        self.model = None
        self.device = "cuda" if torch.cuda.is_available() else "cpu"

    def load(self) -> None:
        if self.model is not None and self.tokenizer is not None:
            return
        if not MERGE_MODEL_DIR.exists():
            raise FileNotFoundError(f"模型目录不存在: {MERGE_MODEL_DIR}")

        self.tokenizer = AutoTokenizer.from_pretrained(
            MERGE_MODEL_DIR,
            trust_remote_code=True,
            local_files_only=True,
        )
        model = AutoModel.from_pretrained(
            MERGE_MODEL_DIR,
            trust_remote_code=True,
            local_files_only=True,
        )
        if self.device == "cuda":
            model = model.half().cuda()
        self.model = model.eval()

    def chat(self, prompt: str) -> str:
        self.load()
        response, _ = self.model.chat(self.tokenizer, prompt, history=[])
        return response


class TomatoDetector:
    def __init__(self) -> None:
        self.model = None
        self.device = 0 if torch.cuda.is_available() else "cpu"

    def load(self) -> None:
        if self.model is not None:
            return
        if not YOLO_WEIGHTS.exists():
            raise FileNotFoundError(f"YOLO 权重不存在: {YOLO_WEIGHTS}")
        self.model = YOLO(str(YOLO_WEIGHTS))

    def predict(self, image_path: Path) -> dict:
        self.load()
        results = self.model.predict(
            source=str(image_path),
            conf=0.25,
            imgsz=640,
            save=False,
            verbose=False,
            device=self.device,
        )
        result = results[0]
        names = result.names
        boxes = result.boxes
        counts = {"Riped": 0, "UnRiped": 0}
        detections = []

        if boxes is not None:
            for cls_id, conf, xyxy in zip(boxes.cls.tolist(), boxes.conf.tolist(), boxes.xyxy.tolist()):
                label = names[int(cls_id)]
                if label in counts:
                    counts[label] += 1
                detections.append(
                    {
                        "label": label,
                        "confidence": round(float(conf), 4),
                        "bbox": [round(float(v), 2) for v in xyxy],
                    }
                )

        return {"counts": counts, "detections": detections}


expert_model = TomatoExpertModel()
detector = TomatoDetector()


def analyze_image(image_path: Path) -> str:
    if not image_path.exists():
        raise FileNotFoundError(f"图片不存在: {image_path}")

    try:
        with Image.open(image_path) as image:
            rgb_image = image.convert("RGB")
            width, height = rgb_image.size
            pixels = list(rgb_image.getdata())
    except UnidentifiedImageError as exc:
        raise ValueError(f"无法识别图片文件: {image_path}") from exc

    total_pixels = max(len(pixels), 1)
    red_dominant = sum(1 for r, g, b in pixels if r > g + 18 and r > b + 18)
    green_dominant = sum(1 for r, g, b in pixels if g > r + 12 and g > b + 12)
    brightness = sum((r + g + b) / 3 for r, g, b in pixels) / total_pixels
    red_ratio = red_dominant / total_pixels
    green_ratio = green_dominant / total_pixels

    if red_ratio > 0.16 and green_ratio < 0.42:
        maturity_hint = "图像中的番茄更偏成熟或正在转红。"
    elif green_ratio > 0.33 and red_ratio < 0.08:
        maturity_hint = "图像中的番茄整体更偏青绿，较像未成熟状态。"
    else:
        maturity_hint = "图像中同时存在较明显的红色和绿色区域，可能是混合成熟度。"

    light_hint = "画面较明亮。" if brightness >= 120 else "画面偏暗。"
    return (
        f"图片基础信息：分辨率 {width}x{height}。"
        f"红色像素占比约 {red_ratio:.2%}，绿色像素占比约 {green_ratio:.2%}。"
        f"{maturity_hint}{light_hint}"
    )


def build_merge_prompt(user_prompt: str, image_path: Path, image_summary: str, detection_summary: dict) -> str:
    counts = detection_summary["counts"]
    detections = detection_summary["detections"]
    lines = []
    for index, item in enumerate(detections, start=1):
        lines.append(f"{index}. 类别: {item['label']}，置信度: {item['confidence']}，边框: {item['bbox']}")
    detection_text = "\n".join(lines) if lines else "深度学习模型未检测到明确的番茄目标。"

    return f"""
你是一名番茄种植专家，请结合深度学习成熟度检测结果、图片摘要和用户问题，给出专业、简洁、可执行的中文回答。

图片路径：{image_path}
深度学习成熟度统计：成熟 Riped={counts['Riped']}，未成熟 UnRiped={counts['UnRiped']}
深度学习检测详情：
{detection_text}
图片摘要：{image_summary}
用户问题：{user_prompt}

请按下面结构回答：
1. 图片观察
2. 初步判断
3. 管理建议

如果深度学习模型未检测到目标，也要结合图片摘要继续给出谨慎判断。
""".strip()


@app.get("/generate", response_model=GenerateResponse)
def generate(prompt: str = Query(..., min_length=1)) -> GenerateResponse:
    return GenerateResponse(generated_text=expert_model.chat(prompt))


@app.get("/image-generate", response_model=GenerateResponse)
def image_generate(
    prompt: str = Query(..., min_length=1),
    imagePath: str = Query(..., min_length=1),
) -> GenerateResponse:
    image_path = Path(imagePath).expanduser()
    try:
        image_summary = analyze_image(image_path)
        detection_summary = detector.predict(image_path)
        final_prompt = build_merge_prompt(prompt, image_path, image_summary, detection_summary)
        answer = expert_model.chat(final_prompt)
    except (FileNotFoundError, ValueError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"图像问答服务异常: {exc}") from exc
    return GenerateResponse(generated_text=answer)


@app.get("/health")
def health() -> dict:
    return {
        "status": "ok",
        "merge_model_dir": str(MERGE_MODEL_DIR),
        "yolo_weights": str(YOLO_WEIGHTS),
        "cuda_available": torch.cuda.is_available(),
        "device_name": torch.cuda.get_device_name(0) if torch.cuda.is_available() else "CPU",
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        app,
        host=os.getenv("TOMATO_SERVICE_HOST", "0.0.0.0"),
        port=int(os.getenv("TOMATO_SERVICE_PORT", "8000")),
    )
