export interface MindmapNode {
  id: string;
  label: string;
  children: MindmapNode[];
}

export interface MindmapListItem {
  id: number;
  notebook_id: number;
  title: string;
  source_document_ids: number[];
  created_at: string;
  updated_at: string;
}

export interface Mindmap extends MindmapListItem {
  content_json: MindmapNode;
}
