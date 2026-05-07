from kfp import dsl

DOCLING_BASE_IMAGE = "quay.io/fabianofranz/docling-ubi9:2.54.0"


@dsl.component(
    base_image=DOCLING_BASE_IMAGE,
    packages_to_install=[
        "torch",
        "datasets>=4.2.0",
        "docling>=2.53.0",
        "markdown-it-py>=4.0.0",
        "tiktoken>=0.11.0",
        "python-dotenv>=1.1.1",
    ],
)
def document_processing(
    artifacts_path: dsl.Input[dsl.Artifact],
    output_path: dsl.Output[dsl.Artifact],
    web_urls: str = "",
    chunk_max_tokens: int = 512,
    chunk_overlap_tokens: int = 50,
    domain: str = None,
    document_outline: str = None,
    icl_document: str = None,
    icl_query1: str = None,
    icl_query2: str = None,
    icl_query3: str = None,
):
    import glob
    from pathlib import Path
    from typing import List

    import tiktoken
    from datasets import load_dataset
    from docling.datamodel.base_models import InputFormat
    from docling.datamodel.pipeline_options import PdfPipelineOptions
    from docling.document_converter import (
        DocumentConverter,
        HTMLFormatOption,
        PdfFormatOption,
    )

    OUTPUT_DIR = Path(output_path.path)  # Path to the workspace directory

    OUTPUT_DIR.mkdir(
        parents=True, exist_ok=True
    )  # Create output directory if it does not exist

    DOCLING_OUTPUT_DIR = OUTPUT_DIR / "docling_output"
    DOCLING_OUTPUT_DIR.mkdir(
        parents=True, exist_ok=True
    )  # Create docling output directory if it does not exist

    WEB_URLS = []
    for idx, url in enumerate(web_urls.split(",")):
        if url.strip():
            WEB_URLS.append((
                f"url-{idx + 1}",
                url.strip(),
            ))

    if not WEB_URLS:
        raise ValueError("web_urls must contain at least one non-empty URL")

    # Let Docling use the default cache location where models were downloaded
    pdf_pipeline_options = PdfPipelineOptions()
    pdf_pipeline_options.artifacts_path = Path(artifacts_path.path)
    pdf_options = PdfFormatOption(pipeline_options=pdf_pipeline_options)

    html_options = HTMLFormatOption()

    converter = DocumentConverter(
        format_options={InputFormat.PDF: pdf_options, InputFormat.HTML: html_options}
    )

    for name, url in WEB_URLS:
        result = converter.convert(url)
        result.document.save_as_markdown(f"{DOCLING_OUTPUT_DIR}/{name}.md")

    print(
        f"Number of md files in {DOCLING_OUTPUT_DIR}: ",
        len(glob.glob(f"{DOCLING_OUTPUT_DIR}/*.md")),
    )

    def chunk_markdown(
        text: str, max_tokens: int = 200, overlap: int = 50
    ) -> List[str]:
        """
        Splits Markdown text into chunks at block-level elements
        (headings, paragraphs, lists, tables, code, blockquotes).
        Adds overlap (in words) between all consecutive chunks.

        Args:
            text: The markdown text to be chunked
            max_tokens: Maximum number of words per chunk
            overlap: Number of overlapping words between consecutive chunks

        Returns:
            List of text chunks with specified overlap
        """
        from markdown_it import MarkdownIt

        # Initialize the Markdown parser to understand the document structure
        md = MarkdownIt()
        tokens = md.parse(text)

        # To ensure that you do not split the text in the middle of headings or lists,
        # group tokens into block-level segments to preserve the Markdown structure
        blocks = []
        buf = []
        for tok in tokens:
            if tok.block and tok.type.endswith("_open"):
                buf = []
            elif tok.block and tok.type.endswith("_close"):
                if buf:
                    blocks.append("\n".join(buf).strip())
                    buf = []
            elif tok.content:
                buf.append(tok.content)
        if buf:
            blocks.append("\n".join(buf).strip())

        # Split blocks into chunks with overlap to maintain context continuity
        chunks = []
        current_words = []
        for block in blocks:
            words = block.split()
            for w in words:
                current_words.append(w)
                if len(current_words) >= max_tokens:
                    # Emit a complete chunk
                    chunks.append(" ".join(current_words))
                    # Prepare next buffer with overlap from the end of this chunk
                    # to ensure context continuity between chunks
                    current_words = current_words[-overlap:] if overlap > 0 else []

        # Add any remaining words as the final chunk
        if current_words:
            chunks.append(" ".join(current_words))

        return chunks

    def save_chunks_to_jsonl(chunks, filename):
        """
        Save a list of strings to a JSONL file where each line is a JSON object
        with the key 'chunk'. Returns the path to the saved file.

        Args:
            chunks (list of str): List of text chunks to save.
            filename (str): Path to the output .jsonl file (string or Path).

        Returns:
            pathlib.Path: Path to the saved file.
        """
        import json

        path = Path(filename)
        with path.open("w", encoding="utf-8") as f:
            for chunk in chunks:
                json_line = json.dumps({"chunk": chunk}, ensure_ascii=False)
                f.write(json_line + "\n")
        print(f"Saved {len(chunks)} chunks to {path}")
        return path

    markdown_files = sorted(DOCLING_OUTPUT_DIR.glob("*.md"))
    if not markdown_files:
        raise FileNotFoundError(
            f"No markdown files were generated in {DOCLING_OUTPUT_DIR}"
        )

    print(f"Number of Markdown files : {len(markdown_files)}")
    print(f"List of Markdown files : {markdown_files}")
    chunks = []
    print("Chunking of markdown files")
    print("-----------------------------------", end="\n\n\n")
    for markdown_file in markdown_files:
        print(f"Chunking file : {markdown_file} \n\n")
        text = markdown_file.read_text(encoding="utf-8")
        chunks.extend(
            chunk_markdown(
                text,
                max_tokens=chunk_max_tokens,
                overlap=chunk_overlap_tokens,
            )
        )

    _ = save_chunks_to_jsonl(chunks, f"{OUTPUT_DIR}/chunks.jsonl")

    i = 1
    min_tokens = 6000
    max_tokens = 8000
    for chunk in chunks:
        enc = tiktoken.get_encoding("cl100k_base")
        token_count = len(enc.encode(chunk))
        if (token_count < min_tokens or token_count > max_tokens) and (
            i != len(chunks)
        ):
            print(
                f"\033[31mWARNING: Chunk {i} ({chunk[:30]} ... {chunk[-30:]}) {token_count} tokens\033[0m"
            )
        i += 1

    icl = {
        "document_outline": document_outline,
        "icl_document": icl_document,
        "icl_query_1": icl_query1,
        "icl_query_2": icl_query2,
        "icl_query_3": icl_query3,
        "domain": domain,
    }

    chunks_files = [f"{OUTPUT_DIR}/chunks.jsonl"]

    # Load the dataset from the JSON file
    chunks = (
        load_dataset("json", data_files=chunks_files)
        .rename_columns({"chunk": "document"})
        .select_columns("document")
    )
    # chunks is a DatasetDict. By default, the dataset for the chunks is put in the "train" split in the DatasetDict
    chunks = chunks["train"]

    # Map the ICL fields to each document chunk (if you want to use the same ICL for all, as shown here)
    seed_data = chunks.map(lambda x: icl)

    # Save the seed data to a JSONL file
    seed_data.to_json(f"{OUTPUT_DIR}/seed_data.jsonl", orient="records", lines=True)
