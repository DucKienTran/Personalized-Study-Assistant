"use client";

import React from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";

interface MarkdownRendererProps {
  content: string;
  isStreaming?: boolean;
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
  isStreaming = false,
}) => {

  // Stream thì render plain text
  if (isStreaming) {
    return (
      <div className="whitespace-pre-wrap leading-7 text-gray-800">
        {content}
      </div>
    );
  }

  const parsed = content.replace(
    /\[(\d+)\]/g,
    "[[$1]](#citation-$1)"
  );

  return (
    <div className="prose prose-sm max-w-none text-gray-800">
      <ReactMarkdown
        remarkPlugins={[remarkGfm]}
        components={{
          a({ href, children }) {

            const match = href?.match(/^#citation-(\d+)$/);

            if (!match) {
              return <a href={href}>{children}</a>;
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
                className="rounded px-1 font-semibold text-[#2E8B57] hover:bg-[#DCFCE7]"
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