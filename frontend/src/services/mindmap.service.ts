import api from "./api";
import { Mindmap, MindmapListItem } from "@/types/mindmap";

interface BaseResponse<T> {
  message?: string;
  data: T;
}

class MindmapService {
  async list(notebookId: number): Promise<MindmapListItem[]> {
    const response = await api.get<BaseResponse<MindmapListItem[]>>(
      `/notebooks/${notebookId}/mindmaps`
    );
    return response.data.data;
  }

  async get(notebookId: number, mindmapId: number): Promise<Mindmap> {
    const response = await api.get<BaseResponse<Mindmap>>(
      `/notebooks/${notebookId}/mindmaps/${mindmapId}`
    );
    return response.data.data;
  }

  async create(notebookId: number, title?: string): Promise<Mindmap> {
    const response = await api.post<BaseResponse<Mindmap>>(
      `/notebooks/${notebookId}/mindmaps`,
      { title: title?.trim() || null }
    );
    return response.data.data;
  }

  async delete(notebookId: number, mindmapId: number): Promise<void> {
    await api.delete(`/notebooks/${notebookId}/mindmaps/${mindmapId}`);
  }
}

export const mindmapService = new MindmapService();
