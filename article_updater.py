from wordpress_client import WordPressClient
from content_processor import ContentProcessor
from url_content_extractor import URLContentExtractor
import logging
import time

logger = logging.getLogger(__name__)

class ArticleUpdater:
    """文章更新器主类"""
    
    def __init__(self):
        """初始化文章更新器"""
        self.wp_client = WordPressClient()
        self.content_processor = ContentProcessor()
        self.url_extractor = URLContentExtractor()
        
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
    
    def copy_content_from_url(self, target_post_url, source_url, dry_run=False, start_keyword=None):
        """从源URL复制内容到目标文章（先清空文字保留图片，再填入新内容）"""
        try:
            logger.info(f"开始从 {source_url} 复制内容到 {target_post_url}")
            
            # 1. 获取目标文章
            target_post = self.wp_client.get_post_by_url(target_post_url)
            if not target_post:
                logger.error(f"无法获取目标文章: {target_post_url}")
                return False
            
            # 2. 获取目标文章原始内容
            original_content = self.wp_client.get_post_content(target_post)
            if not original_content:
                logger.warning(f"目标文章内容为空: {target_post_url}")
                # 继续执行，因为可能只是要添加新内容
            
            # 3. 只保留目标文章的描述部分和图片，清空其他内容
            logger.info("正在提取目标文章的描述和图片，清空主要内容...")
            separated_content = self.content_processor.extract_description_and_images_only(original_content)
            target_description_content = separated_content['description_content']
            target_images_content = separated_content['images_content']
            
            # 4. 从源URL提取内容
            if start_keyword:
                logger.info(f"正在从源URL提取内容（从关键词 '{start_keyword}' 开始）: {source_url}")
            else:
                logger.info(f"正在从源URL提取内容: {source_url}")
                
            source_content = self.url_extractor.extract_and_format(source_url, start_keyword)
            if not source_content:
                logger.error(f"无法从源URL提取内容: {source_url}")
                return False
            
            # 5. 合并内容（目标文章描述 + 源内容 + 图片）
            logger.info("正在合并内容...")
            final_content = self._merge_content_with_description(target_description_content, source_content, target_images_content)
            
            # 验证处理结果
            validation_result = self.content_processor.validate_images(final_content)
            logger.info(f"图片验证结果: {validation_result['valid']}/{validation_result['total']} 张图片有效")
            
            # 如果是试运行模式，只显示结果不更新
            if dry_run:
                logger.info("试运行模式 - 不会实际更新文章")
                self._show_copy_preview_with_description(original_content, final_content, source_url)
                return True
            
            # 6. 获取文章ID并更新
            post_id = self._get_post_id(target_post)
            if not post_id:
                logger.error("无法获取目标文章ID")
                return False
            
            # 更新文章
            logger.info("开始更新目标文章...")
            success = self.wp_client.update_post(post_id, final_content)
            
            if success:
                logger.info(f"成功从 {source_url} 复制内容到 {target_post_url}")
                return True
            else:
                logger.error(f"更新目标文章失败: {target_post_url}")
                return False
                
        except Exception as e:
            logger.error(f"复制内容时发生错误: {e}")
            return False
    
    def _merge_content(self, images_content, text_content):
        """合并图片内容和文字内容"""
        try:
            from bs4 import BeautifulSoup
            
            # 解析图片内容
            images_soup = BeautifulSoup(images_content, 'html.parser')
            
            # 解析文字内容
            text_soup = BeautifulSoup(text_content, 'html.parser')
            
            # 创建新的容器
            merged_soup = BeautifulSoup('<div></div>', 'html.parser')
            container = merged_soup.div
            
            # 先添加从源URL提取的文字内容
            for element in text_soup.contents:
                if element.name or (hasattr(element, 'strip') and element.strip()):
                    container.append(element)
            
            # 然后添加原文章的图片（如果有的话）
            images = images_soup.find_all('img')
            if images:
                # 添加分隔符
                hr = merged_soup.new_tag('hr')
                container.append(hr)
                
                # 添加图片说明
                img_header = merged_soup.new_tag('h3')
                img_header.string = "原文图片"
                container.append(img_header)
                
                # 添加所有图片
                for img in images:
                    container.append(img)
            
            return str(container).replace('<div>', '').replace('</div>', '')
            
        except Exception as e:
            logger.error(f"合并内容时发生错误: {e}")
            # 如果合并失败，返回文字内容
            return text_content
    
    def _show_copy_preview(self, original_content, final_content, source_url):
        """显示复制内容的预览信息"""
        logger.info("=== 内容复制预览 ===")
        
        # 获取图片信息
        original_images = self.content_processor.get_image_info(original_content)
        final_images = self.content_processor.get_image_info(final_content)
        
        logger.info(f"源URL: {source_url}")
        logger.info(f"原始文章图片数量: {len(original_images)}")
        logger.info(f"最终内容图片数量: {len(final_images)}")
        
        if final_images:
            logger.info("保留的图片:")
            for img in final_images:
                logger.info(f"  - {img['src']} (alt: {img['alt']})")
        
        # 计算文字变化
        from bs4 import BeautifulSoup
        original_soup = BeautifulSoup(original_content, 'html.parser')
        final_soup = BeautifulSoup(final_content, 'html.parser')
        
        original_text = original_soup.get_text(strip=True)
        final_text = final_soup.get_text(strip=True)
        
        logger.info(f"原始文字长度: {len(original_text)} 字符")
        logger.info(f"最终文字长度: {len(final_text)} 字符")
        logger.info(f"文字变化: {len(final_text) - len(original_text)} 字符")
    
    def _merge_content_with_description(self, target_description_content, source_content, target_images_content):
        """合并目标文章描述、源内容和图片"""
        try:
            from bs4 import BeautifulSoup
            
            # 解析目标文章的描述内容
            target_soup = BeautifulSoup(target_description_content, 'html.parser')
            
            # 解析源内容
            source_soup = BeautifulSoup(source_content, 'html.parser')
            
            # 创建新的容器
            merged_soup = BeautifulSoup('<div></div>', 'html.parser')
            container = merged_soup.div
            
            # 1. 首先添加目标文章的描述内容（去掉图片后的文字内容）
            logger.info("添加目标文章的描述内容...")
            for element in target_soup.contents:
                if element.name or (hasattr(element, 'strip') and element.strip()):
                    container.append(element)
            
            # 2. 添加分隔符
            if target_description_content.strip():
                hr = merged_soup.new_tag('hr')
                container.append(hr)
            
            # 3. 然后添加从源URL提取的内容
            logger.info("添加源URL的内容...")
            for element in source_soup.contents:
                if element.name or (hasattr(element, 'strip') and element.strip()):
                    container.append(element)
            
            # 4. 最后添加目标文章的图片（如果有的话）
            if target_images_content.strip():
                logger.info("添加目标文章的图片...")
                # 添加分隔符
                hr = merged_soup.new_tag('hr')
                container.append(hr)
                
                # 添加图片说明
                img_header = merged_soup.new_tag('h3')
                img_header.string = "相关图片"
                container.append(img_header)
                
                # 解析图片HTML并添加
                images_soup = BeautifulSoup(target_images_content, 'html.parser')
                for img in images_soup.find_all('img'):
                    container.append(img)
            
            result = str(container).replace('<div>', '').replace('</div>', '')
            logger.info(f"内容合并完成，最终长度: {len(result)} 字符")
            
            return result
            
        except Exception as e:
            logger.error(f"合并内容时发生错误: {e}")
            # 如果合并失败，返回源内容 + 图片
            return source_content + '\n\n' + target_images_content
    
    def _show_copy_preview_with_description(self, original_content, final_content, source_url):
        """显示保留描述的复制内容预览信息"""
        logger.info("=== 内容复制预览（保留描述） ===")
        
        # 获取图片信息
        original_images = self.content_processor.get_image_info(original_content)
        final_images = self.content_processor.get_image_info(final_content)
        
        logger.info(f"源URL: {source_url}")
        logger.info(f"原始文章图片数量: {len(original_images)}")
        logger.info(f"最终内容图片数量: {len(final_images)}")
        
        if final_images:
            logger.info("保留的图片:")
            for img in final_images:
                logger.info(f"  - {img['src']} (alt: {img['alt']})")
        
        # 计算文字变化
        from bs4 import BeautifulSoup
        original_soup = BeautifulSoup(original_content, 'html.parser')
        final_soup = BeautifulSoup(final_content, 'html.parser')
        
        original_text = original_soup.get_text(strip=True)
        final_text = final_soup.get_text(strip=True)
        
        logger.info(f"原始文字长度: {len(original_text)} 字符")
        logger.info(f"最终文字长度: {len(final_text)} 字符")
        logger.info(f"文字变化: {len(final_text) - len(original_text)} 字符")
        logger.info("注意: 最终内容包含原文章描述 + 源URL内容 + 原文章图片")
    
    def process_multiple_configs(self, url_configs, dry_run=False):
        """批量处理多种类型的URL配置"""
        results = {
            'total': len(url_configs),
            'success': 0,
            'failed': 0,
            'details': []
        }
        
        logger.info(f"开始批量处理 {len(url_configs)} 个URL配置")
        
        for i, config in enumerate(url_configs, 1):
            config_type = config['type']
            target_url = config['target_url']
            line_num = config['line']
            
            logger.info(f"处理第 {i}/{len(url_configs)} 个配置 (第{line_num}行): {config_type}模式")
            
            try:
                if config_type == 'delete':
                    # 删除文字保留图片模式
                    logger.info(f"删除模式: {target_url}")
                    success = self.update_article_by_url(target_url, dry_run)
                elif config_type == 'copy':
                    # 复制内容模式
                    source_url = config['source_url']
                    start_keyword = config.get('start_keyword')
                    if start_keyword:
                        logger.info(f"复制模式（从关键词 '{start_keyword}' 开始）: {source_url} -> {target_url}")
                    else:
                        logger.info(f"复制模式: {source_url} -> {target_url}")
                    success = self.copy_content_from_url(target_url, source_url, dry_run, start_keyword)
                else:
                    logger.error(f"未知的配置类型: {config_type}")
                    success = False
                
                result_detail = {
                    'line': line_num,
                    'type': config_type,
                    'target_url': target_url,
                    'source_url': config.get('source_url', ''),
                    'start_keyword': config.get('start_keyword', ''),
                    'success': success,
                    'timestamp': time.strftime('%Y-%m-%d %H:%M:%S')
                }
                
                if success:
                    results['success'] += 1
                    logger.info(f"✓ 第{line_num}行配置处理成功")
                else:
                    results['failed'] += 1
                    logger.error(f"✗ 第{line_num}行配置处理失败")
                
                results['details'].append(result_detail)
                
                # 添加延迟避免请求过于频繁
                if i < len(url_configs):
                    time.sleep(2)
                    
            except Exception as e:
                logger.error(f"处理第{line_num}行配置时发生异常: {e}")
                results['failed'] += 1
                results['details'].append({
                    'line': line_num,
                    'type': config_type,
                    'target_url': target_url,
                    'source_url': config.get('source_url', ''),
                    'start_keyword': config.get('start_keyword', ''),
                    'success': False,
                    'error': str(e),
                    'timestamp': time.strftime('%Y-%m-%d %H:%M:%S')
                })
        
        # 输出总结
        self._print_configs_summary(results)
        return results
    
    def _print_configs_summary(self, results):
        """打印配置处理总结"""
        logger.info("=== 批量配置处理总结 ===")
        logger.info(f"总配置数: {results['total']}")
        logger.info(f"成功: {results['success']}")
        logger.info(f"失败: {results['failed']}")
        logger.info(f"成功率: {(results['success']/results['total']*100):.1f}%")
        
        if results['failed'] > 0:
            logger.info("失败的配置:")
            for detail in results['details']:
                if not detail['success']:
                    logger.info(f"  - 第{detail['line']}行 ({detail['type']}模式): {detail['target_url']}")
                    if 'error' in detail:
                        logger.info(f"    错误: {detail['error']}")
        
        # 按类型统计
        delete_count = sum(1 for d in results['details'] if d['type'] == 'delete')
        copy_count = sum(1 for d in results['details'] if d['type'] == 'copy')
        
        if delete_count > 0:
            logger.info(f"删除模式处理: {delete_count} 个")
        if copy_count > 0:
            logger.info(f"复制模式处理: {copy_count} 个")
