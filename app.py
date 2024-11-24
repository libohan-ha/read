from flask import Flask, render_template, request, jsonify
from werkzeug.utils import secure_filename
import os
from learning_app import LearningApp
from flask_cors import CORS
import shutil
import tempfile
import uuid
import logging

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
CORS(app)

# 使用系统临时目录
app.config['UPLOAD_FOLDER'] = os.path.join(tempfile.gettempdir(), 'learning_assistant', 'uploads')
app.config['CHUNK_FOLDER'] = os.path.join(tempfile.gettempdir(), 'learning_assistant', 'chunks')
app.config['MAX_CONTENT_LENGTH'] = 500 * 1024 * 1024  # 500MB max-limit

# 确保上传目录存在并有正确的权限
for folder in [app.config['UPLOAD_FOLDER'], app.config['CHUNK_FOLDER']]:
    try:
        os.makedirs(folder, exist_ok=True)
        logger.info(f"创建目录成功: {folder}")
    except Exception as e:
        logger.error(f"创建目录失败: {str(e)}")

# 初始化学习助手
learning_app = LearningApp(
    api_url='https://xiaoai.plus/v1/chat/completions',
    api_key='sk-wkJ8C4yXkzkXiwUm2e0322A6Bf254239824bC7D6F91a3468',
    model='claude-3-5-sonnet-20240620'
)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/upload', methods=['POST'])
def upload_chunk():
    try:
        if 'file' not in request.files:
            return jsonify({'error': '没有文件被上传'}), 400
        
        file = request.files['file']
        if file.filename == '':
            return jsonify({'error': '没有选择文件'}), 400
            
        chunk = request.form.get('chunk')
        chunks = request.form.get('chunks')
        
        if not all([chunk, chunks]):
            return jsonify({'error': '缺少分块信息'}), 400
            
        # 使用UUID作为临时文件夹名称
        temp_id = str(uuid.uuid4())
        chunk_dir = os.path.join(app.config['CHUNK_FOLDER'], temp_id)
        
        try:
            os.makedirs(chunk_dir, exist_ok=True)
            logger.info(f"创建临时目录成功: {chunk_dir}")
        except Exception as e:
            logger.error(f"创建临时目录失败: {str(e)}")
            return jsonify({'error': f'创建临时目录失败: {str(e)}'}), 500
        
        # 保存分块
        chunk_file = os.path.join(chunk_dir, f'chunk_{chunk}')
        try:
            file.save(chunk_file)
            logger.info(f"保存分块成功: {chunk}/{chunks}")
        except Exception as e:
            logger.error(f"保存文件分块失败: {str(e)}")
            return jsonify({'error': f'保存文件分块失败: {str(e)}'}), 500
        
        return jsonify({
            'message': f'分块 {chunk}/{chunks} 上传成功',
            'temp_id': temp_id
        })
        
    except Exception as e:
        logger.error(f"上传分块时出错: {str(e)}", exc_info=True)
        return jsonify({'error': str(e)}), 500

@app.route('/upload/complete', methods=['POST'])
def complete_upload():
    try:
        data = request.json
        filename = secure_filename(data['filename'])
        temp_id = data.get('temp_id')
        
        if not temp_id:
            return jsonify({'error': '缺少临时ID'}), 400
            
        chunk_dir = os.path.join(app.config['CHUNK_FOLDER'], temp_id)
        
        if not os.path.exists(chunk_dir):
            return jsonify({'error': '找不到上传的文件分块'}), 400
            
        # 合并分块
        output_file = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        try:
            with open(output_file, 'wb') as outfile:
                chunk_files = sorted(os.listdir(chunk_dir), 
                                   key=lambda x: int(x.split('_')[1]))
                
                for chunk_file in chunk_files:
                    chunk_path = os.path.join(chunk_dir, chunk_file)
                    with open(chunk_path, 'rb') as infile:
                        shutil.copyfileobj(infile, outfile)
                        
            logger.info(f"文件合并成功: {output_file}")
            
            # 清理分块文件
            shutil.rmtree(chunk_dir, ignore_errors=True)
            logger.info(f"清理临时文件成功: {chunk_dir}")
            
            # 处理文档
            learning_app.load_document(output_file)
            logger.info("文档处理成功")
            
            return jsonify({
                'message': '文件上传并处理成功',
                'status': 'success',
                'filename': filename
            })
            
        except Exception as e:
            logger.error(f"处理文件时出错: {str(e)}")
            # 清理临时文件
            if os.path.exists(chunk_dir):
                shutil.rmtree(chunk_dir, ignore_errors=True)
            if os.path.exists(output_file):
                os.remove(output_file)
            raise e
            
    except Exception as e:
        logger.error(f"合并文件时出错: {str(e)}", exc_info=True)
        return jsonify({'error': str(e)}), 500

@app.route('/chat', methods=['POST'])
def chat():
    try:
        data = request.json
        message = data.get('message')
        if not message:
            return jsonify({'error': '消息不能为空'}), 400
            
        response = learning_app.chat(message)
        return jsonify({'response': response})
    except Exception as e:
        logger.error(f"处理消息时出错: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/summary', methods=['POST'])
def get_summary():
    try:
        if not learning_app.current_doc:
            return jsonify({'error': '请先上传文档'}), 400
            
        logger.info("开始生成总结")
        summary = learning_app.generate_study_summary()
        logger.info("总结生成成功")
        return jsonify({'summary': summary})
    except Exception as e:
        logger.error(f"生成总结时出错: {str(e)}", exc_info=True)
        return jsonify({'error': str(e)}), 500

@app.route('/review', methods=['POST'])
def get_review():
    try:
        if not learning_app.current_doc:
            return jsonify({'error': '请先上传文档'}), 400
            
        logger.info("开始生成复习建议")
        reviews = learning_app.get_review_suggestions()
        logger.info("复习建议生成成功")
        return jsonify({'reviews': reviews})
    except Exception as e:
        logger.error(f"生成复习建议时出错: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.errorhandler(Exception)
def handle_error(error):
    logger.error(f"服务器错误: {str(error)}", exc_info=True)
    response = {
        'error': str(error),
        'status': 'error'
    }
    return jsonify(response), 500

if __name__ == '__main__':
    app.run(debug=True) 