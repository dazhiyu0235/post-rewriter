from wordpress_client import WordPressClient
from content_processor import ContentProcessor
import logging
import time

logger = logging.getLogger(__name__)

class ArticleUpdater:
    """文章更新器主类"""
    
    def __init__(self):
        """初始化文章更新器"""
        self.wp_client = WordPressClient()
        self.content_processor = ContentProcessor()
        
        # 测试连接
        if not self.wp_client.test_connection():
            raise ConnectionError("无法连接到WordPress网站，请检查配置")
    
    def update_article_by_url(self, post_url, dry_run=False):
        """根据URL更新文章"""
        try:
            logger.info(f"开始处理文章: {post_url}")
            
            # 获取文章
            post = self.wp_client.get_post_by_url(post_url)
            if not post:
                logger.error(f"无法获取文章: {post_url}")
                return False
            
            # 获取文章内容
            original_content = self.wp_client.get_post_content(post)
            if not original_content:
                logger.warning(f"文章内容为空: {post_url}")
                return False
            
            # 处理内容
            logger.info("开始处理文章内容...")
            processed_content = self.content_processor.process_content(original_content)
            
            # 验证处理结果
            validation_result = self.content_processor.validate_images(processed_content)
            logger.info(f"图片验证结果: {validation_result['valid']}/{validation_result['total']} 张图片有效")
            
            # 如果是试运行模式，只显示结果不更新
            if dry_run:
                logger.info("试运行模式 - 不会实际更新文章")
                self._show_preview(original_content, processed_content)
                return True
            
            # 获取文章ID
            post_id = self._get_post_id(post)
            if not post_id:
                logger.error("无法获取文章ID")
                return False
            
            # 更新文章
            logger.info("开始更新文章...")
            success = self.wp_client.update_post(post_id, processed_content)
            
            if success:
                logger.info(f"文章更新成功: {post_url}")
                return True
            else:
                logger.error(f"文章更新失败: {post_url}")
                return False
                
        except Exception as e:
            logger.error(f"更新文章时发生错误: {e}")
            return False
    
    def update_multiple_articles(self, post_urls, dry_run=False):
        """批量更新多篇文章"""
        results = {
            'total': len(post_urls),
            'success': 0,
            'failed': 0,
            'details': []
        }
        
        logger.info(f"开始批量更新 {len(post_urls)} 篇文章")
        
        for i, url in enumerate(post_urls, 1):
            logger.info(f"处理第 {i}/{len(post_urls)} 篇文章: {url}")
            
            try:
                success = self.update_article_by_url(url, dry_run)
                
                result_detail = {
                    'url': url,
                    'success': success,
                    'timestamp': time.strftime('%Y-%m-%d %H:%M:%S')
                }
                
                if success:
                    results['success'] += 1
                    logger.info(f"✓ 文章处理成功: {url}")
                else:
                    results['failed'] += 1
                    logger.error(f"✗ 文章处理失败: {url}")
                
                results['details'].append(result_detail)
                
                # 添加延迟避免请求过于频繁
                if i < len(post_urls):
                    time.sleep(2)
                    
            except Exception as e:
                logger.error(f"处理文章时发生异常: {url} - {e}")
                results['failed'] += 1
                results['details'].append({
                    'url': url,
                    'success': False,
                    'error': str(e),
                    'timestamp': time.strftime('%Y-%m-%d %H:%M:%S')
                })
        
        # 输出总结
        self._print_summary(results)
        return results
    
    def _get_post_id(self, post):
        """从文章对象中获取ID"""
        if isinstance(post, dict):
            # 检查是否是REST API格式
            if 'id' in post:
                # REST API格式
                return post.get('id')
            else:
                # XML-RPC格式
                return post.get('post_id')
        else:
            # 其他格式
            return post.get('id')
    
    def _show_preview(self, original_content, processed_content):
        """显示预览信息"""
        logger.info("=== 内容处理预览 ===")
        
        # 获取图片信息
        original_images = self.content_processor.get_image_info(original_content)
        processed_images = self.content_processor.get_image_info(processed_content)
        
        logger.info(f"原始内容图片数量: {len(original_images)}")
        logger.info(f"处理后图片数量: {len(processed_images)}")
        
        if processed_images:
            logger.info("保留的图片:")
            for img in processed_images:
                logger.info(f"  - {img['src']} (alt: {img['alt']})")
        
        # 计算文字删除量
        from bs4 import BeautifulSoup
        original_soup = BeautifulSoup(original_content, 'html.parser')
        processed_soup = BeautifulSoup(processed_content, 'html.parser')
        
        original_text = original_soup.get_text(strip=True)
        processed_text = processed_soup.get_text(strip=True)
        
        logger.info(f"原始文字长度: {len(original_text)} 字符")
        logger.info(f"处理后文字长度: {len(processed_text)} 字符")
        logger.info(f"删除文字长度: {len(original_text) - len(processed_text)} 字符")
    
    def _print_summary(self, results):
        """打印处理总结"""
        logger.info("=== 批量处理总结 ===")
        logger.info(f"总文章数: {results['total']}")
        logger.info(f"成功: {results['success']}")
        logger.info(f"失败: {results['failed']}")
        logger.info(f"成功率: {(results['success']/results['total']*100):.1f}%")
        
        if results['failed'] > 0:
            logger.info("失败的文章:")
            for detail in results['details']:
                if not detail['success']:
                    logger.info(f"  - {detail['url']}")
                    if 'error' in detail:
                        logger.info(f"    错误: {detail['error']}")
    
    def get_article_info(self, post_url):
        """获取文章信息"""
        try:
            post = self.wp_client.get_post_by_url(post_url)
            if not post:
                return None
            
            content = self.wp_client.get_post_content(post)
            image_info = self.content_processor.get_image_info(content)
            
            return {
                'post': post,
                'content_length': len(content),
                'image_count': len(image_info),
                'images': image_info
            }
            
        except Exception as e:
            logger.error(f"获取文章信息时发生错误: {e}")
            return None
