import { useState, type ChangeEvent } from "react";
import "./App.css";
import { ApiError, getLayout, listPeople, uploadProject } from "./api/client";
import type { PersonSummary, ProjectSummary } from "./api/client";
import { FamilyTreeCanvas } from "./canvas/FamilyTreeCanvas";
import { Viewport } from "./canvas/Viewport";
import type { Calendar, LayoutResult } from "./types/layout";

function App() {
  const [project, setProject] = useState<ProjectSummary | null>(null);
  const [people, setPeople] = useState<PersonSummary[]>([]);
  const [rootHandle, setRootHandle] = useState<string>("");
  const [calendar, setCalendar] = useState<Calendar>("wareki");
  const [layout, setLayout] = useState<LayoutResult | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

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
      setLayout(null);
      setRootHandle("");
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
      setLayout(result);
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
      <main className="app__canvas-area">
        {layout && project ? (
          <Viewport>
            <FamilyTreeCanvas layout={layout} projectId={project.project_id} />
          </Viewport>
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
