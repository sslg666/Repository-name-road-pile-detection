import re
import cv2
import numpy as np


class TextRecognizer:
    """文字识别模块 - 轻量版本，使用 OpenCV 和模板匹配"""

    def __init__(self, use_gpu=False):
        self.use_gpu = use_gpu
        self.reader = None
        self._try_init_easyocr()

    def _try_init_easyocr(self):
        """尝试初始化 EasyOCR（可选）"""
        try:
            import easyocr
            self.reader = easyocr.Reader(['ch_sim', 'en'], gpu=self.use_gpu, verbose=False)
            print("EasyOCR 初始化成功")
        except Exception as e:
            print(f"EasyOCR 不可用，使用基础识别: {e}")
            self.reader = None

    def recognize(self, image):
        """识别图像中的文字"""
        if image is None:
            return {
                'text': '',
                'confidence': 0,
                'pile_number': None,
                'details': []
            }

        # 如果 EasyOCR 可用，使用它
        if self.reader:
            return self._recognize_with_easyocr(image)

        # 否则使用基础识别
        return self._recognize_basic(image)

    def _recognize_with_easyocr(self, image):
        """使用 EasyOCR 识别"""
        try:
            results = self.reader.readtext(image)
            texts = []
            details = []
            total_confidence = 0

            for (bbox, text, conf) in results:
                if conf > 0.3:
                    texts.append(text)
                    total_confidence += conf
                    details.append({
                        'text': text,
                        'confidence': float(conf),
                        'bbox': [[int(p[0]), int(p[1])] for p in bbox]
                    })

            full_text = ' '.join(texts)
            avg_confidence = total_confidence / len(texts) if texts else 0
            pile_number = self.parse_pile_number(full_text)

            return {
                'text': full_text,
                'confidence': float(avg_confidence),
                'pile_number': pile_number,
                'details': details
            }
        except Exception as e:
            print(f"EasyOCR 识别失败: {e}")
            return self._recognize_basic(image)

    def _recognize_basic(self, image):
        """基础识别 - 使用图像特征分析"""
        if image is None:
            return {
                'text': '',
                'confidence': 0,
                'pile_number': None,
                'details': []
            }

        try:
            # 转换为灰度图
            if len(image.shape) == 3:
                gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
            else:
                gray = image.copy()

            # 预处理
            blurred = cv2.GaussianBlur(gray, (5, 5), 0)
            _, binary = cv2.threshold(blurred, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)

            # 检测文字区域
            contours, _ = cv2.findContours(binary, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

            # 分析图像特征
            h, w = gray.shape
            text_density = np.sum(binary == 0) / (h * w) if h * w > 0 else 0

            # 基于特征估算可能的桩号
            confidence = min(text_density * 2, 0.8) if text_density > 0.1 else 0.3

            # 尝试从文件名或图像特征推断桩号
            estimated_pile = self._estimate_pile_number(image)

            return {
                'text': f'检测到文字区域 (密度: {text_density:.2%})',
                'confidence': confidence,
                'pile_number': estimated_pile,
                'details': []
            }
        except Exception as e:
            print(f"基础识别失败: {e}")
            return {
                'text': '',
                'confidence': 0,
                'pile_number': None,
                'details': []
            }

    def _estimate_pile_number(self, image):
        """基于图像特征估算桩号"""
        # 这里可以添加更复杂的特征分析
        # 目前返回 None，表示无法确定
        return None

    def parse_pile_number(self, text):
        """解析桩号格式"""
        if not text:
            return None

        patterns = [
            r'[Kk]\s*(\d+)\s*[+\＋]\s*(\d+)',
            r'[Kk]\s*(\d{3,})',
            r'(\d+)\s*[+\＋]\s*(\d+)',
            r'(\d{4,})',
        ]

        for pattern in patterns:
            match = re.search(pattern, text)
            if match:
                groups = match.groups()
                if len(groups) == 2:
                    return {
                        'prefix': 'K',
                        'main_km': groups[0],
                        'sub_meter': groups[1],
                        'full': f"K{groups[0]}+{groups[1]}",
                        'raw': match.group(0)
                    }
                elif len(groups) == 1:
                    num = groups[0]
                    if len(num) >= 4:
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
        """为 OCR 优化图像预处理"""
        if image is None:
            return None

        if len(image.shape) == 3:
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        else:
            gray = image.copy()

        h, w = gray.shape
        if w < 100:
            scale = 200 / w
            gray = cv2.resize(gray, None, fx=scale, fy=scale, interpolation=cv2.INTER_CUBIC)

        _, binary = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)

        if np.mean(binary) < 127:
            binary = cv2.bitwise_not(binary)

        return binary

    def recognize_with_preprocess(self, image):
        """使用预处理后识别"""
        if image is None:
            return self.recognize(image)

        processed = self.preprocess_for_ocr(image)
        result = self.recognize(processed)

        if result['confidence'] < 0.5:
            result_original = self.recognize(image)
            if result_original['confidence'] > result['confidence']:
                return result_original

        return result
