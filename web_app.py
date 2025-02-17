from flask import Flask, request, render_template_string, send_file
import os
import sys

# Import functions from onefilellm.py. 
# Ensure onefilellm.py is accessible in the same directory.
from onefilellm import process_github_repo, process_github_pull_request, process_github_issue
from onefilellm import process_arxiv_pdf, process_local_folder, fetch_youtube_transcript
from onefilellm import crawl_and_extract_text, process_doi_or_pmid, get_token_count, preprocess_text, safe_file_read
from pathlib import Path
import pyperclip

app = Flask(__name__)

# Simple HTML template using inline rendering for demonstration.
template = """
<!DOCTYPE html>
<html>
<head>
    <title>1FileLLM Web Interface</title>
    <style>
        :root {
            --primary-color: #2563eb;
            --secondary-color: #1e40af;
            --background-color: #f3f4f6;
            --text-color: #1f2937;
            --border-color: #e5e7eb;
        }
        
        body { 
            font-family: 'Segoe UI', system-ui, sans-serif;
            margin: 0;
            padding: 2em;
            background-color: var(--background-color);
            color: var(--text-color);
            line-height: 1.5;
        }
        
        .container {
            max-width: 1200px;
            margin: 0 auto;
            background-color: white;
            padding: 2em;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }

        h1 {
            color: var(--primary-color);
            text-align: center;
            margin-bottom: 1em;
        }

        .input-section {
            margin-bottom: 2em;
        }

        input[type="text"] {
            width: 100%;
            padding: 0.75em;
            border: 2px solid var(--border-color);
            border-radius: 4px;
            font-size: 1em;
            margin-bottom: 1em;
        }

        button {
            background-color: var(--primary-color);
            color: white;
            padding: 0.75em 2em;
            border: none;
            border-radius: 4px;
            cursor: pointer;
            font-size: 1em;
            transition: background-color 0.3s;
        }

        button:hover {
            background-color: var(--secondary-color);
        }

        .examples {
            background-color: #f8fafc;
            padding: 1.5em;
            border-radius: 4px;
            margin: 1.5em 0;
        }

        .examples h3 {
            color: var(--primary-color);
            margin-top: 0;
        }

        .example-item {
            margin-bottom: 0.5em;
        }

        .output-container {
            margin-top: 2em;
            padding: 1.5em;
            background-color: #f8fafc;
            border-radius: 4px;
        }

        .token-counts {
            background-color: white;
            padding: 1em;
            border-radius: 4px;
            margin: 1em 0;
            border: 1px solid var(--border-color);
        }

        .download-links {
            display: flex;
            gap: 1em;
            margin-top: 1em;
        }

        .download-links a {
            background-color: var(--primary-color);
            color: white;
            padding: 0.5em 1em;
            border-radius: 4px;
            text-decoration: none;
            transition: background-color 0.3s;
        }

        .download-links a:hover {
            background-color: var(--secondary-color);
        }

        pre {
            background-color: white;
            padding: 1em;
            border-radius: 4px;
            overflow-x: auto;
            border: 1px solid var(--border-color);
        }

        .copy-button {
            position: absolute;
            top: 10px;
            right: 10px;
            background-color: var(--primary-color);
            color: white;
            padding: 0.5em 1em;
            border: none;
            border-radius: 4px;
            cursor: pointer;
            font-size: 0.9em;
            transition: background-color 0.3s;
        }

        .copy-button:hover {
            background-color: var(--secondary-color);
        }

        .output-text-container {
            position: relative;
            margin-top: 1em;
        }
    </style>
    <script>
        function copyToClipboard() {
            const outputText = document.getElementById('output-text').innerText;
            navigator.clipboard.writeText(outputText).then(() => {
                const button = document.getElementById('copy-button');
                button.textContent = 'Copied!';
                setTimeout(() => {
                    button.textContent = 'Copy to Clipboard';
                }, 2000);
            }).catch(err => {
                console.error('Failed to copy text: ', err);
            });
        }
    </script>
</head>
<body>
    <div class="container">
        <h1>1FileLLM Web Interface</h1>
        
        <div class="input-section">
            <form method="POST" action="/">
                <input type="text" name="input_path" required 
                    placeholder="Enter URL, path, DOI, or PMID"/>
                <button type="submit">Process</button>
            </form>
        </div>

        <div class="examples">
            <h3>Supported Input Types:</h3>
            <div class="example-item">• GitHub repository: <code>https://github.com/username/repo</code></div>
            <div class="example-item">• GitHub pull request: <code>https://github.com/user/repo/pull/102</code></div>
            <div class="example-item">• GitHub issue: <code>https://github.com/user/repo/issues/1191</code></div>
            <div class="example-item">• ArXiv paper: <code>https://arxiv.org/abs/2401.14295</code></div>
            <div class="example-item">• YouTube video: <code>https://www.youtube.com/watch?v=KZ_NlnmPQYk</code></div>
            <div class="example-item">• Webpage: <code>https://llm.datasette.io/en/stable/</code></div>
            <div class="example-item">• Sci-Hub DOI: <code>10.1053/j.ajkd.2017.08.002</code></div>
            <div class="example-item">• Sci-Hub PMID: <code>29203127</code></div>
        </div>

        {% if output %}
        <div class="output-container">
            <h2>Processed Output</h2>
            
            <div class="token-counts">
                <h3>Token Counts</h3>
                <p>
                    Uncompressed Tokens: <strong>{{ uncompressed_token_count }}</strong><br>
                    Compressed Tokens: <strong>{{ compressed_token_count }}</strong>
                </p>
            </div>

             <div class="download-links">
                <a href="/download?filename=uncompressed_output.txt">Download Uncompressed Output</a>
                <a href="/download?filename=compressed_output.txt">Download Compressed Output</a>
            </div>

            <div class="output-text-container">
                <button id="copy-button" class="copy-button" onclick="copyToClipboard()">
                    Copy to Clipboard
                </button>
                <pre id="output-text">{{ output }}</pre>
            </div>
            
           
        </div>
        {% endif %}
    </div>
</body>
</html>
"""

@app.route("/", methods=["GET", "POST"])
def index():
    if request.method == "POST":
        input_path = request.form.get("input_path", "").strip()

        # Prepare filenames
        output_file = "uncompressed_output.txt"
        processed_file = "compressed_output.txt"
        urls_list_file = "processed_urls.txt"

        # Determine input type and process accordingly (mirroring logic from onefilellm.py main)
        try:
            from urllib.parse import urlparse
            parsed = urlparse(input_path)

            if "github.com" in input_path:
                if "/pull/" in input_path:
                    final_output = process_github_pull_request(input_path)
                elif "/issues/" in input_path:
                    final_output = process_github_issue(input_path)
                else:
                    final_output = process_github_repo(input_path)
            elif parsed.scheme in ["http", "https"]:
                if "youtube.com" in input_path or "youtu.be" in input_path:
                    final_output = fetch_youtube_transcript(input_path)
                elif "arxiv.org" in input_path:
                    final_output = process_arxiv_pdf(input_path)
                else:
                    crawl_result = crawl_and_extract_text(input_path, max_depth=2, include_pdfs=True, ignore_epubs=True)
                    final_output = crawl_result['content']
                    with open(urls_list_file, 'w', encoding='utf-8') as urls_file:
                        urls_file.write('\n'.join(crawl_result['processed_urls']))
            elif (input_path.startswith("10.") and "/" in input_path) or input_path.isdigit():
                final_output = process_doi_or_pmid(input_path)
            else:
                final_output = process_local_folder(input_path)

            # Write the uncompressed output
            with open(output_file, "w", encoding="utf-8") as file:
                file.write(final_output)

            # Process the compressed output
            preprocess_text(output_file, processed_file)

            compressed_text = safe_file_read(processed_file)
            compressed_token_count = get_token_count(compressed_text)

            uncompressed_text = safe_file_read(output_file)
            uncompressed_token_count = get_token_count(uncompressed_text)

            # Copy to clipboard
            pyperclip.copy(uncompressed_text)

            return render_template_string(template,
                                          output=final_output,
                                          uncompressed_token_count=uncompressed_token_count,
                                          compressed_token_count=compressed_token_count)
        except Exception as e:
            return render_template_string(template, output=f"Error: {str(e)}")

    return render_template_string(template)


@app.route("/download")
def download():
    filename = request.args.get("filename")
    if filename and os.path.exists(filename):
        return send_file(filename, as_attachment=True)
    return "File not found", 404

if __name__ == "__main__":
    try:
        # Try running in development mode
        app.run(
            host="127.0.0.1",
            port=5000,
            debug=True  # Enable debug mode for development
        )
    except Exception as e:
        print(f"Error starting server: {str(e)}")
