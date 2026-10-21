import os
import pytest
from app.agent.schemas import WebSearchInput, CreateReminderInput, GenerateFileInput
from app.agent.tool_registry import tool_registry
from app.services.file_service import file_generator


def test_schema_validations():
    # Valid web search
    s = WebSearchInput(query="Python jobs", max_results=5)
    assert s.query == "Python jobs"
    assert s.max_results == 5

    # Invalid reminder (missing required fields)
    with pytest.raises(Exception):
        CreateReminderInput()


def test_file_generation_txt(tmp_path):
    gen = file_generator
    txt_path = gen.generate_text_file("Hello world from unit test", filename="test.txt")
    assert os.path.exists(txt_path)
    with open(txt_path, "r", encoding="utf-8") as f:
        assert f.read() == "Hello world from unit test"


def test_file_generation_csv(tmp_path):
    gen = file_generator
    rows = [{"name": "Alice", "role": "Engineer"}, {"name": "Bob", "role": "Designer"}]
    csv_path = gen.generate_csv_file(rows=rows, filename="users.csv")
    assert os.path.exists(csv_path)
    with open(csv_path, "r", encoding="utf-8") as f:
        content = f.read()
        assert "Alice" in content
        assert "Designer" in content


def test_file_generation_pdf(tmp_path):
    gen = file_generator
    pdf_path = gen.generate_pdf_report(
        title="Weekly AI Report",
        paragraphs=["First paragraph of the report.", "Second paragraph with conclusions."],
        filename="report.pdf",
    )
    assert os.path.exists(pdf_path)
    assert os.path.getsize(pdf_path) > 500


def test_file_generation_docx(tmp_path):
    gen = file_generator
    docx_path = gen.generate_docx_document(
        title="Engineering Proposal",
        paragraphs=["Project overview", "Milestones"],
        filename="proposal.docx",
    )
    assert os.path.exists(docx_path)
    assert os.path.getsize(docx_path) > 500


def test_file_generation_path_traversal():
    gen = file_generator
    # Path traversal should be sanitized and contained within base dir
    path = gen.generate_text_file("safe content", filename="../../etc/passwd.txt")
    assert path.startswith(gen.base_dir)
    assert not os.path.exists("../../etc/passwd.txt")
    assert ".." not in os.path.basename(path)


@pytest.mark.asyncio
async def test_tool_registry_execution():
    res = await tool_registry.execute_tool(
        name="generate_file",
        arguments={"file_type": "txt", "filename": "registry_test.txt", "content": "Registry works!"},
        user_id=12345,
    )
    assert "file_path" in res
    assert os.path.exists(res["file_path"])
