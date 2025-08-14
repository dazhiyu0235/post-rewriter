#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
WordPress文章更新器测试示例
演示如何使用文章更新器的各种功能
"""

import logging
from article_updater import ArticleUpdater

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_single_article():
    """测试单篇文章更新"""
    print("=== 测试单篇文章更新 ===")
    
    try:
        # 初始化更新器
        updater = ArticleUpdater()
        
        # 测试文章URL（请替换为您的实际URL）
        test_url = "https://your-wordpress-site.com/post/123"
        
        # 获取文章信息
        print(f"获取文章信息: {test_url}")
        info = updater.get_article_info(test_url)
        
        if info:
            print(f"文章信息:")
            print(f"  内容长度: {info['content_length']} 字符")
            print(f"  图片数量: {info['image_count']} 张")
            
            if info['images']:
                print("  图片列表:")
                for img in info['images']:
                    print(f"    - {img['src']}")
        
        # 试运行更新
        print(f"\n试运行更新: {test_url}")
        success = updater.update_article_by_url(test_url, dry_run=True)
        
        if success:
            print("✓ 试运行成功")
        else:
            print("✗ 试运行失败")
            
    except Exception as e:
        logger.error(f"测试失败: {e}")

def test_batch_update():
    """测试批量更新"""
    print("\n=== 测试批量更新 ===")
    
    try:
        # 初始化更新器
        updater = ArticleUpdater()
        
        # 测试URL列表（请替换为您的实际URL）
        test_urls = [
            "https://your-wordpress-site.com/post/1",
            "https://your-wordpress-site.com/post/2",
            "https://your-wordpress-site.com/post/3"
        ]
        
        print(f"批量更新 {len(test_urls)} 篇文章（试运行模式）")
        results = updater.update_multiple_articles(test_urls, dry_run=True)
        
        print(f"批量更新结果:")
        print(f"  总数: {results['total']}")
        print(f"  成功: {results['success']}")
        print(f"  失败: {results['failed']}")
        
        if results['failed'] > 0:
            print("失败的文章:")
            for detail in results['details']:
                if not detail['success']:
                    print(f"  - {detail['url']}")
                    if 'error' in detail:
                        print(f"    错误: {detail['error']}")
                        
    except Exception as e:
        logger.error(f"批量测试失败: {e}")

def test_content_processing():
    """测试内容处理功能"""
    print("\n=== 测试内容处理 ===")
    
    try:
        from content_processor import ContentProcessor
        
        # 创建内容处理器
        processor = ContentProcessor()
        
        # 测试HTML内容
        test_html = """
        <div class="post-content">
            <h1>测试文章标题</h1>
            <p>这是一段测试文字内容。</p>
            <img src="https://example.com/image1.jpg" alt="测试图片1" />
            <p>这是另一段文字内容。</p>
            <figure>
                <img src="https://example.com/image2.jpg" alt="测试图片2" />
                <figcaption>图片说明</figcaption>
            </figure>
            <p>最后一段文字。</p>
        </div>
        """
        
        print("原始HTML内容:")
        print(test_html)
        
        # 处理内容
        processed_content = processor.process_content(test_html)
        
        print("\n处理后的内容:")
        print(processed_content)
        
        # 获取图片信息
        image_info = processor.get_image_info(processed_content)
        print(f"\n图片信息:")
        for img in image_info:
            print(f"  - {img['src']} (alt: {img['alt']})")
            
    except Exception as e:
        logger.error(f"内容处理测试失败: {e}")

def main():
    """主测试函数"""
    print("WordPress文章更新器测试")
    print("=" * 50)
    
    # 运行各种测试
    test_content_processing()
    test_single_article()
    test_batch_update()
    
    print("\n测试完成！")
    print("注意：请在实际使用前修改测试URL为您的真实WordPress文章URL")

if __name__ == '__main__':
    main()
