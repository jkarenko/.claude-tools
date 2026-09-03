---
name: translate-file
description: Translate a file's text content to a target language while preserving the file's structure (timestamps, speaker labels, formatting, markup). Takes target language and optional special instructions as arguments. Use when user says "translate", "translate file", "translate to English", etc.
---

# Translate File

Translate the text content of a file to a target language while preserving all structural elements unchanged.

## Arguments

The skill receives arguments in this format:
- First argument or keyword: **target language** (e.g., "English", "Finnish", "French")
- Remaining text: **special instructions** (optional, e.g., "keep technical terms in English", "formal tone", "summarize while translating")

If no file is specified in the arguments, check if the user has a file open in the IDE or mentioned a file path in conversation context. If still unclear, ask.

## Workflow

### 1. Identify the File and Parameters

Determine:
- **Source file path**: From arguments, IDE context, or ask the user
- **Target language**: From first argument (required — ask if missing)
- **Special instructions**: Any additional guidance from remaining arguments

Read the file to understand its structure.

### 2. Analyze the File Structure

Identify structural elements that must be preserved **exactly as-is**:

| Element | Example | Action |
|---------|---------|--------|
| Timestamps | `[00:01:23.45]`, `[01:00:02:03 - 01:00:05:21]` | Keep unchanged |
| Speaker labels | `Bruno`, `Speaker 4`, `Juho` | Keep unchanged |
| Line breaks and blank lines | | Keep unchanged |
| Markdown formatting | `#`, `**`, `- `, `|` | Keep unchanged |
| Code blocks | ` ``` ` | Keep unchanged |
| File paths, URLs | `/path/to/file`, `https://...` | Keep unchanged |
| Numbers, IDs, codes | `RITM0010633`, `€5,000` | Keep unchanged |
| Proper nouns (people, companies, products) | `Proactis`, `Nettailer`, `BNP Paribas` | Keep unchanged unless translation is obvious and requested |

**Only translate the spoken/written text content.**

### 3. Translate in Chunks

Process the file in manageable chunks to maintain quality:

- Read a section of the file (respect natural boundaries like speaker turns or paragraphs)
- Translate the text content while preserving structure
- Write the translated chunk to the output file
- Continue until complete

**Translation rules:**
- Maintain the same register and tone as the original
- If the source mixes languages (e.g., French with English technical terms), translate everything to the target language unless special instructions say otherwise
- Preserve meaning over literal translation — natural phrasing in the target language
- If a passage is garbled or unclear in the original (common in auto-transcriptions), translate what is understandable and keep unclear parts marked with `[unclear]`
- Do not add, remove, or reorder content — the output must be a 1:1 structural match of the input

### 4. Write Output

Write the translated file to the **same directory** as the source file with a language suffix:
- Source: `filename.txt` → Output: `filename_en.txt` (for English)
- Source: `filename.md` → Output: `filename_en.md`
- Language codes: `en` (English), `fi` (Finnish), `fr` (French), `de` (German), `sv` (Swedish), `it` (Italian), `es` (Spanish), etc.

If a file with the output name already exists, ask the user before overwriting.

### 5. Report

After translation, report:
- Source file and target file paths
- Source language (detected) → target language
- Any special instructions applied
- Number of unclear passages marked with `[unclear]`, if any
- Any notable translation decisions made (e.g., ambiguous terms)

## Rules

- **Never modify the source file** — always write to a new file
- **Structure preservation is paramount** — if in doubt, keep the original formatting
- **Speaker labels stay in original** — do not translate names or speaker identifiers
- **Timestamps are sacred** — never modify any timestamp format
- **Large files**: For files over 500 lines, process in chunks and use the Write tool for the first chunk, then Edit tool to append subsequent chunks. Report progress periodically.
- **Ask before overwriting** — if the output file already exists

## Examples

**Translate French transcript to English:**
```
/translate-file English
```
With a French transcript open, translates all French text to English while keeping timestamps and speaker labels.

**Translate with special instructions:**
```
/translate-file Finnish keep technical IT terms in English
```
Translates to Finnish but preserves technical terminology in English.

**Translate a specific file:**
```
/translate-file English formal tone /path/to/document.md
```
Translates the specified file to English with formal register.
