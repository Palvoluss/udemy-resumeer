# Implementation Plan: Course Summarization Agent (Base Product)

This document outlines the step-by-step implementation plan for creating the base product of the Course Summarization Agent. Each step is designed to be small, specific, and includes a test to validate its correct implementation. Developers should refer to `memory-bank/architecture.md`, `memory-bank/product-requirements.md`, and `memory-bank/tech-stack.md` before starting and during development.

## Phase 1: Project Setup & Basic Structure

**Step 1: Create Main Script File**
-   **Instruction**: Create the main Python script file named `resume_generator.py` in the root directory of the project.
-   **Test**: Verify that the file `resume_generator.py` exists in the project's root directory.

**Step 2: Implement Basic Command-Line Argument Parsing**
-   **Instruction**: Using the `argparse` module in `resume_generator.py`, implement command-line argument parsing for:
    -   `course_dir`: A required argument specifying the path to the course directory.
    -   `output_dir`: An optional argument specifying the path to the output directory. If not provided, it should default to `resume_[course_name]` (where `[course_name]` is the name of the input course directory).
-   **Test**:
    1.  Run the script with the `--help` flag. Verify that `course_dir` and `output_dir` are listed with their descriptions.
    2.  Create a dummy directory named `my_test_course`. Run the script providing `my_test_course` as `course_dir`. Verify that an output directory named `resume_my_test_course` is created.
    3.  Run the script providing `my_test_course` as `course_dir` and a custom path for `output_dir`. Verify that the custom output directory is created.

**Step 3: Initialize Basic Logging**
-   **Instruction**: Configure basic logging using the `logging` module in `resume_generator.py`. Log messages should include a timestamp, log level, and the message. Initial log messages should indicate the script start and the parameters being used (course directory, output directory).
-   **Test**: Run the script with a dummy `course_dir`. Verify that console output shows log messages, including the script starting, and the resolved paths for the course and output directories.

## Phase 2: Core Logic - File System Interaction & Text Extraction

**Step 4: List Chapter Directories**
-   **Instruction**: Implement a function within `resume_generator.py` that takes the `course_dir` path as input and returns a sorted list of `Path` objects, each representing a chapter directory (direct subdirectories of `course_dir`).
-   **Test**: Create a test course structure: `test_data/course_A/Chapter1_Intro`, `test_data/course_A/Chapter02_Advanced`. Call the function with `test_data/course_A`. Verify the function returns a list containing paths to `Chapter1_Intro` and `Chapter02_Advanced`, in that order.
-   **Unit Test**: Create an automated test that validates the function returns the correct paths in the expected order.

**Step 5: List VTT Files within a Chapter**
-   **Instruction**: Implement a function that takes a chapter directory path as input and returns a sorted list of `Path` objects for all `.vtt` files found directly within that chapter directory.
-   **Test**: In the `test_data/course_A/Chapter1_Intro` directory, create `01_Welcome.vtt` and `02_Overview.vtt`. Call the function with the path to `Chapter1_Intro`. Verify it returns a list containing paths to `01_Welcome.vtt` and `02_Overview.vtt`, in that order.
-   **Unit Test**: Create an automated test for this function.

**Step 6: Extract Text from VTT Files**
-   **Instruction**: Implement a function `extract_text_from_vtt(vtt_file_path)` that takes the path to a `.vtt` file. Using `webvtt-py` (or a similar robust VTT parsing library as specified in `tech-stack.md`), extract and return only the spoken text content as a single string. Timestamps, cue settings, and the WEBVTT header should be excluded.
-   **Test**: Create a sample `.vtt` file containing a WEBVTT header, timestamps, and cue text (e.g., "WEBVTT\n\n00:00:01.000 --> 00:00:03.000\nHello world.\n\n00:00:04.000 --> 00:00:05.000\nThis is a test."). Call `extract_text_from_vtt` with the path to this sample file. Verify the returned string is "Hello world.\nThis is a test." (or similar, ensuring only text content remains).
-   **Unit Test**: Create an automated test with sample VTT content.

**Step 7: Extract Text from PDF Files (Basic)**
-   **Instruction**: Implement a function `extract_text_from_pdf(pdf_file_path)` that takes the path to a `.pdf` file. Using `PyPDF2` (as specified in `tech-stack.md`), extract and return the text content from all pages as a single string.
-   **Test**: Create a simple one-page PDF file containing the text "Sample PDF content for testing.". Call `extract_text_from_pdf` with the path to this file. Verify the returned string contains "Sample PDF content for testing.".
-   **Unit Test**: Create an automated test with a sample PDF file.

**Step 8: Implement Text Chunking**
-   **Instruction**: Implement a function `chunk_text(text, max_chunk_size=4000)` that splits a long text into smaller chunks that don't exceed the specified max size. Use LangChain's text splitters (preferably RecursiveCharacterTextSplitter) to create semantically meaningful chunks.
-   **Test**: Create a sample text of approximately 10,000 characters. Call the function with this text. Verify it returns a list of chunks, each under the max_chunk_size, and that all original content is preserved when joining the chunks back together.
-   **Unit Test**: Create an automated test verifying chunk sizes and content preservation.

## Phase 3: API Key Management & OpenAI Integration (Basic)

**Step 9: Implement API Key Manager**
-   **Instruction**: Create a class `APIKeyManager` (initially, this can be within `resume_generator.py`; refactor to a separate file `api_key_manager.py` later if preferred for modularity). This class should have a method `get_key()` that:
    1.  Attempts to load an API key named `OPENAI_API_KEY` from a `.env` file in the project root.
    2.  If not found in `.env`, attempts to load it from an OS environment variable named `OPENAI_API_KEY`.
    3.  Logs whether a key was found (and optionally a non-sensitive part of it, like a hash, for verification, or simply "API key loaded successfully").
    4.  Returns the API key string if found, otherwise raises a clear exception explaining that an API key is required for summarization.
-   **Test**:
    1.  Without a `.env` file or OS environment variable set, call `get_key()`. Verify it raises an appropriate exception.
    2.  Create a `.env` file with `OPENAI_API_KEY="key_from_dotenv"`. Call `get_key()`. Verify it returns `"key_from_dotenv"` and logs success.
    3.  Remove/rename the `.env` file. Set an OS environment variable `OPENAI_API_KEY` to `"key_from_os_env"`. Call `get_key()`. Verify it returns `"key_from_os_env"` and logs success.
-   **Unit Test**: Create tests for different key source scenarios.

**Step 10: Implement OpenAI Summarization Function**
-   **Instruction**: Implement a function `summarize_with_openai(text_content: str, api_key: str)` that:
    1.  Takes a string of text and an OpenAI API key.
    2.  Makes a call to the OpenAI Chat Completions API (e.g., using `gpt-3.5-turbo` model).
    3.  Uses a detailed system prompt that specifies the summary should be precise, detailed, and schematic when appropriate, with no specific length restrictions. For example: "You are an assistant that creates precise and detailed summaries. Maintain all key concepts from the original text. Use schematic representations (bullet points, tables) where appropriate to organize information clearly. Focus on accuracy and completeness rather than brevity."
    4.  Includes the provided `text_content` as the user message.
    5.  Returns the summarized text content from the API response.
    6.  Includes robust error handling for API calls (log detailed errors, and rethrow with clear user-friendly messages).
-   **Test**: 
    1.  Provide a short sample text (e.g., 3-4 sentences) and a valid OpenAI API key. Call the function. Verify it returns a string that is a precise, detailed summary of the input text.
    2.  Call the function with an invalid API key. Verify it handles the error gracefully with a clear error message.
-   **Unit Test**: Create a mock test that simulates API calls without actually calling OpenAI.

**Step 11: Implement Chunked Text Summarization**
-   **Instruction**: Implement a function `summarize_long_text(text: str, api_key: str)` that:
    1.  Takes a potentially long text and an API key.
    2.  Chunks the text using the `chunk_text` function from Step 8.
    3.  For each chunk, calls `summarize_with_openai`.
    4.  If there's only one chunk, returns its summary directly.
    5.  If there are multiple chunks, implements a simple "map-reduce" approach: summarize each chunk, then summarize the combined summaries with an appropriate prompt that indicates this is a meta-summary.
-   **Test**: Create a sample text of approximately 10,000 characters. Call the function with this text and a valid API key. Verify it returns a coherent summary of the entire text.
-   **Unit Test**: Create a mock test that verifies the chunking and summarization flow.

## Phase 4: Markdown Output Generation (Basic)

**Step 12: Write Lesson Summary to Markdown**
-   **Instruction**: Implement a function `write_lesson_summary(lesson_title: str, summary_text: str, output_file_path: Path)`.
    -   This function should create (or overwrite) a Markdown file at `output_file_path`.
    -   The file content should be: `## [lesson_title]

[summary_text]
`.
-   **Test**: Call the function with `lesson_title="Introduction to Topic"`, `summary_text="This is the lesson summary."`, and `output_file_path=Path("output/Chapter1/01_LessonOne.md")`. Verify the file `output/Chapter1/01_LessonOne.md` is created with the correct content.
-   **Unit Test**: Create a test that verifies file creation and content.

**Step 13: Associate PDF Files with VTT Files**
-   **Instruction**: Implement a function `find_related_pdf(vtt_file_path: Path, chapter_dir: Path)` that:
    1.  Takes a VTT file path and its containing chapter directory.
    2.  Extracts the numeric prefix from the VTT filename (e.g., "01" from "01_Welcome.vtt").
    3.  Searches the chapter directory for PDF files with the same numeric prefix.
    4.  Returns a list of matching PDF file paths, or an empty list if none are found.
-   **Test**: In a test chapter directory, create files `01_Welcome.vtt` and `01_Materials.pdf`. Call the function with the path to `01_Welcome.vtt`. Verify it returns a list containing the path to `01_Materials.pdf`.
-   **Unit Test**: Create tests for various filename patterns.

**Step 14: Process VTT and Related PDF Files Together**
-   **Instruction**: Implement a function `process_lesson(vtt_file: Path, chapter_dir: Path, output_dir: Path, api_key: str)` that:
    1.  Takes a VTT file path, its chapter directory, an output directory, and an API key.
    2.  Extracts text from the VTT file.
    3.  Finds related PDF files using `find_related_pdf`.
    4.  For each related PDF, extracts its text.
    5.  Summarizes both the VTT text and each PDF text (using chunking if necessary).
    6.  Constructs a lesson title from the VTT filename.
    7.  Creates an output directory structure mirroring the input: `output_dir/[chapter_name]/`.
    8.  Writes the VTT summary and any PDF summaries to a single Markdown file within this structure.
-   **Test**: 
    1.  Create a test structure with `Chapter1/01_Lesson.vtt` and `Chapter1/01_Materials.pdf`.
    2.  Call the function with appropriate parameters.
    3.  Verify that a Markdown file is created in `output_dir/Chapter1/` with both the VTT summary and PDF summary.
-   **Unit Test**: Create a test that verifies the entire lesson processing flow.

**Step 15: Process All VTT Files in a Chapter**
-   **Instruction**: Implement a function `process_chapter(chapter_dir: Path, output_dir: Path, api_key: str)` that:
    1.  Takes a chapter directory, an output directory, and an API key.
    2.  Lists all VTT files in the chapter directory.
    3.  For each VTT file, calls `process_lesson`.
    4.  Returns information about processed lessons (e.g., paths to generated Markdown files).
-   **Test**: Create a test chapter with multiple VTT files and PDF files. Call the function. Verify that all VTT files are processed and Markdown files are created.
-   **Unit Test**: Create a test that verifies proper chapter processing.

## Phase 5: Creating Summaries and Index Files

**Step 16: Create Chapter Summary File**
-   **Instruction**: Implement a function `create_chapter_summary(chapter_dir: Path, lesson_summaries: list, output_dir: Path)` that:
    1.  Takes a chapter directory, a list of processed lesson summary information, and an output directory.
    2.  Extracts the chapter title from the directory name.
    3.  Creates a Markdown file for the chapter at `output_dir/[chapter_name].md`.
    4.  The chapter file should start with `# [chapter_title]`.
    5.  It should then list each lesson with a link to its individual summary file.
-   **Test**: Call the function with appropriate parameters after processing a test chapter. Verify a chapter summary file is created with the correct title and links to all lesson summaries.
-   **Unit Test**: Create a test verifying the chapter summary creation.

**Step 17: Create Main Index File (README.md)**
-   **Instruction**: Implement a function `create_main_index(course_name: str, chapter_summaries: list, output_dir: Path)` that:
    1.  Takes a course name, a list of chapter summary file paths, and an output directory.
    2.  Creates `README.md` in the `output_dir`.
    3.  The `README.md` should have a main title (e.g., `# Summary for [course_name]`).
    4.  It should then list each processed chapter with a relative link to its chapter summary file.
-   **Test**: Call the function after processing test chapters. Verify `README.md` is created with the correct title and links to all chapter summaries.
-   **Unit Test**: Create a test verifying the index creation.

**Step 18: Orchestrate Complete Course Processing**
-   **Instruction**: In the main execution block of `resume_generator.py`:
    1.  Parse command-line arguments to get `course_dir` and `output_dir`.
    2.  Get the OpenAI API key using `APIKeyManager`.
    3.  List all chapter directories in the course directory.
    4.  For each chapter directory, call `process_chapter`.
    5.  Create chapter summaries for all processed chapters.
    6.  Create the main index file.
    7.  Log detailed progress throughout.
-   **Test**: 
    1.  Create a test course with multiple chapters, each with multiple lessons (VTT files) and some PDF materials.
    2.  Run the script on this test course.
    3.  Verify that the output directory structure mirrors the input structure, with lesson summaries, chapter summaries, and a main index.

## Phase 6: Testing and Documentation

**Step 19: Create Comprehensive Unit Tests**
-   **Instruction**: Create a directory `tests/` in the project root. Implement unit tests for all major functions using a testing framework like pytest. Tests should cover:
    1.  File system operations
    2.  Text extraction
    3.  Text chunking
    4.  API key management
    5.  Summarization (with appropriate mocking)
    6.  Markdown generation
-   **Test**: Run the full test suite. Verify all tests pass.

**Step 20: Create Requirements File and Update Documentation**
-   **Instruction**: 
    1.  Create a `requirements.txt` file listing all dependencies with versions as specified in `tech-stack.md`.
    2.  Update the main `README.md` with installation and usage instructions.
-   **Test**: Test installation in a fresh virtual environment. Verify all dependencies install correctly and the script runs as expected.

This plan focuses on achieving a working product that can process courses with hierarchical structures, extracting text from VTT and PDF files, summarizing content with efficient chunking, and producing well-organized output that mirrors the input structure. The implementation emphasizes modularity, robust error handling, and effective token usage through chunking. 