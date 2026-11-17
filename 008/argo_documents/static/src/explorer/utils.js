/** Tiện ích dùng chung cho Kho tài liệu */

export const TYPE_ICON = {
    folder: "fa-folder",
    image: "fa-file-image-o",
    pdf: "fa-file-pdf-o",
    word: "fa-file-word-o",
    excel: "fa-file-excel-o",
    powerpoint: "fa-file-powerpoint-o",
    video: "fa-file-video-o",
    archive: "fa-file-archive-o",
    text: "fa-file-text-o",
    note: "fa-sticky-note-o",
    other: "fa-file-o",
};

export const TYPE_LABEL = {
    folder: "Thư mục",
    image: "Hình ảnh",
    pdf: "PDF",
    word: "Word",
    excel: "Excel",
    powerpoint: "PowerPoint",
    video: "Video / âm thanh",
    archive: "File nén",
    text: "Văn bản",
    note: "Ghi chú",
    other: "File",
};

export const NEW_FILE_ITEMS = [
    { kind: "note", label: "Ghi chú (soạn online)", icon: "fa-sticky-note-o", cls: "note" },
    { kind: "docx", label: "Tài liệu Word", icon: "fa-file-word-o", cls: "word" },
    { kind: "xlsx", label: "Bảng tính Excel", icon: "fa-file-excel-o", cls: "excel" },
    { kind: "pptx", label: "Bản trình bày PowerPoint", icon: "fa-file-powerpoint-o", cls: "powerpoint" },
    { kind: "txt", label: "Tài liệu văn bản (.txt)", icon: "fa-file-text-o", cls: "text" },
];

export function humanSize(size) {
    size = Number(size) || 0;
    if (size < 1024) {
        return `${size} B`;
    }
    const units = ["KB", "MB", "GB"];
    let i = -1;
    do {
        size /= 1024;
        i++;
    } while (size >= 1024 && i < units.length - 1);
    return `${size.toFixed(size >= 100 ? 0 : 1)} ${units[i]}`;
}

export function formatDate(value) {
    if (!value) {
        return "";
    }
    const d = new Date(value.replace(" ", "T") + "Z");
    if (isNaN(d)) {
        return value;
    }
    const pad = (n) => String(n).padStart(2, "0");
    return `${pad(d.getDate())}/${pad(d.getMonth() + 1)}/${d.getFullYear()} ${pad(d.getHours())}:${pad(d.getMinutes())}`;
}

export function itemKey(item) {
    return `${item.kind}:${item.id}`;
}

export function parseKey(key) {
    const [kind, id] = key.split(":");
    return { kind, id: Number(id) };
}

export function storageGet(key, fallback) {
    try {
        const v = window.localStorage.getItem(`argo_documents.${key}`);
        return v === null ? fallback : JSON.parse(v);
    } catch {
        return fallback;
    }
}

export function storageSet(key, value) {
    try {
        window.localStorage.setItem(`argo_documents.${key}`, JSON.stringify(value));
    } catch {
        // trình duyệt chặn localStorage -> bỏ qua
    }
}

/** Đọc toàn bộ file (kể cả trong thư mục con) từ sự kiện kéo-thả. */
export async function collectDroppedFiles(dataTransfer) {
    const entries = [];
    for (const item of dataTransfer.items || []) {
        if (item.kind !== "file") {
            continue;
        }
        const entry = item.webkitGetAsEntry ? item.webkitGetAsEntry() : null;
        if (entry) {
            entries.push(entry);
        } else {
            const file = item.getAsFile();
            if (file) {
                entries.push({ isFile: true, _file: file, name: file.name });
            }
        }
    }
    if (!entries.length) {
        return { files: [...(dataTransfer.files || [])].map((file) => ({ file, relPath: "" })), dirs: [] };
    }
    const result = [];
    const dirs = new Set();
    const readEntry = async (entry, prefix) => {
        if (entry._file) {
            result.push({ file: entry._file, relPath: prefix });
        } else if (entry.isFile) {
            const file = await new Promise((resolve, reject) => entry.file(resolve, reject));
            result.push({ file, relPath: prefix });
        } else if (entry.isDirectory) {
            const reader = entry.createReader();
            const dirPath = prefix ? `${prefix}/${entry.name}` : entry.name;
            dirs.add(dirPath);
            let batch;
            do {
                batch = await new Promise((resolve, reject) => reader.readEntries(resolve, reject));
                for (const child of batch) {
                    await readEntry(child, dirPath);
                }
            } while (batch.length);
        }
    };
    for (const entry of entries) {
        await readEntry(entry, "");
    }
    return { files: result, dirs: [...dirs] };
}

/** Nhãn quyền xem: "Phòng A", "Phòng B", "Tên người"... (dùng cho chi tiết thư mục và hộp thoại). */
export function accessLabels(departments, users) {
    return [
        ...(departments || []).map((d) => `Phòng ${d.name}`),
        ...(users || []).map((u) => u.name),
    ];
}
