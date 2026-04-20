import os
import sys
import threading
from pathlib import Path

import torch
from fastapi import FastAPI, HTTPException, Query
from PIL import Image, UnidentifiedImageError
from pydantic import BaseModel
from transformers import AutoModel, AutoTokenizer


BASE_DIR = Path(__file__).resolve().parent.parent
MODELS_DIR = BASE_DIR / "models"
RUNTIME_DIR = BASE_DIR / "runtime"
YOLO_RUNTIME_DIR = RUNTIME_DIR / "ultralytics_runtime"

MERGE_MODEL_DIR = Path(os.getenv("TOMATO_MODEL_DIR", str(MODELS_DIR / "merge"))).expanduser()
YOLO_WEIGHTS = Path(os.getenv("TOMATO_YOLO_WEIGHTS", str(MODELS_DIR / "yolo" / "yolo11n_best.pt"))).expanduser()
HF_HOME = Path(os.getenv("TOMATO_HF_HOME", str(RUNTIME_DIR / "hf-cache"))).expanduser()
HF_MODULES_CACHE = Path(os.getenv("TOMATO_HF_MODULES_CACHE", str(RUNTIME_DIR / "hf-modules"))).expanduser()
YOLO_CONFIG_DIR = Path(os.getenv("YOLO_CONFIG_DIR", str(RUNTIME_DIR / "yolo-config"))).expanduser()

DETECT_TIMEOUT_SEC = int(os.getenv("TOMATO_DETECT_TIMEOUT_SEC", "30"))
DETECT_DEVICE = os.getenv("TOMATO_DETECT_DEVICE", "cpu").strip().lower()
IMAGE_USE_LLM = os.getenv("TOMATO_IMAGE_USE_LLM", "0").strip().lower() in {"1", "true", "yes"}
TEXT_USE_LLM = os.getenv("TOMATO_TEXT_USE_LLM", "1").strip().lower() in {"1", "true", "yes"}
TEXT_MAX_LENGTH = int(os.getenv("TOMATO_TEXT_MAX_LENGTH", "2048"))
PRELOAD_TEXT_MODEL = os.getenv("TOMATO_PRELOAD_TEXT_MODEL", "1").strip().lower() in {"1", "true", "yes"}

HF_HOME.mkdir(parents=True, exist_ok=True)
HF_MODULES_CACHE.mkdir(parents=True, exist_ok=True)
YOLO_CONFIG_DIR.mkdir(parents=True, exist_ok=True)
os.environ["HF_HOME"] = str(HF_HOME)
os.environ["TRANSFORMERS_CACHE"] = str(HF_HOME)
os.environ["HF_MODULES_CACHE"] = str(HF_MODULES_CACHE)
os.environ["YOLO_CONFIG_DIR"] = str(YOLO_CONFIG_DIR)

if str(YOLO_RUNTIME_DIR) not in sys.path:
    sys.path.insert(0, str(YOLO_RUNTIME_DIR))

from ultralytics import YOLO  # noqa: E402

app = FastAPI(title="Tomato DL+Merge Service")


class GenerateResponse(BaseModel):
    generated_text: str


class TomatoExpertModel:
    def __init__(self) -> None:
        self.tokenizer = None
        self.model = None
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        self.load_error = None
        self.load_lock = threading.Lock()
        self.chat_lock = threading.Lock()

    def load(self) -> None:
        if self.model is not None and self.tokenizer is not None:
            return
        if self.load_error is not None:
            raise RuntimeError(self.load_error)
        if not MERGE_MODEL_DIR.exists():
            raise FileNotFoundError(f"Merge model dir not found: {MERGE_MODEL_DIR}")

        with self.load_lock:
            if self.model is not None and self.tokenizer is not None:
                return
            try:
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
            except Exception as exc:
                self.load_error = str(exc)
                raise

    def chat(self, prompt: str) -> str:
        self.load()
        with self.chat_lock:
            response, _ = self.model.chat(
                self.tokenizer,
                prompt,
                history=[],
                max_length=TEXT_MAX_LENGTH,
                do_sample=False,
                temperature=0.7,
            )
            return response


class TomatoDetector:
    def __init__(self) -> None:
        self.model = None
        if DETECT_DEVICE == "cuda":
            self.device = 0
        elif DETECT_DEVICE == "cpu":
            self.device = "cpu"
        else:
            self.device = 0 if torch.cuda.is_available() else "cpu"

    def load(self) -> None:
        if self.model is not None:
            return
        if not YOLO_WEIGHTS.exists():
            raise FileNotFoundError(f"YOLO weights not found: {YOLO_WEIGHTS}")
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


@app.on_event("startup")
def preload_text_model() -> None:
    if not TEXT_USE_LLM or not PRELOAD_TEXT_MODEL:
        return

    def _load() -> None:
        try:
            expert_model.load()
        except Exception as exc:
            print(f"Text model preload failed: {exc}", flush=True)

    threading.Thread(target=_load, daemon=True).start()


def analyze_image(image_path: Path) -> str:
    if not image_path.exists():
        raise FileNotFoundError(f"Image not found: {image_path}")

    try:
        with Image.open(image_path) as image:
            rgb_image = image.convert("RGB")
            width, height = rgb_image.size
            pixels = list(rgb_image.getdata())
    except UnidentifiedImageError as exc:
        raise ValueError(f"Cannot read image file: {image_path}") from exc

    total_pixels = max(len(pixels), 1)
    red_dominant = sum(1 for r, g, b in pixels if r > g + 18 and r > b + 18)
    green_dominant = sum(1 for r, g, b in pixels if g > r + 12 and g > b + 12)
    brightness = sum((r + g + b) / 3 for r, g, b in pixels) / total_pixels
    red_ratio = red_dominant / total_pixels
    green_ratio = green_dominant / total_pixels

    if red_ratio > 0.16 and green_ratio < 0.42:
        maturity_hint = "图像中番茄偏成熟或正在转红。"
    elif green_ratio > 0.33 and red_ratio < 0.08:
        maturity_hint = "图像中番茄偏青，整体成熟度较低。"
    else:
        maturity_hint = "图像中红绿比例混合，可能处于混合成熟阶段。"

    light_hint = "画面较亮。" if brightness >= 120 else "画面偏暗。"
    return (
        f"图片信息：分辨率 {width}x{height}。"
        f"红色像素约 {red_ratio:.2%}，绿色像素约 {green_ratio:.2%}。"
        f"{maturity_hint}{light_hint}"
    )


def predict_with_timeout(image_path: Path) -> dict:
    result_holder = {"value": {"counts": {"Riped": 0, "UnRiped": 0}, "detections": []}}

    def _run():
        try:
            result_holder["value"] = detector.predict(image_path)
        except Exception:
            result_holder["value"] = {"counts": {"Riped": 0, "UnRiped": 0}, "detections": []}

    thread = threading.Thread(target=_run, daemon=True)
    thread.start()
    thread.join(timeout=DETECT_TIMEOUT_SEC)
    return result_holder["value"]


def build_merge_prompt(user_prompt: str, image_path: Path, image_summary: str, detection_summary: dict) -> str:
    counts = detection_summary["counts"]
    detections = detection_summary["detections"]
    if detections:
        detail_lines = [
            f"{idx}. 类别: {item['label']}，置信度: {item['confidence']}，框: {item['bbox']}"
            for idx, item in enumerate(detections, start=1)
        ]
        detection_text = "\n".join(detail_lines)
    else:
        detection_text = "未检测到明确目标，按图像摘要进行谨慎判断。"

    return f"""
你是番茄种植专家，请根据检测和图像摘要回答用户问题。
图片路径: {image_path}
成熟统计: Riped={counts['Riped']}，UnRiped={counts['UnRiped']}
检测详情:
{detection_text}
图像摘要: {image_summary}
用户问题: {user_prompt}

请按以下结构回答：
1. 图片观察
2. 初步判断
3. 管理建议
""".strip()


def build_fast_image_report(user_prompt: str, image_summary: str, detection_summary: dict) -> str:
    counts = detection_summary["counts"]
    detections = detection_summary["detections"]
    lines = []
    lines.append(f"图片分析：{image_summary}")
    lines.append(f"检测结果：成熟 Riped={counts['Riped']}，未成熟 UnRiped={counts['UnRiped']}。")
    if detections:
        top = detections[:8]
        details = "；".join([f"{item['label']}({item['confidence']})" for item in top])
        lines.append(f"目标详情：{details}")
    else:
        lines.append("目标详情：未检测到明确番茄目标。")
    lines.append(f"你的问题：{user_prompt}")
    lines.append("建议：如果成熟果数量较多可分批采摘；未成熟较多则继续养护并复查。")
    return "\n".join(lines)


def build_fast_text_reply(prompt: str) -> str:
    prompt_lower = prompt.lower()

    if any(word in prompt for word in ["种植", "栽培", "定植", "技术"]):
        return (
            "番茄常用种植技术可以按这几步做：\n"
            "1. 选地整地：选择排水好、光照足、土壤疏松肥沃的地块，定植前施足腐熟有机肥。\n"
            "2. 育苗定植：幼苗长到 4-6 片真叶、茎秆粗壮时定植，避免徒长苗和病弱苗。\n"
            "3. 温光管理：番茄喜光，白天适宜温度约 22-28 摄氏度，夜间保持 15-18 摄氏度更利于坐果。\n"
            "4. 水肥管理：定植后缓苗期少浇水，开花坐果后保持土壤见干见湿，追肥以氮磷钾均衡为主，结果期适当补钾。\n"
            "5. 整枝搭架：及时搭架绑蔓，常用单干或双干整枝，去除老叶、病叶和过密侧枝，改善通风透光。\n"
            "6. 保花保果：花期避免高温、低温和湿度过大，必要时轻振花序或采用合规方式辅助授粉。\n"
            "7. 病虫害防控：重点预防晚疫病、灰霉病、叶霉病、白粉虱和蚜虫，优先做好通风降湿、清除病残体和轮作。\n"
            "8. 适时采收：果实转色均匀、达到商品成熟度后分批采摘，避免过熟影响储运。"
        )

    if any(word in prompt for word in ["病", "虫", "叶斑", "晚疫", "灰霉", "白粉虱", "蚜虫"]):
        return (
            "番茄病虫害处理建议：先观察症状位置和扩展速度，及时摘除病叶病果，保持通风透光并控制湿度。"
            "常见病害包括晚疫病、灰霉病、叶霉病和病毒病；常见虫害包括白粉虱、蚜虫、蓟马。"
            "如果叶片出现水渍状斑、霉层或快速萎蔫，应隔离病株并按当地农技要求选择合规药剂。"
        )

    if any(word in prompt for word in ["施肥", "肥", "营养", "缺素"]):
        return (
            "番茄施肥要做到基肥足、追肥稳、结果期重钾。定植前施腐熟有机肥和适量复合肥；"
            "缓苗后少量追肥，第一穗果膨大后增加钾肥和钙肥供应，减少裂果和脐腐病风险。"
            "如果叶片发黄、卷曲或果实异常，应结合土壤湿度、根系状态和缺素症状综合判断。"
        )

    if any(word in prompt for word in ["浇水", "水分", "灌溉", "裂果"]):
        return (
            "番茄浇水以见干见湿为原则。缓苗期少浇，开花期避免忽干忽湿，结果膨大期保持稳定水分。"
            "长期干旱后突然大水容易裂果；棚室种植还要注意浇水后及时通风，降低灰霉病等病害风险。"
        )

    if any(word in prompt for word in ["采摘", "成熟", "转色", "能摘"]):
        return (
            "番茄是否适合采摘主要看用途和成熟度。鲜食可在果面大部分转红、硬度适中时采摘；"
            "需要运输时可在转色期或半红期采收；留种或就近食用可以等完全成熟后再摘。"
        )

    if "tomato" in prompt_lower:
        return (
            "Tomatoes need enough sunlight, loose fertile soil, steady watering, balanced fertilizer, support pruning, "
            "and regular disease and pest monitoring. For a specific plan, tell me your growing environment and problem."
        )

    return (
        "我是番茄专家助手，可以回答番茄种植、育苗、定植、水肥管理、整枝打杈、病虫害防治、成熟采摘和图像分析相关问题。"
        "你可以把问题描述得更具体一些，例如种植环境、叶片症状、果实状态或当前生长期。"
    )


@app.get("/generate", response_model=GenerateResponse)
def generate(prompt: str = Query(..., min_length=1)) -> GenerateResponse:
    if TEXT_USE_LLM:
        return GenerateResponse(generated_text=expert_model.chat(prompt))
    return GenerateResponse(generated_text=build_fast_text_reply(prompt))


@app.get("/image-generate", response_model=GenerateResponse)
def image_generate(
    prompt: str = Query(..., min_length=1),
    imagePath: str = Query(..., min_length=1),
) -> GenerateResponse:
    image_path = Path(imagePath).expanduser()
    try:
        image_summary = analyze_image(image_path)
        detection_summary = predict_with_timeout(image_path)
        if IMAGE_USE_LLM:
            final_prompt = build_merge_prompt(prompt, image_path, image_summary, detection_summary)
            answer = expert_model.chat(final_prompt)
        else:
            answer = build_fast_image_report(prompt, image_summary, detection_summary)
    except (FileNotFoundError, ValueError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"image-generate failed: {exc}") from exc
    return GenerateResponse(generated_text=answer)


@app.get("/health")
def health() -> dict:
    return {
        "status": "ok",
        "merge_model_dir": str(MERGE_MODEL_DIR),
        "yolo_weights": str(YOLO_WEIGHTS),
        "cuda_available": torch.cuda.is_available(),
        "device_name": torch.cuda.get_device_name(0) if torch.cuda.is_available() else "CPU",
        "detect_device": str(detector.device),
        "detect_timeout_sec": DETECT_TIMEOUT_SEC,
        "image_use_llm": IMAGE_USE_LLM,
        "text_use_llm": TEXT_USE_LLM,
        "text_model_loaded": expert_model.model is not None,
        "text_model_device": expert_model.device,
        "text_max_length": TEXT_MAX_LENGTH,
        "text_model_error": expert_model.load_error,
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        app,
        host=os.getenv("TOMATO_SERVICE_HOST", "0.0.0.0"),
        port=int(os.getenv("TOMATO_SERVICE_PORT", "8000")),
    )
