import re
import cv2
import numpy as np
import easyocr


class TextRecognizer:
    """文字识别模块 - 用于识别桩号文字"""

    def __init__(self, use_gpu=False):
        self.reader = None
        self.use_gpu = use_gpu
        self._init_reader()

    def _init_reader(self):
        """初始化EasyOCR读取器"""
        try:
            self.reader = easyocr.Reader(
                ['ch_sim', 'en'],
                gpu=self.use_gpu,
                verbose=False
            )
            print("EasyOCR初始化成功")
        except Exception as e:
            print(f"EasyOCR初始化失败: {e}")
            self.reader = None

    def recognize(self, image):
        """识别图像中的文字"""
        if image is None or self.reader is None:
            return {
                'text': '',
                'confidence': 0,
                'pile_number': None,
                'details': []
            }

        try:
            # 使用EasyOCR识别
            results = self.reader.readtext(image)

            # 解析结果
            texts = []
            details = []
            total_confidence = 0

            for (bbox, text, conf) in results:
                if conf > 0.3:  # 置信度阈值
                    texts.append(text)
                    total_confidence += conf
                    details.append({
                        'text': text,
                        'confidence': float(conf),
                        'bbox': [[int(p[0]), int(p[1])] for p in bbox]
                    })

            # 合并所有文字
            full_text = ' '.join(texts)
            avg_confidence = total_confidence / len(texts) if texts else 0

            # 尝试解析桩号
            pile_number = self.parse_pile_number(full_text)

            return {
                'text': full_text,
                'confidence': float(avg_confidence),
                'pile_number': pile_number,
                'details': details
            }

        except Exception as e:
            print(f"文字识别失败: {e}")
            return {
                'text': '',
                'confidence': 0,
                'pile_number': None,
                'details': []
            }

    def parse_pile_number(self, text):
        """解析桩号格式"""
        if not text:
            return None

        # 常见桩号格式
        patterns = [
            # K123+456 格式
            r'[Kk]\s*(\d+)\s*[+\＋]\s*(\d+)',
            # K123456 格式
            r'[Kk]\s*(\d{3,})',
            # 123+456 格式
            r'(\d+)\s*[+\＋]\s*(\d+)',
            # 纯数字（可能是简写）
            r'(\d{4,})',
        ]

        for pattern in patterns:
            match = re.search(pattern, text)
            if match:
                groups = match.groups()
                if len(groups) == 2:
                    # K123+456 格式
                    return {
                        'prefix': 'K',
                        'main_km': groups[0],
                        'sub_meter': groups[1],
                        'full': f"K{groups[0]}+{groups[1]}",
                        'raw': match.group(0)
                    }
                elif len(groups) == 1:
                    # 简单格式
                    num = groups[0]
                    if len(num) >= 4:
                        # 假设前3位是公里，后几位是米
                        return {
                            'prefix': 'K',
                            'main_km': num[:3],
                            'sub_meter': num[3:],
                            'full': f"K{num[:3]}+{num[3:]}",
                            'raw': match.group(0)
                        }
                    else:
                        return {
                            'prefix': 'K',
                            'main_km': num,
                            'sub_meter': '0',
                            'full': f"K{num}+0",
                            'raw': match.group(0)
                        }

        return None

    def preprocess_for_ocr(self, image):
        """为OCR优化图像预处理"""
        if image is None:
            return None

        # 转换为灰度图
        if len(image.shape) == 3:
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        else:
            gray = image.copy()

        # 调整大小（如果太小）
        h, w = gray.shape
        if w < 100:
            scale = 200 / w
            gray = cv2.resize(gray, None, fx=scale, fy=scale, interpolation=cv2.INTER_CUBIC)

        # 二值化
        _, binary = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)

        # 如果背景是黑色，反转
        if np.mean(binary) < 127:
            binary = cv2.bitwise_not(binary)

        return binary

    def recognize_with_preprocess(self, image):
        """使用预处理后识别"""
        if image is None:
            return self.recognize(image)

        # 预处理
        processed = self.preprocess_for_ocr(image)

        # 识别
        result = self.recognize(processed)

        # 如果预处理后识别效果不好，尝试原图
        if result['confidence'] < 0.5:
            result_original = self.recognize(image)
            if result_original['confidence'] > result['confidence']:
                return result_original

        return result
