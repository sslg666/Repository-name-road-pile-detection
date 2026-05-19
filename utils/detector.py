import cv2
import numpy as np
import os
from ultralytics import YOLO


class PileDetector:
    """桩号检测模块 - 使用YOLOv8进行目标检测"""

    def __init__(self, model_path=None):
        self.model = None
        self.model_loaded = False
        self.use_fallback = False

        # 尝试加载模型
        if model_path and os.path.exists(model_path):
            try:
                self.model = YOLO(model_path)
                self.model_loaded = True
                print(f"已加载自定义模型: {model_path}")
            except Exception as e:
                print(f"加载自定义模型失败: {e}")
                self.use_fallback = True
        else:
            print("使用默认检测方法（特征匹配）")
            self.use_fallback = True

    def detect(self, image):
        """检测图像中的桩号"""
        if image is None:
            return []

        if self.model_loaded and self.model:
            return self._detect_with_yolo(image)
        else:
            return self._detect_with_features(image)

    def _detect_with_yolo(self, image):
        """使用YOLOv8进行检测"""
        results = self.model(image, conf=0.5, verbose=False)

        detections = []
        for result in results:
            boxes = result.boxes
            if boxes is not None:
                for box in boxes:
                    x1, y1, x2, y2 = box.xyxy[0].cpu().numpy()
                    conf = box.conf[0].cpu().numpy()
                    cls = int(box.cls[0].cpu().numpy())

                    detections.append({
                        'x': int(x1),
                        'y': int(y1),
                        'width': int(x2 - x1),
                        'height': int(y2 - y1),
                        'confidence': float(conf),
                        'class': cls
                    })

        return detections

    def _detect_with_features(self, image):
        """使用传统特征匹配方法检测桩号区域"""
        if image is None:
            return []

        # 转换为灰度图
        if len(image.shape) == 3:
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        else:
            gray = image.copy()

        h, w = gray.shape

        # 方法1: 基于颜色特征检测（桩号通常是白色/黄色背景上的黑色文字）
        detections = self._detect_by_color(image)

        # 方法2: 基于文字区域检测
        text_regions = self._detect_text_regions(gray)

        # 合并结果
        all_regions = detections + text_regions

        # 去重
        final_regions = self._merge_regions(all_regions)

        # 按置信度排序
        final_regions.sort(key=lambda r: r.get('confidence', 0), reverse=True)

        return final_regions[:5]  # 返回前5个最可能的区域

    def _detect_by_color(self, image):
        """基于颜色特征检测桩号"""
        detections = []

        # 转换到HSV颜色空间
        hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)

        # 检测白色区域（桩号牌常见颜色）
        lower_white = np.array([0, 0, 200])
        upper_white = np.array([180, 30, 255])
        mask_white = cv2.inRange(hsv, lower_white, upper_white)

        # 检测黄色区域
        lower_yellow = np.array([20, 100, 100])
        upper_yellow = np.array([30, 255, 255])
        mask_yellow = cv2.inRange(hsv, lower_yellow, upper_yellow)

        # 合并掩码
        mask = cv2.bitwise_or(mask_white, mask_yellow)

        # 形态学操作
        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (15, 5))
        mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel)
        mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel)

        # 查找轮廓
        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        for contour in contours:
            x, y, cw, ch = cv2.boundingRect(contour)
            area = cw * ch

            # 筛选条件
            if area < 1000:
                continue

            aspect_ratio = cw / ch if ch > 0 else 0
            if aspect_ratio < 1.5 or aspect_ratio > 8:
                continue

            # 计算该区域的边缘密度作为置信度
            roi = mask[y:y+ch, x:x+cw]
            confidence = np.sum(roi > 0) / area if area > 0 else 0

            if confidence > 0.3:
                detections.append({
                    'x': int(x),
                    'y': int(y),
                    'width': int(cw),
                    'height': int(ch),
                    'confidence': float(confidence * 0.8),
                    'method': 'color'
                })

        return detections

    def _detect_text_regions(self, gray):
        """检测文字区域"""
        regions = []

        # 使用MSER检测文字区域
        mser = cv2.MSER_create()
        mser.setMinArea(100)
        mser.setMaxArea(10000)

        # 检测区域
        regions_mser, _ = mser.detectRegions(gray)

        # 合并相近的区域
        bboxes = []
        for region in regions_mser:
            x, y, w, h = cv2.boundingRect(region)
            bboxes.append((x, y, w, h))

        if not bboxes:
            return regions

        # 合并相近的边界框
        merged = self._merge_close_boxes(bboxes)

        for x, y, w, h in merged:
            area = w * h
            if area < 500:
                continue

            aspect_ratio = w / h if h > 0 else 0
            if 1.0 < aspect_ratio < 10:
                regions.append({
                    'x': int(x),
                    'y': int(y),
                    'width': int(w),
                    'height': int(h),
                    'confidence': 0.5,
                    'method': 'text'
                })

        return regions

    def _merge_close_boxes(self, bboxes, threshold=20):
        """合并相近的边界框"""
        if not bboxes:
            return []

        # 转换为numpy数组
        boxes = np.array(bboxes)

        # 按x坐标排序
        sorted_idx = np.argsort(boxes[:, 0])
        boxes = boxes[sorted_idx]

        merged = []
        current = list(boxes[0])

        for box in boxes[1:]:
            # 如果两个框足够近，合并它们
            if (box[0] <= current[0] + current[2] + threshold and
                abs(box[1] - current[1]) < threshold * 2):
                # 合并
                x2 = max(current[0] + current[2], box[0] + box[2])
                y2 = max(current[1] + current[3], box[1] + box[3])
                current[0] = min(current[0], box[0])
                current[1] = min(current[1], box[1])
                current[2] = x2 - current[0]
                current[3] = y2 - current[1]
            else:
                merged.append(tuple(current))
                current = list(box)

        merged.append(tuple(current))
        return merged

    def _merge_regions(self, regions):
        """合并重叠的检测区域"""
        if not regions:
            return []

        # 按置信度排序
        regions.sort(key=lambda r: r.get('confidence', 0), reverse=True)

        merged = []
        used = [False] * len(regions)

        for i, region in enumerate(regions):
            if used[i]:
                continue

            current = region.copy()
            for j, other in enumerate(regions[i+1:], i+1):
                if used[j]:
                    continue

                # 检查是否重叠
                if self._regions_overlap(current, other):
                    # 合并区域
                    x1 = min(current['x'], other['x'])
                    y1 = min(current['y'], other['y'])
                    x2 = max(current['x'] + current['width'], other['x'] + other['width'])
                    y2 = max(current['y'] + current['height'], other['y'] + other['height'])

                    current = {
                        'x': x1,
                        'y': y1,
                        'width': x2 - x1,
                        'height': y2 - y1,
                        'confidence': max(current.get('confidence', 0), other.get('confidence', 0)),
                        'method': 'merged'
                    }
                    used[j] = True

            merged.append(current)
            used[i] = True

        return merged

    def _regions_overlap(self, r1, r2, threshold=0.3):
        """检查两个区域是否重叠"""
        x1 = max(r1['x'], r2['x'])
        y1 = max(r1['y'], r2['y'])
        x2 = min(r1['x'] + r1['width'], r2['x'] + r2['width'])
        y2 = min(r1['y'] + r1['height'], r2['y'] + r2['height'])

        if x2 < x1 or y2 < y1:
            return False

        intersection = (x2 - x1) * (y2 - y1)
        area1 = r1['width'] * r1['height']
        area2 = r2['width'] * r2['height']
        min_area = min(area1, area2)

        return intersection / min_area > threshold if min_area > 0 else False
