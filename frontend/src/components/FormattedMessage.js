import React from 'react';
import '../styles/FormattedMessage.css';

const FormattedMessage = ({ blocks }) => {
  return (
    <div className="formatted-message">
      {blocks.map((block) => {
        if (block.type === 'code') {
          return (
            <pre key={block.id} className="code-block">
              <code>{block.content}</code>
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
                    return (
                      <li key={element.key} className="list-item">
                        {element.content}
                      </li>
                    );
                  case 'paragraph':
                    return (
                      <p key={element.key} className="paragraph">
                        <span dangerouslySetInnerHTML={{ __html: element.content }} />
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
