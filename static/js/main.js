async function handleFileUpload(file) {
    // 检查文件类型
    const allowedTypes = ['.pdf', '.txt', '.md'];
    const fileExt = file.name.substring(file.name.lastIndexOf('.')).toLowerCase();
    if (!allowedTypes.includes(fileExt)) {
        showMessage('系统', `不支持的文件格式。支持的格式：${allowedTypes.join(', ')}`);
        return;
    }
    
    // 检查文件大小 (500MB)
    const maxSize = 500 * 1024 * 1024;
    if (file.size > maxSize) {
        showMessage('系统', '文件太大，最大支持500MB');
        return;
    }
    
    try {
        // 分块上传
        const chunkSize = 5 * 1024 * 1024; // 5MB chunks
        const chunks = Math.ceil(file.size / chunkSize);
        let uploadedChunks = 0;
        let tempId = null;  // 用于存储临时ID
        
        showMessage('系统', '开始上传文件...');
        showCircleProgress('uploadProgress');
        
        for (let i = 0; i < chunks; i++) {
            const start = i * chunkSize;
            const end = Math.min(file.size, start + chunkSize);
            const chunk = file.slice(start, end);
            
            const formData = new FormData();
            formData.append('file', chunk, file.name);
            formData.append('chunk', i.toString());
            formData.append('chunks', chunks.toString());
            
            const response = await fetch('/upload', {
                method: 'POST',
                body: formData,
            });
            
            if (!response.ok) {
                const data = await response.json();
                throw new Error(data.error || `上传失败 (${response.status})`);
            }
            
            const responseData = await response.json();
            if (responseData.temp_id) {
                tempId = responseData.temp_id;  // 保存临时ID
            }
            
            uploadedChunks++;
            showMessage('系统', `已上传 ${uploadedChunks}/${chunks} 块`);
        }
        
        showMessage('系统', '文件上传完成，正在处理...');
        
        // 完成上传
        const finalResponse = await fetch('/upload/complete', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ 
                filename: file.name,
                temp_id: tempId
            })
        });
        
        if (!finalResponse.ok) {
            const data = await finalResponse.json();
            throw new Error(data.error || '文件处理失败');
        }
        
        const data = await finalResponse.json();
        removeCircleProgress('uploadProgress');
        showMessage('系统', '✅ ' + (data.message || '文件上传并处理成功！现在可以开始对话了。'));
        
        // 启用所有功能
        document.getElementById('messageInput').disabled = false;
        document.getElementById('sendButton').disabled = false;
        updateButtonStates(true);
    } catch (error) {
        console.error('Upload error:', error);
        removeCircleProgress('uploadProgress');
        showMessage('系统', `❌ 上传失败：${error.message}`);
        updateButtonStates(false);
    }
}

// 开始对话
function startChat() {
    showMessage('系统', '开始对话，请输入您的问题...');
    // 启用输入框和发送按钮
    document.getElementById('messageInput').disabled = false;
    document.getElementById('sendButton').disabled = false;
}

// 发送消息
async function sendMessage() {
    const messageInput = document.getElementById('messageInput');
    const message = messageInput.value.trim();
    
    if (!message) return;
    
    showMessage('用户', message, 'user-message');
    messageInput.value = '';
    
    // 显示加载中的进度条
    showCircleProgress('chatProgress');
    
    try {
        const response = await fetch('/chat', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ message })
        });
        
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        
        const data = await response.json();
        showMessage('AI', data.response, 'ai-message');
        removeCircleProgress('chatProgress');
    } catch (error) {
        console.error('Send message error:', error);
        showMessage('系统', `发送失败：${error.message}`);
        removeCircleProgress('chatProgress');
    }
}

// 改进消息显示函数，添加时间戳和内容处理
function showMessage(sender, content, className = '') {
    const chatContainer = document.getElementById('chatContainer');
    const messageDiv = document.createElement('div');
    messageDiv.className = `message ${className}`;
    
    // 添加时间戳
    const timestamp = new Date().toLocaleTimeString();
    
    // 处理内容中的特殊字符
    const processedContent = content.replace(/\*/g, '');
    
    messageDiv.innerHTML = `
        <div class="message-header">
            <strong>${sender}</strong>
            <span class="timestamp">${timestamp}</span>
        </div>
        <div class="message-content">${processedContent}</div>
    `;
    
    chatContainer.appendChild(messageDiv);
    chatContainer.scrollTop = chatContainer.scrollHeight;
    return messageDiv;
}

// 文件上传处理
let isInitialized = false;  // 防止重复初始化

function initializeEventListeners() {
    if (isInitialized) return;  // 如果已经初始化过，直接返回
    
    const dropZone = document.getElementById('dropZone');
    const fileInput = document.getElementById('fileInput');
    const messageInput = document.getElementById('messageInput');
    
    if (!dropZone || !fileInput || !messageInput) {
        console.error('找不到必要的DOM元素');
        return;
    }

    // 点击上传区域触发文件选择
    dropZone.addEventListener('click', () => {
        fileInput.click();
    });

    // 文件选择变化时处理
    fileInput.addEventListener('change', (e) => {
        const file = e.target.files[0];
        if (file) {
            handleFileUpload(file);
        }
    });

    // 处理拖拽
    dropZone.addEventListener('dragover', (e) => {
        e.preventDefault();
        dropZone.classList.add('dragover');
    });

    dropZone.addEventListener('dragleave', () => {
        dropZone.classList.remove('dragover');
    });

    dropZone.addEventListener('drop', (e) => {
        e.preventDefault();
        dropZone.classList.remove('dragover');
        const file = e.dataTransfer.files[0];
        if (file) {
            handleFileUpload(file);
        }
    });

    // 添加回车发送功能
    messageInput.addEventListener('keypress', (e) => {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            sendMessage();
        }
    });

    // 禁用输入框和发送按钮
    messageInput.disabled = true;
    const sendButton = document.getElementById('sendButton');
    if (sendButton) sendButton.disabled = true;

    isInitialized = true;  // 标记为已初始化
}

// 在页面加载完成后初始化事件监听
document.addEventListener('DOMContentLoaded', initializeEventListeners); 

// 生成总结
async function getSummary() {
    // 检查是否已加载文档
    const messageInput = document.getElementById('messageInput');
    if (messageInput.disabled) {
        showMessage('系统', '请先上传并处理文档');
        return;
    }

    showMessage('系统', '正在生成学习总结...');
    showCircleProgress('summaryProgress');
    
    try {
        const response = await fetch('/summary', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            }
        });
        
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        
        const responseData = await response.json();
        if (responseData.error) {
            throw new Error(responseData.error);
        }

        // 创建总结内容的消息元素
        const messageDiv = showMessage('系统', '', 'ai-message');
        
        // 创建总结内容容器
        const summaryContent = document.createElement('div');
        summaryContent.className = 'summary-content';
        
        // 添加总结文本
        summaryContent.innerHTML = `
            <div class="summary-title">📚 学习总结</div>
            <div class="summary-text">${responseData.summary}</div>
            <div class="mindmap-container" id="mindmap-${Date.now()}"></div>
        `;
        
        // 将总结内容添加到消息中
        messageDiv.querySelector('.message-content').appendChild(summaryContent);
        
        // 等待DOM更新
        await new Promise(resolve => setTimeout(resolve, 100));
        
        // 获取思维导图容器
        const mindmapContainer = summaryContent.querySelector('.mindmap-container');
        
        // 初始化思维导图
        try {
            const { Transformer } = window.markmap;
            if (!Transformer) {
                throw new Error('Markmap transformer not loaded');
            }
            
            const transformer = new Transformer();
            const markdown = responseData.summary;
            const { root: mindmapData } = transformer.transform(markdown);
            
            if (mindmapContainer) {
                initMindmap(mindmapContainer, mindmapData);
            }
        } catch (error) {
            console.error('思维导图创建失败:', error);
            mindmapContainer.innerHTML = `
                <div class="error-message">
                    思维导图加载失败: ${error.message}
                    <br>
                    <small>请检查网络连接或刷新页面重试</small>
                </div>
            `;
        }
        
        removeCircleProgress('summaryProgress');
        
    } catch (error) {
        console.error('Summary error:', error);
        removeCircleProgress('summaryProgress');
        showMessage('系统', `❌ 生成总结失败：${error.message}`);
    }
}

// 解析内容为思维导图数据结构
function parseContentToMindmap(content) {
    const lines = content.split('\n');
    const nodes = [];
    let currentNode = null;
    
    for (const line of lines) {
        const trimmedLine = line.trim();
        if (!trimmedLine) continue;
        
        if (trimmedLine.startsWith('# ')) {
            // 主标题
            currentNode = {
                t: trimmedLine.substring(2),
                c: []
            };
            nodes.push(currentNode);
        } else if (trimmedLine.startsWith('## ')) {
            // 子标题
            if (currentNode) {
                const subNode = {
                    t: trimmedLine.substring(3),
                    c: []
                };
                currentNode.c.push(subNode);
            }
        } else if (trimmedLine.startsWith('- ')) {
            // 列表项
            const item = {
                t: trimmedLine.substring(2)
            };
            if (currentNode && currentNode.c.length > 0) {
                currentNode.c[currentNode.c.length - 1].c.push(item);
            } else if (currentNode) {
                currentNode.c.push(item);
            } else {
                nodes.push(item);
            }
        }
    }
    
    return nodes;
}

// 获取复习建议
async function getReview() {
    // 检查是否已加载文档
    const messageInput = document.getElementById('messageInput');
    if (messageInput.disabled) {
        showMessage('系统', '请先上传并处理文档');
        return;
    }

    showMessage('系统', '正在生成复习建议...');
    
    showCircleProgress('reviewProgress');
    updateCircleProgress(50, 'reviewProgress');
    
    try {
        const response = await fetch('/review', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            }
        });
        
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        
        const data = await response.json();
        if (data.error) {
            throw new Error(data.error);
        }
        
        if (Array.isArray(data.reviews)) {
            showMessage('系统', '📝 复习建议：');
            data.reviews.forEach((review, index) => {
                showMessage('系统', `${index + 1}. ${review}`);
            });
        } else {
            showMessage('系统', '📝 ' + data.reviews);
        }
        removeCircleProgress('reviewProgress');
    } catch (error) {
        console.error('Review error:', error);
        showMessage('系统', `❌ 获取复习建议失败：${error.message}`);
        removeCircleProgress('reviewProgress');
    }
}

// 更新按钮状态函数
function updateButtonStates(enabled) {
    const buttons = document.querySelectorAll('.action-btn');
    buttons.forEach(button => {
        button.disabled = !enabled;
    });
}

// 在页面加载时禁用所有按钮
document.addEventListener('DOMContentLoaded', () => {
    const messageInput = document.getElementById('messageInput');
    const sendButton = document.getElementById('sendButton');
    
    if (messageInput) messageInput.disabled = true;
    if (sendButton) sendButton.disabled = true;
    updateButtonStates(false);
}); 

// 圆形进度条相关函数
function showCircleProgress(containerId = 'uploadProgress') {
    const chatContainer = document.getElementById('chatContainer');
    const progressDiv = document.createElement('div');
    progressDiv.className = 'circle-progress-container';
    progressDiv.id = containerId;
    progressDiv.innerHTML = `
        <div class="circle-progress loading">
            <div class="circle-progress-circle">
                <div class="circle-progress-mask full">
                    <div class="circle-progress-fill"></div>
                </div>
                <div class="circle-progress-mask">
                    <div class="circle-progress-fill"></div>
                </div>
                <div class="circle-progress-inside">处理中</div>
            </div>
        </div>
    `;
    chatContainer.appendChild(progressDiv);
}

// 移除进度条
function removeCircleProgress(containerId = 'uploadProgress') {
    const progressDiv = document.getElementById(containerId);
    if (progressDiv) {
        progressDiv.remove();
    }
}

// 下载思维导��
function downloadMindmap() {
    const mindmapContainer = document.querySelector('.mindmap-container');
    if (!mindmapContainer) return;
    
    const svg = mindmapContainer.querySelector('svg');
    if (!svg) {
        console.error('找不到思维导图SVG');
        return;
    }
    
    try {
        // 克隆SVG以进行修改
        const clonedSvg = svg.cloneNode(true);
        
        // 设置样式
        const style = document.createElement('style');
        style.textContent = `
            .markmap-node-text { font-family: Arial, sans-serif; }
            .markmap-link { stroke: #007AFF; }
            .markmap-node-circle { fill: #007AFF; }
        `;
        clonedSvg.appendChild(style);
        
        // 转换为字符串
        const svgData = new XMLSerializer().serializeToString(clonedSvg);
        const svgBlob = new Blob([svgData], { type: 'image/svg+xml;charset=utf-8' });
        
        // 创建下载链接
        const downloadLink = document.createElement('a');
        downloadLink.href = URL.createObjectURL(svgBlob);
        downloadLink.download = `mindmap_${Date.now()}.svg`;
        
        // 触发下载
        document.body.appendChild(downloadLink);
        downloadLink.click();
        document.body.removeChild(downloadLink);
        
        // 清理
        URL.revokeObjectURL(downloadLink.href);
        
        showMessage('系统', '✅ 思维导图已下载');
    } catch (error) {
        console.error('下载思维导图失败:', error);
        showMessage('系统', '❌ 下载失败：' + error.message);
    }
}

// 修改思维导图初始化代码
function initMindmap(container, data) {
    try {
        const { Markmap } = window.markmap;
        if (!Markmap) {
            throw new Error('Markmap not loaded');
        }
        
        // 创建思维导图实例
        const mm = Markmap.create(container, {
            autoFit: true,
            color: d => '#007AFF',
            duration: 500,
            maxWidth: 300,
            nodeMinHeight: 16,
            spacingHorizontal: 80,
            spacingVertical: 10,
            paddingX: 20,
            initialExpandLevel: 2, // 初始展开两级
            zoom: true,
            pan: true,
        }, data);
        
        // 添加控制按钮
        const template = document.getElementById('mindmap-controls-template');
        if (template) {
            const controls = template.content.cloneNode(true);
            container.appendChild(controls);
            
            // 存储mindmap实例供控制按钮使用
            window.mindmap = mm;
        }
        
        // 自动调整大小
        window.addEventListener('resize', () => {
            mm.fit();
        });
        
        // 初始化完成后自动适应大小
        mm.fit();
        
        return mm;
    } catch (error) {
        console.error('思维导图创建失败:', error);
        container.innerHTML = `
            <div class="error-message">
                思维导图加载失败: ${error.message}
                <br>
                <small>请检查网络连接或刷新页面重试</small>
            </div>
        `;
        return null;
    }
} 