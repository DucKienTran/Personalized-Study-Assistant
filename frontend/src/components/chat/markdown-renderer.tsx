"use client";

import React from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";

interface MarkdownRendererProps {
  content: string;
  isStreaming?: boolean;
  linkCitations?: boolean;
}

function jumpToCitation(
  index: number,
  button: HTMLButtonElement
) {
  // Bubble chat hiện tại
  const bubble = button.closest("[data-chat-bubble]");

  if (!bubble) return;

  const target = bubble.querySelector(
    `#citation-${index}`
  ) as HTMLElement | null;

  if (!target) return;

  target.scrollIntoView({
    behavior: "smooth",
    block: "center",
  });

  target.dispatchEvent(
    new CustomEvent("citation-focus")
  );
}

export const MarkdownRenderer: React.FC<MarkdownRendererProps> = ({
  content,
  isStreaming: _isStreaming = false,
  linkCitations = true,
}) => {
  const parsed = linkCitations
    ? content.replace(/\[(\d+)\]/g, "[[$1]](#citation-$1)")
    : content;

  return (
    <div className="min-w-0 max-w-full break-words text-gray-800 [overflow-wrap:anywhere]">
      <ReactMarkdown
        remarkPlugins={[remarkGfm]}
        components={{
          p: ({ children }) => <p className="mb-4 leading-7 last:mb-0">{children}</p>,
          strong: ({ children }) => <strong className="font-semibold">{children}</strong>,
          em: ({ children }) => <em>{children}</em>,
          h1: ({ children }) => <h1 className="mb-3 mt-6 text-xl font-semibold first:mt-0">{children}</h1>,
          h2: ({ children }) => <h2 className="mb-3 mt-6 text-lg font-semibold first:mt-0">{children}</h2>,
          h3: ({ children }) => <h3 className="mb-2 mt-5 text-base font-semibold first:mt-0">{children}</h3>,
          h4: ({ children }) => <h4 className="mb-2 mt-4 text-sm font-semibold first:mt-0">{children}</h4>,
          ul: ({ children }) => <ul className="mb-4 list-disc space-y-1 pl-6 last:mb-0">{children}</ul>,
          ol: ({ children }) => <ol className="mb-4 list-decimal space-y-1 pl-6 last:mb-0">{children}</ol>,
          li: ({ children }) => <li className="leading-7 [&>p]:mb-1">{children}</li>,
          blockquote: ({ children }) => (
            <blockquote className="mb-4 border-l-2 border-border pl-4 text-muted-foreground last:mb-0">
              {children}
            </blockquote>
          ),
          pre: ({ children }) => (
            <pre className="mb-4 max-w-full overflow-x-auto rounded-lg border border-border bg-muted/50 p-4 last:mb-0">
              {children}
            </pre>
          ),
          code: ({ className, children }) => (
            <code
              className={
                className
                  ? `${className} font-mono text-sm`
                  : "rounded bg-muted px-1.5 py-0.5 font-mono text-sm"
              }
            >
              {children}
            </code>
          ),
          table: ({ children }) => (
            <div className="mb-4 max-w-full overflow-x-auto last:mb-0">
              <table className="w-full min-w-max border-collapse text-left">
                {children}
              </table>
            </div>
          ),
          th: ({ children }) => <th className="border border-border bg-muted/50 px-3 py-2 font-semibold">{children}</th>,
          td: ({ children }) => <td className="border border-border px-3 py-2 align-top">{children}</td>,
          a({ href, children }) {

            const match = href?.match(/^#citation-(\d+)$/);

            if (!match) {
              return <a href={href} className="text-primary underline underline-offset-2">{children}</a>;
            }

            const index = Number(match[1]);

            return (
              <button
                type="button"
                onClick={(e) =>
                  jumpToCitation(
                    index,
                    e.currentTarget
                  )
                }
                className="rounded-sm px-1 font-semibold text-[#2E8B57] hover:bg-[#DCFCE7]"
              >
                [{index}]
              </button>
            );
          },
        }}
      >
        {parsed}
      </ReactMarkdown>
    </div>
  );
};
