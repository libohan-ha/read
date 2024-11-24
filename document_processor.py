from typing import List, Dict
import fitz  # PyMuPDF
import json
import os
from datetime import datetime
import logging
import re
from tqdm import tqdm
import hashlib

# 配置日志
logger = logging.getLogger(__name__)

class DocumentProcessor:
    def __init__(self, chunk_size: int = 4000):
        self.chunk_size = chunk_size
        self.processed_docs = {}
        self.cache_dir = os.path.join(os.path.expanduser('~'), '.learning_assistant', 'cache')
        os.makedirs(self.cache_dir, exist_ok=True)
        
    def process_document(self, file_path: str) -> Dict:
        """处理文档并返回处理结果"""
        try:
            logger.info(f"开始处理文档: {file_path}")
            
            # 检查缓存
            cache_key = self._get_cache_key(file_path)
            cached_result = self._get_cached_result(cache_key)
            if cached_result:
                logger.info("使用缓存的处理结果")
                return cached_result
            
            if not os.path.exists(file_path):
                raise FileNotFoundError(f"文件不存在: {file_path}")
                
            file_ext = os.path.splitext(file_path)[1].lower()
            
            # 根据文件类型选择处理方法
            if file_ext == '.pdf':
                chunks = self.process_pdf(file_path)
            elif file_ext in ['.txt', '.md']:
                chunks = self.process_text(file_path)
            else:
                raise ValueError(f"不支持的文件格式: {file_ext}")
                
            if not chunks:
                raise ValueError("文档处理后没有内容")
                
            # 后处理：清理和优化文本块
            chunks = self.post_process_chunks(chunks)
            
            # 保存处理结果
            doc_info = {
                'file_path': file_path,
                'file_name': os.path.basename(file_path),
                'file_type': file_ext,
                'chunks': chunks,
                'chunk_count': len(chunks),
                'total_length': sum(len(chunk) for chunk in chunks),
                'processed_time': datetime.now().isoformat(),
                'chunk_size': self.chunk_size,
                'file_size': os.path.getsize(file_path),
                'file_hash': self._get_file_hash(file_path)
            }
            
            # 缓存处理结果
            self._cache_result(cache_key, doc_info)
            
            logger.info(f"文档处理完成，共 {len(chunks)} 个片段")
            return doc_info
            
        except Exception as e:
            logger.error(f"处理文档时出错: {str(e)}", exc_info=True)
            raise
            
    def _get_cache_key(self, file_path: str) -> str:
        """生成缓存键"""
        file_stat = os.stat(file_path)
        cache_key = f"{file_path}_{file_stat.st_size}_{file_stat.st_mtime}"
        return hashlib.md5(cache_key.encode()).hexdigest()
        
    def _get_file_hash(self, file_path: str) -> str:
        """计算文件哈希值"""
        hasher = hashlib.md5()
        with open(file_path, 'rb') as f:
            for chunk in iter(lambda: f.read(4096), b''):
                hasher.update(chunk)
        return hasher.hexdigest()
        
    def _get_cached_result(self, cache_key: str) -> Dict:
        """获取缓存的处理结果"""
        cache_file = os.path.join(self.cache_dir, f'{cache_key}.json')
        if os.path.exists(cache_file):
            try:
                with open(cache_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                logger.warning(f"读取缓存失败: {str(e)}")
        return None
        
    def _cache_result(self, cache_key: str, doc_info: Dict):
        """缓存处理结果"""
        try:
            cache_file = os.path.join(self.cache_dir, f'{cache_key}.json')
            with open(cache_file, 'w', encoding='utf-8') as f:
                json.dump(doc_info, f, ensure_ascii=False, indent=2)
            logger.info(f"处理结果已缓存: {cache_file}")
        except Exception as e:
            logger.warning(f"缓存结果失败: {str(e)}")
            
    def process_pdf(self, file_path: str) -> List[str]:
        """处理PDF文档"""
        chunks = []
        current_chunk = ""
        
        try:
            doc = fitz.open(file_path)
            total_pages = len(doc)
            
            logger.info(f"开始处理PDF文档，共 {total_pages} 页")
            
            for page_num in tqdm(range(total_pages), desc="处理PDF页面"):
                page = doc[page_num]
                text = page.get_text()
                
                # 处理页面文本
                paragraphs = self._split_into_paragraphs(text)
                for paragraph in paragraphs:
                    if not paragraph.strip():
                        continue
                        
                    # 如果当前块加上新段落会超过大小限制
                    if len(current_chunk) + len(paragraph) > self.chunk_size:
                        if current_chunk:
                            chunks.append(current_chunk.strip())
                            current_chunk = ""
                            
                    current_chunk += paragraph + "\n\n"
                    
                    # 如果当前块已经足够大
                    if len(current_chunk) >= self.chunk_size:
                        chunks.append(current_chunk.strip())
                        current_chunk = ""
                        
            # 添加最后一个块
            if current_chunk.strip():
                chunks.append(current_chunk.strip())
                
            return chunks
            
        except Exception as e:
            logger.error(f"处理PDF文档时出错: {str(e)}", exc_info=True)
            raise
            
    def _split_into_paragraphs(self, text: str) -> List[str]:
        """将文本分割成段落"""
        # 移除多余的空白字符
        text = re.sub(r'\s+', ' ', text)
        
        # 按照常见的段落分隔符分割
        paragraphs = re.split(r'\n\s*\n|\.\s+(?=[A-Z])', text)
        
        # 清理每个段落
        return [p.strip() for p in paragraphs if p.strip()]
        
    def process_text(self, file_path: str) -> List[str]:
        """处理文本文件"""
        chunks = []
        current_chunk = ""
        
        try:
            content = self._read_text_file(file_path)
            paragraphs = self._split_into_paragraphs(content)
            
            for paragraph in paragraphs:
                if len(current_chunk) + len(paragraph) > self.chunk_size:
                    if current_chunk:
                        chunks.append(current_chunk.strip())
                        current_chunk = ""
                        
                current_chunk += paragraph + "\n\n"
                
                if len(current_chunk) >= self.chunk_size:
                    chunks.append(current_chunk.strip())
                    current_chunk = ""
                    
            if current_chunk.strip():
                chunks.append(current_chunk.strip())
                
            return chunks
            
        except Exception as e:
            logger.error(f"处理文本文件时出错: {str(e)}", exc_info=True)
            raise
            
    def _read_text_file(self, file_path: str) -> str:
        """读取文本文件，自动处理编码"""
        encodings = ['utf-8', 'gbk', 'gb2312', 'latin1']
        
        for encoding in encodings:
            try:
                with open(file_path, 'r', encoding=encoding) as f:
                    return f.read()
            except UnicodeDecodeError:
                continue
                
        raise UnicodeDecodeError(f"无法使用支持的编码读取文件: {encodings}")
        
    def post_process_chunks(self, chunks: List[str]) -> List[str]:
        """后处理文本块"""
        processed_chunks = []
        
        for chunk in chunks:
            # 清理空白字符
            chunk = re.sub(r'\s+', ' ', chunk).strip()
            
            # 移除重复的标点符号
            chunk = re.sub(r'([。！？.!?])\1+', r'\1', chunk)
            
            # 确保每个块都以句号结束
            if chunk and not re.search(r'[。.!！?？]$', chunk):
                chunk += '。'
                
            if chunk:
                processed_chunks.append(chunk)
                
        return processed_chunks