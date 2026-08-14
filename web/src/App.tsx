import { useEffect, useMemo, useRef, useState, type ChangeEvent } from "react";
import "./App.css";
import { ApiError, getLayout, listPeople, uploadProject } from "./api/client";
import type { PersonSummary, ProjectSummary } from "./api/client";
import { FamilyTreeCanvas } from "./canvas/FamilyTreeCanvas";
import { computePixelSize } from "./canvas/layoutConstants";
import { Legend } from "./canvas/Legend";
import { TitleDisplay } from "./canvas/TitleDisplay";
import { Viewport } from "./canvas/Viewport";
import { CommandStack, makeCommand } from "./editing/commandStack";
import { applyOverrides, createEmptyOverrides, descendantsOf, type Overrides } from "./editing/overrides";
import { downloadSvg, serializeChartToSvg } from "./export/exportChart";
import { DEFAULT_DISPLAY_OPTIONS, type DisplayOptions } from "./types/displayOptions";
import type { Calendar, LayoutResult } from "./types/layout";

// SP-06-01: 標題の文言・大きさ。位置は右端固定、書体は --font-title 固定
// (書体選択 UI は将来追加)。
interface TitleSettings {
  text: string;
  fontSize: number;
}

const DEFAULT_TITLE_SETTINGS: TitleSettings = { text: "", fontSize: 28 };

// SP-05-04 のプロジェクト保存形式 (ProjectDocument, DF-03-01) を実装範囲に
// 合わせて簡略化したもの。永続化はサーバを介さず、ブラウザのファイル保存/
// 読込ダイアログのみで完結させる (SP-05-04: 元データを書き換えない)。
interface ProjectDocumentV1 {
  format_version: 1;
  source_gpkg_filename: string;
  root_handle: string;
  calendar: Calendar;
  overrides: Overrides;
  display_options: DisplayOptions;
  title_settings?: TitleSettings;
}

function App() {
  const [project, setProject] = useState<ProjectSummary | null>(null);
  const [people, setPeople] = useState<PersonSummary[]>([]);
  const [rootHandle, setRootHandle] = useState<string>("");
  const [calendar, setCalendar] = useState<Calendar>("wareki");
  const [baseLayout, setBaseLayout] = useState<LayoutResult | null>(null);
  const [overrides, setOverrides] = useState<Overrides>(createEmptyOverrides());
  const [displayOptions, setDisplayOptions] = useState<DisplayOptions>(DEFAULT_DISPLAY_OPTIONS);
  const [titleSettings, setTitleSettings] = useState<TitleSettings>(DEFAULT_TITLE_SETTINGS);
  const [zoom, setZoom] = useState(1);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const commandStackRef = useRef(new CommandStack<Overrides>());
  // commandStackRef は変更してもレンダリングを起こさないミュータブルな参照
  // なので、Undo/Redo ボタンの有効/無効やラベルを更新するために手動で
  // 再レンダリングのきっかけを作る。
  const [stackVersion, setStackVersion] = useState(0);
  const loadFileInputRef = useRef<HTMLInputElement>(null);
  const chartRowRef = useRef<HTMLDivElement>(null);

  const displayLayout = useMemo(
    () => (baseLayout ? applyOverrides(baseLayout, overrides) : null),
    [baseLayout, overrides],
  );

  const descendantsCache = useMemo(() => {
    const map = new Map<string, string[]>();
    if (!baseLayout) return map;
    for (const node of baseLayout.nodes) {
      map.set(node.handle, descendantsOf(baseLayout, node.handle));
    }
    return map;
  }, [baseLayout]);

  const collapsibleHandles = useMemo(() => {
    const result = new Set<string>();
    for (const [handle, descendants] of descendantsCache) {
      if (descendants.length > 0) result.add(handle);
    }
    return result;
  }, [descendantsCache]);

  const collapsedHandles = useMemo(() => {
    const hidden = new Set(overrides.hidden_handles);
    const result = new Set<string>();
    for (const [handle, descendants] of descendantsCache) {
      if (descendants.length > 0 && descendants.some((h) => hidden.has(h))) {
        result.add(handle);
      }
    }
    return result;
  }, [descendantsCache, overrides]);

  const hasDeceased = useMemo(() => {
    if (!displayLayout) return false;
    return [...displayLayout.nodes, ...displayLayout.auxiliary_nodes].some(
      (n) => n.view.is_deceased,
    );
  }, [displayLayout]);

  const titleHeightPx = useMemo(
    () => (displayLayout ? computePixelSize(displayLayout).height : 0),
    [displayLayout],
  );

  function pushOverridesCommand(label: string, next: Overrides) {
    commandStackRef.current.push(makeCommand(label, overrides, next));
    setStackVersion((v) => v + 1);
    setOverrides(next);
  }

  function handleUndo() {
    const previous = commandStackRef.current.undo();
    setStackVersion((v) => v + 1);
    if (previous) setOverrides(previous);
  }

  function handleRedo() {
    const next = commandStackRef.current.redo();
    setStackVersion((v) => v + 1);
    if (next) setOverrides(next);
  }

  useEffect(() => {
    function handleKeyDown(event: KeyboardEvent) {
      const key = event.key.toLowerCase();
      if (!(event.ctrlKey || event.metaKey)) return;
      if (key === "z") {
        event.preventDefault();
        const previous = commandStackRef.current.undo();
        setStackVersion((v) => v + 1);
        if (previous) setOverrides(previous);
      } else if (key === "y") {
        event.preventDefault();
        const next = commandStackRef.current.redo();
        setStackVersion((v) => v + 1);
        if (next) setOverrides(next);
      }
    }
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, []);

  function handleNodeDragEnd(handle: string, x: number, y: number) {
    pushOverridesCommand("ノード移動", {
      ...overrides,
      node_positions: { ...overrides.node_positions, [handle]: { x, y } },
    });
  }

  function handleToggleCollapse(handle: string) {
    const descendants = descendantsCache.get(handle) ?? [];
    if (descendants.length === 0) return;
    const hidden = new Set(overrides.hidden_handles);
    const isCollapsed = descendants.some((h) => hidden.has(h));
    const nextHidden = isCollapsed
      ? overrides.hidden_handles.filter((h) => !descendants.includes(h))
      : Array.from(new Set([...overrides.hidden_handles, ...descendants]));
    pushOverridesCommand(isCollapsed ? "枝を展開" : "枝を折りたたむ", {
      ...overrides,
      hidden_handles: nextHidden,
    });
  }

  function handleResetOverrides() {
    pushOverridesCommand("自動レイアウトの再実行", createEmptyOverrides());
  }

  async function handleFileChange(event: ChangeEvent<HTMLInputElement>) {
    const file = event.target.files?.[0];
    if (!file) return;
    setError(null);
    setBusy(true);
    try {
      const summary = await uploadProject(file);
      setProject(summary);
      const list = await listPeople(summary.project_id);
      setPeople(list);
      setBaseLayout(null);
      setRootHandle("");
      setOverrides(createEmptyOverrides());
      commandStackRef.current.clear();
      setStackVersion((v) => v + 1);
    } catch (err) {
      setError(err instanceof ApiError ? `${err.code}: ${err.message}` : String(err));
    } finally {
      setBusy(false);
    }
  }

  async function loadLayout(handle: string, cal: Calendar) {
    if (!project || !handle) return;
    setError(null);
    setBusy(true);
    try {
      const result = await getLayout(project.project_id, handle, cal);
      setBaseLayout(result);
      setOverrides(createEmptyOverrides());
      commandStackRef.current.clear();
      setStackVersion((v) => v + 1);
    } catch (err) {
      setError(err instanceof ApiError ? `${err.code}: ${err.message}` : String(err));
    } finally {
      setBusy(false);
    }
  }

  function handleRootChange(event: ChangeEvent<HTMLSelectElement>) {
    const handle = event.target.value;
    setRootHandle(handle);
    void loadLayout(handle, calendar);
  }

  function handleCalendarChange(event: ChangeEvent<HTMLSelectElement>) {
    const cal = event.target.value as Calendar;
    setCalendar(cal);
    void loadLayout(rootHandle, cal);
  }

  function toggleDisplayOption(key: keyof DisplayOptions) {
    setDisplayOptions((current) => ({ ...current, [key]: !current[key] }));
  }

  function handlePrint() {
    window.print();
  }

  function handleExportSvg() {
    if (!chartRowRef.current || !project) return;
    const svgText = serializeChartToSvg(chartRowRef.current);
    downloadSvg(svgText, `${project.filename.replace(/\.gpkg$/i, "")}.svg`);
  }

  function handleSaveDocument() {
    if (!project || !rootHandle) return;
    const doc: ProjectDocumentV1 = {
      format_version: 1,
      source_gpkg_filename: project.filename,
      root_handle: rootHandle,
      calendar,
      overrides,
      display_options: displayOptions,
      title_settings: titleSettings,
    };
    const blob = new Blob([JSON.stringify(doc, null, 2)], { type: "application/json" });
    const url = URL.createObjectURL(blob);
    const anchor = document.createElement("a");
    anchor.href = url;
    anchor.download = `${project.filename.replace(/\.gpkg$/i, "")}.gpkgjsr.json`;
    anchor.click();
    URL.revokeObjectURL(url);
  }

  async function handleLoadDocument(event: ChangeEvent<HTMLInputElement>) {
    const file = event.target.files?.[0];
    event.target.value = "";
    if (!file || !project) return;
    setError(null);
    setBusy(true);
    try {
      const text = await file.text();
      const doc = JSON.parse(text) as Partial<ProjectDocumentV1>;
      if (doc.format_version !== 1 || !doc.root_handle) {
        throw new Error("不明な保存形式のファイルです");
      }
      const cal = doc.calendar ?? "wareki";
      const result = await getLayout(project.project_id, doc.root_handle, cal);
      setBaseLayout(result);
      setRootHandle(doc.root_handle);
      setCalendar(cal);
      setOverrides(doc.overrides ?? createEmptyOverrides());
      setDisplayOptions(doc.display_options ?? DEFAULT_DISPLAY_OPTIONS);
      setTitleSettings(doc.title_settings ?? DEFAULT_TITLE_SETTINGS);
      commandStackRef.current.clear();
      setStackVersion((v) => v + 1);
    } catch (err) {
      setError(err instanceof ApiError ? `${err.code}: ${err.message}` : String(err));
    } finally {
      setBusy(false);
    }
  }

  const commandStack = commandStackRef.current;
  void stackVersion; // 依存させるための読み取り (再レンダリングのトリガー用)

  return (
    <div className="app">
      <header className="app__toolbar">
        <h1 className="app__title">gpkg Japanese Style Renderer</h1>
        <label className="app__upload">
          .gpkg を開く
          <input type="file" accept=".gpkg" onChange={handleFileChange} disabled={busy} />
        </label>
        {project && (
          <>
            <span className="app__summary">
              {project.filename} ({project.people}人 / {project.families}家族)
            </span>
            <label>
              起点人物:
              <select value={rootHandle} onChange={handleRootChange} disabled={busy}>
                <option value="">選択してください</option>
                {people.map((person) => (
                  <option key={person.handle} value={person.handle}>
                    {person.display_name}
                    {person.birth_date_text ? ` (${person.birth_date_text})` : ""}
                  </option>
                ))}
              </select>
            </label>
            <label>
              暦:
              <select value={calendar} onChange={handleCalendarChange} disabled={busy}>
                <option value="wareki">和暦</option>
                <option value="western">西暦</option>
              </select>
            </label>
          </>
        )}
        {error && <span className="app__error">{error}</span>}
      </header>

      {displayLayout && (
        <div className="app__edit-bar">
          <button type="button" onClick={handleUndo} disabled={!commandStack.canUndo()}>
            元に戻す
            {commandStack.peekUndoLabel() ? `: ${commandStack.peekUndoLabel()}` : ""}
          </button>
          <button type="button" onClick={handleRedo} disabled={!commandStack.canRedo()}>
            やり直す
            {commandStack.peekRedoLabel() ? `: ${commandStack.peekRedoLabel()}` : ""}
          </button>
          <button type="button" onClick={handleResetOverrides}>
            自動レイアウトを再実行
          </button>
          <span className="app__edit-bar-separator" />
          <label>
            <input
              type="checkbox"
              checked={displayOptions.showRuby}
              onChange={() => toggleDisplayOption("showRuby")}
            />
            ルビ
          </label>
          <label>
            <input
              type="checkbox"
              checked={displayOptions.showBirthOrder}
              onChange={() => toggleDisplayOption("showBirthOrder")}
            />
            続柄
          </label>
          <label>
            <input
              type="checkbox"
              checked={displayOptions.showDates}
              onChange={() => toggleDisplayOption("showDates")}
            />
            生没年
          </label>
          <label>
            <input
              type="checkbox"
              checked={displayOptions.showPhotos}
              onChange={() => toggleDisplayOption("showPhotos")}
            />
            写真
          </label>
          <label>
            <input
              type="checkbox"
              checked={displayOptions.showFormerSurname}
              onChange={() => toggleDisplayOption("showFormerSurname")}
            />
            旧姓
          </label>
          <label>
            <input
              type="checkbox"
              checked={displayOptions.showFrame}
              onChange={() => toggleDisplayOption("showFrame")}
            />
            人物枠
          </label>
          <span className="app__edit-bar-separator" />
          <label>
            標題:
            <input
              type="text"
              className="app__title-input"
              value={titleSettings.text}
              onChange={(event) =>
                setTitleSettings((current) => ({ ...current, text: event.target.value }))
              }
              placeholder="例: 山田家系図"
            />
          </label>
          <label>
            大きさ:
            <input
              type="number"
              className="app__title-size-input"
              min={12}
              max={72}
              value={titleSettings.fontSize}
              onChange={(event) =>
                setTitleSettings((current) => ({
                  ...current,
                  fontSize: Number(event.target.value) || DEFAULT_TITLE_SETTINGS.fontSize,
                }))
              }
            />
          </label>
          <span className="app__edit-bar-separator" />
          <button type="button" onClick={handleSaveDocument}>
            保存
          </button>
          <button type="button" onClick={() => loadFileInputRef.current?.click()}>
            読込
          </button>
          <input
            ref={loadFileInputRef}
            type="file"
            accept="application/json"
            className="app__hidden-file-input"
            onChange={handleLoadDocument}
          />
          <span className="app__edit-bar-separator" />
          <button type="button" onClick={handlePrint}>
            印刷
          </button>
          <button type="button" onClick={handleExportSvg}>
            SVGで書き出す
          </button>
        </div>
      )}

      <main className="app__canvas-area">
        {displayLayout && project ? (
          <>
            <Viewport zoom={zoom} onZoomChange={setZoom}>
              <div className="app__chart-row" ref={chartRowRef}>
                <FamilyTreeCanvas
                  layout={displayLayout}
                  projectId={project.project_id}
                  zoom={zoom}
                  displayOptions={displayOptions}
                  onNodeDragEnd={handleNodeDragEnd}
                  collapsibleHandles={collapsibleHandles}
                  collapsedHandles={collapsedHandles}
                  onToggleCollapse={handleToggleCollapse}
                />
                <TitleDisplay
                  text={titleSettings.text}
                  heightPx={titleHeightPx}
                  fontSize={titleSettings.fontSize}
                />
              </div>
            </Viewport>
            <Legend hasDeceased={hasDeceased} />
          </>
        ) : (
          <div className="app__placeholder">
            {project ? "起点人物を選択してください" : ".gpkg ファイルを開いてください"}
          </div>
        )}
      </main>
    </div>
  );
}

export default App;
