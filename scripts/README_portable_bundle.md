# 番茄 DL+Merge 便携包说明

这个便携包目标是让另一台电脑在不重新配项目结构的情况下，直接运行：

- 单张图片分析脚本
- FastAPI 服务
- 已打包的 `merge` 模型
- 已打包的 YOLO 权重
- 已打包的 Python 环境

## 包内关键内容

- `python_env/`
  打包好的 Python 运行环境。
- `models/merge/`
  `merge` 大模型目录。
- `models/yolo/yolo11n_best.pt`
  已实测可用的成熟度检测权重。
- `runtime/ultralytics_runtime/ultralytics/`
  本地 YOLO 运行代码。
- `service/tomato_dl_merge_service.py`
  可直接启动的服务脚本。
- `scripts/run_one_image_portable.py`
  单图直接运行脚本。

## 建议启动方式

### 单图直接跑

```bat
python_env\python.exe scripts\run_one_image_portable.py
```

### 启动服务

```bat
python_env\python.exe service\tomato_dl_merge_service.py
```

## 说明

- 如果目标电脑有 NVIDIA 显卡且驱动兼容，脚本会自动尝试用 GPU。
- 如果没有可用 GPU，会自动退回 CPU。
- 默认图片路径写在 `scripts/run_one_image_portable.py` 里，换图时改 `IMAGE_PATH` 即可。
