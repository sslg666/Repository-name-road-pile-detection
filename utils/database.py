import sqlite3
import json
import os
from datetime import datetime


class DatabaseManager:
    """数据管理模块 - SQLite数据库操作"""

    def __init__(self, db_path='detection_results.db'):
        self.db_path = db_path
        self._init_database()

    def _init_database(self):
        """初始化数据库"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # 创建检测结果表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS detections (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                filename TEXT NOT NULL,
                file_path TEXT,
                file_type TEXT,
                pile_number TEXT,
                detected_text TEXT,
                confidence REAL,
                detection_data TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        # 创建统计表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS statistics (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                date TEXT,
                total_detections INTEGER DEFAULT 0,
                successful_detections INTEGER DEFAULT 0,
                avg_confidence REAL DEFAULT 0
            )
        ''')

        conn.commit()
        conn.close()

    def save_detection(self, filename, file_path, file_type, pile_number, detected_text, confidence, detection_data=None):
        """保存检测结果"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # 将检测数据转换为JSON字符串
        data_json = json.dumps(detection_data, ensure_ascii=False) if detection_data else None

        cursor.execute('''
            INSERT INTO detections (filename, file_path, file_type, pile_number, detected_text, confidence, detection_data)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (filename, file_path, file_type, pile_number, detected_text, confidence, data_json))

        detection_id = cursor.lastrowid
        conn.commit()
        conn.close()

        return detection_id

    def get_detection(self, detection_id):
        """获取单个检测结果"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        cursor.execute('SELECT * FROM detections WHERE id = ?', (detection_id,))
        row = cursor.fetchone()
        conn.close()

        if row:
            result = dict(row)
            if result['detection_data']:
                result['detection_data'] = json.loads(result['detection_data'])
            return result
        return None

    def get_all_detections(self, limit=100, offset=0):
        """获取所有检测结果"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        cursor.execute('''
            SELECT * FROM detections
            ORDER BY created_at DESC
            LIMIT ? OFFSET ?
        ''', (limit, offset))

        rows = cursor.fetchall()
        conn.close()

        results = []
        for row in rows:
            result = dict(row)
            if result['detection_data']:
                result['detection_data'] = json.loads(result['detection_data'])
            results.append(result)

        return results

    def search_detections(self, keyword):
        """搜索检测结果"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        cursor.execute('''
            SELECT * FROM detections
            WHERE pile_number LIKE ? OR detected_text LIKE ? OR filename LIKE ?
            ORDER BY created_at DESC
        ''', (f'%{keyword}%', f'%{keyword}%', f'%{keyword}%'))

        rows = cursor.fetchall()
        conn.close()

        results = []
        for row in rows:
            result = dict(row)
            if result['detection_data']:
                result['detection_data'] = json.loads(result['detection_data'])
            results.append(result)

        return results

    def delete_detection(self, detection_id):
        """删除检测结果"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute('DELETE FROM detections WHERE id = ?', (detection_id,))
        deleted = cursor.rowcount > 0

        conn.commit()
        conn.close()

        return deleted

    def get_statistics(self):
        """获取统计数据"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # 总检测数
        cursor.execute('SELECT COUNT(*) FROM detections')
        total = cursor.fetchone()[0]

        # 成功检测数（有桩号的）
        cursor.execute('SELECT COUNT(*) FROM detections WHERE pile_number IS NOT NULL AND pile_number != ""')
        successful = cursor.fetchone()[0]

        # 平均置信度
        cursor.execute('SELECT AVG(confidence) FROM detections WHERE confidence > 0')
        avg_confidence = cursor.fetchone()[0] or 0

        # 今日检测数
        today = datetime.now().strftime('%Y-%m-%d')
        cursor.execute('SELECT COUNT(*) FROM detections WHERE DATE(created_at) = ?', (today,))
        today_count = cursor.fetchone()[0]

        # 最近检测
        cursor.execute('''
            SELECT pile_number, confidence, created_at
            FROM detections
            WHERE pile_number IS NOT NULL AND pile_number != ""
            ORDER BY created_at DESC
            LIMIT 10
        ''')
        recent = cursor.fetchall()

        conn.close()

        return {
            'total_detections': total,
            'successful_detections': successful,
            'success_rate': round(successful / total * 100, 1) if total > 0 else 0,
            'avg_confidence': round(avg_confidence * 100, 1),
            'today_count': today_count,
            'recent_detections': [
                {'pile_number': r[0], 'confidence': r[1], 'time': r[2]}
                for r in recent
            ]
        }

    def export_to_json(self, output_path):
        """导出所有数据为JSON"""
        detections = self.get_all_detections(limit=10000)

        export_data = {
            'export_time': datetime.now().isoformat(),
            'total_records': len(detections),
            'detections': detections
        }

        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(export_data, f, ensure_ascii=False, indent=2)

        return output_path

    def export_to_csv(self, output_path):
        """导出所有数据为CSV"""
        import csv

        detections = self.get_all_detections(limit=10000)

        with open(output_path, 'w', newline='', encoding='utf-8-sig') as f:
            writer = csv.writer(f)

            # 写入表头
            writer.writerow(['ID', '文件名', '文件类型', '桩号', '识别文字', '置信度', '检测时间'])

            # 写入数据
            for d in detections:
                writer.writerow([
                    d['id'],
                    d['filename'],
                    d['file_type'],
                    d['pile_number'] or '',
                    d['detected_text'] or '',
                    f"{d['confidence']:.2%}" if d['confidence'] else '0%',
                    d['created_at']
                ])

        return output_path
