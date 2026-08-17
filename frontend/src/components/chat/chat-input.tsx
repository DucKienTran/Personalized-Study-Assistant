"use client";

import React, { forwardRef, useImperativeHandle, useRef, useState } from "react";
import { Icon, StopIcon } from "@/components/shared/icons";
import { Button } from "@/components/ui/button";

interface ChatInputProps {
  onSend: (message: string) => void;
  onStop?: () => void;

  isStreaming?: boolean;
  disabled?: boolean;

  placeholder?: string;

  className?: string;
  inputClassName?: string;
}

export interface ChatInputHandle {
  clear: () => void;
  focus: () => void;
}

export const ChatInput = forwardRef<ChatInputHandle, ChatInputProps>(function ChatInput({
  onSend,
  onStop,
  isStreaming = false,
  disabled = false,
  placeholder = "Ask a question...",
  className = "",
  inputClassName = "",
}, ref) {
  const [text, setText] = useState("");
  const inputRef = useRef<HTMLInputElement>(null);

  useImperativeHandle(ref, () => ({
    clear: () => setText(""),
    focus: () => inputRef.current?.focus(),
  }), []);

  // Deliberately not a <form onSubmit>. With a form, the Send/Stop button
  // has to toggle its `type` between "submit" and "button" depending on
  // isStreaming — and flipping that attribute mid-click (Stop's onClick
  // sets isStreaming=false synchronously, React re-renders within the
  // same click event, the button becomes type="submit" before the click
  // "finishes") can cause the browser to treat that same click as a form
  // submit, firing handleSubmit with isStreaming already false and
  // sending whatever text is sitting in the input — even if the user
  // never pressed Enter. Keeping both buttons a fixed type="button" and
  // sending explicitly from onClick/onKeyDown removes that race entirely.
  const handleSend = () => {
    const trimmed = text.trim();

    if (!trimmed || disabled || isStreaming) return;

    onSend(trimmed);
    setText("");
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === "Enter") {
      e.preventDefault();
      handleSend();
    }
  };

  return (
    <div
      className={`relative flex items-center bg-card border border-border/80 rounded-[10px] p-1.5 shadow-2xs focus-within:border-primary transition-all ${className}`}
    >
      <input
        ref={inputRef}
        type="text"
        value={text}
        onChange={(e) => setText(e.target.value)}
        onKeyDown={handleKeyDown}
        placeholder={placeholder}
        disabled={disabled}
        className={`w-full bg-transparent border-none text-xs text-foreground placeholder:text-muted-foreground focus:outline-none pl-3 pr-10 h-8 disabled:opacity-50 ${inputClassName}`}
      />

      {isStreaming ? (
        <Button
          type="button"
          size="icon"
          onClick={() => onStop?.()}
          className="cursor-pointer absolute right-1.5 w-7 h-7 rounded-[10px] bg-primary text-primary-foreground hover:bg-[var(--primary-hover)]"
        >
          <StopIcon size={20} />
        </Button>
      ) : (
        <Button
          type="button"
          size="icon"
          onClick={handleSend}
          disabled={!text.trim() || disabled}
          className="absolute right-1.5 w-7 h-7 rounded-[10px] bg-primary text-primary-foreground hover:bg-[var(--primary-hover)] disabled:opacity-40"
        >
          <Icon name="arrow_upward" className="text-sm" />
        </Button>
      )}
    </div>
  );
});
