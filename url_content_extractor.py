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
        
        # 获取所有文本内容，保留基本结构
        cleaned_parts = []
        
        # 递归处理所有元素
        def process_element(elem):
            if elem.name in allowed_tags:
                # 对于允许的标签，保留其结构
                if elem.name in ['p', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6']:
                    # 段落和标题标签
                    text_content = elem.get_text(strip=True)
                    if text_content:
                        if elem.name.startswith('h'):
                            cleaned_parts.append(f"<{elem.name}>{text_content}</{elem.name}>")
                        else:
                            cleaned_parts.append(f"<p>{text_content}</p>")
                elif elem.name in ['ul', 'ol']:
                    # 列表处理
                    list_items = []
                    for li in elem.find_all('li'):
                        li_text = li.get_text(strip=True)
                        if li_text:
                            list_items.append(f"<li>{li_text}</li>")
                    if list_items:
                        list_content = ''.join(list_items)
                        cleaned_parts.append(f"<{elem.name}>{list_content}</{elem.name}>")
                elif elem.name == 'blockquote':
                    # 引用处理
                    quote_text = elem.get_text(strip=True)
                    if quote_text:
                        cleaned_parts.append(f"<blockquote>{quote_text}</blockquote>")
                else:
                    # 其他标签，提取文本内容
                    text_content = elem.get_text(strip=True)
                    if text_content:
                        cleaned_parts.append(f"<p>{text_content}</p>")
            elif elem.name is None:  # 文本节点
                text = str(elem).strip()
                if text and len(text) > 10:  # 只保留有意义的文本
                    cleaned_parts.append(f"<p>{text}</p>")
        
        # 处理所有直接子元素
        for child in content_copy.children:
            if hasattr(child, 'name'):
                process_element(child)
        
        # 如果没有提取到内容，尝试直接获取所有段落
        if not cleaned_parts:
            logger.warning("标准清理方法没有提取到内容，尝试直接提取段落")
            for p in content_copy.find_all(['p', 'div']):
                text = p.get_text(strip=True)
                if text and len(text) > 20:
                    cleaned_parts.append(f"<p>{text}</p>")
        
        # 合并所有清理后的内容
        cleaned_html = '\n\n'.join(cleaned_parts)
        
        # 进一步清理
        cleaned_html = re.sub(r'<p>\s*</p>', '', cleaned_html)  # 移除空段落
        cleaned_html = re.sub(r'\n\s*\n\s*\n', '\n\n', cleaned_html)  # 规范化换行
        
        return cleaned_html.strip()
    
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
        
        # 添加标题
        formatted_content = f"<h1>{result['title']}</h1>\n\n"
        formatted_content += content
        
        # 添加来源信息
        formatted_content += f"\n\n<p><em>原文来源: <a href=\"{url}\" target=\"_blank\">{result['domain']}</a></em></p>"
        
        return formatted_content
    
    def _extract_from_keyword(self, content: str, keyword: str) -> str:
        """
        从指定关键词开始提取内容
        
        Args:
            content: 原始HTML内容
            keyword: 起始关键词
            
        Returns:
            从关键词开始的内容，如果未找到关键词返回空字符串
        """
        try:
            from bs4 import BeautifulSoup
            
            # 解析HTML内容
            soup = BeautifulSoup(content, 'html.parser')
            
            # 查找包含关键词的元素
            keyword_element = None
            keyword_position = -1
            
            # 遍历所有元素，查找包含关键词的元素
            for element in soup.find_all():
                element_text = element.get_text()
                if keyword in element_text:
                    keyword_element = element
                    keyword_position = element_text.find(keyword)
                    logger.info(f"在 {element.name} 元素中找到关键词 '{keyword}'")
                    break
            
            if not keyword_element:
                # 如果在元素中没找到，尝试在纯文本中查找
                full_text = soup.get_text()
                if keyword in full_text:
                    logger.info(f"在文本中找到关键词 '{keyword}'，但无法精确定位元素")
                    # 简单的文本截取
                    keyword_pos = full_text.find(keyword)
                    remaining_text = full_text[keyword_pos:]
                    return f"<p>{remaining_text}</p>"
                else:
                    logger.warning(f"未找到关键词 '{keyword}'")
                    return ""
            
            # 从找到关键词的元素开始收集内容
            collected_content = []
            found_start = False
            
            # 获取关键词元素的父容器
            container = keyword_element.parent
            if not container:
                container = soup
            
            # 从容器中的所有子元素开始处理
            for element in container.find_all():
                element_text = element.get_text()
                
                # 如果这个元素包含关键词，开始收集
                if keyword in element_text and not found_start:
                    found_start = True
                    
                    # 处理包含关键词的这个元素
                    if keyword_position >= 0:
                        # 截取从关键词开始的文本
                        before_keyword = element_text[:element_text.find(keyword)]
                        from_keyword = element_text[element_text.find(keyword):]
                        
                        # 重建元素，只保留从关键词开始的部分
                        if element.name in ['p', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6']:
                            collected_content.append(f"<{element.name}>{from_keyword}</{element.name}>")
                        else:
                            collected_content.append(f"<p>{from_keyword}</p>")
                    else:
                        # 保留整个元素
                        if element.name in ['p', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6']:
                            collected_content.append(f"<{element.name}>{element_text}</{element.name}>")
                        else:
                            collected_content.append(f"<p>{element_text}</p>")
                
                # 如果已经开始收集且这不是包含关键词的元素，继续收集后续元素
                elif found_start and element != keyword_element:
                    if element.name in ['p', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6']:
                        collected_content.append(f"<{element.name}>{element_text}</{element.name}>")
                    elif element.name in ['ul', 'ol']:
                        # 处理列表
                        list_items = []
                        for li in element.find_all('li'):
                            li_text = li.get_text(strip=True)
                            if li_text:
                                list_items.append(f"<li>{li_text}</li>")
                        if list_items:
                            list_content = ''.join(list_items)
                            collected_content.append(f"<{element.name}>{list_content}</{element.name}>")
                    elif len(element_text.strip()) > 10:  # 忽略很短的文本
                        collected_content.append(f"<p>{element_text}</p>")
            
            result_content = '\n\n'.join(collected_content)
            logger.info(f"从关键词 '{keyword}' 开始提取了 {len(result_content)} 字符的内容")
            
            return result_content
            
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

