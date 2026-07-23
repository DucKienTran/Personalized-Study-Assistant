"use client";

import { useEffect, useRef, useState } from "react";

interface Props {
    value: number;
    min?: number;
    max?: number;
    onChange: (value: number) => void;
}

export default function QuestionCounter({
    value,
    min = 1,
    max = 100,
    onChange,
}: Props) {
    const [editing, setEditing] = useState(false);
    const [draft, setDraft] = useState(String(value));

    const inputRef = useRef<HTMLInputElement>(null);

    useEffect(() => {
        setDraft(String(value));
    }, [value]);

    useEffect(() => {
        if (editing) {
            inputRef.current?.focus();
            inputRef.current?.select();
        }
    }, [editing]);

    function commit() {
        let next = Number(draft);

        if (Number.isNaN(next)) {
            next = value;
        }

        next = Math.max(min, Math.min(max, next));

        onChange(next);
        setEditing(false);
    }

    return (
        <div className="inline-flex items-center rounded-xl border border-gray-200 overflow-hidden bg-white">

            <button
                type="button"
                className="w-10 h-10 hover:bg-gray-100 transition"
                onClick={() => onChange(Math.max(min, value - 1))}
            >
                −
            </button>

            <div className="w-16 flex justify-center">

                {editing ? (
                    <input
                        ref={inputRef}
                        value={draft}
                        onChange={(e) => setDraft(e.target.value)}
                        onBlur={commit}
                        onKeyDown={(e) => {
                            if (e.key === "Enter") commit();

                            if (e.key === "Escape") {
                                setDraft(String(value));
                                setEditing(false);
                            }
                        }}
                        className="w-full text-center outline-none"
                    />
                ) : (
                    <button
                        type="button"
                        onClick={() => setEditing(true)}
                        className="w-full h-10 hover:bg-gray-50 text-sm font-semibold"
                    >
                        {value}
                    </button>
                )}

            </div>

            <button
                type="button"
                className="w-10 h-10 hover:bg-gray-100 transition"
                onClick={() => onChange(Math.min(max, value + 1))}
            >
                +
            </button>

        </div>
    );
}