"use client";

import React, { useEffect, useState } from "react";
import { FileText } from "lucide-react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";

import { CitationSource } from "@/types/chat";
import { formatPageRange } from "@/utils/format-citation";

interface CitationCardProps {
  source: CitationSource;
  onClick?: (source: CitationSource) => void;
}

export const CitationCard: React.FC<CitationCardProps> = ({
  source,
  onClick,
}) => {
  const pageText = formatPageRange(
    source.pageStart,
    source.pageEnd
  );

  const [active, setActive] = useState(false);

  useEffect(() => {
    const element = document.getElementById(
      `citation-${source.index}`
    );

    if (!element) return;

    const handler = () => {
      setActive(true);

      setTimeout(() => {
        setActive(false);
      }, 2500);
    };

    element.addEventListener(
      "citation-focus",
      handler as EventListener
    );

    return () => {
      element.removeEventListener(
        "citation-focus",
        handler as EventListener
      );
    };
  }, [source.index]);

  return (
    <div
      id={`citation-${source.index}`}
      className="relative group"
    >
      <button
        type="button"
        onClick={() => onClick?.(source)}
        className={`
          flex items-center gap-2
          rounded-xl
          border
          px-3
          py-2
          text-xs
          transition-all
          duration-200

          ${
            active
              ? "border-[#69B989] bg-[#ECF9F1] shadow-md"
              : "border-gray-300 bg-white hover:border-[#69B989] hover:bg-[#F7FCF9]"
          }
        `}
      >
        <FileText
          size={14}
          className="shrink-0 text-[#69B989]"
        />

        <span className="font-semibold text-[#2E8B57]">
          [{source.index}]
        </span>

        <span className="max-w-[170px] truncate">
          {source.documentTitle}
        </span>

        {pageText && (
          <>
            <span className="text-gray-300">•</span>

            <span className="whitespace-nowrap text-gray-500">
              {pageText}
            </span>
          </>
        )}
      </button>

      {/* Tooltip */}
      <div
        className={`
          absolute
          left-0
          bottom-full
          mb-3
          z-30
          w-[360px]

          rounded-2xl
          border
          border-gray-300
          bg-white
          p-4

          shadow-2xl

          opacity-0
          invisible
          translate-y-1

          transition-all
          duration-200

          ${
            active
              ? "visible translate-y-0 opacity-100"
              : "group-hover:visible group-hover:translate-y-0 group-hover:opacity-100"
          }
        `}
      >
                {source.headerPath.length > 0 && (
          <div className="space-y-2">
            {source.headerPath.map((item, index) => (
              <div
                key={index}
                className="flex items-start gap-2"
                style={{
                  paddingLeft: `${index * 14}px`,
                }}
              >
                {index > 0 && (
                  <span className="mt-[5px] h-1.5 w-1.5 shrink-0 rounded-full bg-[#69B989]" />
                )}

                <span className="text-xs leading-5 text-gray-700">
                  {item
                    .replace(/\*\*/g, "")
                    .replace(/_/g, "")}
                </span>
              </div>
            ))}
          </div>
        )}

        {source.snippet && (
          <>
            <div className="my-4 border-t border-gray-200" />

            {/* Snippet */}
            <div className="rounded-xl border border-gray-200 bg-gray-50 p-3">
              <div className="prose prose-xs max-w-none line-clamp-3 text-gray-700">
                <ReactMarkdown
                  remarkPlugins={[remarkGfm]}
                >
                  {source.snippet}
                </ReactMarkdown>
              </div>
            </div>
          </>
        )}

        <div className="mt-4 border-t border-gray-200 pt-3 text-[11px] text-gray-500">
          {source.documentTitle}

          {pageText && (
            <>
              {" "}
              • <span>{pageText}</span>
            </>
          )}
        </div>
      </div>
    </div>
  );
};