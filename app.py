import os
import uuid
import cv2
import numpy as np
from flask import Flask, render_template, request, jsonify, send_file, url_for
from werkzeug.utils import secure_filename
from datetime import datetime

from utils.preprocessor import ImagePreprocessor
from utils.detector import PileDetector
from utils.recognizer import TextRecognizer
from utils.database import DatabaseManager

app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 100 * 1024 * 1024  # 100MB限制

# 支持云端和本地部署
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
UPLOAD_FOLDER = os.environ.get('UPLOAD_FOLDER', os.path.join(BASE_DIR, 'static', 'uploads'))
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# 确保上传目录存在
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# 允许的文件类型
ALLOWED_IMAGE_EXTENSIONS = {'png', 'jpg', 'jpeg', 'bmp', 'gif'}
ALLOWED_VIDEO_EXTENSIONS = {'mp4', 'avi', 'mov', 'mkv'}

# 初始化模块
preprocessor = ImagePreprocessor()
detector = PileDetector()
recognizer = TextRecognizer(use_gpu=False)
db = DatabaseManager()


def allowed_file(filename, allowed_extensions):
    """检查文件类型是否允许"""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in allowed_extensions


def process_image(image_path):
    """处理单张图片"""
    image = cv2.imread(image_path)
    if image is None:
        return {'error': '无法读取图像文件'}

    enhanced = preprocessor.enhance_for_detection(image)
    detections = detector.detect(enhanced)

    results = []
    for detection in detections:
        region = {
            'x': detection['x'],
            'y': detection['y'],
            'width': detection['width'],
            'height': detection['height']
        }
        cropped = preprocessor.crop_region(image, region)

        if cropped is not None and cropped.size > 0:
            ocr_result = recognizer.recognize_with_preprocess(cropped)
            results.append({
                'region': region,
                'confidence': detection.get('confidence', 0),
                'text': ocr_result['text'],
                'pile_number': ocr_result['pile_number'],
                'ocr_confidence': ocr_result['confidence'],
                'details': ocr_result['details']
            })

    # 在图像上绘制检测结果
    annotated = image.copy()
    for result in results:
        r = result['region']
        color = (0, 255, 0) if result['pile_number'] else (0, 165, 255)
        cv2.rectangle(annotated, (r['x'], r['y']),
                     (r['x'] + r['width'], r['y'] + r['height']), color, 2)
        label = result['pile_number']['full'] if result['pile_number'] else result['text'][:20]
        cv2.putText(annotated, label, (r['x'], r['y'] - 10),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 2)

    result_filename = f"result_{uuid.uuid4().hex[:8]}.jpg"
    result_path = os.path.join(UPLOAD_FOLDER, result_filename)
    cv2.imwrite(result_path, annotated)

    return {
        'detections': results,
        'result_image': result_filename,
        'total_detections': len(results)
    }


def process_video(video_path, sample_rate=30):
    """处理视频文件"""
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        return {'error': '无法打开视频文件'}

    fps = cap.get(cv2.CAP_PROP_FPS)
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    duration = total_frames / fps if fps > 0 else 0

    frame_results = []
    frame_count = 0
    detected_numbers = set()

    while True:
        ret, frame = cap.read()
        if not ret:
            break

        if frame_count % sample_rate == 0:
            detections = detector.detect(frame)
            for detection in detections:
                region = {
                    'x': detection['x'],
                    'y': detection['y'],
                    'width': detection['width'],
                    'height': detection['height']
                }
                cropped = preprocessor.crop_region(frame, region)
                if cropped is not None and cropped.size > 0:
                    ocr_result = recognizer.recognize_with_preprocess(cropped)
                    if ocr_result['pile_number']:
                        pile_num = ocr_result['pile_number']['full']
                        if pile_num not in detected_numbers:
                            detected_numbers.add(pile_num)
                            frame_results.append({
                                'frame': frame_count,
                                'time': frame_count / fps if fps > 0 else 0,
                                'pile_number': ocr_result['pile_number'],
                                'text': ocr_result['text'],
                                'confidence': ocr_result['confidence']
                            })
        frame_count += 1

    cap.release()

    return {
        'video_info': {
            'fps': fps,
            'total_frames': total_frames,
            'duration': round(duration, 2)
        },
        'detections': frame_results,
        'unique_pile_numbers': list(detected_numbers),
        'total_unique': len(detected_numbers)
    }


@app.route('/')
def index():
    """主页"""
    return render_template('index.html')


@app.route('/api/upload', methods=['POST'])
def upload_file():
    """上传并处理文件"""
    if 'file' not in request.files:
        return jsonify({'error': '没有文件'}), 400

    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': '未选择文件'}), 400

    if not (allowed_file(file.filename, ALLOWED_IMAGE_EXTENSIONS) or
            allowed_file(file.filename, ALLOWED_VIDEO_EXTENSIONS)):
        return jsonify({'error': '不支持的文件类型'}), 400

    filename = secure_filename(file.filename)
    unique_filename = f"{uuid.uuid4().hex[:8]}_{filename}"
    file_path = os.path.join(UPLOAD_FOLDER, unique_filename)
    file.save(file_path)

    is_video = allowed_file(file.filename, ALLOWED_VIDEO_EXTENSIONS)
    file_type = 'video' if is_video else 'image'

    if is_video:
        sample_rate = int(request.form.get('sample_rate', 30))
        result = process_video(file_path, sample_rate)
    else:
        result = process_image(file_path)

    if 'error' in result:
        return jsonify(result), 400

    pile_numbers = []
    for d in result.get('detections', []):
        if d.get('pile_number'):
            pile_numbers.append(d['pile_number']['full'])

    primary_pile = pile_numbers[0] if pile_numbers else None
    detected_text = ', '.join(pile_numbers) if pile_numbers else ''

    detection_id = db.save_detection(
        filename=filename,
        file_path=unique_filename,
        file_type=file_type,
        pile_number=primary_pile,
        detected_text=detected_text,
        confidence=result.get('detections', [{}])[0].get('confidence', 0) if result.get('detections') else 0,
        detection_data=result
    )

    return jsonify({
        'success': True,
        'detection_id': detection_id,
        'result': result
    })


@app.route('/api/detections', methods=['GET'])
def get_detections():
    """获取检测历史"""
    limit = request.args.get('limit', 20, type=int)
    offset = request.args.get('offset', 0, type=int)
    keyword = request.args.get('keyword', '')

    if keyword:
        detections = db.search_detections(keyword)
    else:
        detections = db.get_all_detections(limit=limit, offset=offset)

    return jsonify({
        'success': True,
        'detections': detections,
        'total': len(detections)
    })


@app.route('/api/detection/<int:detection_id>', methods=['GET'])
def get_detection(detection_id):
    """获取单个检测结果"""
    detection = db.get_detection(detection_id)
    if detection:
        return jsonify({'success': True, 'detection': detection})
    return jsonify({'error': '未找到检测记录'}), 404


@app.route('/api/detection/<int:detection_id>', methods=['DELETE'])
def delete_detection(detection_id):
    """删除检测结果"""
    if db.delete_detection(detection_id):
        return jsonify({'success': True})
    return jsonify({'error': '删除失败'}), 400


@app.route('/api/statistics', methods=['GET'])
def get_statistics():
    """获取统计数据"""
    stats = db.get_statistics()
    return jsonify({'success': True, 'statistics': stats})


@app.route('/api/export/<format_type>', methods=['GET'])
def export_data(format_type):
    """导出数据"""
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')

    if format_type == 'json':
        output_path = os.path.join(UPLOAD_FOLDER, f'export_{timestamp}.json')
        db.export_to_json(output_path)
    elif format_type == 'csv':
        output_path = os.path.join(UPLOAD_FOLDER, f'export_{timestamp}.csv')
        db.export_to_csv(output_path)
    else:
        return jsonify({'error': '不支持的导出格式'}), 400

    return send_file(output_path, as_attachment=True)


@app.route('/uploads/<filename>')
def uploaded_file(filename):
    """访问上传的文件"""
    return send_file(os.path.join(UPLOAD_FOLDER, filename))


@app.route('/api/import', methods=['POST'])
def import_data():
    """导入数据"""
    if 'file' not in request.files:
        return jsonify({'error': '没有文件'}), 400

    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': '未选择文件'}), 400

    filename = secure_filename(file.filename)
    ext = filename.rsplit('.', 1)[1].lower() if '.' in filename else ''

    if ext not in ['json', 'csv']:
        return jsonify({'error': '只支持JSON或CSV格式'}), 400

    try:
        temp_path = os.path.join(UPLOAD_FOLDER, f'temp_import_{uuid.uuid4().hex[:8]}.{ext}')
        file.save(temp_path)

        imported_count = 0

        if ext == 'json':
            import json
            with open(temp_path, 'r', encoding='utf-8') as f:
                data = json.load(f)

            detections = data.get('detections', [])
            for d in detections:
                db.save_detection(
                    filename=d.get('filename', 'imported'),
                    file_path=d.get('file_path', ''),
                    file_type=d.get('file_type', 'image'),
                    pile_number=d.get('pile_number'),
                    detected_text=d.get('detected_text', ''),
                    confidence=d.get('confidence', 0),
                    detection_data=d.get('detection_data')
                )
                imported_count += 1

        elif ext == 'csv':
            import csv
            with open(temp_path, 'r', encoding='utf-8-sig') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    db.save_detection(
                        filename=row.get('文件名', 'imported'),
                        file_path='',
                        file_type=row.get('文件类型', 'image'),
                        pile_number=row.get('桩号') or None,
                        detected_text=row.get('识别文字', ''),
                        confidence=float(row.get('置信度', '0').replace('%', '')) / 100
                    )
                    imported_count += 1

        os.remove(temp_path)

        return jsonify({
            'success': True,
            'imported': imported_count
        })

    except Exception as e:
        return jsonify({'error': f'导入失败: {str(e)}'}), 400


@app.route('/api/clear-all', methods=['POST'])
def clear_all_data():
    """清空所有数据"""
    try:
        detections = db.get_all_detections(limit=10000)

        for d in detections:
            if d.get('file_path'):
                file_path = os.path.join(UPLOAD_FOLDER, d['file_path'])
                if os.path.exists(file_path):
                    try:
                        os.remove(file_path)
                    except:
                        pass
            if d.get('detection_data') and d['detection_data'].get('result_image'):
                result_path = os.path.join(UPLOAD_FOLDER, d['detection_data']['result_image'])
                if os.path.exists(result_path):
                    try:
                        os.remove(result_path)
                    except:
                        pass

        import sqlite3
        conn = sqlite3.connect(db.db_path)
        cursor = conn.cursor()
        cursor.execute('DELETE FROM detections')
        conn.commit()
        conn.close()

        return jsonify({'success': True})

    except Exception as e:
        return jsonify({'error': f'清空失败: {str(e)}'}), 400


# 健康检查端点（用于云平台）
@app.route('/health')
def health_check():
    return jsonify({'status': 'ok', 'timestamp': datetime.now().isoformat()})


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    debug = os.environ.get('FLASK_DEBUG', 'true').lower() == 'true'

    print("=" * 50)
    print("动态环境下道路桩号视觉检测与文字识别软件 V1.0")
    print("=" * 50)
    print(f"本地访问: http://localhost:{port}")
    print(f"局域网访问: http://0.0.0.0:{port}")
    print("=" * 50)

    app.run(debug=debug, host='0.0.0.0', port=port)
