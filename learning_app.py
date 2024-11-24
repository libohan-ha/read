from document_processor import DocumentProcessor
from chat_manager import ChatManager
from datetime import datetime
import logging

# 配置日志
logger = logging.getLogger(__name__)

class LearningApp:
    def __init__(self, api_url: str, api_key: str, model: str):
        self.document_processor = DocumentProcessor()
        self.chat_manager = ChatManager(api_url, api_key, model)
        self.current_doc = None
        self.learning_progress = {}
        self.summaries = []
        
    def load_document(self, file_path: str):
        """加载并处理文档"""
        try:
            logger.info(f"开始处理文档: {file_path}")
            self.current_doc = self.document_processor.process_document(file_path)
            
            # 初始化学习进度
            self.learning_progress = {
                'file_path': file_path,
                'start_time': datetime.now().isoformat(),
                'chunks_total': len(self.current_doc['chunks']),
                'chunks_read': set(),
                'questions_asked': 0,
                'last_summary_time': None,
                'last_review_time': None
            }
            
            logger.info(f"文档处理完成，共 {len(self.current_doc['chunks'])} 个片段")
            return True
            
        except Exception as e:
            logger.error(f"文档处理失败: {str(e)}", exc_info=True)
            raise Exception(f"文档处理失败: {str(e)}")
            
    def chat(self, message: str):
        """处理用户消息"""
        if not self.current_doc:
            return "请先加载文档"
            
        try:
            logger.info(f"处理用户消息: {message[:100]}...")
            
            # 找到相关上下文
            context = self.chat_manager.find_relevant_context(
                message, 
                self.current_doc['chunks']
            )
            
            # 更新学习进度
            self.learning_progress['questions_asked'] += 1
            
            # 记录已读片段
            for i, chunk in enumerate(self.current_doc['chunks']):
                if chunk in context:
                    self.learning_progress['chunks_read'].add(i)
                    
            logger.info(f"已读片段数: {len(self.learning_progress['chunks_read'])}")
            
            return self.chat_manager.send_message(message, context)
            
        except Exception as e:
            logger.error(f"处理消息失败: {str(e)}", exc_info=True)
            raise Exception(f"处理消息失败: {str(e)}")
            
    def generate_study_summary(self):
        """生成学习总结"""
        try:
            if not self.current_doc:
                return "请先上传文档"
            
            logger.info("开始生成学习总结")
            
            # 使用完整的文档内容生成总结
            context = "\n".join(self.current_doc['chunks'])
            summary = self.chat_manager.generate_summary(context)
            
            # 记录总结
            self.summaries.append({
                'time': datetime.now().isoformat(),
                'content': summary,
                'chunks_covered': len(self.learning_progress['chunks_read']),
                'questions_asked': self.learning_progress['questions_asked']
            })
            
            self.learning_progress['last_summary_time'] = datetime.now().isoformat()
            
            logger.info("学习总结生成成功")
            return summary
            
        except Exception as e:
            logger.error(f"生成总结失败: {str(e)}", exc_info=True)
            raise Exception(f"生成总结失败: {str(e)}")
            
    def get_review_suggestions(self):
        """获取复习建议"""
        try:
            if not self.current_doc:
                return "请先上传文档"
            
            logger.info("开始生成复习建议")
            
            # 获取已学习内容
            read_chunks = [self.current_doc['chunks'][i] 
                          for i in self.learning_progress['chunks_read']]
            
            if not read_chunks:
                return "还没有学习任何内容"
            
            # 生成复习建议
            context = "\n".join(read_chunks)
            review = self.chat_manager.send_message(
                "请针对以下已学习的内容生成复习建议和重点提示",
                context
            )
            
            self.learning_progress['last_review_time'] = datetime.now().isoformat()
            
            logger.info("复习建议生成成功")
            return review
            
        except Exception as e:
            logger.error(f"生成复习建议失败: {str(e)}", exc_info=True)
            raise Exception(f"生成复习建议失败: {str(e)}")
            
    def get_learning_progress(self):
        """获取学习进度统计"""
        if not self.current_doc:
            return "未加载文档"
            
        total_chunks = len(self.current_doc['chunks'])
        read_chunks = len(self.learning_progress['chunks_read'])
        progress = {
            'total_chunks': total_chunks,
            'read_chunks': read_chunks,
            'progress_percentage': round(read_chunks / total_chunks * 100, 2),
            'questions_asked': self.learning_progress['questions_asked'],
            'summaries_count': len(self.summaries),
            'start_time': self.learning_progress['start_time'],
            'last_summary_time': self.learning_progress['last_summary_time'],
            'last_review_time': self.learning_progress['last_review_time']
        }
        
        return progress