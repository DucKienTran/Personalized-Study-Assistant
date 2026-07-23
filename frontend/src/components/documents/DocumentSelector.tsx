"use client";

import { DocumentListItem } from "@/services/document.service";
import DocumentCard from "./DocumentCard";

interface Props {
    documents: DocumentListItem[];
    selected?: DocumentListItem | null;
    onSelect: (document: DocumentListItem) => void;
}

export default function DocumentSelector({
    documents,
    selected,
    onSelect,
}: Props) {
    return (
        <div className="rounded-2xl border border-gray-100 bg-white p-5 shadow-sm">
            <div className="mb-3">
                <h2 className="text-sm font-semibold text-gray-900">
                    Chọn tài liệu
                </h2>
            </div>

            <div className="max-h-72 space-y-2 overflow-y-auto pr-1">
                {documents.map((document) => (
                    <DocumentCard
                        key={document.id}
                        document={document}
                        selected={selected?.id === document.id}
                        onClick={() => onSelect(document)}
                    />
                ))}
            </div>
        </div>
    );
}