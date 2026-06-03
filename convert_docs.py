import os
import re

DOCS_DIR = "./docs"

TITLE_MAPPING = {
    "CATAN — OFFICIAL RULES SUMMARY": "Catan — Official Rules Summary",
    "CLUE (CLUEDO) — OFFICIAL RULES SUMMARY": "Clue (Cluedo) — Official Rules Summary",
    "CODENAMES — OFFICIAL RULES SUMMARY": "Codenames — Official Rules Summary",
    "MONOPOLY — OFFICIAL RULES SUMMARY": "Monopoly — Official Rules Summary",
    "PANDEMIC — OFFICIAL RULES SUMMARY": "Pandemic — Official Rules Summary",
    "RISK — OFFICIAL RULES SUMMARY": "Risk — Official Rules Summary",
    "TICKET TO RIDE — OFFICIAL RULES SUMMARY": "Ticket to Ride — Official Rules Summary",
    "UNO — OFFICIAL RULES SUMMARY": "Uno — Official Rules Summary"
}

def is_header(line):
    cleaned = line.strip()
    if not cleaned:
        return False
    # Must contain at least one alphabetic character
    if not any(c.isalpha() for c in cleaned):
        return False
    # Must be fully uppercase
    return cleaned.isupper()

def convert_file(filepath):
    print(f"Processing: {filepath}")
    with open(filepath, "r", encoding="utf-8") as f:
        content = f.read()

    lines = content.splitlines()
    new_lines = []
    is_first_line = True

    for line in lines:
        stripped = line.strip()
        if not stripped:
            new_lines.append(line)
            continue

        if is_first_line:
            # Map or title-case the first line as the main h1 header
            mapped_title = TITLE_MAPPING.get(stripped, stripped.title())
            new_lines.append(f"# {mapped_title}")
            is_first_line = False
            continue

        if is_header(stripped):
            # Format uppercase headers as h2 headers
            new_lines.append(f"## {stripped}")
        else:
            new_lines.append(line)

    new_content = "\n".join(new_lines) + "\n"
    
    # Write the new .md file
    md_filepath = filepath.replace(".txt", ".md")
    with open(md_filepath, "w", encoding="utf-8") as f:
        f.write(new_content)
    print(f"Created: {md_filepath}")

    # Remove the old .txt file
    os.remove(filepath)
    print(f"Deleted: {filepath}")

def main():
    if not os.path.exists(DOCS_DIR):
        print(f"Directory {DOCS_DIR} not found.")
        return

    txt_files = [f for f in os.listdir(DOCS_DIR) if f.endswith(".txt")]
    if not txt_files:
        print("No .txt files found in the docs directory.")
        return

    for filename in sorted(txt_files):
        filepath = os.path.join(DOCS_DIR, filename)
        convert_file(filepath)

    print("\nAll files successfully reformatted!")

if __name__ == "__main__":
    main()
