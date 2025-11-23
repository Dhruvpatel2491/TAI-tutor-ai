import React from 'react';
import '../styles/FormattedMessage.css';

const escapeHtml = (str = '') =>
  str
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#39;');

// New helper: convert inline backtick code to <code class="inline-code">...</code>
//  - escapes HTML first, then replaces `code` occurrences
const formatInlineCode = (raw = '') => {
  const escaped = escapeHtml(String(raw));
  // Replace occurrences of `code` with <code class="inline-code">code</code>
  return escaped.replace(/`([^`]+)`/g, (_m, inner) => {
    // inner is already escaped because we escaped the whole string; return wrapped code tag
    // return `<code class="inline-code"><b>${inner}</b></code>`;
    return `<code class="inline-code"><b>${inner}</b></code>`;
  });
};

const FormattedMessage = ({ blocks = [], variant = 'default', ariaLabel }) => {
  // Compute block class by variant for future theming (e.g., hint, info, error)
  const rootClass = `formatted-message formatted-message--${variant}`;

  const renderFormattedText = (elements, blockKey) => {
    const nodes = [];
    let currentList = null;

    const flushList = () => {
      if (!currentList) return;
      nodes.push(
        <ul key={`${blockKey}-list-${nodes.length}`} className="fm-list">
          {currentList.map((el) => (
            <li
              key={el.key}
              className="list-item"
              dangerouslySetInnerHTML={{ __html: formatInlineCode(el.content) }}
            />
          ))}
        </ul>
      );
      currentList = null;
    };

    elements.forEach((element) => {
      if (element.type === 'li') {
        // start or continue a list
        if (!currentList) currentList = [];
        currentList.push(element);
        return;
      }

      // if we encounter a non-list element, flush any pending list
      if (currentList) flushList();

      if (element.type === 'empty') {
        nodes.push(<div key={element.key} className="empty-line" />);
        return;
      }

      if (element.type === 'paragraph') {
        nodes.push(
          <p key={element.key} className="paragraph">
            <span dangerouslySetInnerHTML={{ __html: formatInlineCode(element.content) }} />
          </p>
        );
        return;
      }

      // Unknown element types are ignored safely
    });

    // flush leftover list if the last elements were list items
    if (currentList) flushList();

    return <div className="text-block">{nodes}</div>;
  };

  return (
    <div className={rootClass} role="article" aria-label={ariaLabel || 'formatted message'}>
      {blocks.map((block) => {
        if (block.type === 'code') {
          // Render code with a class and escaped HTML so it can be highlighted via CSS or a syntax highlighter.
          // block.lang is optional — if provided we include a language- class (e.g. language-javascript).
          const langClass = block.lang ? `language-${block.lang}` : '';
          return (
            <pre key={block.id} className="code-block" tabIndex={0} aria-label={block.lang ? `${block.lang} code` : 'code block'}>
              <code
                className={`code-block__code ${langClass}`}
                // escaped to preserve special characters; CSS should use white-space: pre / pre-wrap
                dangerouslySetInnerHTML={{ __html: escapeHtml(block.content) }}
              />
            </pre>
          );
        }

        if (block.type === 'formatted-text') {
          return <div key={block.id}>{renderFormattedText(block.content, block.id)}</div>;
        }

        return null;
      })}
    </div>
  );
};

export default FormattedMessage;
