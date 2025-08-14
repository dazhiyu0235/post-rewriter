import requests
import xmlrpc.client
from urllib.parse import urljoin, urlparse
from config import Config
import logging

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class WordPressClient:
    """WordPress客户端类"""
    
    def __init__(self):
        """初始化WordPress客户端"""
        self.config = Config()
        self.config.validate_config()
        
        self.base_url = self.config.WORDPRESS_URL.rstrip('/')
        self.username = self.config.WORDPRESS_USERNAME
        self.password = self.config.WORDPRESS_APP_PASSWORD
        
        # 初始化XML-RPC客户端
        self.xmlrpc_url = urljoin(self.base_url, '/xmlrpc.php')
        self.client = xmlrpc.client.ServerProxy(self.xmlrpc_url)
        
        # 初始化REST API会话
        self.session = requests.Session()
        self.session.auth = (self.username, self.password)
        self.session.headers.update({
            'User-Agent': 'WordPress-Article-Updater/1.0'
        })
    
    def test_connection(self):
        """测试WordPress连接"""
        try:
            # 测试XML-RPC连接
            options = self.client.wp.getOptions(1, self.username, self.password, 'blog_title')
            logger.info(f"成功连接到WordPress: {options.get('blog_title', 'Unknown')}")
            return True
        except Exception as e:
            logger.error(f"连接WordPress失败: {e}")
            return False
    
    def get_post_by_url(self, post_url):
        """根据URL获取文章"""
        try:
            # 解析URL获取文章ID
            parsed_url = urlparse(post_url)
            path_parts = parsed_url.path.strip('/').split('/')
            
            # 尝试从URL中提取文章ID或slug
            if path_parts:
                # 如果是数字，直接作为ID使用
                if path_parts[-1].isdigit():
                    post_id = int(path_parts[-1])
                    return self.get_post_by_id(post_id)
                else:
                    # 否则作为slug使用
                    slug = path_parts[-1]
                    return self.get_post_by_slug(slug)
            
            raise ValueError("无法从URL中提取文章信息")
            
        except Exception as e:
            logger.error(f"获取文章失败: {e}")
            return None
    
    def get_post_by_id(self, post_id):
        """根据ID获取文章"""
        try:
            post = self.client.wp.getPost(1, self.username, self.password, post_id)
            logger.info(f"成功获取文章: {post.get('post_title', 'Unknown')}")
            return post
        except Exception as e:
            logger.error(f"根据ID获取文章失败: {e}")
            return None
    
    def get_post_by_slug(self, slug):
        """根据slug获取文章"""
        try:
            # 使用REST API获取文章
            api_url = urljoin(self.base_url, f'/wp-json/wp/v2/posts?slug={slug}')
            response = self.session.get(api_url, timeout=self.config.API_TIMEOUT)
            response.raise_for_status()
            
            posts = response.json()
            if posts:
                post = posts[0]
                logger.info(f"成功获取文章: {post.get('title', {}).get('rendered', 'Unknown')}")
                return post
            
            logger.error(f"未找到slug为 '{slug}' 的文章")
            return None
            
        except Exception as e:
            logger.error(f"根据slug获取文章失败: {e}")
            return None
    
    def update_post(self, post_id, content, title=None):
        """更新文章内容"""
        try:
            # 准备更新数据
            post_data = {
                'post_content': content
            }
            
            if title:
                post_data['post_title'] = title
            
            # 使用XML-RPC更新文章
            result = self.client.wp.editPost(1, self.username, self.password, post_id, post_data)
            
            if result:
                logger.info(f"成功更新文章 ID: {post_id}")
                return True
            else:
                logger.error(f"更新文章失败 ID: {post_id}")
                return False
                
        except Exception as e:
            logger.error(f"更新文章时发生错误: {e}")
            return False
    
    def get_post_content(self, post):
        """从文章对象中提取内容"""
        if isinstance(post, dict):
            # 检查是否是REST API返回的格式
            if 'content' in post and isinstance(post['content'], dict):
                # REST API返回的格式
                return post.get('content', {}).get('rendered', '')
            else:
                # XML-RPC返回的格式
                return post.get('post_content', '')
        else:
            # 其他格式
            return post.get('content', {}).get('rendered', '')
