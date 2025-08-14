import os
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

class Config:
    """WordPress配置类"""
    
    # WordPress网站配置
    WORDPRESS_URL = os.getenv('WORDPRESS_URL', '')
    WORDPRESS_USERNAME = os.getenv('WORDPRESS_USERNAME', '')
    WORDPRESS_APP_PASSWORD = os.getenv('WORDPRESS_APP_PASSWORD', '')
    
    # API配置
    API_TIMEOUT = 30
    MAX_RETRIES = 3
    
    # 内容提取配置
    # 截断关键词：遇到这些关键词时停止复制后续内容
    TRUNCATION_KEYWORDS = [
        'Wrapping Up',
        'Read Next',
        'Conclusion',
        'Final Thoughts',
        'In Summary',
        'To Conclude',
        'Bottom Line',
        'Related Posts',
        'More Reading',
        'Further Reading',
        'Check Out',
        'Don\'t Miss',
        'Popular Posts',
        'Recent Posts',
        'About the Author',
        'Author Bio',
        'Comments',
        'Leave a Reply',
        'Share this',
        'Follow us'
    ]
    
    @classmethod
    def validate_config(cls):
        """验证配置是否完整"""
        required_fields = [
            'WORDPRESS_URL',
            'WORDPRESS_USERNAME', 
            'WORDPRESS_APP_PASSWORD'
        ]
        
        missing_fields = []
        for field in required_fields:
            if not getattr(cls, field):
                missing_fields.append(field)
        
        if missing_fields:
            raise ValueError(f"缺少必要的配置项: {', '.join(missing_fields)}")
        
        return True
