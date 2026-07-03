import { EditorState } from "https://esm.sh/@codemirror/state@6";
import { EditorView, lineNumbers, highlightSpecialChars } from "https://esm.sh/@codemirror/view@6";
import { syntaxHighlighting, defaultHighlightStyle } from "https://esm.sh/@codemirror/language@6";
import { json } from "https://esm.sh/@codemirror/lang-json@6";
import { python } from "https://esm.sh/@codemirror/lang-python@6";

// ------------ Actions of builder ------------
const output = document.getElementById("output");

document.getElementById("actions").addEventListener("click", async (e) => {
    const action = e.target.dataset.action;
    if (!action) return;

    const buttons = document.querySelectorAll("#actions button");
    buttons.forEach((b) => (b.disabled = true));
    output.className = "";
    output.textContent = `Выполняется: ${action}...`;

    try {
        const res = await fetch(`/api/${action}`, { method: "POST" });
        const data = await res.json();
        output.textContent = data.log || "";
        if (data.data) {
            output.textContent += "\n" + JSON.stringify(data.data, null, 2);
        }
        if (!data.ok) {
            output.className = "error";
            output.textContent += "\n\nОШИБКА: " + (data.error || "неизвестная ошибка");
        }
    } catch (err) {
        output.className = "error";
        output.textContent = "Сетевая ошибка: " + err;
    } finally {
        buttons.forEach((b) => (b.disabled = false));
    }
});

// ------------ Module Browser ------------
const moduleList = document.getElementById("module-list");
const fileTabs = document.getElementById("file-tabs");
const editorHost = document.getElementById("editor");

let editorView = null;
let currentModule = null;

function langExtension(ext) {
    if (ext === ".json") return [json()];
    if (ext === ".py") return [python()];
    return [];
}

function showEditor(content, ext) {
    if (editorView) editorView.destroy();
    editorHost.innerHTML = "";
    const state = EditorState.create({
        doc: content,
        extensions: [
            lineNumbers(),
            highlightSpecialChars(),
            syntaxHighlighting(defaultHighlightStyle),
            EditorState.readOnly.of(true),
            EditorView.editable.of(false),
            ...langExtension(ext),
        ],
    });
    editorView = new EditorView({ state, parent: editorHost });
}

async function loadModules() {
    try {
        const res = await fetch("/api/modules");
        const { data } = await res.json();
        moduleList.innerHTML = "";
        for (const module of data) {
            const li = document.createElement("li");
            const badge = module.has_manifest
                ? (module.manifest_valid === false ? '<span class="badge invalid">битый JSON</span>' : "")
                : '<span class="badge">без манифеста</span>';
            li.innerHTML = `${module.module_name} ${badge}`;
            li.addEventListener("click", () => selectModule(module.module_name, li));
            moduleList.appendChild(li);
        }
        if (!data.length) moduleList.innerHTML = '<li class="hint">Модулей нет.</li>';
    } catch (err) {
        moduleList.innerHTML = `<li class="hint">Ошибка загрузки: ${err}</li>`;
    }
}

async function selectModule(name, li) {
    currentModule = name;
    document.querySelectorAll("#module-list li").forEach((el) => el.classList.remove("active"));
    if (li) li.classList.add("active");

    const res = await fetch(`/api/modules/${encodeURIComponent(name)}`);
    const { data } = await res.json();

    fileTabs.innerHTML = "";
    for (const filename of data.files) {
        const btn = document.createElement("button");
        btn.textContent = filename;
        btn.addEventListener("click", () => selectFile(name, filename, btn));
        fileTabs.appendChild(btn);
    }
    if (data.files.length) {
        selectFile(name, data.files[0], fileTabs.firstChild);
    } else {
        editorHost.innerHTML = '<div class="hint">В модуле нет файлов для просмотра.</div>';
    }
}

async function selectFile(name, filename, btn) {
    document.querySelectorAll("#file-tabs button").forEach((el) => el.classList.remove("active"));
    if (btn) btn.classList.add("active");

    const res = await fetch(`/api/modules/${encodeURIComponent(name)}/files/${encodeURIComponent(filename)}`);
    if (!res.ok) {
        editorHost.innerHTML = `<div class="hint">Не удалось открыть файл (${res.status}).</div>`;
        return;
    }
    const { data } = await res.json();
    showEditor(data.content, data.file_ext);
}

loadModules();
