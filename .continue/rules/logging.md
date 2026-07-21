---
name: Logging Style
description: Standard logging conventions for the LearningAid project.
globs: "backend/**/*.py"
alwaysApply: true
---

# Logging Style

All log messages MUST be written in English.

## Tone

- Professional
- Concise
- Neutral
- No conversational language

## Formatting

Use sentence case.

Correct:

- Processing document.
- Generating summary.
- Generating quiz.
- Quiz generation completed.
- Cache hit.
- Cache miss.
- Upload completed.
- Failed to parse PDF.

Avoid:

- PROCESSING DOCUMENT
- GENERATE QUIZ...
- SUCCESS!!!
- ERROR!!!!!!!!
- LOADING...
- DONE

## Emojis

Never use emojis or Unicode icons in log messages.

Incorrect:

logger.info("📄 Processing document.")

Correct:

logger.info("Processing document.")

## Information

Include useful context whenever possible.

Good:

logger.info("Processing document: %s", document.filename)

logger.info("Generating quiz for document_id=%s", document.id)

Bad:

logger.info("Processing...")

## Errors

Describe what failed.

Bad:

logger.error("Error")

Good:

logger.error("Failed to generate quiz.")

Prefer structured logging and include the exception rather than embedding stack traces in the message.