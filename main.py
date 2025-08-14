#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
WordPress文章更新器
用于删除文章中的文字内容，只保留图片
"""

import argparse
import sys
import logging
from pathlib import Path
from article_updater import ArticleUpdater

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('wordpress_updater.log', encoding='utf-8')
    ]
)

logger = logging.getLogger(__name__)

def main():
    """主函数"""
    parser = argparse.ArgumentParser(
        description='WordPress文章更新器 - 删除文字保留图片',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
使用示例:
  # 更新单篇文章（删除文字保留图片，试运行）
  python main.py --url "https://example.com/post/123" --dry-run
  
  # 更新单篇文章（删除文字保留图片，实际更新）
  python main.py --url "https://example.com/post/123"
  
  # 复制内容模式（试运行）
  python main.py --url "https://example.com/target-post" --source-url "https://source.com/article" --copy-mode --dry-run
  
  # 复制内容模式（实际更新）
  python main.py --url "https://example.com/target-post" --source-url "https://source.com/article" --copy-mode
  
  # 批量处理文章（支持混合模式和关键词起始位置，根据urls.txt文件配置）
  python main.py --file urls.txt --dry-run
  
  # 获取文章信息
  python main.py --url "https://example.com/post/123" --info
        """
    )
    
    # 添加参数
    parser.add_argument(
        '--url', 
        help='要更新的文章URL（目标文章）'
    )
    
    parser.add_argument(
        '--file', 
        help='包含URL配置的文件路径（支持删除模式和复制模式的混合配置）'
    )
    
    parser.add_argument(
        '--dry-run', 
        action='store_true',
        help='试运行模式，不实际更新文章'
    )
    
    parser.add_argument(
        '--info', 
        action='store_true',
        help='只获取文章信息，不进行更新'
    )
    
    parser.add_argument(
        '--verbose', 
        action='store_true',
        help='显示详细日志'
    )
    
    parser.add_argument(
        '--source-url', 
        help='源文章URL（要复制内容的来源）'
    )
    
    parser.add_argument(
        '--copy-mode', 
        action='store_true',
        help='复制模式：从源URL复制内容到目标文章（先清空目标文章文字内容保留图片）'
    )
    
    # 解析参数
    args = parser.parse_args()
    
    # 设置日志级别
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    # 验证参数
    if not args.url and not args.file:
        parser.error("必须提供 --url 或 --file 参数")
    
    if args.url and args.file:
        parser.error("不能同时使用 --url 和 --file 参数")
    
    if args.copy_mode and not args.source_url:
        parser.error("使用 --copy-mode 时必须提供 --source-url 参数")
    
    if args.copy_mode and args.file:
        parser.error("复制模式不支持批量处理，请使用单个URL")
    
    if args.source_url and not args.copy_mode:
        parser.error("提供 --source-url 时必须启用 --copy-mode")
    
    try:
        # 初始化文章更新器
        logger.info("初始化WordPress文章更新器...")
        updater = ArticleUpdater()
        
        if args.url:
            # 处理单个URL
            if args.info:
                # 只获取信息
                logger.info(f"获取文章信息: {args.url}")
                info = updater.get_article_info(args.url)
                if info:
                    print(f"\n文章信息:")
                    print(f"  内容长度: {info['content_length']} 字符")
                    print(f"  图片数量: {info['image_count']} 张")
                    if info['images']:
                        print(f"  图片列表:")
                        for img in info['images']:
                            print(f"    - {img['src']}")
                else:
                    logger.error("无法获取文章信息")
                    sys.exit(1)
            elif args.copy_mode:
                # 复制模式：从源URL复制内容到目标文章
                logger.info(f"复制模式：从 {args.source_url} 复制内容到 {args.url}")
                success = updater.copy_content_from_url(args.url, args.source_url, args.dry_run)
                if not success:
                    logger.error("内容复制失败")
                    sys.exit(1)
            else:
                # 更新文章（原有功能：删除文字保留图片）
                success = updater.update_article_by_url(args.url, args.dry_run)
                if not success:
                    logger.error("文章更新失败")
                    sys.exit(1)
        
        elif args.file:
            # 处理文件中的多个URL
            file_path = Path(args.file)
            if not file_path.exists():
                logger.error(f"文件不存在: {args.file}")
                sys.exit(1)
            
            # 读取URL列表
            with open(file_path, 'r', encoding='utf-8') as f:
                lines = [line.strip() for line in f if line.strip() and not line.startswith('#')]
            
            if not lines:
                logger.error("文件中没有找到有效的URL配置")
                sys.exit(1)
            
            # 解析URL配置
            url_configs = []
            for line_num, line in enumerate(lines, 1):
                if '|' in line:
                    # 复制模式：目标URL|源URL 或 目标URL|源URL|关键词
                    parts = line.split('|')
                    if len(parts) == 2:
                        target_url, source_url = parts[0].strip(), parts[1].strip()
                        if target_url and source_url:
                            url_configs.append({
                                'type': 'copy',
                                'target_url': target_url,
                                'source_url': source_url,
                                'start_keyword': None,
                                'line': line_num
                            })
                        else:
                            logger.warning(f"第 {line_num} 行格式不正确，跳过: {line}")
                    elif len(parts) == 3:
                        target_url, source_url, start_keyword = parts[0].strip(), parts[1].strip(), parts[2].strip()
                        if target_url and source_url:
                            url_configs.append({
                                'type': 'copy',
                                'target_url': target_url,
                                'source_url': source_url,
                                'start_keyword': start_keyword if start_keyword else None,
                                'line': line_num
                            })
                        else:
                            logger.warning(f"第 {line_num} 行格式不正确，跳过: {line}")
                    else:
                        logger.warning(f"第 {line_num} 行格式不正确，跳过: {line}")
                else:
                    # 删除模式：单个URL
                    if line:
                        url_configs.append({
                            'type': 'delete',
                            'target_url': line,
                            'line': line_num
                        })
            
            if not url_configs:
                logger.error("文件中没有找到有效的URL配置")
                sys.exit(1)
            
            logger.info(f"从文件中读取到 {len(url_configs)} 个URL配置")
            
            # 批量处理
            results = updater.process_multiple_configs(url_configs, args.dry_run)
            
            if results['failed'] > 0:
                logger.warning(f"有 {results['failed']} 篇文章处理失败")
                sys.exit(1)
        
        logger.info("处理完成！")
        
    except KeyboardInterrupt:
        logger.info("用户中断操作")
        sys.exit(1)
    except Exception as e:
        logger.error(f"程序执行出错: {e}")
        sys.exit(1)

if __name__ == '__main__':
    main()
