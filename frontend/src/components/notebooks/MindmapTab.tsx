"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { Icon } from "@/components/shared/icons";
import { Button } from "@/components/ui/button";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { mindmapService } from "@/services/mindmap.service";
import { Mindmap, MindmapListItem, MindmapNode } from "@/types/mindmap";

interface MindmapTabProps {
  notebookId: number;
  eligibleDocumentCount: number;
  selectedMindmapId?: number | null;
}

interface FlatNode {
  node: MindmapNode;
  depth: number;
  parentId?: string;
  width: number;
  height: number;
}

interface PositionedNode extends FlatNode {
  x: number;
  y: number;
  visible: boolean;
}

interface VisiblePosition {
  x: number;
  y: number;
}

const NODE_HEIGHT = 44;
const ROOT_HEIGHT = 48;
const HORIZONTAL_GAP = 150;
const CONNECTOR_HANDLE_GAP = 18;
const TOGGLE_SIZE = 22;
const VERTICAL_STEP = 68;
const MIN_NODE_WIDTH = 96;
const MAX_NODE_WIDTH = 280;
const MIN_SCALE = 0.22;
const MAX_SCALE = 2.4;
const VIEW_PADDING = 72;
const LAYOUT_TRANSITION_MS = 1200;
const CAMERA_TRANSITION_MS = 1050;
const OPACITY_TRANSITION_MS = 950;

// Root is intentionally strongest. Each following depth has its own softer color.
// MAX_DEPTH on the backend is 8, so depth indexes here are 0..7.
const DEPTH_PALETTE = [
  { fill: "#667D6B", stroke: "#526757", text: "#FFFFFF" },
  { fill: "#B7D2EF", stroke: "#94B7DD", text: "#19324A" },
  { fill: "#A7DED5", stroke: "#82C9BD", text: "#173A35" },
  { fill: "#C9E2B6", stroke: "#A9CF8E", text: "#29401E" },
  { fill: "#F2DBA8", stroke: "#DFC17C", text: "#4A3712" },
  { fill: "#EDC0B8", stroke: "#DCA399", text: "#4D2721" },
  { fill: "#DCC8EA", stroke: "#C7AADD", text: "#382545" },
  { fill: "#E5E2D2", stroke: "#CFCCB8", text: "#39382D" },
] as const;

function estimateNodeWidth(label: string, depth: number): number {
  const averageGlyphWidth = depth === 0 ? 7.8 : 7.1;
  const horizontalChrome = 42;
  return Math.max(
    MIN_NODE_WIDTH,
    Math.min(MAX_NODE_WIDTH, Math.ceil(label.length * averageGlyphWidth + horizontalChrome)),
  );
}

function flattenTree(root: MindmapNode): FlatNode[] {
  const rows: FlatNode[] = [];

  const walk = (node: MindmapNode, depth: number, parentId?: string) => {
    rows.push({
      node,
      depth,
      parentId,
      width: estimateNodeWidth(node.label, depth),
      height: depth === 0 ? ROOT_HEIGHT : NODE_HEIGHT,
    });
    for (const child of node.children ?? []) {
      walk(child, depth + 1, node.id);
    }
  };

  walk(root, 0);
  return rows;
}

function buildLayout(root: MindmapNode, collapsed: Set<string>): PositionedNode[] {
  const flat = flattenTree(root);
  const flatById = new Map(flat.map((item) => [item.node.id, item]));

  // Every depth shares one left edge. The next depth starts after the widest node
  // of the previous depth plus a generous connector gap.
  const maxWidthByDepth = new Map<number, number>();
  for (const item of flat) {
    maxWidthByDepth.set(
      item.depth,
      Math.max(maxWidthByDepth.get(item.depth) ?? 0, item.width),
    );
  }

  const xByDepth = new Map<number, number>();
  xByDepth.set(0, 0);
  const maxDepth = Math.max(...flat.map((item) => item.depth), 0);
  for (let depth = 1; depth <= maxDepth; depth += 1) {
    const previousX = xByDepth.get(depth - 1) ?? 0;
    const previousWidth = maxWidthByDepth.get(depth - 1) ?? MIN_NODE_WIDTH;
    xByDepth.set(depth, previousX + previousWidth + HORIZONTAL_GAP);
  }

  const visiblePositions = new Map<string, VisiblePosition>();
  let leafIndex = 0;

  const walkVisible = (node: MindmapNode, depth: number): number => {
    const visibleChildren = collapsed.has(node.id) ? [] : node.children ?? [];
    let centerY: number;

    if (!visibleChildren.length) {
      centerY = leafIndex * VERTICAL_STEP;
      leafIndex += 1;
    } else {
      const childCenters = visibleChildren.map((child) => walkVisible(child, depth + 1));
      centerY = (childCenters[0] + childCenters[childCenters.length - 1]) / 2;
    }

    const item = flatById.get(node.id);
    const height = item?.height ?? NODE_HEIGHT;
    visiblePositions.set(node.id, {
      x: xByDepth.get(depth) ?? 0,
      y: centerY - height / 2,
    });
    return centerY;
  };

  walkVisible(root, 0);

  // Hidden descendants stay mounted at their nearest visible ancestor. This lets
  // CSS animate them out of / into the parent instead of popping in and out.
  const resolveHiddenPosition = (item: FlatNode): VisiblePosition => {
    let current = item;
    while (current.parentId) {
      const parent = flatById.get(current.parentId);
      if (!parent) break;
      const visibleParentPosition = visiblePositions.get(parent.node.id);
      if (visibleParentPosition) {
        return {
          // Hidden descendants collapse into the parent connector handle so both
          // the node and its edge animate from/to the same visual origin.
          x:
            visibleParentPosition.x +
            parent.width +
            CONNECTOR_HANDLE_GAP +
            TOGGLE_SIZE / 2,
          y: visibleParentPosition.y + (parent.height - item.height) / 2,
        };
      }
      current = parent;
    }
    return { x: 0, y: 0 };
  };

  return flat.map((item) => {
    const visiblePosition = visiblePositions.get(item.node.id);
    const position = visiblePosition ?? resolveHiddenPosition(item);
    return {
      ...item,
      ...position,
      visible: Boolean(visiblePosition),
    };
  });
}

function collectCollapsibleIds(root: MindmapNode): Set<string> {
  const ids = new Set<string>();
  const walk = (node: MindmapNode, depth: number) => {
    if (depth >= 1 && (node.children?.length ?? 0) > 0) ids.add(node.id);
    for (const child of node.children ?? []) walk(child, depth + 1);
  };
  walk(root, 0);
  return ids;
}

export function MindmapTab({
  notebookId,
  eligibleDocumentCount,
  selectedMindmapId,
}: MindmapTabProps) {
  const [items, setItems] = useState<MindmapListItem[]>([]);
  const [selected, setSelected] = useState<Mindmap | null>(null);
  const [title, setTitle] = useState("");
  const [loading, setLoading] = useState(true);
  const [generating, setGenerating] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [collapsed, setCollapsed] = useState<Set<string>>(new Set());
  const [scale, setScale] = useState(1);
  const [offset, setOffset] = useState({ x: 60, y: 60 });
  const dragRef = useRef<{
    pointerId: number;
    x: number;
    y: number;
    ox: number;
    oy: number;
  } | null>(null);
  const pointersRef = useRef(new Map<number, { x: number; y: number }>());
  const pinchRef = useRef<{
    distance: number;
    startScale: number;
    worldX: number;
    worldY: number;
  } | null>(null);
  const selectionRequestRef = useRef(0);
  const viewportRef = useRef<HTMLDivElement>(null);
  const pendingViewActionRef = useRef<
    { type: "fit" } | { type: "focus"; nodeId: string } | null
  >(null);

  const loadList = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const list = await mindmapService.list(notebookId);
      setItems(list);
      if (list.length) {
        const targetId = selectedMindmapId ?? list[0].id;
        const detail = await mindmapService.get(notebookId, targetId);
        setSelected(detail);
      } else {
        setSelected(null);
      }
    } catch (err) {
      console.error(err);
      setError("Could not load mindmaps.");
    } finally {
      setLoading(false);
    }
  }, [notebookId, selectedMindmapId]);

  useEffect(() => {
    void loadList();
  }, [loadList]);

  const nodes = useMemo(
    () => (selected ? buildLayout(selected.content_json, collapsed) : []),
    [selected, collapsed],
  );
  const visibleNodes = useMemo(() => nodes.filter((item) => item.visible), [nodes]);
  const byId = useMemo(
    () => new Map(nodes.map((item) => [item.node.id, item])),
    [nodes],
  );
  const allExpanded = collapsed.size === 0;

  const fitView = useCallback(() => {
    const viewport = viewportRef.current;
    if (!viewport || !visibleNodes.length) return;

    const minX = Math.min(...visibleNodes.map((node) => node.x));
    const maxX = Math.max(...visibleNodes.map((node) => node.x + node.width));
    const minY = Math.min(...visibleNodes.map((node) => node.y));
    const maxY = Math.max(...visibleNodes.map((node) => node.y + node.height));
    const width = Math.max(1, maxX - minX);
    const height = Math.max(1, maxY - minY);
    const usableWidth = Math.max(120, viewport.clientWidth - VIEW_PADDING * 2);
    const usableHeight = Math.max(120, viewport.clientHeight - VIEW_PADDING * 2);
    const nextScale = Math.min(
      1.3,
      Math.max(MIN_SCALE, Math.min(usableWidth / width, usableHeight / height)),
    );

    setScale(nextScale);
    setOffset({
      x: (viewport.clientWidth - width * nextScale) / 2 - minX * nextScale,
      y: (viewport.clientHeight - height * nextScale) / 2 - minY * nextScale,
    });
  }, [visibleNodes]);

  const focusNode = useCallback(
    (nodeId: string) => {
      const viewport = viewportRef.current;
      const node = byId.get(nodeId);
      if (!viewport || !node || !node.visible) return;

      // Focus adaptively on the branch that just changed. The camera uses the
      // post-layout geometry, so variable node widths / connector lengths do not
      // require any fixed screen target such as "38% of the viewport".
      const isDescendantOf = (candidate: PositionedNode, ancestorId: string) => {
        let parentId = candidate.parentId;
        while (parentId) {
          if (parentId === ancestorId) return true;
          parentId = byId.get(parentId)?.parentId;
        }
        return false;
      };

      const branchNodes = visibleNodes.filter(
        (candidate) =>
          candidate.node.id === nodeId || isDescendantOf(candidate, nodeId),
      );
      const focusNodes = branchNodes.length ? branchNodes : [node];

      const minX = Math.min(...focusNodes.map((item) => item.x));
      const maxX = Math.max(...focusNodes.map((item) => item.x + item.width));
      const minY = Math.min(...focusNodes.map((item) => item.y));
      const maxY = Math.max(...focusNodes.map((item) => item.y + item.height));
      const branchWidth = Math.max(1, maxX - minX);
      const branchHeight = Math.max(1, maxY - minY);

      // Keep comfortable asymmetric padding: a little room before the parent and
      // more room to the right for descendants. Zoom out only when the changed
      // branch cannot fit at the current scale; otherwise preserve the user's zoom.
      const leftPadding = Math.max(48, viewport.clientWidth * 0.12);
      const rightPadding = Math.max(64, viewport.clientWidth * 0.12);
      const verticalPadding = Math.max(48, viewport.clientHeight * 0.14);
      const usableWidth = Math.max(120, viewport.clientWidth - leftPadding - rightPadding);
      const usableHeight = Math.max(120, viewport.clientHeight - verticalPadding * 2);
      const fitScale = Math.min(
        usableWidth / branchWidth,
        usableHeight / branchHeight,
      );
      const nextScale = Math.min(
        scale,
        MAX_SCALE,
        Math.max(MIN_SCALE, fitScale),
      );

      const scaledMinX = minX * nextScale;
      const scaledMaxX = maxX * nextScale;
      const scaledMinY = minY * nextScale;
      const scaledMaxY = maxY * nextScale;

      // Start from the current camera and apply the smallest pan that puts the
      // whole changed branch inside the safe viewport rectangle. This means a
      // small expansion causes only a small camera movement.
      let nextX = offset.x;
      let nextY = offset.y;
      const screenMinX = scaledMinX + nextX;
      const screenMaxX = scaledMaxX + nextX;
      const screenMinY = scaledMinY + nextY;
      const screenMaxY = scaledMaxY + nextY;
      const safeRight = viewport.clientWidth - rightPadding;
      const safeBottom = viewport.clientHeight - verticalPadding;

      if (screenMinX < leftPadding) nextX += leftPadding - screenMinX;
      if (screenMaxX > safeRight) nextX -= screenMaxX - safeRight;
      if (screenMinY < verticalPadding) nextY += verticalPadding - screenMinY;
      if (screenMaxY > safeBottom) nextY -= screenMaxY - safeBottom;

      // If zooming out was necessary, center the branch inside the safe area so
      // the newly revealed descendants remain readable instead of hugging an edge.
      if (nextScale < scale - 0.001) {
        const safeCenterX = leftPadding + usableWidth / 2;
        const safeCenterY = verticalPadding + usableHeight / 2;
        nextX = safeCenterX - ((minX + maxX) / 2) * nextScale;
        nextY = safeCenterY - ((minY + maxY) / 2) * nextScale;
      }

      setScale(nextScale);
      setOffset({ x: nextX, y: nextY });
    },
    [byId, offset.x, offset.y, scale, visibleNodes],
  );

  useEffect(() => {
    if (!selected || !visibleNodes.length) return;

    const action = pendingViewActionRef.current;
    if (action) {
      pendingViewActionRef.current = null;
      const frame = requestAnimationFrame(() => {
        if (action.type === "fit") fitView();
        else focusNode(action.nodeId);
      });
      return () => cancelAnimationFrame(frame);
    }

    // New / newly selected mindmaps start fitted once. Branch changes use the
    // explicit pending actions above instead of continuously fighting user pan.
    const frame = requestAnimationFrame(fitView);
    return () => cancelAnimationFrame(frame);
    // selected.id intentionally scopes the automatic initial fit to selection changes.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [selected?.id]);

  useEffect(() => {
    const action = pendingViewActionRef.current;
    if (!action || !visibleNodes.length) return;
    pendingViewActionRef.current = null;
    const frame = requestAnimationFrame(() => {
      if (action.type === "fit") fitView();
      else focusNode(action.nodeId);
    });
    return () => cancelAnimationFrame(frame);
  }, [collapsed, fitView, focusNode, visibleNodes.length]);

  const zoomAroundPoint = useCallback(
    (nextScale: number, screenX: number, screenY: number) => {
      const clampedScale = Math.min(MAX_SCALE, Math.max(MIN_SCALE, nextScale));
      if (clampedScale === scale) return;
      const worldX = (screenX - offset.x) / scale;
      const worldY = (screenY - offset.y) / scale;
      setScale(clampedScale);
      setOffset({
        x: screenX - worldX * clampedScale,
        y: screenY - worldY * clampedScale,
      });
    },
    [offset.x, offset.y, scale],
  );

  const zoomFromButton = (factor: number) => {
    const viewport = viewportRef.current;
    if (!viewport) return;
    zoomAroundPoint(
      scale * factor,
      viewport.clientWidth / 2,
      viewport.clientHeight / 2,
    );
  };

  useEffect(() => {
    const viewport = viewportRef.current;
    if (!viewport) return;

    // Native non-passive listener is intentional. Trackpad pinch gestures often
    // arrive as ctrl+wheel; preventing the browser default here keeps zoom scoped
    // to the mindmap viewport instead of zooming the whole application.
    const handleWheel = (event: WheelEvent) => {
      event.preventDefault();
      event.stopPropagation();

      const rect = viewport.getBoundingClientRect();
      const pointerX = event.clientX - rect.left;
      const pointerY = event.clientY - rect.top;
      const factor = event.ctrlKey
        ? Math.max(0.78, Math.min(1.28, Math.exp(-event.deltaY * 0.012)))
        : event.deltaY > 0
          ? 0.9
          : 1.1;

      zoomAroundPoint(scale * factor, pointerX, pointerY);
    };

    const preventGesture = (event: Event) => {
      event.preventDefault();
      event.stopPropagation();
    };

    viewport.addEventListener("wheel", handleWheel, { passive: false });
    // Safari exposes trackpad/mobile pinch through gesture events in addition to
    // pointer/wheel events. These listeners are local to the mindmap only.
    viewport.addEventListener("gesturestart", preventGesture, { passive: false } as AddEventListenerOptions);
    viewport.addEventListener("gesturechange", preventGesture, { passive: false } as AddEventListenerOptions);

    return () => {
      viewport.removeEventListener("wheel", handleWheel);
      viewport.removeEventListener("gesturestart", preventGesture);
      viewport.removeEventListener("gesturechange", preventGesture);
    };
  }, [scale, zoomAroundPoint]);


  const createMindmap = async () => {
    if (!eligibleDocumentCount || generating) return;
    setGenerating(true);
    setError(null);
    try {
      const created = await mindmapService.create(notebookId, title);
      setItems((current) => [
        created,
        ...current.filter((item) => item.id !== created.id),
      ]);
      setSelected(created);
      setTitle("");
      setCollapsed(new Set());
    } catch (err: any) {
      console.error(err);
      setError(err?.response?.data?.detail ?? "Could not generate mindmap.");
    } finally {
      setGenerating(false);
    }
  };

  const selectMindmap = async (id: number) => {
    const requestId = ++selectionRequestRef.current;
    setError(null);
    try {
      const detail = await mindmapService.get(notebookId, id);
      if (requestId !== selectionRequestRef.current) return;
      setSelected(detail);
      setCollapsed(new Set());
    } catch (err) {
      console.error(err);
      setError("Could not open mindmap.");
    }
  };

  const deleteSelected = async () => {
    if (!selected || !confirm(`Delete “${selected.title}”?`)) return;
    setError(null);
    try {
      await mindmapService.delete(notebookId, selected.id);
      await loadList();
    } catch (err) {
      console.error(err);
      setError("Could not delete mindmap.");
    }
  };

  const toggleNode = (id: string) => {
    pendingViewActionRef.current = { type: "focus", nodeId: id };
    setCollapsed((current) => {
      const next = new Set(current);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  };

  const toggleAll = () => {
    if (!selected) return;
    pendingViewActionRef.current = { type: "fit" };
    if (allExpanded) {
      // Keep root + first level visible. Collapsing every non-root branch node
      // hides depth >= 2 while preserving the top-level overview.
      setCollapsed(collectCollapsibleIds(selected.content_json));
    } else {
      setCollapsed(new Set());
    }
  };

  if (loading) {
    return (
      <div className="flex h-full flex-1 items-center justify-center text-xs text-muted-foreground">
        <Icon name="progress_activity" className="mr-2 animate-spin" />
        Loading mindmaps...
      </div>
    );
  }

  return (
    <div className="flex min-h-0 flex-1 flex-col bg-background">
      <div className="flex flex-wrap items-center gap-2 border-b border-border/60 px-4 py-3">
        <input
          value={title}
          onChange={(event) => setTitle(event.target.value)}
          placeholder="Mindmap title (optional)"
          className="h-9 min-w-[220px] flex-1 rounded-lg border border-border bg-background px-3 text-xs outline-none focus:border-primary/50"
          maxLength={255}
        />
        <DropdownMenu>
          <DropdownMenuTrigger
            disabled={!items.length}
            aria-label="Mindmap history"
            title="Mindmap history"
            className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg border border-border bg-background text-muted-foreground outline-none transition-colors hover:bg-secondary hover:text-foreground disabled:cursor-not-allowed disabled:opacity-40"
          >
            <Icon name="history" size={18} />
          </DropdownMenuTrigger>
          <DropdownMenuContent
            align="end"
            className="w-72 rounded-xl border border-border p-1.5 shadow-lg"
          >
            <div className="px-2 py-1.5">
              <p className="text-xs font-semibold text-foreground">Mindmap history</p>
              <p className="text-[10px] text-muted-foreground">Open a previously generated mindmap</p>
            </div>
            <div className="max-h-72 overflow-y-auto">
              {items.map((item) => (
                <DropdownMenuItem
                  key={item.id}
                  onClick={() => void selectMindmap(item.id)}
                  className={`cursor-pointer rounded-lg px-2 py-2 ${
                    selected?.id === item.id ? "bg-secondary" : ""
                  }`}
                >
                  <div className="min-w-0 flex-1">
                    <div className="truncate text-xs font-medium text-foreground">
                      {item.title}
                    </div>
                    <div className="mt-0.5 flex items-center gap-2 text-[10px] text-muted-foreground">
                      <span>{item.source_document_ids.length} sources</span>
                      <span>•</span>
                      <span>{new Date(item.created_at).toLocaleDateString()}</span>
                    </div>
                  </div>
                  {selected?.id === item.id && (
                    <Icon name="check" size={15} className="ml-2 shrink-0 text-primary" />
                  )}
                </DropdownMenuItem>
              ))}
            </div>
          </DropdownMenuContent>
        </DropdownMenu>

        <Button
          onClick={createMindmap}
          disabled={!eligibleDocumentCount || generating}
          className="h-9 rounded-lg text-xs"
        >
          <Icon
            name={generating ? "progress_activity" : "account_tree"}
            className={generating ? "mr-2 animate-spin" : "mr-2"}
          />
          {generating ? "Generating..." : "Create mindmap"}
        </Button>
      </div>

      {error && (
        <div className="border-b border-destructive/20 bg-destructive/5 px-4 py-2 text-xs text-destructive">
          {error}
        </div>
      )}

      <div className="flex min-h-0 flex-1">
        {!selected ? (
          <div className="flex flex-1 flex-col items-center justify-center p-8 text-center">
            <Icon
              name="account_tree"
              className="mb-3 text-4xl text-muted-foreground/60"
            />
            <h3 className="font-heading text-base font-semibold">
              Create your first mindmap
            </h3>
            <p className="mt-1 max-w-md text-xs text-muted-foreground">
              The mindmap is generated once from the notebook&apos;s currently active
              sources and then stored as a fixed snapshot.
            </p>
          </div>
        ) : (
          <div className="relative min-w-0 flex-1 overflow-hidden">
            <div className="absolute left-3 top-3 z-10 flex items-center gap-1 rounded-xl border border-border bg-background/95 p-1 shadow-sm backdrop-blur-sm">
              <button
                aria-label="Zoom in"
                title="Zoom in"
                className="flex h-8 w-8 items-center justify-center rounded-lg hover:bg-secondary"
                onClick={() => zoomFromButton(1.15)}
              >
                <Icon name="add" />
              </button>
              <button
                aria-label="Zoom out"
                title="Zoom out"
                className="flex h-8 w-8 items-center justify-center rounded-lg hover:bg-secondary"
                onClick={() => zoomFromButton(1 / 1.15)}
              >
                <Icon name="remove" />
              </button>
              <div className="mx-0.5 h-5 w-px bg-border/70" />
              <button
                aria-label={allExpanded ? "Collapse all branches" : "Expand all branches"}
                title={allExpanded ? "Collapse all" : "Expand all"}
                className="flex h-8 w-8 items-center justify-center rounded-lg hover:bg-secondary"
                onClick={toggleAll}
              >
                <Icon name={allExpanded ? "unfold_less" : "unfold_more"} size={19} />
              </button>
            </div>

            <button
              onClick={() => void deleteSelected()}
              className="absolute right-3 top-3 z-10 flex h-9 items-center gap-1 rounded-lg border border-border bg-background/95 px-3 text-xs text-destructive shadow-sm hover:bg-destructive/5"
            >
              <Icon name="delete" size={15} />
              Delete
            </button>

            <div
              ref={viewportRef}
              className="h-full w-full cursor-grab overflow-hidden select-none active:cursor-grabbing"
              style={{ touchAction: "none", overscrollBehavior: "contain" }}
              onPointerDown={(event) => {
                if (event.pointerType === "mouse" && event.button !== 0) return;
                if ((event.target as HTMLElement).closest("button")) return;

                event.preventDefault();
                event.stopPropagation();
                event.currentTarget.setPointerCapture(event.pointerId);
                pointersRef.current.set(event.pointerId, {
                  x: event.clientX,
                  y: event.clientY,
                });

                const points: Array<{ x: number; y: number }> = Array.from(pointersRef.current.values());
                if (points.length >= 2) {
                  const [a, b] = points;
                  const distance = Math.hypot(b.x - a.x, b.y - a.y);
                  const rect = event.currentTarget.getBoundingClientRect();
                  const centerX = (a.x + b.x) / 2 - rect.left;
                  const centerY = (a.y + b.y) / 2 - rect.top;
                  pinchRef.current = {
                    distance: Math.max(1, distance),
                    startScale: scale,
                    worldX: (centerX - offset.x) / scale,
                    worldY: (centerY - offset.y) / scale,
                  };
                  dragRef.current = null;
                  return;
                }

                dragRef.current = {
                  pointerId: event.pointerId,
                  x: event.clientX,
                  y: event.clientY,
                  ox: offset.x,
                  oy: offset.y,
                };
              }}
              onPointerMove={(event) => {
                if (!pointersRef.current.has(event.pointerId)) return;
                event.preventDefault();
                event.stopPropagation();
                pointersRef.current.set(event.pointerId, {
                  x: event.clientX,
                  y: event.clientY,
                });

                const points: Array<{ x: number; y: number }> = Array.from(pointersRef.current.values());
                const pinch = pinchRef.current;
                if (points.length >= 2 && pinch) {
                  const [a, b] = points;
                  const distance = Math.max(1, Math.hypot(b.x - a.x, b.y - a.y));
                  const rect = event.currentTarget.getBoundingClientRect();
                  const centerX = (a.x + b.x) / 2 - rect.left;
                  const centerY = (a.y + b.y) / 2 - rect.top;
                  const nextScale = Math.min(
                    MAX_SCALE,
                    Math.max(MIN_SCALE, pinch.startScale * (distance / pinch.distance)),
                  );
                  setScale(nextScale);
                  setOffset({
                    x: centerX - pinch.worldX * nextScale,
                    y: centerY - pinch.worldY * nextScale,
                  });
                  return;
                }

                const drag = dragRef.current;
                if (!drag || drag.pointerId !== event.pointerId) return;
                setOffset({
                  x: drag.ox + event.clientX - drag.x,
                  y: drag.oy + event.clientY - drag.y,
                });
              }}
              onPointerUp={(event) => {
                pointersRef.current.delete(event.pointerId);
                if (dragRef.current?.pointerId === event.pointerId) dragRef.current = null;
                if (pointersRef.current.size < 2) pinchRef.current = null;
              }}
              onPointerCancel={(event) => {
                pointersRef.current.delete(event.pointerId);
                if (dragRef.current?.pointerId === event.pointerId) dragRef.current = null;
                if (pointersRef.current.size < 2) pinchRef.current = null;
              }}
              onLostPointerCapture={(event) => {
                pointersRef.current.delete(event.pointerId);
                if (dragRef.current?.pointerId === event.pointerId) dragRef.current = null;
                if (pointersRef.current.size < 2) pinchRef.current = null;
              }}
            >
              <svg className="h-full w-full overflow-visible">
                <g
                  style={{
                    transform: `translate(${offset.x}px, ${offset.y}px) scale(${scale})`,
                    transformOrigin: "0 0",
                    transition: dragRef.current || pinchRef.current
                      ? "none"
                      : `transform ${CAMERA_TRANSITION_MS}ms cubic-bezier(0.22, 1, 0.36, 1)`,
                  }}
                >
                  {nodes.map((item) => {
                    if (!item.parentId) return null;
                    const parent = byId.get(item.parentId);
                    if (!parent) return null;

                    const parentHasChildren = (parent.node.children?.length ?? 0) > 0;
                    const startX =
                      parent.x +
                      parent.width +
                      (parentHasChildren
                        ? CONNECTOR_HANDLE_GAP + TOGGLE_SIZE / 2
                        : 0);
                    const startY = parent.y + parent.height / 2;

                    // Keep collapsed edges mounted and retract them into the exact
                    // connector origin instead of letting the path disappear.
                    const targetEndX = item.visible ? item.x : startX;
                    const targetEndY = item.visible
                      ? item.y + item.height / 2
                      : startY;
                    const deltaX = Math.max(0.001, targetEndX - startX);
                    const deltaY = targetEndY - startY;
                    const depthColor =
                      DEPTH_PALETTE[Math.min(item.depth, DEPTH_PALETTE.length - 1)];

                    return (
                      <g
                        key={`edge-${item.node.id}`}
                        style={{
                          transform: `translate(${startX}px, ${startY}px) scale(${deltaX}, ${deltaY || 0.001})`,
                          transformOrigin: "0 0",
                          opacity: item.visible && parent.visible ? 0.82 : 0,
                          transition: `transform ${LAYOUT_TRANSITION_MS}ms cubic-bezier(0.22, 1, 0.36, 1), opacity ${OPACITY_TRANSITION_MS}ms ease`,
                        }}
                      >
                        <path
                          // Normalized cubic curve. The group transform stretches it
                          // to the live parent/child geometry, so the wire grows,
                          // retracts and follows layout movement with the nodes.
                          d="M 0 0 C 0.46 0, 0.54 1, 1 1"
                          fill="none"
                          stroke={depthColor.stroke}
                          strokeWidth={1.8}
                          vectorEffect="non-scaling-stroke"
                        />
                      </g>
                    );
                  })}

                  {nodes.map((item) => {
                    const hasChildren = (item.node.children?.length ?? 0) > 0;
                    const color =
                      DEPTH_PALETTE[Math.min(item.depth, DEPTH_PALETTE.length - 1)];
                    const toggleSize = TOGGLE_SIZE;
                    const labelRightPadding = 14;

                    return (
                      <g
                        key={item.node.id}
                        style={{
                          transform: `translate(${item.x}px, ${item.y}px)`,
                          opacity: item.visible ? 1 : 0,
                          pointerEvents: item.visible ? "auto" : "none",
                          transition: `transform ${LAYOUT_TRANSITION_MS}ms cubic-bezier(0.22, 1, 0.36, 1), opacity ${OPACITY_TRANSITION_MS}ms ease`,
                        }}
                      >
                        <rect
                          width={item.width}
                          height={item.height}
                          rx={item.depth === 0 ? 11 : 9}
                          fill={color.fill}
                          stroke={color.stroke}
                          strokeWidth={item.depth === 0 ? 1.8 : 1.35}
                        />

                        <foreignObject
                          x={12}
                          y={0}
                          width={Math.max(28, item.width - 12 - labelRightPadding)}
                          height={item.height}
                          className="pointer-events-none"
                        >
                          <div
                            className={`flex h-full items-center whitespace-nowrap text-xs leading-none ${
                              item.depth === 0 ? "font-semibold" : "font-medium"
                            }`}
                            style={{ color: color.text }}
                            title={item.node.label}
                          >
                            {item.node.label}
                          </div>
                        </foreignObject>

                        {hasChildren && (
                          <foreignObject
                            x={item.width + CONNECTOR_HANDLE_GAP}
                            y={(item.height - toggleSize) / 2}
                            width={toggleSize}
                            height={toggleSize}
                          >
                            <button
                              onClick={(event) => {
                                event.stopPropagation();
                                toggleNode(item.node.id);
                              }}
                              className="flex h-[22px] w-[22px] items-center justify-center rounded-full bg-white/70 shadow-[0_0_0_1px_rgba(0,0,0,0.08)] transition-all duration-500 ease-out hover:scale-105 hover:bg-white"
                              title={
                                collapsed.has(item.node.id)
                                  ? "Expand branch"
                                  : "Collapse branch"
                              }
                              aria-label={
                                collapsed.has(item.node.id)
                                  ? `Expand ${item.node.label}`
                                  : `Collapse ${item.node.label}`
                              }
                            >
                              <Icon
                                name={
                                  collapsed.has(item.node.id)
                                    ? "chevron_right"
                                    : "chevron_left"
                                }
                                size={14}
                                style={{ color: color.text }}
                              />
                            </button>
                          </foreignObject>
                        )}
                      </g>
                    );
                  })}
                </g>
              </svg>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
