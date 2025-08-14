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
  # 更新单篇文章（试运行）
  python main.py --url "https://example.com/post/123" --dry-run
  
  # 更新单篇文章（实际更新）
  python main.py --url "https://example.com/post/123"
  
  # 批量更新文章
  python main.py --file urls.txt --dry-run
  
  # 获取文章信息
  python main.py --url "https://example.com/post/123" --info
        """
    )
    
    # 添加参数
    parser.add_argument(
        '--url', 
        help='要更新的文章URL'
    )
    
    parser.add_argument(
        '--file', 
        help='包含多个URL的文件路径（每行一个URL）'
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
            else:
                # 更新文章
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
                urls = [line.strip() for line in f if line.strip()]
            
            if not urls:
                logger.error("文件中没有找到有效的URL")
                sys.exit(1)
            
            logger.info(f"从文件中读取到 {len(urls)} 个URL")
            
            # 批量更新
            results = updater.update_multiple_articles(urls, args.dry_run)
            
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
