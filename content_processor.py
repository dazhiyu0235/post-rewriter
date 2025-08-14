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
    
    def extract_text_and_images_separately(self, html_content):
        """
        分别提取文字内容和图片内容
        
        Returns:
            dict: {'text_content': str, 'images_content': str}
        """
        try:
            # 解析HTML
            self.soup = BeautifulSoup(html_content, 'html.parser')
            
            # 提取所有图片
            images = self.soup.find_all('img')
            images_html = []
            for img in images:
                images_html.append(str(img))
            
            # 创建一个副本用于提取文字
            text_soup = BeautifulSoup(html_content, 'html.parser')
            
            # 从文字版本中移除所有图片
            for img in text_soup.find_all('img'):
                img.decompose()
            
            # 移除其他媒体元素
            for tag in text_soup.find_all(['figure', 'picture', 'source']):
                tag.decompose()
            
            # 获取纯文字内容
            text_content = str(text_soup)
            
            # 获取图片内容
            images_content = '\n'.join(images_html) if images_html else ''
            
            logger.info(f"分离提取: 文字长度={len(text_content)}, 图片数量={len(images)}")
            
            return {
                'text_content': text_content,
                'images_content': images_content
            }
            
        except Exception as e:
            logger.error(f"分离提取内容时发生错误: {e}")
            return {'text_content': html_content, 'images_content': ''}
    
    def extract_description_and_images_only(self, html_content, max_description_paragraphs=2):
        """
        只提取文章描述部分和图片，清空其他内容
        
        Args:
            html_content: HTML内容
            max_description_paragraphs: 保留的描述段落数量（默认前2段）
            
        Returns:
            dict: {'description_content': str, 'images_content': str}
        """
        try:
            # 解析HTML
            soup = BeautifulSoup(html_content, 'html.parser')
            
            # 提取所有图片
            images = soup.find_all('img')
            images_html = []
            for img in images:
                images_html.append(str(img))
            
            # 创建一个副本用于提取描述
            desc_soup = BeautifulSoup(html_content, 'html.parser')
            
            # 移除所有图片和媒体元素
            for img in desc_soup.find_all('img'):
                img.decompose()
            for tag in desc_soup.find_all(['figure', 'picture', 'source']):
                tag.decompose()
            
            # 查找文章的前几个段落作为描述
            paragraphs = desc_soup.find_all('p')
            description_paragraphs = []
            
            # 只保留前几个有实质内容的段落
            for p in paragraphs[:max_description_paragraphs * 2]:  # 多取一些以防有空段落
                text = p.get_text(strip=True)
                if text and len(text) > 20:  # 过滤掉太短的段落
                    description_paragraphs.append(str(p))
                    if len(description_paragraphs) >= max_description_paragraphs:
                        break
            
            # 如果没找到足够的段落，尝试其他方法
            if not description_paragraphs:
                # 查找其他可能的描述元素
                for tag in desc_soup.find_all(['div', 'section']):
                    text = tag.get_text(strip=True)
                    if 50 <= len(text) <= 500:  # 描述长度在合理范围内
                        description_paragraphs.append(str(tag))
                        break
            
            # 合并描述内容
            description_content = '\n\n'.join(description_paragraphs) if description_paragraphs else ''
            
            # 获取图片内容
            images_content = '\n'.join(images_html) if images_html else ''
            
            logger.info(f"提取描述和图片: 描述长度={len(description_content)}, 图片数量={len(images)}")
            logger.info(f"保留的描述段落数: {len(description_paragraphs)}")
            
            return {
                'description_content': description_content,
                'images_content': images_content
            }
            
        except Exception as e:
            logger.error(f"提取描述和图片时发生错误: {e}")
            return {'description_content': '', 'images_content': ''}
