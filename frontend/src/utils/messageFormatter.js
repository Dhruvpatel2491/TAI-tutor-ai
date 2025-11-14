export const formatBotResponse = (text) => {
  // Split content into blocks
  const blocks = [];
  let currentIndex = 0;

  // Parse code blocks
  const codeBlockRegex = /```([\s\S]*?)```/g;
  let match;

  while ((match = codeBlockRegex.exec(text)) !== null) {
    // Add text before code block
    if (match.index > currentIndex) {
      blocks.push({
        type: 'text',
        content: text.substring(currentIndex, match.index)
      });
    }

    // Add code block
    blocks.push({
      type: 'code',
      content: match[1].trim()
    });

    currentIndex = match.index + match[0].length;
  }

  // Add remaining text
  if (currentIndex < text.length) {
    blocks.push({
      type: 'text',
      content: text.substring(currentIndex)
    });
  }

  // Process text blocks for formatting
  return blocks.map((block, idx) => {
    if (block.type === 'code') {
      return {
        ...block,
        id: idx
      };
    }

    // Parse markdown in text blocks
    const formattedContent = parseMarkdown(block.content);
    return {
      type: 'formatted-text',
      content: formattedContent,
      id: idx
    };
  });
};

const parseMarkdown = (text) => {
  const elements = [];
  const lines = text.split('\n');

  lines.forEach((line, idx) => {
    const trimmed = line.trim();

    if (!trimmed) {
      elements.push({ type: 'empty', content: '', key: `empty-${idx}` });
      return;
    }

    // Ordered lists
    if (/^\d+\.\s/.test(trimmed)) {
      elements.push({
        type: 'li',
        content: trimmed.replace(/^\d+\.\s/, ''),
        key: `li-${idx}`
      });
      return;
    }

    // Unordered lists
    if (/^[-*]\s/.test(trimmed)) {
      elements.push({
        type: 'li',
        content: trimmed.replace(/^[-*]\s/, ''),
        key: `li-${idx}`
      });
      return;
    }

    // Bold and italic
    const processed = trimmed
      .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
      .replace(/\*(.*?)\*/g, '<em>$1</em>')
      .replace(/__(.*?)__/g, '<strong>$1</strong>')
      .replace(/_(.*?)_/g, '<em>$1</em>');

    elements.push({
      type: 'paragraph',
      content: processed,
      key: `p-${idx}`
    });
  });

  return elements;
};
