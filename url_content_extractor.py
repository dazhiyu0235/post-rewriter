#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
URL内容提取器
从指定URL提取文章内容，保留原格式
"""

import requests
from bs4 import BeautifulSoup
import re
from urllib.parse import urlparse
import logging
from typing import Optional, Dict, Any
import time

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class URLContentExtractor:
    """URL内容提取器"""
    
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        })
        
        # 常见的内容选择器
        self.content_selectors = [
            'article',
            '.post-content',
            '.entry-content',
            '.content',
            '.article-content',
            '.post-body',
            '.story-body',
            '.main-content',
            '#content',
            '#main-content',
            '.text-content',
            '.article-text',
            '.post',
            '.single-post',
            '.blog-post',
            '.page-content',
            'main',
            '[role="main"]',
            '.container .content',
            '.wrapper .content'
        ]
        
        # 需要移除的元素
        self.remove_selectors = [
            'script',
            'style',
            'nav',
            'header',
            'footer',
            '.advertisement',
            '.ads',
            '.social-share',
            '.comments',
            '.related-posts',
            '.sidebar',
            '.navigation',
            '.menu'
        ]
    
    def extract_content(self, url: str) -> Optional[Dict[str, Any]]:
        """
        从URL提取文章内容
        
        Args:
            url: 要提取内容的URL
            
        Returns:
            包含标题和内容的字典，如果失败返回None
        """
        try:
            logger.info(f"正在提取URL内容: {url}")
            
            # 发送请求
            response = self.session.get(url, timeout=30)
            response.raise_for_status()
            
            # 解析HTML
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # 提取标题
            title = self._extract_title(soup)
            
            # 提取内容
            content = self._extract_main_content(soup)
            
            if not content:
                logger.warning(f"无法从URL提取内容: {url}")
                return None
            
            # 清理内容
            cleaned_content = self._clean_content(content)
            
            return {
                'url': url,
                'title': title,
                'content': cleaned_content,
                'domain': urlparse(url).netloc
            }
            
        except requests.RequestException as e:
            logger.error(f"请求失败: {url} - {e}")
            return None
        except Exception as e:
            logger.error(f"提取内容时发生错误: {url} - {e}")
            return None
    
    def _extract_title(self, soup: BeautifulSoup) -> str:
        """提取页面标题"""
        # 尝试多种标题选择器
        title_selectors = [
            'h1',
            '.post-title',
            '.entry-title',
            '.article-title',
            '.headline',
            'title'
        ]
        
        for selector in title_selectors:
            title_elem = soup.select_one(selector)
            if title_elem:
                title = title_elem.get_text(strip=True)
                if title and len(title) > 5:  # 确保标题有意义
                    return title
        
        # 如果没有找到合适的标题，使用页面title
        title_elem = soup.find('title')
        if title_elem:
            return title_elem.get_text(strip=True)
        
        return "无标题"
    
    def _extract_main_content(self, soup: BeautifulSoup) -> Optional[BeautifulSoup]:
        """提取主要内容区域"""
        # 首先尝试使用预定义的选择器
        for selector in self.content_selectors:
            content_elem = soup.select_one(selector)
            if content_elem and self._is_valid_content(content_elem):
                return content_elem
        
        # 如果没有找到，使用启发式方法
        return self._find_content_heuristic(soup)
    
    def _is_valid_content(self, elem: BeautifulSoup) -> bool:
        """检查元素是否包含有效内容"""
        text = elem.get_text(strip=True)
        return len(text) > 100  # 至少100个字符
    
    def _find_content_heuristic(self, soup: BeautifulSoup) -> Optional[BeautifulSoup]:
        """使用启发式方法查找内容"""
        # 查找包含最多文本的容器元素
        content_candidates = []
        
        # 扩大搜索范围，包括更多标签
        for tag in soup.find_all(['div', 'section', 'main', 'article', 'aside']):
            text = tag.get_text(strip=True)
            if len(text) > 100:  # 降低最小字符要求
                # 计算文本密度
                html_length = len(str(tag))
                text_density = len(text) / html_length if html_length > 0 else 0
                
                # 降低文本密度要求，并考虑段落数量
                paragraphs = tag.find_all('p')
                paragraph_bonus = len(paragraphs) * 0.1  # 段落越多得分越高
                
                if text_density > 0.05 or len(paragraphs) > 3:  # 降低密度要求或有足够段落
                    score = len(text) + paragraph_bonus * 100
                    content_candidates.append((tag, score, text_density, len(paragraphs)))
        
        if content_candidates:
            # 按综合得分排序
            content_candidates.sort(key=lambda x: x[1], reverse=True)
            logger.info(f"找到 {len(content_candidates)} 个内容候选，选择得分最高的")
            best_candidate = content_candidates[0]
            logger.info(f"最佳候选：文本长度={int(best_candidate[1])}, 密度={best_candidate[2]:.3f}, 段落数={best_candidate[3]}")
            return best_candidate[0]
        
        # 如果还是没找到，尝试查找body下的主要内容
        logger.warning("启发式方法未找到合适内容，尝试使用body内容")
        body = soup.find('body')
        if body:
            return body
        
        return None
    
    def _clean_content(self, content_elem: BeautifulSoup) -> str:
        """清理内容，保留格式"""
        # 创建内容副本以避免修改原始内容
        content_copy = BeautifulSoup(str(content_elem), 'html.parser')
        
        # 移除不需要的元素
        for selector in self.remove_selectors:
            for elem in content_copy.select(selector):
                elem.decompose()
        
        # 保留重要的HTML标签
        allowed_tags = ['p', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'br', 'strong', 'b', 'em', 'i', 'u', 'ul', 'ol', 'li', 'blockquote', 'div', 'span']
        
        # 直接保留HTML结构，只清理不需要的标签
        def clean_element(elem):
            """递归清理元素，保留允许的标签结构"""
            if elem.name is None:  # 文本节点
                return str(elem)
            
            if elem.name in allowed_tags:
                # 保留允许的标签
                cleaned_children = []
                for child in elem.children:
                    cleaned_child = clean_element(child)
                    if cleaned_child and cleaned_child.strip():
                        cleaned_children.append(cleaned_child)
                
                if cleaned_children or elem.name in ['br']:  # br标签即使没有子元素也保留
                    children_html = ''.join(cleaned_children)
                    if elem.name == 'br':
                        return '<br>'
                    elif children_html.strip():
                        return f"<{elem.name}>{children_html}</{elem.name}>"
                return ""
            else:
                # 不允许的标签，提取其内容
                cleaned_children = []
                for child in elem.children:
                    cleaned_child = clean_element(child)
                    if cleaned_child and cleaned_child.strip():
                        cleaned_children.append(cleaned_child)
                return ''.join(cleaned_children)
        
        # 清理整个内容
        cleaned_parts = []
        for child in content_copy.children:
            cleaned_child = clean_element(child)
            if cleaned_child and cleaned_child.strip():
                cleaned_parts.append(cleaned_child.strip())
        
        # 如果没有提取到内容，尝试备用方法
        if not cleaned_parts:
            logger.warning("标准清理方法没有提取到内容，尝试直接提取段落")
            for elem in content_copy.find_all(['p', 'div', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6']):
                text = elem.get_text(strip=True)
                if text and len(text) > 20:
                    if elem.name.startswith('h'):
                        cleaned_parts.append(f"<{elem.name}>{text}</{elem.name}>")
                    else:
                        # 对于长文本，尝试智能分段
                        formatted_text = self._smart_paragraph_split(text)
                        cleaned_parts.append(formatted_text)
        
        # 合并所有清理后的内容
        cleaned_html = '\n\n'.join(cleaned_parts)
        
        # 进一步清理
        cleaned_html = re.sub(r'<p>\s*</p>', '', cleaned_html)  # 移除空段落
        cleaned_html = re.sub(r'<([^>]+)>\s*</\1>', '', cleaned_html)  # 移除其他空标签
        cleaned_html = re.sub(r'\n\s*\n\s*\n+', '\n\n', cleaned_html)  # 规范化换行
        
        return cleaned_html.strip()
    
    def _smart_paragraph_split(self, text: str) -> str:
        """
        智能分段：根据内容特点自动分段
        """
        try:
            # 检查是否是名字列表格式，先分离出独立的名字条目
            # 按大写字母分割文本，每个大写字母开头的部分可能是一个名字条目
            parts = re.split(r'(?=[A-Z][a-z]+[A-Z])', text)
            
            # 过滤出看起来像名字条目的部分
            name_entries = []
            for part in parts:
                part = part.strip()
                if len(part) > 10 and re.match(r'^[A-Z][a-z]+[A-Z]', part):
                    name_entries.append(part)
            
            if len(name_entries) > 3:  # 如果找到多个名字条目
                logger.info(f"检测到名字列表格式，找到 {len(name_entries)} 个条目")
                formatted_parts = []
                for entry in name_entries:
                    # 提取名字（第一个单词）
                    match = re.match(r'^([A-Z][a-z]+)(.*)$', entry)
                    if match:
                        name = match.group(1)
                        description = match.group(2).strip()
                        # 格式化为标题+段落的形式，匹配源文章格式
                        if description:
                            # 名字作为h3标题，描述作为段落
                            formatted_parts.append(f"<h3>{name}</h3>\n<p>{description}</p>")
                        else:
                            formatted_parts.append(f"<h3>{name}</h3>")
                
                if formatted_parts:
                    return '\n\n'.join(formatted_parts)
            else:
                # 普通文本，尝试按句子分段
                sentences = re.split(r'[.!?]+\s+', text)
                if len(sentences) > 3:
                    # 每2-3句组成一段
                    paragraphs = []
                    current_paragraph = []
                    for sentence in sentences:
                        current_paragraph.append(sentence.strip())
                        if len(current_paragraph) >= 2:
                            if current_paragraph[-1]:  # 确保不是空字符串
                                paragraph_text = '. '.join(current_paragraph).strip()
                                if not paragraph_text.endswith('.'):
                                    paragraph_text += '.'
                                paragraphs.append(f"<p>{paragraph_text}</p>")
                            current_paragraph = []
                    
                    # 处理剩余的句子
                    if current_paragraph:
                        paragraph_text = '. '.join(current_paragraph).strip()
                        if paragraph_text and not paragraph_text.endswith('.'):
                            paragraph_text += '.'
                        if paragraph_text:
                            paragraphs.append(f"<p>{paragraph_text}</p>")
                    
                    return '\n\n'.join(paragraphs)
                else:
                    # 文本太短，直接作为一个段落
                    return f"<p>{text}</p>"
                    
        except Exception as e:
            logger.error(f"智能分段时发生错误: {e}")
            return f"<p>{text}</p>"
    
    def extract_and_format(self, url: str, start_keyword: str = None) -> Optional[str]:
        """
        提取内容并格式化为适合WordPress的格式
        
        Args:
            url: 要提取内容的URL
            start_keyword: 可选的起始关键词，如果提供则从此关键词开始复制内容
            
        Returns:
            格式化后的HTML内容，如果失败返回None
        """
        result = self.extract_content(url)
        if not result:
            return None
        
        content = result['content']
        
        # 如果指定了起始关键词，从该关键词开始截取内容
        if start_keyword:
            content = self._extract_from_keyword(content, start_keyword)
            if not content:
                logger.warning(f"未找到关键词 '{start_keyword}'，使用完整内容")
                content = result['content']
        
        # 不添加源URL的标题，直接使用内容
        formatted_content = content
        
        # 添加来源信息
        formatted_content += f"\n\n<p><em>原文来源: <a href=\"{url}\" target=\"_blank\">{result['domain']}</a></em></p>"
        
        return formatted_content
    
    def _extract_from_keyword(self, content: str, keyword: str) -> str:
        """
        从指定关键词开始提取内容，保留HTML格式
        
        Args:
            content: 原始HTML内容
            keyword: 起始关键词
            
        Returns:
            从关键词开始的内容，保留原始HTML格式
        """
        try:
            from bs4 import BeautifulSoup
            
            # 解析HTML内容
            soup = BeautifulSoup(content, 'html.parser')
            
            # 查找包含关键词的元素
            keyword_element = None
            
            # 遍历所有元素，查找包含关键词的元素
            for element in soup.find_all():
                element_text = element.get_text()
                if keyword in element_text:
                    keyword_element = element
                    logger.info(f"在 {element.name} 元素中找到关键词 '{keyword}'")
                    break
            
            if not keyword_element:
                logger.warning(f"未找到关键词 '{keyword}'")
                return ""
            
            # 获取关键词元素的父容器
            container = keyword_element.parent
            while container and container.name in ['span', 'strong', 'em', 'b', 'i']:
                container = container.parent
            
            if not container:
                container = soup
            
            # 获取容器中的所有子元素
            all_elements = list(container.children)
            
            # 找到包含关键词的元素在容器中的位置
            keyword_index = -1
            for i, child in enumerate(all_elements):
                if hasattr(child, 'get_text') and keyword in child.get_text():
                    keyword_index = i
                    break
            
            if keyword_index == -1:
                logger.warning(f"无法在容器中定位关键词元素")
                return ""
            
            # 从关键词元素开始收集所有后续内容
            collected_elements = []
            
            # 处理包含关键词的元素
            keyword_elem = all_elements[keyword_index]
            if hasattr(keyword_elem, 'get_text'):
                elem_text = keyword_elem.get_text()
                keyword_pos = elem_text.find(keyword)
                
                if keyword_pos >= 0:
                    # 获取从关键词开始的文本
                    from_keyword_text = elem_text[keyword_pos:]
                    
                    # 对从关键词开始的文本进行智能分段
                    formatted_text = self._smart_paragraph_split(from_keyword_text)
                    collected_elements.append(formatted_text)
                else:
                    collected_elements.append(str(keyword_elem))
            
            # 收集关键词元素之后的所有元素
            for i in range(keyword_index + 1, len(all_elements)):
                elem = all_elements[i]
                if hasattr(elem, 'name') and elem.name:
                    # 保留HTML元素的完整结构
                    collected_elements.append(str(elem))
                elif hasattr(elem, 'strip') and elem.strip():
                    # 处理文本节点
                    text_content = str(elem).strip()
                    if len(text_content) > 10:
                        collected_elements.append(f"<p>{text_content}</p>")
            
            # 合并所有元素
            result_content = '\n\n'.join(collected_elements)
            
            # 清理格式
            result_content = re.sub(r'\n\s*\n\s*\n+', '\n\n', result_content)
            result_content = re.sub(r'<p>\s*</p>', '', result_content)
            
            logger.info(f"从关键词 '{keyword}' 开始提取了 {len(result_content)} 字符的内容")
            
            return result_content.strip()
            
        except Exception as e:
            logger.error(f"从关键词提取内容时发生错误: {e}")
            return ""


def extract_url_content(url: str, start_keyword: str = None) -> Optional[str]:
    """
    便捷函数：从URL提取内容
    
    Args:
        url: 要提取内容的URL
        start_keyword: 可选的起始关键词
        
    Returns:
        格式化后的HTML内容，如果失败返回None
    """
    extractor = URLContentExtractor()
    return extractor.extract_and_format(url, start_keyword)


if __name__ == "__main__":
    # 测试功能
    test_url = input("请输入要提取内容的URL: ")
    content = extract_url_content(test_url)
    
    if content:
        print("\n提取的内容:")
        print("=" * 50)
        print(content)
        print("=" * 50)
    else:
        print("无法提取内容")

