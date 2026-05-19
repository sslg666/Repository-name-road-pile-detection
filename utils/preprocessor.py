import cv2
import numpy as np


class ImagePreprocessor:
    """图像预处理模块 - 用于道路桩号图像的预处理"""

    def __init__(self):
        self.clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))

    def preprocess(self, image):
        """完整预处理流程"""
        if image is None:
            return None

        # 转换为灰度图
        if len(image.shape) == 3:
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        else:
            gray = image.copy()

        # 高斯滤波去噪
        denoised = cv2.GaussianBlur(gray, (5, 5), 0)

        # 直方图均衡化增强对比度
        enhanced = self.clahe.apply(denoised)

        # 自适应阈值二值化
        binary = cv2.adaptiveThreshold(
            enhanced, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
            cv2.THRESH_BINARY_INV, 11, 2
        )

        # 形态学操作 - 开运算去除小噪点
        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (3, 3))
        morphed = cv2.morphologyEx(binary, cv2.MORPH_OPEN, kernel, iterations=1)

        # 形态学操作 - 闭运算连接断裂区域
        morphed = cv2.morphologyEx(morphed, cv2.MORPH_CLOSE, kernel, iterations=2)

        return morphed

    def enhance_for_detection(self, image):
        """增强图像用于检测"""
        if image is None:
            return None

        # 转换为LAB颜色空间
        if len(image.shape) == 3:
            lab = cv2.cvtColor(image, cv2.COLOR_BGR2LAB)
            l, a, b = cv2.split(lab)

            # 对L通道进行CLAHE增强
            l_enhanced = self.clahe.apply(l)

            # 合并通道
            enhanced_lab = cv2.merge([l_enhanced, a, b])
            enhanced = cv2.cvtColor(enhanced_lab, cv2.COLOR_LAB2BGR)
        else:
            enhanced = self.clahe.apply(image)

        return enhanced

    def detect_edges(self, image):
        """边缘检测"""
        if image is None:
            return None

        # 转换为灰度图
        if len(image.shape) == 3:
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        else:
            gray = image.copy()

        # 高斯模糊
        blurred = cv2.GaussianBlur(gray, (5, 5), 0)

        # Canny边缘检测
        edges = cv2.Canny(blurred, 50, 150)

        return edges

    def find_pile_regions(self, image):
        """查找可能的桩号区域"""
        if image is None:
            return []

        # 预处理
        processed = self.preprocess(image)

        # 查找轮廓
        contours, _ = cv2.findContours(
            processed, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
        )

        # 筛选可能的桩号区域
        regions = []
        h, w = image.shape[:2]

        for contour in contours:
            x, y, cw, ch = cv2.boundingRect(contour)
            area = cw * ch

            # 过滤条件
            # 1. 面积不能太小
            if area < 500:
                continue

            # 2. 宽高比合理（桩号通常是长条形）
            aspect_ratio = cw / ch if ch > 0 else 0
            if aspect_ratio < 0.5 or aspect_ratio > 10:
                continue

            # 3. 面积不能超过图像的一定比例
            if area > (h * w * 0.5):
                continue

            regions.append({
                'x': int(x),
                'y': int(y),
                'width': int(cw),
                'height': int(ch),
                'area': int(area)
            })

        # 按面积排序，取前5个
        regions.sort(key=lambda r: r['area'], reverse=True)
        return regions[:5]

    def crop_region(self, image, region):
        """裁剪指定区域"""
        if image is None or region is None:
            return None

        x = region['x']
        y = region['y']
        w = region['width']
        h = region['height']

        # 确保不超出边界
        img_h, img_w = image.shape[:2]
        x1 = max(0, x)
        y1 = max(0, y)
        x2 = min(img_w, x + w)
        y2 = min(img_h, y + h)

        return image[y1:y2, x1:x2]
