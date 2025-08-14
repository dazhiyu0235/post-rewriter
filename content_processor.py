from bs4 import BeautifulSoup
import re
import logging

logger = logging.getLogger(__name__)

class ContentProcessor:
    """内容处理器类，用于处理HTML内容"""
    
    def __init__(self):
        """初始化内容处理器"""
        self.soup = None
    
    def process_content(self, html_content):
        """处理HTML内容，删除文字但保留图片"""
        try:
            # 解析HTML
            self.soup = BeautifulSoup(html_content, 'html.parser')
            
            # 备份原始内容
            original_content = str(self.soup)
            
            # 删除文字内容但保留图片
            self._remove_text_keep_images()
            
            # 获取处理后的内容
            processed_content = str(self.soup)
            
            # 记录处理结果
            self._log_processing_results(original_content, processed_content)
            
            return processed_content
            
        except Exception as e:
            logger.error(f"处理内容时发生错误: {e}")
            return html_content
    
    def _remove_text_keep_images(self):
        """删除文字但保留图片"""
        if not self.soup:
            return
        
        # 保留的标签
        keep_tags = ['img', 'figure', 'figcaption', 'picture', 'source']
        
        # 遍历所有元素
        for element in self.soup.find_all():
            # 如果是需要保留的标签，跳过
            if element.name in keep_tags:
                continue
            
            # 如果元素包含图片，只保留图片部分
            if element.find('img'):
                # 找到所有图片
                images = element.find_all('img')
                # 清空元素内容
                element.clear()
                # 重新添加图片
                for img in images:
                    element.append(img)
            else:
                # 如果元素不包含图片，删除该元素
                element.decompose()
        
        # 清理空的容器元素
        self._clean_empty_containers()
    
    def _clean_empty_containers(self):
        """清理空的容器元素"""
        if not self.soup:
            return
        
        # 常见的空容器标签
        empty_containers = ['div', 'p', 'span', 'section', 'article', 'header', 'footer']
        
        for tag_name in empty_containers:
            for element in self.soup.find_all(tag_name):
                # 如果元素没有内容或只有空白字符，删除它
                if not element.get_text(strip=True) and not element.find('img'):
                    element.decompose()
    
    def _log_processing_results(self, original_content, processed_content):
        """记录处理结果"""
        # 统计原始内容中的图片数量
        original_soup = BeautifulSoup(original_content, 'html.parser')
        original_images = len(original_soup.find_all('img'))
        
        # 统计处理后内容中的图片数量
        processed_images = len(self.soup.find_all('img')) if self.soup else 0
        
        # 计算删除的文字长度
        original_text_length = len(original_soup.get_text(strip=True))
        processed_text_length = len(self.soup.get_text(strip=True)) if self.soup else 0
        
        logger.info(f"内容处理完成:")
        logger.info(f"  - 原始图片数量: {original_images}")
        logger.info(f"  - 保留图片数量: {processed_images}")
        logger.info(f"  - 删除文字长度: {original_text_length - processed_text_length} 字符")
        logger.info(f"  - 图片保留率: {(processed_images/original_images*100):.1f}%" if original_images > 0 else "  - 图片保留率: N/A")
    
    def get_image_info(self, html_content):
        """获取图片信息"""
        try:
            soup = BeautifulSoup(html_content, 'html.parser')
            images = soup.find_all('img')
            
            image_info = []
            for i, img in enumerate(images):
                info = {
                    'index': i + 1,
                    'src': img.get('src', ''),
                    'alt': img.get('alt', ''),
                    'title': img.get('title', ''),
                    'width': img.get('width', ''),
                    'height': img.get('height', ''),
                    'class': img.get('class', [])
                }
                image_info.append(info)
            
            return image_info
            
        except Exception as e:
            logger.error(f"获取图片信息时发生错误: {e}")
            return []
    
    def validate_images(self, html_content):
        """验证图片是否完整保留"""
        try:
            soup = BeautifulSoup(html_content, 'html.parser')
            images = soup.find_all('img')
            
            valid_images = []
            invalid_images = []
            
            for img in images:
                src = img.get('src', '')
                if src and (src.startswith('http') or src.startswith('/')):
                    valid_images.append(img)
                else:
                    invalid_images.append(img)
            
            return {
                'total': len(images),
                'valid': len(valid_images),
                'invalid': len(invalid_images),
                'valid_images': valid_images,
                'invalid_images': invalid_images
            }
            
        except Exception as e:
            logger.error(f"验证图片时发生错误: {e}")
            return {'total': 0, 'valid': 0, 'invalid': 0, 'valid_images': [], 'invalid_images': []}
