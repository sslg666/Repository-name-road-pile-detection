import cv2
import numpy as np


class PileDetector:
    """桩号检测模块 - 使用 OpenCV 特征检测"""

    def __init__(self, model_path=None):
        self.model_loaded = False
        print("使用 OpenCV 特征检测方法")

    def detect(self, image):
        """检测图像中的桩号"""
        if image is None:
            return []

        # 使用多种方法检测
        detections = []

        # 方法1: 基于颜色特征
        color_detections = self._detect_by_color(image)
        detections.extend(color_detections)

        # 方法2: 基于文字区域
        text_detections = self._detect_text_regions(image)
        detections.extend(text_detections)

        # 合并和去重
        merged = self._merge_regions(detections)

        # 按置信度排序
        merged.sort(key=lambda r: r.get('confidence', 0), reverse=True)

        return merged[:5]

    def _detect_by_color(self, image):
        """基于颜色特征检测桩号"""
        detections = []

        # 转换到 HSV 颜色空间
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
            x, y, w, h = cv2.boundingRect(contour)
            area = w * h

            # 筛选条件
            if area < 1000:
                continue

            aspect_ratio = w / h if h > 0 else 0
            if aspect_ratio < 1.5 or aspect_ratio > 8:
                continue

            # 计算置信度
            roi = mask[y:y+h, x:x+w]
            confidence = np.sum(roi > 0) / area if area > 0 else 0

            if confidence > 0.3:
                detections.append({
                    'x': int(x),
                    'y': int(y),
                    'width': int(w),
                    'height': int(h),
                    'confidence': float(confidence * 0.8),
                    'method': 'color'
                })

        return detections

    def _detect_text_regions(self, image):
        """检测文字区域"""
        detections = []

        # 转换为灰度图
        if len(image.shape) == 3:
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        else:
            gray = image.copy()

        # 边缘检测
        edges = cv2.Canny(gray, 50, 150)

        # 膨胀操作连接边缘
        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (20, 3))
        dilated = cv2.dilate(edges, kernel, iterations=1)

        # 查找轮廓
        contours, _ = cv2.findContours(dilated, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        for contour in contours:
            x, y, w, h = cv2.boundingRect(contour)
            area = w * h

            if area < 500:
                continue

            aspect_ratio = w / h if h > 0 else 0
            if 1.0 < aspect_ratio < 10:
                # 计算边缘密度作为置信度
                roi = edges[y:y+h, x:x+w]
                confidence = np.sum(roi > 0) / area if area > 0 else 0

                if confidence > 0.05:
                    detections.append({
                        'x': int(x),
                        'y': int(y),
                        'width': int(w),
                        'height': int(h),
                        'confidence': float(confidence),
                        'method': 'text'
                    })

        return detections

    def _merge_regions(self, regions):
        """合并重叠的检测区域"""
        if not regions:
            return []

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

                if self._regions_overlap(current, other):
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
