"use strict";

const form = document.querySelector("#task-form");
const titleInput = document.querySelector("#task-title");
const list = document.querySelector("#task-list");
const emptyState = document.querySelector("#empty-state");
const errors = document.querySelector("#errors");
const feedback = document.querySelector("#feedback");
const refreshButton = document.querySelector("#refresh");
let busy = false;

async function api(path, options = {}) {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), 10000);
  try {
    const response = await fetch(path, {
      ...options,
      headers: {"Accept": "application/json", ...(options.body ? {"Content-Type": "application/json"} : {})},
      signal: controller.signal,
      redirect: "error",
    });
    const data = response.status === 204 ? null : await response.json();
    if (!response.ok) {
      throw new Error(typeof data?.error === "string" ? data.error : `Request failed (${response.status}).`);
    }
    return data;
  } catch (error) {
    if (error.name === "AbortError") throw new Error("Request timed out. Please try again.");
    if (error instanceof TypeError) throw new Error("Cannot reach Tasks. Check the service and try again.");
    if (error instanceof SyntaxError) throw new Error("Tasks returned an invalid response. Please try again.");
    throw error;
  } finally {
    clearTimeout(timer);
  }
}

function showErrors(messages) {
  errors.replaceChildren();
  for (const message of messages) {
    const paragraph = document.createElement("p");
    paragraph.textContent = message;
    errors.append(paragraph);
  }
  errors.hidden = messages.length === 0;
}

function setBusy(value) {
  busy = value;
  document.querySelector(".task-section").setAttribute("aria-busy", String(value));
  document.querySelectorAll("button, input").forEach(control => { control.disabled = value; });
}

function renderTasks(tasks) {
  list.replaceChildren();
  emptyState.hidden = tasks.length > 0;
  emptyState.textContent = "No tasks yet.";
  document.querySelector("#list-count").textContent = `${tasks.length} ${tasks.length === 1 ? "task" : "tasks"}`;
  for (const task of tasks) {
    const row = document.createElement("li");
    row.className = task.completed ? "task is-completed" : "task";
    row.dataset.taskId = String(task.id);
    const checkbox = document.createElement("input");
    checkbox.type = "checkbox";
    checkbox.checked = task.completed;
    checkbox.setAttribute("aria-label", `Mark ${task.title} ${task.completed ? "pending" : "completed"}`);
    checkbox.addEventListener("change", async () => {
      const requested = checkbox.checked;
      checkbox.checked = task.completed;
      await mutate(`/api/tasks/${task.id}`, {method: "PATCH", body: JSON.stringify({completed: requested})}, "Task updated.");
    });
    const content = document.createElement("div");
    const title = document.createElement("p");
    title.className = "task-title";
    title.textContent = task.title;
    const date = document.createElement("p");
    date.className = "task-date";
    date.textContent = new Date(task.created_at).toLocaleString(undefined, {dateStyle: "medium", timeStyle: "short"});
    content.append(title, date);
    const remove = document.createElement("button");
    remove.type = "button";
    remove.className = "delete-task";
    remove.textContent = "Delete";
    remove.setAttribute("aria-label", `Delete ${task.title}`);
    remove.addEventListener("click", () => mutate(`/api/tasks/${task.id}`, {method: "DELETE"}, "Task deleted."));
    row.append(checkbox, content, remove);
    list.append(row);
  }
}

async function loadAll() {
  const results = await Promise.allSettled([api("/api/tasks"), api("/api/statistics")]);
  const messages = [];
  if (results[0].status === "fulfilled") {
    renderTasks(results[0].value);
  } else {
    emptyState.hidden = list.children.length > 0;
    emptyState.textContent = "Tasks could not be loaded.";
    messages.push(`Tasks: ${results[0].reason.message}`);
  }
  for (const key of ["total", "completed", "pending"]) {
    document.querySelector(`#${key}`).textContent = results[1].status === "fulfilled" ? results[1].value[key] : "--";
  }
  if (results[1].status === "rejected") messages.push(`Statistics: ${results[1].reason.message}`);
  showErrors(messages);
}

async function mutate(path, options, message) {
  if (busy) return false;
  setBusy(true);
  feedback.textContent = "Saving...";
  showErrors([]);
  try {
    await api(path, options);
    await loadAll();
    feedback.textContent = message;
    return true;
  } catch (error) {
    feedback.textContent = "";
    showErrors([error.message]);
    return false;
  } finally {
    setBusy(false);
  }
}

form.addEventListener("submit", async event => {
  event.preventDefault();
  const title = titleInput.value.trim();
  if (!title) {
    showErrors(["Enter a title with at least one non-space character."]);
    titleInput.focus();
    return;
  }
  if (await mutate("/api/tasks", {method: "POST", body: JSON.stringify({title})}, "Task added.")) {
    titleInput.value = "";
    titleInput.focus();
  }
});

refreshButton.addEventListener("click", async () => {
  if (busy) return;
  setBusy(true);
  feedback.textContent = "";
  try { await loadAll(); } finally { setBusy(false); }
});

setBusy(true);
loadAll().finally(() => setBusy(false));