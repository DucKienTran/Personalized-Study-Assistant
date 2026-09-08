interface AssistantThinkingTextProps {
  children: string;
}

export function AssistantThinkingText({ children }: AssistantThinkingTextProps) {
  return (
    <span>
      {children.split("").map((char, index) => (
        <span
          key={index}
          className="thinking-char"
          style={{ animationDelay: `${index * 80}ms` }}
        >
          {char === " " ? "\u00A0" : char}
        </span>
      ))}
    </span>
  );
}
