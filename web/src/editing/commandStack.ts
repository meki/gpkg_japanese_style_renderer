// コマンドスタックによる Undo/Redo (SP-05-03, RQ-05-06)。
//
// 各コマンドは適用前 (before) ・適用後 (after) の状態をスナップショットとして
// 丸ごと保持するメメント方式にする。ノード移動・枝の表示/非表示・自動レイアウト
// の再実行 (= オーバーライド全体のリセット) のいずれも「編集対象の状態
// (Overrides) をある値から別の値へ変える」という同じ形の操作として扱えるため、
// 個々のコマンドごとに逆操作を実装する必要がなく、実装・検証の両方が単純になる。

export interface Command<S> {
  readonly label: string;
  readonly before: S;
  readonly after: S;
}

export function makeCommand<S>(label: string, before: S, after: S): Command<S> {
  return { label, before, after };
}

export class CommandStack<S> {
  private undoStack: Command<S>[] = [];
  private redoStack: Command<S>[] = [];

  /** 新しいコマンドを積む。redo スタックは破棄する (新規操作は分岐点になる)。 */
  push(command: Command<S>): void {
    this.undoStack.push(command);
    this.redoStack = [];
  }

  canUndo(): boolean {
    return this.undoStack.length > 0;
  }

  canRedo(): boolean {
    return this.redoStack.length > 0;
  }

  /** 直前のコマンドを取り消し、適用前の状態を返す。取り消せなければ null。 */
  undo(): S | null {
    const command = this.undoStack.pop();
    if (!command) return null;
    this.redoStack.push(command);
    return command.before;
  }

  /** 直前に取り消したコマンドをやり直し、適用後の状態を返す。なければ null。 */
  redo(): S | null {
    const command = this.redoStack.pop();
    if (!command) return null;
    this.undoStack.push(command);
    return command.after;
  }

  peekUndoLabel(): string | null {
    return this.undoStack.at(-1)?.label ?? null;
  }

  peekRedoLabel(): string | null {
    return this.redoStack.at(-1)?.label ?? null;
  }

  clear(): void {
    this.undoStack = [];
    this.redoStack = [];
  }
}
