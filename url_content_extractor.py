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
from config import Config

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
        self.config = Config()
        
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
        
        # 检查是否是新的minimalistmama格式（HTML已经结构化）
        if self._is_structured_html_format(content_copy):
            logger.info("检测到结构化HTML格式，直接保留HTML结构")
            return self._clean_structured_html(content_copy)
        
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
    
    def _is_structured_html_format(self, soup: BeautifulSoup) -> bool:
        """
        检查是否是新的结构化HTML格式（如minimalistmama.co）
        这种格式特征：
        - 名字在<p><strong>名字</strong></p>中
        - 详细信息在随后的<ul><li><span>标签</span>值</li></ul>中
        """
        try:
            # 查找<p><strong>名字</strong></p>格式的元素数量
            strong_names = soup.select('p strong')
            
            # 查找包含"Origin"或"Meaning"的span元素
            origin_count = 0
            meaning_count = 0
            
            for span in soup.find_all('span'):
                span_text = span.get_text().strip()
                if 'Origin' in span_text:
                    origin_count += 1
                elif 'Meaning' in span_text:
                    meaning_count += 1
            
            # 如果找到多个名字和相应的详细信息，认为是结构化HTML格式
            if len(strong_names) >= 3 and (origin_count >= 3 or meaning_count >= 3):
                logger.info(f"检测到结构化HTML格式：{len(strong_names)} 个名字，{origin_count} 个起源，{meaning_count} 个含义")
                return True
                
            return False
            
        except Exception as e:
            logger.error(f"检测结构化HTML格式时发生错误: {e}")
            return False
    
    def _clean_structured_html(self, soup: BeautifulSoup) -> str:
        """
        清理结构化HTML格式，保持原有的HTML结构
        """
        try:
            allowed_tags = ['p', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'br', 'strong', 'b', 'em', 'i', 'u', 'ul', 'ol', 'li', 'blockquote', 'div', 'span']
            
            # 递归清理函数，保留结构化内容的完整性
            def clean_structured_element(elem):
                if elem.name is None:  # 文本节点
                    return str(elem).strip()
                
                if elem.name in allowed_tags:
                    # 特殊处理：保留名字和详细信息的结构
                    cleaned_children = []
                    for child in elem.children:
                        cleaned_child = clean_structured_element(child)
                        if cleaned_child:
                            cleaned_children.append(cleaned_child)
                    
                    if cleaned_children or elem.name in ['br']:
                        children_html = ''.join(cleaned_children)
                        if elem.name == 'br':
                            return '<br>'
                        elif children_html.strip():
                            # 保留元素的属性（如果需要）
                            return f"<{elem.name}>{children_html}</{elem.name}>"
                    return ""
                else:
                    # 不允许的标签，提取其内容但保持子元素结构
                    cleaned_children = []
                    for child in elem.children:
                        cleaned_child = clean_structured_element(child)
                        if cleaned_child:
                            cleaned_children.append(cleaned_child)
                    return ''.join(cleaned_children)
            
            # 清理整个内容，保持结构
            cleaned_parts = []
            for child in soup.children:
                cleaned_child = clean_structured_element(child)
                if cleaned_child and cleaned_child.strip():
                    cleaned_parts.append(cleaned_child.strip())
            
            # 合并内容
            cleaned_html = '\n\n'.join(cleaned_parts)
            
            # 轻量级清理，不破坏结构
            cleaned_html = re.sub(r'<p>\s*</p>', '', cleaned_html)  # 移除空段落
            cleaned_html = re.sub(r'<li>\s*</li>', '', cleaned_html)  # 移除空列表项
            cleaned_html = re.sub(r'\n\s*\n\s*\n+', '\n\n', cleaned_html)  # 规范化换行
            
            # 在冒号后面添加空格，改善可读性
            cleaned_html = self._format_structured_spacing(cleaned_html)
            
            return cleaned_html.strip()
            
        except Exception as e:
            logger.error(f"清理结构化HTML时发生错误: {e}")
            # 如果出错，回退到原始清理方法
            return str(soup)
    
    def _format_structured_spacing(self, content: str) -> str:
        """
        为结构化内容添加适当的空格，改善可读性
        """
        try:
            # 在span标签后面的冒号和内容之间添加空格
            # 匹配模式: </span>直接跟着文本内容
            # 例如: </span>English -> </span> English
            content = re.sub(r'</span>([A-Za-z])', r'</span> \1', content)
            
            # 在About:, Origin:, Meaning:, Popularity: 等标签后添加空格
            # 如果冒号后面直接跟着文字，添加空格
            content = re.sub(r':</span>([A-Za-z])', r':</span> \1', content)
            
            # 处理其他可能的冒号情况
            # 匹配 >: 后直接跟字母的情况
            content = re.sub(r'>:([A-Za-z])', r'>: \1', content)
            
            logger.info("已应用结构化内容空格格式化")
            return content
            
        except Exception as e:
            logger.error(f"格式化结构化内容空格时发生错误: {e}")
            return content
    
    def _truncate_content(self, content: str) -> str:
        """
        根据配置的关键词截断内容
        
        Args:
            content: 原始内容
            
        Returns:
            截断后的内容
        """
        try:
            # 检查是否包含截断关键词
            truncation_keywords = self.config.TRUNCATION_KEYWORDS
            
            for keyword in truncation_keywords:
                # 不区分大小写地查找关键词
                keyword_lower = keyword.lower()
                content_lower = content.lower()
                
                # 查找关键词位置
                keyword_pos = content_lower.find(keyword_lower)
                if keyword_pos != -1:
                    logger.info(f"找到截断关键词 '{keyword}' 在位置 {keyword_pos}")
                    
                    # 截断内容到关键词之前
                    truncated_content = content[:keyword_pos].strip()
                    
                    # 确保截断后的内容以完整的HTML标签结束
                    truncated_content = self._clean_truncated_html(truncated_content)
                    
                    logger.info(f"内容已截断：从 {len(content)} 字符减少到 {len(truncated_content)} 字符")
                    return truncated_content
            
            # 如果没有找到截断关键词，返回原内容
            return content
            
        except Exception as e:
            logger.error(f"截断内容时发生错误: {e}")
            return content
    
    def _clean_truncated_html(self, content: str) -> str:
        """
        清理截断后的HTML内容，确保标签完整
        
        Args:
            content: 截断后的内容
            
        Returns:
            清理后的内容
        """
        try:
            from bs4 import BeautifulSoup
            
            # 解析HTML并自动修复不完整的标签
            soup = BeautifulSoup(content, 'html.parser')
            
            # 返回修复后的HTML
            return str(soup)
            
        except Exception as e:
            logger.error(f"清理截断HTML时发生错误: {e}")
            return content
    
    def _smart_paragraph_split(self, text: str) -> str:
        """
        智能分段：根据内容特点自动分段
        """
        try:
            # 首先检查是否是标准化的名字列表格式（包含Origin, Meaning, Popularity）
            if self._is_structured_name_list(text):
                return self._format_structured_name_list(text)
            
            # 检查是否是传统的名字列表格式，先分离出独立的名字条目
            # 按大写字母分割文本，每个大写字母开头的部分可能是一个名字条目
            parts = re.split(r'(?=[A-Z][a-z]+[A-Z])', text)
            
            # 过滤出看起来像名字条目的部分
            name_entries = []
            for part in parts:
                part = part.strip()
                if len(part) > 10 and re.match(r'^[A-Z][a-z]+[A-Z]', part):
                    name_entries.append(part)
            
            if len(name_entries) > 3:  # 如果找到多个名字条目
                logger.info(f"检测到传统名字列表格式，找到 {len(name_entries)} 个条目")
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
    
    def _is_structured_name_list(self, text: str) -> bool:
        """
        检查是否是标准化的名字列表格式（包含Origin, Meaning, Popularity）
        """
        try:
            # 检查文本中是否包含典型的名字列表特征
            origin_count = text.count('Origin:')
            meaning_count = text.count('Meaning:')
            popularity_count = text.count('Popularity:')
            
            # 如果这些关键词都出现多次，且数量相近，则认为是标准化名字列表
            if origin_count >= 3 and meaning_count >= 3 and popularity_count >= 3:
                # 检查数量是否相近（允许一定的差异）
                counts = [origin_count, meaning_count, popularity_count]
                max_count = max(counts)
                min_count = min(counts)
                
                # 如果最大值和最小值的差异不超过2，认为是结构化列表
                if max_count - min_count <= 2:
                    logger.info(f"检测到标准化名字列表格式: Origin={origin_count}, Meaning={meaning_count}, Popularity={popularity_count}")
                    return True
            
            return False
            
        except Exception as e:
            logger.error(f"检测标准化名字列表格式时发生错误: {e}")
            return False
    
    def _format_structured_name_list(self, text: str) -> str:
        """
        格式化标准化的名字列表（包含Origin, Meaning, Popularity）
        """
        try:
            formatted_parts = []
            
            # 更精确的正则表达式匹配模式
            # 匹配：名字 Origin: xxx Meaning: xxx Popularity: xxx 直到下一个名字或结束
            name_pattern = r'([A-Z][a-z]+(?:[A-Z][a-z]+)*)\s*Origin:\s*([^M]+?)Meaning:\s*([^P]+?)Popularity:\s*([^A-Z]+?)(?=\s*[A-Z][a-z]+Origin:|$)'
            matches = re.finditer(name_pattern, text, re.MULTILINE | re.DOTALL)
            
            for match in matches:
                name = match.group(1).strip()
                origin = match.group(2).strip()
                meaning = match.group(3).strip()
                popularity = match.group(4).strip()
                
                # 清理各字段
                origin = re.sub(r'[^\w\s,.-]', '', origin).strip()
                meaning = re.sub(r'[*_]', '', meaning).strip()
                popularity = re.sub(r'[^\w\s#>]', '', popularity).strip()
                
                # 确保字段不为空
                if name and origin and meaning and popularity:
                    # 格式化每个名字为HTML结构
                    formatted_name = f"<h3>{name}</h3>\n"
                    formatted_name += f"<ul>\n"
                    formatted_name += f"<li><strong>Origin:</strong> {origin}</li>\n"
                    formatted_name += f"<li><strong>Meaning:</strong> <em>{meaning}</em></li>\n"
                    formatted_name += f"<li><strong>Popularity:</strong> {popularity}</li>\n"
                    formatted_name += f"</ul>"
                    
                    formatted_parts.append(formatted_name)
            
            if formatted_parts:
                logger.info(f"成功格式化 {len(formatted_parts)} 个标准化名字条目")
                return '\n\n'.join(formatted_parts)
            else:
                # 如果没有匹配到，尝试简单的分割方法
                logger.warning("未能匹配标准格式，尝试简单分割")
                return self._fallback_structured_format(text)
                
        except Exception as e:
            logger.error(f"格式化标准化名字列表时发生错误: {e}")
            return f"<p>{text}</p>"
    
    def _fallback_structured_format(self, text: str) -> str:
        """
        备用的标准化格式处理方法
        """
        try:
            # 使用更简单的方法分割各个名字条目
            formatted_parts = []
            
            # 通过"Origin:"分割文本，每个部分应该包含一个完整的名字信息
            parts = text.split('Origin:')
            
            for i, part in enumerate(parts):
                if i == 0:  # 第一部分可能只是介绍文字，跳过
                    continue
                    
                part = 'Origin:' + part.strip()
                
                # 尝试从这部分提取名字信息
                name_info = self._extract_name_from_part(part)
                if name_info:
                    formatted_name = f"<h3>{name_info['name']}</h3>\n"
                    formatted_name += f"<ul>\n"
                    formatted_name += f"<li><strong>Origin:</strong> {name_info['origin']}</li>\n"
                    formatted_name += f"<li><strong>Meaning:</strong> <em>{name_info['meaning']}</em></li>\n"
                    formatted_name += f"<li><strong>Popularity:</strong> {name_info['popularity']}</li>\n"
                    formatted_name += f"</ul>"
                    formatted_parts.append(formatted_name)
            
            if formatted_parts:
                logger.info(f"备用方法成功格式化 {len(formatted_parts)} 个名字条目")
                return '\n\n'.join(formatted_parts)
            else:
                logger.warning("备用方法也无法解析，返回原文")
                return f"<p>{text}</p>"
                
        except Exception as e:
            logger.error(f"备用格式化方法发生错误: {e}")
            return f"<p>{text}</p>"
    
    def _extract_name_from_part(self, part: str) -> dict:
        """
        从文本片段中提取名字信息
        """
        try:
            # 在前面寻找名字（Origin:之前的大写字母开头的单词）
            name_match = re.search(r'([A-Z][a-z]+(?:[A-Z][a-z]+)*)\s*Origin:', part)
            if not name_match:
                return None
                
            name = name_match.group(1).strip()
            
            # 提取Origin
            origin_match = re.search(r'Origin:\s*([^M]*?)(?=Meaning:|$)', part)
            origin = origin_match.group(1).strip() if origin_match else ""
            
            # 提取Meaning  
            meaning_match = re.search(r'Meaning:\s*([^P]*?)(?=Popularity:|$)', part)
            meaning = meaning_match.group(1).strip() if meaning_match else ""
            meaning = re.sub(r'[*_]', '', meaning)  # 清理斜体标记
            
            # 提取Popularity
            popularity_match = re.search(r'Popularity:\s*([^A-Z]*?)(?=[A-Z][a-z]*Origin:|$)', part)
            popularity = popularity_match.group(1).strip() if popularity_match else ""
            
            # 清理字段
            origin = origin.replace('\n', ' ').strip()
            meaning = meaning.replace('\n', ' ').strip() 
            popularity = popularity.replace('\n', ' ').strip()
            
            if name and origin and meaning and popularity:
                return {
                    'name': name,
                    'origin': origin,
                    'meaning': meaning,
                    'popularity': popularity
                }
            else:
                return None
                
        except Exception as e:
            logger.error(f"提取名字信息时发生错误: {e}")
            return None
    
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
        
        # 应用内容截断（移除尾部不需要的部分）
        content = self._truncate_content(content)
        
        # 不添加源URL的标题，直接使用内容
        formatted_content = content
        
        # 不添加来源信息，直接返回内容
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
            
            # 检查是否是结构化HTML格式
            is_structured = self._is_structured_html_format(soup)
            
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
            
            if is_structured:
                # 对于结构化HTML，从关键词元素开始收集结构化内容
                return self._extract_structured_from_keyword(soup, keyword_element, keyword)
            
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
    
    def _extract_structured_from_keyword(self, soup: BeautifulSoup, keyword_element, keyword: str) -> str:
        """
        从结构化HTML中提取从关键词开始的内容，保持HTML结构
        """
        try:
            # 找到包含关键词的确切元素
            target_element = None
            
            # 在结构化格式中，关键词通常在 <p><strong>关键词</strong></p> 中
            # 我们需要找到这个确切的<p>元素
            for p_elem in soup.find_all('p'):
                strong_elem = p_elem.find('strong')
                if strong_elem and keyword in strong_elem.get_text():
                    target_element = p_elem
                    logger.info(f"找到包含关键词 '{keyword}' 的名字元素: <p><strong>{keyword}</strong></p>")
                    break
            
            if not target_element:
                logger.warning(f"未找到包含关键词 '{keyword}' 的名字元素")
                return ""
            
            # 获取整个文档的所有顶级元素（按顺序）
            all_elements = []
            for elem in soup.descendants:
                # 只收集顶级的内容元素，避免重复
                if (elem.name in ['p', 'ul', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6'] and 
                    elem.parent and elem.parent.name in ['div', 'body', '[document]']):
                    all_elements.append(elem)
            
            # 找到目标元素在列表中的位置
            start_index = -1
            for i, elem in enumerate(all_elements):
                if elem == target_element:
                    start_index = i
                    logger.info(f"找到目标元素在索引 {i} 位置")
                    break
            
            if start_index == -1:
                logger.warning("无法定位目标元素在文档中的位置")
                return ""
            
            # 从目标元素开始收集所有后续的结构化内容
            collected_elements = []
            
            for i in range(start_index, len(all_elements)):
                elem = all_elements[i]
                # 保留完整的HTML结构
                collected_elements.append(str(elem))
            
            # 合并所有元素
            result_content = '\n\n'.join(collected_elements)
            
            # 轻量级清理
            result_content = re.sub(r'\n\s*\n\s*\n+', '\n\n', result_content)
            
            logger.info(f"从结构化关键词 '{keyword}' 开始提取了 {len(result_content)} 字符的内容")
            return result_content.strip()
            
        except Exception as e:
            logger.error(f"从结构化内容提取关键词时发生错误: {e}")
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

