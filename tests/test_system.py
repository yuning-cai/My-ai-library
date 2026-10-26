import sys
import time
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pymupdf

from src.config import ROOT_DIR
from src.client.server_thread import BackgroundServer
from src.client.api_client import api_client


def create_sample_pdf(output_path: Path) -> Path:
    doc = pymupdf.open()
    
    # 第 1 页
    p1 = doc.new_page()
    p1.insert_text((50, 80), "第一章：人工智能导论", fontsize=20)
    p1.insert_text((50, 130), "欢迎来到私人 AI 图书馆系统！这是测试用电子书的第一页。", fontsize=12)
    p1.insert_text((50, 160), "本阅读器支持高清晰度平滑渲染、页码快速跳转与缩放控制。", fontsize=12)

    # 第 2 页
    p2 = doc.new_page()
    p2.insert_text((50, 80), "第二章：向量检索与 RAG 架构", fontsize=20)
    p2.insert_text((50, 130), "这是第二页，专门介绍未来将要接入的知识库问答大模型。", fontsize=12)

    # 第 3 页
    p3 = doc.new_page()
    p3.insert_text((50, 80), "第三章：全文总结", fontsize=20)
    p3.insert_text((50, 130), "第三页是总结与致谢。", fontsize=12)

    # 设置元数据和大纲
    doc.set_metadata({
        "title": "人工智能实战与导论 (测试书)",
        "author": "AI 助手",
    })
    doc.set_toc([
        [1, "第一章：人工智能导论", 1],
        [1, "第二章：向量检索与 RAG 架构", 2],
        [1, "第三章：全文总结", 3],
    ])

    doc.save(str(output_path))
    doc.close()
    return output_path


def run_verification():
    print("--- 1. 启动后台 FastAPI 服务 ---")
    server = BackgroundServer()
    server.start()

    ready = False
    for _ in range(30):
        if api_client.health_check():
            ready = True
            break
        time.sleep(0.1)

    assert ready, "FastAPI 健康检测未通过！"
    print("FastAPI 运行正常: Health Check Passed!")

    print("--- 2. 创建测试 PDF 文件 ---")
    test_pdf = ROOT_DIR / "storage" / "sample_test.pdf"
    create_sample_pdf(test_pdf)
    assert test_pdf.exists(), "测试 PDF 创建失败！"
    print(f"测试 PDF 生成成功: {test_pdf}")

    print("--- 3. 测试通过 FastAPI 上传电子书 ---")
    upload_res = api_client.upload_book(str(test_pdf))
    print("上传返回信息:", upload_res.get("message"))
    book_id = upload_res.get("book_id")
    assert book_id is not None, "上传失败，无 book_id"

    print("--- 4. 测试获取图书列表与详情 ---")
    books = api_client.get_books()
    print(f"书架当前共有 {len(books)} 本书")
    uploaded = next((b for b in books if b["id"] == book_id), None)
    assert uploaded is not None, "未在书架列表中找到刚上传的书籍！"
    print(f"书籍书名: {uploaded['title']}, 作者: {uploaded['author']}, 页数: {uploaded['page_count']}")
    assert uploaded["page_count"] == 3, f"预期页数为 3，实际为 {uploaded['page_count']}"

    print("--- 5. 测试更新阅读进度 ---")
    ok = api_client.update_progress(book_id, current_page=2, total_pages=3)
    assert ok, "更新进度失败"
    updated_book = api_client.get_book(book_id)
    print(f"更新后进度: {updated_book['reading_progress']}% (当前第 {updated_book['current_page']} 页)")
    assert updated_book["current_page"] == 2

    print("--- 6. 立即清理测试上传的数据，不污染用户书架 ---")
    api_client.delete_book(book_id)
    if test_pdf.exists():
        test_pdf.unlink(missing_ok=True)
    print("测试书籍与临时文件已彻底清理！")

    print("--- 7. 清理服务 ---")
    server.stop()
    print("=== 所有核心功能自动化验证全部通过！ ===")


if __name__ == "__main__":
    run_verification()
