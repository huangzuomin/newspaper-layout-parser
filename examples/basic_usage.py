"""
基础使用示例
Basic Usage Example

演示如何使用报纸大样PDF解析系统的核心功能
"""

import sys
from pathlib import Path

# 添加parser模块路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from parser import (
    PDFLoader,
    BlockExtractor,
    FontAnalyzer,
    ZoneSegmenter,
    BlockClassifier,
    ColumnDetector,
    ArticleBuilder,
    ReadingOrderBuilder,
    Visualizer,
)
import json


def basic_usage():
    """基础使用示例"""
    # 设置PDF路径
    pdf_path = "版面解析/B2026-03-18要闻一版01.pdf"
    output_dir = "output"

    print("=" * 60)
    print("报纸大样PDF解析 - 基础使用示例")
    print("=" * 60)

    # 1. 加载PDF
    print("\n1. 加载PDF...")
    loader = PDFLoader(pdf_path)
    page_count = loader.page_count
    print(f"   PDF页数: {page_count}")

    # 2. 处理第一页
    page_no = 0
    print(f"\n2. 处理第 {page_no + 1} 页...")
    page = loader.load_page(page_no)
    page_width, page_height = loader.get_page_dimensions(page_no)
    print(f"   页面尺寸: {page_width:.0f} x {page_height:.0f} points")

    # 3. 提取blocks
    print("\n3. 提取文本块...")
    extractor = BlockExtractor()
    blocks = extractor.extract_blocks(page, page_no)
    blocks = extractor.filter_blocks(blocks, min_chars=3)
    print(f"   提取到 {len(blocks)} 个blocks")

    # 4. 字体分析
    print("\n4. 字体分析...")
    font_analyzer = FontAnalyzer()
    font_profile = font_analyzer.analyze(blocks)
    print(f"   分析方法: {font_profile['method']}")
    print(f"   正文字号: {font_profile.get('body', [0, 0, 0])[2]:.2f}pt")

    # 5. 区域分区
    print("\n5. 区域分区...")
    zone_segmenter = ZoneSegmenter()
    blocks = zone_segmenter.segment(blocks, page_width, page_height)

    # 统计各zone的blocks
    zone_counts = {}
    for block in blocks:
        if block.zone:
            zone = block.zone.value
            zone_counts[zone] = zone_counts.get(zone, 0) + 1
    print(f"   Zone分布: {zone_counts}")

    # 6. Block分类
    print("\n6. Block分类...")
    classifier = BlockClassifier()
    blocks = classifier.classify_candidates(blocks, font_profile)
    blocks = classifier.finalize_classification(blocks)

    # 统计各类型blocks
    type_counts = {}
    for block in blocks:
        if block.type_final:
            type_name = block.type_final.value
            type_counts[type_name] = type_counts.get(type_name, 0) + 1
    print(f"   类型分布: {type_counts}")

    # 7. 分栏检测
    print("\n7. 分栏检测...")
    column_detector = ColumnDetector()
    blocks = column_detector.detect(blocks)

    columns = set(b.column for b in blocks if b.column is not None)
    print(f"   检测到 {len(columns)} 个栏")

    # 8. 文章聚类
    print("\n8. 文章聚类...")
    article_builder = ArticleBuilder()
    articles = article_builder.build(blocks)
    print(f"   构建了 {len(articles)} 篇文章")

    # 显示文章摘要
    for i, article in enumerate(articles[:3]):  # 只显示前3篇
        print(f"   文章 {i + 1}: {article.id}")
        print(f"     - Headline: {article.headline_block_id}")
        print(f"     - Body blocks: {len(article.body_block_ids)}")
        print(f"     - Zone: {article.zone.value if article.zone else 'None'}")

    # 9. 阅读顺序
    print("\n9. 构建阅读顺序...")
    reading_order_builder = ReadingOrderBuilder()
    block_order, article_order = reading_order_builder.build(blocks, articles)
    print(f"   Block级顺序: {len(block_order)} 个blocks")
    print(f"   Article级顺序: {len(article_order)} 篇文章")

    # 10. 可视化
    print("\n10. 生成可视化...")
    visualizer = Visualizer()

    # 原始blocks可视化
    raw_output = Path(output_dir) / "overlays" / "example_raw.png"
    visualizer.visualize_raw_blocks(
        blocks, page_width, page_height,
        str(raw_output),
        show_block_ids=True,
        show_font_sizes=False,
    )
    print(f"   原始可视化: {raw_output}")

    # 结构可视化
    structure_output = Path(output_dir) / "overlays" / "example_structure.png"
    visualizer.visualize_structure(
        blocks, page_width, page_height,
        str(structure_output),
        show_zones=True,
        show_columns=True,
        show_block_types=True,
    )
    print(f"   结构可视化: {structure_output}")

    # 文章可视化
    articles_output = Path(output_dir) / "overlays" / "example_articles.png"
    visualizer.visualize_articles(
        blocks, articles, page_width, page_height,
        str(articles_output),
        show_article_bounds=True,
        show_article_connections=True,
        show_reading_order=False,
    )
    print(f"   文章可视化: {articles_output}")

    # 11. 保存结果
    print("\n11. 保存结果...")
    result = {
        "page_no": page_no + 1,
        "width": page_width,
        "height": page_height,
        "blocks": [b.to_dict() for b in blocks],
        "articles": [a.to_dict() for a in articles],
        "block_reading_order": block_order,
        "article_reading_order": article_order,
        "font_profile": font_profile,
    }

    output_file = Path(output_dir) / "json" / "example_result.json"
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    print(f"   结果已保存: {output_file}")

    # 关闭PDF
    loader.close()

    print("\n" + "=" * 60)
    print("解析完成！")
    print(f"总blocks: {len(blocks)}")
    print(f"总文章: {len(articles)}")
    print("=" * 60)


def analyze_single_article():
    """分析单篇文章的示例"""
    print("\n" + "=" * 60)
    print("示例：深入分析单篇文章")
    print("=" * 60)

    # ... (可扩展更多分析示例)


if __name__ == "__main__":
    # 运行基础示例
    basic_usage()

    print("\n\n提示：")
    print("- 查看 output/overlays/ 目录下的可视化图片")
    print("- 查看 output/json/example_result.json 了解数据结构")
    print("- 使用 examples/batch_process.py 批量处理多个PDF")
