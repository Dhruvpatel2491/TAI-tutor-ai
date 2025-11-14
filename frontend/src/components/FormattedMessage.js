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

const FormattedMessage = ({ blocks }) => {
  return (
    <div className="formatted-message">
      {blocks.map((block) => {
        if (block.type === 'code') {
          // Render code with a class and escaped HTML so it can be highlighted via CSS or a syntax highlighter.
          // block.lang is optional — if provided we include a language- class (e.g. language-javascript).
          const langClass = block.lang ? `language-${block.lang}` : '';
          return (
            <pre key={block.id} className="code-block">
              <code
                className={`code-block__code ${langClass}`}
                // escaped to preserve special characters; CSS should use white-space: pre / pre-wrap
                dangerouslySetInnerHTML={{ __html: escapeHtml(block.content) }}
              />
            </pre>
          );
        }

        if (block.type === 'formatted-text') {
          return (
            <div key={block.id} className="text-block">
              {block.content.map((element) => {
                switch (element.type) {
                  case 'empty':
                    return <div key={element.key} className="empty-line" />;
                  case 'li':
                    // render list item content and convert inline `code` to <code> elements
                    return (
                      <li
                        key={element.key}
                        className="list-item"
                        dangerouslySetInnerHTML={{ __html: formatInlineCode(element.content) }}
                      />
                    );
                  case 'paragraph':
                    // render paragraph content and convert inline `code` to <code> elements
                    return (
                      <p key={element.key} className="paragraph">
                        <span dangerouslySetInnerHTML={{ __html: formatInlineCode(element.content) }} />
                      </p>
                    );
                  default:
                    return null;
                }
              })}
            </div>
          );
        }

        return null;
      })}
    </div>
  );
};

export default FormattedMessage;
