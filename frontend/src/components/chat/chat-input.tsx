"use client";

import React, {
  useState,
  useRef,
  KeyboardEvent,
} from "react";
import { Send } from "lucide-react";

interface ChatInputProps {
  onSend: (message: string) => void;
  isLoading?: boolean;
  placeholder?: string;
}

export const ChatInput: React.FC<ChatInputProps> = ({
  onSend,
  isLoading = false,
  placeholder = "Ask something about your documents...",
}) => {
  const [input, setInput] = useState("");

  const textareaRef =
    useRef<HTMLTextAreaElement>(null);

  const handleSubmit = () => {
    const value = input.trim();

    if (!value || isLoading) return;

    onSend(value);

    setInput("");

    if (textareaRef.current) {
      textareaRef.current.style.height = "auto";
    }
  };

  const handleKeyDown = (
    e: KeyboardEvent<HTMLTextAreaElement>
  ) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSubmit();
    }
  };

  const handleChange = (
    e: React.ChangeEvent<HTMLTextAreaElement>
  ) => {
    setInput(e.target.value);

    const textarea = e.target;

    textarea.style.height = "auto";
    textarea.style.height = `${Math.min(
      textarea.scrollHeight,
      180
    )}px`;
  };

  return (
    <div className="w-full">
      <div className="relative flex items-end rounded-2xl border border-gray-200 bg-white shadow-sm transition-all focus-within:border-[#69B989] focus-within:ring-2 focus-within:ring-[#8FCFA9]/30">

        <textarea
          ref={textareaRef}
          rows={1}
          value={input}
          disabled={isLoading}
          placeholder={placeholder}
          onChange={handleChange}
          onKeyDown={handleKeyDown}
          className="max-h-[180px] min-h-[52px] w-full resize-none bg-transparent px-4 py-3 pr-14 text-sm text-gray-800 placeholder:text-gray-400 focus:outline-none"
        />

        <button
          type="button"
          onClick={handleSubmit}
          disabled={!input.trim() || isLoading}
          className="absolute bottom-2 right-2 flex h-9 w-9 items-center justify-center rounded-xl bg-[#69B989] text-white transition-colors hover:bg-[#57ab79] disabled:bg-gray-200 disabled:text-gray-400"
        >
          <Send size={16} />
        </button>
      </div>

      <p className="mt-2 text-center text-[11px] text-gray-400">
        Press <kbd>Enter</kbd> to send ·
        <kbd className="ml-1">Shift + Enter</kbd> for a new line
      </p>
    </div>
  );
};