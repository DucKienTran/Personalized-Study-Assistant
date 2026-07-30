"use client";

import dynamic from "next/dynamic";

const PdfViewerCore = dynamic(
  () =>
    import("./pdf-viewer-core").then(
      (mod) => mod.PdfViewerCore
    ),
  {
    ssr: false,
  }
);

export default PdfViewerCore;