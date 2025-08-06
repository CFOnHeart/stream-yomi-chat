import React from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import rehypeHighlight from 'rehype-highlight';
import 'highlight.js/styles/github.css'; // 代码高亮样式
import './MarkdownRenderer.css';

const MarkdownRenderer = ({ content, className = '' }) => {
  return (
    <div className={`markdown-renderer ${className}`}>
      <ReactMarkdown
        remarkPlugins={[remarkGfm]}
        rehypePlugins={[rehypeHighlight]}
        components={{
          // 自定义代码块渲染
          code({ node, inline, className, children, ...props }) {
            const match = /language-(\w+)/.exec(className || '');
            return !inline && match ? (
              <pre className={`hljs ${className}`} {...props}>
                <code>{children}</code>
              </pre>
            ) : (
              <code className="inline-code" {...props}>
                {children}
              </code>
            );
          },
          // 自定义链接渲染
          a({ children, href, ...props }) {
            return (
              <a 
                href={href} 
                target="_blank" 
                rel="noopener noreferrer" 
                className="markdown-link"
                {...props}
              >
                {children}
              </a>
            );
          },
          // 自定义表格渲染
          table({ children, ...props }) {
            return (
              <div className="table-container">
                <table className="markdown-table" {...props}>
                  {children}
                </table>
              </div>
            );
          },
          // 自定义列表渲染
          ul({ children, ...props }) {
            return <ul className="markdown-list" {...props}>{children}</ul>;
          },
          ol({ children, ...props }) {
            return <ol className="markdown-list markdown-list-ordered" {...props}>{children}</ol>;
          },
          // 自定义标题渲染
          h1({ children, ...props }) {
            return <h1 className="markdown-h1" {...props}>{children}</h1>;
          },
          h2({ children, ...props }) {
            return <h2 className="markdown-h2" {...props}>{children}</h2>;
          },
          h3({ children, ...props }) {
            return <h3 className="markdown-h3" {...props}>{children}</h3>;
          },
          h4({ children, ...props }) {
            return <h4 className="markdown-h4" {...props}>{children}</h4>;
          },
          h5({ children, ...props }) {
            return <h5 className="markdown-h5" {...props}>{children}</h5>;
          },
          h6({ children, ...props }) {
            return <h6 className="markdown-h6" {...props}>{children}</h6>;
          },
          // 自定义引用块渲染
          blockquote({ children, ...props }) {
            return <blockquote className="markdown-blockquote" {...props}>{children}</blockquote>;
          },
          // 自定义段落渲染
          p({ children, ...props }) {
            return <p className="markdown-paragraph" {...props}>{children}</p>;
          }
        }}
      >
        {content}
      </ReactMarkdown>
    </div>
  );
};

export default MarkdownRenderer;
