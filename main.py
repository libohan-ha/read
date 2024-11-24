from document_processor import DocumentProcessor
from chat_manager import ChatManager
from datetime import datetime

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
            self.current_doc = self.document_processor.process_document(file_path)
            print(f"文档处理完成，共 {len(self.current_doc['chunks'])} 个片段")
            
            # 初始化学习进度
            self.learning_progress = {
                'read_chunks': set(),
                'start_time': datetime.now().isoformat(),
                'questions_asked': 0
            }
            
        except Exception as e:
            print(f"文档处理失败: {str(e)}")
            
    def chat(self, message: str):
        """处理用户消息"""
        try:
            if not self.current_doc:
                return "请先加载文档"
                
            # 找到相关上下文
            context = self.chat_manager.find_relevant_context(
                message, 
                self.current_doc['chunks']
            )
            
            # 更新学习进度
            self.learning_progress['questions_asked'] += 1
            
            return self.chat_manager.send_message(message, context)
            
        except Exception as e:
            return f"处理消息时出错: {str(e)}"
        
    def generate_study_summary(self):
        """生成学习总结"""
        if not self.current_doc:
            return "请先加载文档"
            
        # 获取最近学习的内容
        recent_chunks = [self.current_doc['chunks'][i] 
                        for i in self.learning_progress['read_chunks']]
        
        if not recent_chunks:
            return "还没有学习任何内容"
            
        summary = self.chat_manager.generate_summary("\n".join(recent_chunks))
        self.summaries.append({
            'time': datetime.now().isoformat(),
            'content': summary
        })
        
        return summary
        
    def get_review_suggestions(self):
        """获取复习建议"""
        if not self.summaries:
            return "还没有可复习的内容"
            
        # 基于遗忘曲线选择需要复习的内容
        now = datetime.now()
        review_items = []
        
        for summary in self.summaries:
            summary_time = datetime.fromisoformat(summary['time'])
            days_passed = (now - summary_time).days
            
            # 简单的遗忘曲线实现：1天、7天、30天复习
            if days_passed in [1, 7, 30]:
                review_items.append(summary['content'])
                
        return review_items if review_items else "当前没有需要复习的内容"

def main():
    app = LearningApp(
        api_url='https://xiaoai.plus/v1/chat/completions',
        api_key='sk-wkJ8C4yXkzkXiwUm2e0322A6Bf254239824bC7D6F91a3468',
        model='claude-3-5-sonnet-20240620'
    )
    
    print("欢迎使用AI学习助手！")
    print("支持的命令：")
    print("- load <文件路径>：加载文档")
    print("- chat：开始对话")
    print("- summary：生成学习总结")
    print("- review：获取复习建议")
    print("- quit：退出程序")
    
    while True:
        command = input("\n请输入命令: ").strip()
        
        if command.startswith("load "):
            file_path = command[5:].strip()
            app.load_document(file_path)
            
        elif command == "chat":
            print("进入对话模式（输入'exit'退出对话）")
            while True:
                user_input = input("You: ")
                if user_input.lower() == "exit":
                    break
                response = app.chat(user_input)
                print(f"AI: {response}")
                
        elif command == "summary":
            summary = app.generate_study_summary()
            print(f"学习总结：\n{summary}")
            
        elif command == "review":
            reviews = app.get_review_suggestions()
            if isinstance(reviews, list):
                print("建议复习的内容：")
                for i, review in enumerate(reviews, 1):
                    print(f"\n{i}. {review}")
            else:
                print(reviews)
                
        elif command == "quit":
            print("感谢使用！再见！")
            break
            
        else:
            print("未知命令，请重试")

if __name__ == "__main__":
    main() 