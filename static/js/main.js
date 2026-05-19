// 全局变量
let currentFile = null;
let isDetecting = false;

// 初始化
document.addEventListener('DOMContentLoaded', () => {
    initUpload();
    initSliders();
    loadStatistics();
    loadHistory();
});

// 文件上传初始化
function initUpload() {
    const uploadArea = document.getElementById('uploadArea');
    const fileInput = document.getElementById('fileInput');

    uploadArea.addEventListener('click', () => fileInput.click());

    uploadArea.addEventListener('dragover', (e) => {
        e.preventDefault();
        uploadArea.style.borderColor = '#3498db';
        uploadArea.style.background = '#ecf6fd';
    });

    uploadArea.addEventListener('dragleave', () => {
        uploadArea.style.borderColor = '#ccc';
        uploadArea.style.background = '';
    });

    uploadArea.addEventListener('drop', (e) => {
        e.preventDefault();
        uploadArea.style.borderColor = '#ccc';
        uploadArea.style.background = '';
        if (e.dataTransfer.files.length > 0) {
            handleFile(e.dataTransfer.files[0]);
        }
    });

    fileInput.addEventListener('change', (e) => {
        if (e.target.files.length > 0) {
            handleFile(e.target.files[0]);
        }
    });
}

// 滑块初始化
function initSliders() {
    const slider = document.getElementById('sensitivity');
    const display = document.getElementById('sensitivityVal');
    slider.addEventListener('input', () => {
        display.textContent = slider.value + '%';
    });
}

// 处理文件
function handleFile(file) {
    const validTypes = ['image/jpeg', 'image/png', 'image/bmp', 'video/mp4', 'video/avi'];
    if (!validTypes.includes(file.type)) {
        showToast('不支持的文件格式', 'error');
        return;
    }

    currentFile = file;
    const isVideo = file.type.startsWith('video/');

    document.getElementById('fileName').textContent = file.name;
    document.getElementById('fileType').textContent = isVideo ? '视频' : '图片';
    document.getElementById('fileSize').textContent = formatSize(file.size);
    document.getElementById('fileInfo').style.display = 'block';
    document.getElementById('btnStart').disabled = false;

    showToast('文件已加载', 'success');
}

// 清除文件
function clearFile() {
    currentFile = null;
    document.getElementById('fileInfo').style.display = 'none';
    document.getElementById('fileInput').value = '';
    document.getElementById('btnStart').disabled = true;
    document.getElementById('resultImage').style.display = 'none';
    document.getElementById('btnDownload').style.display = 'none';
}

// 格式化文件大小
function formatSize(bytes) {
    if (bytes === 0) return '0 B';
    const k = 1024;
    const sizes = ['B', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return (bytes / Math.pow(k, i)).toFixed(1) + ' ' + sizes[i];
}

// 开始检测
async function startDetection() {
    if (!currentFile) {
        showToast('请先选择文件', 'error');
        return;
    }

    isDetecting = true;
    document.getElementById('btnStart').disabled = true;
    document.getElementById('btnPause').disabled = false;
    document.getElementById('btnStop').disabled = false;

    showLoading('正在上传并处理文件...');
    updateProgress(10, '上传中...');

    const formData = new FormData();
    formData.append('file', currentFile);
    formData.append('sensitivity', document.getElementById('sensitivity').value);
    formData.append('language', document.getElementById('language').value);
    formData.append('sample_rate', document.getElementById('sampleRate').value);

    try {
        updateProgress(30, '检测中...');

        const response = await fetch('/api/upload', {
            method: 'POST',
            body: formData
        });

        const data = await response.json();

        if (data.success) {
            updateProgress(100, '检测完成');
            showResult(data.result);
            showToast('检测完成！', 'success');
            loadStatistics();
            loadHistory();
        } else {
            showToast(data.error || '检测失败', 'error');
            updateProgress(0, '检测失败');
        }
    } catch (error) {
        showToast('网络错误: ' + error.message, 'error');
        updateProgress(0, '检测失败');
    } finally {
        hideLoading();
        resetButtons();
    }
}

// 暂停检测
function pauseDetection() {
    showToast('暂停功能开发中', 'info');
}

// 停止检测
function stopDetection() {
    isDetecting = false;
    resetButtons();
    updateProgress(0, '已停止');
}

// 重置按钮状态
function resetButtons() {
    document.getElementById('btnStart').disabled = !currentFile;
    document.getElementById('btnPause').disabled = true;
    document.getElementById('btnStop').disabled = true;
}

// 显示结果
function showResult(result) {
    if (!result || !result.detections || result.detections.length === 0) {
        document.getElementById('resultPile').textContent = '未检测到';
        document.getElementById('resultText').textContent = '-';
        document.getElementById('resultConf').textContent = '-';
        document.getElementById('resultRegion').textContent = '-';
        document.getElementById('resultStatus').textContent = '无结果';
        return;
    }

    const d = result.detections[0];

    document.getElementById('resultPile').textContent = d.pile_number ? d.pile_number.full : '未识别';
    document.getElementById('resultText').textContent = d.text || '-';
    document.getElementById('resultConf').textContent = (d.confidence * 100).toFixed(1) + '%';
    document.getElementById('resultRegion').textContent = `(${d.region.x}, ${d.region.y}) ${d.region.width}×${d.region.height}`;
    document.getElementById('resultStatus').textContent = '识别成功';
    document.getElementById('resultStatus').style.color = '#27ae60';

    // 显示结果图片
    if (result.result_image) {
        document.getElementById('resultImg').src = '/uploads/' + result.result_image;
        document.getElementById('resultImage').style.display = 'block';
        document.getElementById('btnDownload').style.display = 'inline-flex';
    }
}

// 下载结果图
function downloadResult() {
    const img = document.getElementById('resultImg');
    if (img.src) {
        const link = document.createElement('a');
        link.href = img.src;
        link.download = 'detection_result_' + Date.now() + '.jpg';
        link.click();
    }
}

// 更新进度
function updateProgress(percent, text) {
    document.getElementById('progressBar').style.width = percent + '%';
    document.getElementById('progressText').textContent = text || '';
}

// 加载统计
async function loadStatistics() {
    try {
        const response = await fetch('/api/statistics');
        const data = await response.json();
        if (data.success) {
            const s = data.statistics;
            document.getElementById('statTotal').textContent = s.total_detections;
            document.getElementById('statSuccess').textContent = s.successful_detections;
            document.getElementById('statRate').textContent = s.success_rate + '%';
            document.getElementById('statToday').textContent = s.today_count;
        }
    } catch (e) {
        console.error('加载统计失败:', e);
    }
}

// 加载历史
async function loadHistory() {
    try {
        const response = await fetch('/api/detections?limit=50');
        const data = await response.json();
        if (data.success) {
            renderHistory(data.detections);
        }
    } catch (e) {
        console.error('加载历史失败:', e);
    }
}

// 渲染历史列表
function renderHistory(detections) {
    const list = document.getElementById('historyList');

    if (!detections || detections.length === 0) {
        list.innerHTML = '<p class="empty">暂无检测记录</p>';
        return;
    }

    list.innerHTML = detections.map(d => {
        const time = new Date(d.created_at).toLocaleString('zh-CN');
        const pile = d.pile_number || '未识别';
        const type = d.file_type === 'video' ? '视频' : '图片';

        return `
            <div class="history-item" onclick="viewDetection(${d.id})">
                <div>
                    <span class="pile">${pile}</span>
                    <br>
                    <span class="file">${d.filename} (${type})</span>
                </div>
                <div class="actions">
                    <span class="time">${time}</span>
                    <button class="btn btn-sm btn-danger" onclick="event.stopPropagation(); deleteDetection(${d.id})">
                        <i class="fas fa-trash"></i>
                    </button>
                </div>
            </div>
        `;
    }).join('');
}

// 查看检测详情
async function viewDetection(id) {
    try {
        const response = await fetch('/api/detection/' + id);
        const data = await response.json();
        if (data.success) {
            const d = data.detection;
            document.getElementById('resultPile').textContent = d.pile_number || '未识别';
            document.getElementById('resultText').textContent = d.detected_text || '-';
            document.getElementById('resultConf').textContent = d.confidence ? (d.confidence * 100).toFixed(1) + '%' : '-';
            document.getElementById('resultStatus').textContent = '历史记录';

            if (d.detection_data && d.detection_data.result_image) {
                document.getElementById('resultImg').src = '/uploads/' + d.detection_data.result_image;
                document.getElementById('resultImage').style.display = 'block';
                document.getElementById('btnDownload').style.display = 'inline-flex';
            }
        }
    } catch (e) {
        showToast('加载详情失败', 'error');
    }
}

// 删除检测记录
async function deleteDetection(id) {
    if (!confirm('确定删除此记录？')) return;

    try {
        const response = await fetch('/api/detection/' + id, { method: 'DELETE' });
        const data = await response.json();
        if (data.success) {
            showToast('删除成功', 'success');
            loadHistory();
            loadStatistics();
        }
    } catch (e) {
        showToast('删除失败', 'error');
    }
}

// 搜索历史
async function searchHistory() {
    const keyword = document.getElementById('searchInput').value.trim();
    if (!keyword) {
        loadHistory();
        return;
    }

    try {
        const response = fetch('/api/detections?keyword=' + encodeURIComponent(keyword));
        const data = await (await response).json();
        if (data.success) {
            renderHistory(data.detections);
        }
    } catch (e) {
        showToast('搜索失败', 'error');
    }
}

// 筛选历史
function filterHistory() {
    const filter = document.getElementById('historyFilter').value;
    loadHistory(); // 简化处理，实际可添加筛选参数
}

// 清空历史
async function clearHistory() {
    if (!confirm('确定清空所有历史记录？此操作不可恢复！')) return;

    try {
        const response = await fetch('/api/detections');
        const data = await response.json();

        if (data.success) {
            for (const d of data.detections) {
                await fetch('/api/detection/' + d.id, { method: 'DELETE' });
            }
            showToast('历史已清空', 'success');
            loadHistory();
            loadStatistics();
        }
    } catch (e) {
        showToast('清空失败', 'error');
    }
}

// 导出数据
function exportData(format) {
    window.location.href = '/api/export/' + format;
    showToast('正在导出 ' + format.toUpperCase() + ' 文件...', 'info');
}

// 导入数据
function importData() {
    document.getElementById('importFile').click();
}

// 文件导入处理
document.getElementById('importFile')?.addEventListener('change', async (e) => {
    const file = e.target.files[0];
    if (!file) return;

    const formData = new FormData();
    formData.append('file', file);

    showLoading('正在导入数据...');

    try {
        const response = await fetch('/api/import', {
            method: 'POST',
            body: formData
        });

        const data = await response.json();

        if (data.success) {
            showToast('导入成功: ' + data.imported + ' 条记录', 'success');
            loadHistory();
            loadStatistics();
        } else {
            showToast(data.error || '导入失败', 'error');
        }
    } catch (e) {
        showToast('导入失败: ' + e.message, 'error');
    } finally {
        hideLoading();
        e.target.value = '';
    }
});

// 清空所有数据
async function clearAllData() {
    if (!confirm('确定清空所有数据？此操作将删除所有检测记录和上传文件！')) return;

    try {
        const response = await fetch('/api/clear-all', { method: 'POST' });
        const data = await response.json();

        if (data.success) {
            showToast('所有数据已清空', 'success');
            clearFile();
            loadHistory();
            loadStatistics();
        } else {
            showToast(data.error || '清空失败', 'error');
        }
    } catch (e) {
        showToast('清空失败', 'error');
    }
}

// 显示加载
function showLoading(text) {
    document.getElementById('loadingText').textContent = text || '处理中...';
    document.getElementById('loading').style.display = 'flex';
}

// 隐藏加载
function hideLoading() {
    document.getElementById('loading').style.display = 'none';
}

// 显示提示
function showToast(message, type = 'info') {
    const container = document.getElementById('toastContainer');
    const toast = document.createElement('div');
    toast.className = 'toast ' + type;

    const icons = {
        success: 'fa-check-circle',
        error: 'fa-exclamation-circle',
        info: 'fa-info-circle'
    };

    toast.innerHTML = '<i class="fas ' + (icons[type] || icons.info) + '"></i><span>' + message + '</span>';
    container.appendChild(toast);

    setTimeout(() => {
        toast.style.opacity = '0';
        setTimeout(() => toast.remove(), 300);
    }, 3000);
}

// 回车搜索
document.getElementById('searchInput')?.addEventListener('keypress', (e) => {
    if (e.key === 'Enter') {
        searchHistory();
    }
});
