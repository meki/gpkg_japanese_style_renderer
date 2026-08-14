import { describe, expect, it } from "vitest";
import { CommandStack, makeCommand } from "./commandStack";

describe("CommandStack", () => {
  it("starts with nothing to undo or redo", () => {
    const stack = new CommandStack<number>();
    expect(stack.canUndo()).toBe(false);
    expect(stack.canRedo()).toBe(false);
    expect(stack.undo()).toBeNull();
    expect(stack.redo()).toBeNull();
  });

  it("undo returns the state before the command", () => {
    const stack = new CommandStack<number>();
    stack.push(makeCommand("increment", 0, 1));
    expect(stack.canUndo()).toBe(true);
    expect(stack.undo()).toBe(0);
    expect(stack.canUndo()).toBe(false);
  });

  it("redo returns the state after the command", () => {
    const stack = new CommandStack<number>();
    stack.push(makeCommand("increment", 0, 1));
    stack.undo();
    expect(stack.canRedo()).toBe(true);
    expect(stack.redo()).toBe(1);
    expect(stack.canRedo()).toBe(false);
  });

  it("undoing multiple commands walks back through history in order", () => {
    const stack = new CommandStack<number>();
    stack.push(makeCommand("to 1", 0, 1));
    stack.push(makeCommand("to 2", 1, 2));
    stack.push(makeCommand("to 3", 2, 3));

    expect(stack.undo()).toBe(2);
    expect(stack.undo()).toBe(1);
    expect(stack.undo()).toBe(0);
    expect(stack.undo()).toBeNull();
  });

  it("pushing a new command after undo discards the redo history", () => {
    const stack = new CommandStack<number>();
    stack.push(makeCommand("to 1", 0, 1));
    stack.push(makeCommand("to 2", 1, 2));
    stack.undo();
    expect(stack.canRedo()).toBe(true);

    stack.push(makeCommand("to 5", 1, 5));
    expect(stack.canRedo()).toBe(false);
    expect(stack.redo()).toBeNull();
  });

  it("exposes labels for the next undo/redo action (UI-02-01)", () => {
    const stack = new CommandStack<number>();
    expect(stack.peekUndoLabel()).toBeNull();

    stack.push(makeCommand("ノード移動", 0, 1));
    expect(stack.peekUndoLabel()).toBe("ノード移動");

    stack.undo();
    expect(stack.peekUndoLabel()).toBeNull();
    expect(stack.peekRedoLabel()).toBe("ノード移動");
  });

  it("clear() resets both stacks", () => {
    const stack = new CommandStack<number>();
    stack.push(makeCommand("to 1", 0, 1));
    stack.undo();
    stack.clear();
    expect(stack.canUndo()).toBe(false);
    expect(stack.canRedo()).toBe(false);
  });
});
