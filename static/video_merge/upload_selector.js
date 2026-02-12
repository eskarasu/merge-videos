(function () {
    "use strict";

    var form = document.querySelector("[data-upload-form]");
    if (!form) {
        return;
    }

    var fileInput = form.querySelector("input[type='file'][name='files']");
    var pickButton = form.querySelector("[data-pick-files]");
    var fileCount = form.querySelector("[data-file-count]");
    var dropzone = form.querySelector("[data-dropzone]");
    var nativeInputWrapper = form.querySelector("[data-native-input-wrapper]");
    var fileList = form.querySelector("[data-file-list]");
    var emptyState = form.querySelector("[data-file-empty-state]");
    var viewModeButtons = Array.from(form.querySelectorAll("[data-view-mode]"));

    if (!fileInput || !pickButton || !fileCount || !dropzone || !fileList || !emptyState || viewModeButtons.length === 0) {
        return;
    }

    if (typeof DataTransfer === "undefined") {
        return;
    }

    var selectedFiles = [];
    var thumbnailByKey = {};
    var thumbnailLoadingByKey = {};
    var VIEW_MODE_STORAGE_KEY = "video_upload_view_mode";
    var viewMode = "list";

    function fileKey(file) {
        return [file.name, file.size, file.lastModified].join("::");
    }

    function formatSize(bytes) {
        if (bytes < 1024) {
            return bytes + " B";
        }
        if (bytes < 1024 * 1024) {
            return (bytes / 1024).toFixed(1) + " KB";
        }
        if (bytes < 1024 * 1024 * 1024) {
            return (bytes / (1024 * 1024)).toFixed(1) + " MB";
        }
        return (bytes / (1024 * 1024 * 1024)).toFixed(2) + " GB";
    }

    function extensionOf(filename) {
        var parts = String(filename || "").split(".");
        if (parts.length < 2) {
            return "VID";
        }
        return parts[parts.length - 1].toUpperCase();
    }

    function setViewMode(mode) {
        if (mode !== "list" && mode !== "grid") {
            mode = "list";
        }

        viewMode = mode;
        fileList.setAttribute("data-view-mode", mode);
        viewModeButtons.forEach(function (button) {
            var isActive = button.getAttribute("data-view-mode") === mode;
            button.classList.toggle("is-active", isActive);
            button.setAttribute("aria-pressed", isActive ? "true" : "false");
        });

        try {
            window.localStorage.setItem(VIEW_MODE_STORAGE_KEY, mode);
        } catch (error) {
            // ignore storage write errors
        }

        renderFiles();
    }

    function restoreViewMode() {
        try {
            var saved = window.localStorage.getItem(VIEW_MODE_STORAGE_KEY);
            if (saved === "list" || saved === "grid") {
                viewMode = saved;
            }
        } catch (error) {
            // ignore storage read errors
        }
    }

    function syncInputFiles() {
        var transfer = new DataTransfer();
        selectedFiles.forEach(function (file) {
            transfer.items.add(file);
        });
        fileInput.files = transfer.files;
    }

    function generateThumbnail(file) {
        return new Promise(function (resolve) {
            if (!window.URL || typeof window.URL.createObjectURL !== "function") {
                resolve("");
                return;
            }

            var sourceUrl = window.URL.createObjectURL(file);
            var video = document.createElement("video");
            var done = false;

            function cleanup() {
                if (done) {
                    return;
                }
                done = true;
                video.pause();
                video.removeAttribute("src");
                video.load();
                window.URL.revokeObjectURL(sourceUrl);
            }

            function finish(dataUrl) {
                cleanup();
                resolve(dataUrl || "");
            }

            function capture() {
                try {
                    if (!video.videoWidth || !video.videoHeight) {
                        finish("");
                        return;
                    }

                    var targetWidth = 320;
                    var targetHeight = Math.max(180, Math.round((targetWidth * video.videoHeight) / video.videoWidth));
                    var canvas = document.createElement("canvas");
                    canvas.width = targetWidth;
                    canvas.height = targetHeight;
                    var context = canvas.getContext("2d");
                    if (!context) {
                        finish("");
                        return;
                    }
                    context.drawImage(video, 0, 0, targetWidth, targetHeight);
                    finish(canvas.toDataURL("image/jpeg", 0.78));
                } catch (error) {
                    finish("");
                }
            }

            video.preload = "metadata";
            video.muted = true;
            video.playsInline = true;
            video.onerror = function () {
                finish("");
            };

            video.onloadedmetadata = function () {
                var targetTime = 0;
                if (Number.isFinite(video.duration) && video.duration > 0.1) {
                    targetTime = Math.min(video.duration * 0.1, Math.max(video.duration - 0.05, 0));
                }

                if (targetTime <= 0) {
                    window.setTimeout(capture, 0);
                    return;
                }

                try {
                    video.currentTime = targetTime;
                } catch (error) {
                    window.setTimeout(capture, 0);
                }
            };

            video.onseeked = capture;
            video.onloadeddata = function () {
                if (!done) {
                    capture();
                }
            };

            video.src = sourceUrl;
        });
    }

    function requestThumbnail(file) {
        var key = fileKey(file);
        if (thumbnailLoadingByKey[key] || thumbnailByKey[key] !== undefined) {
            return;
        }

        thumbnailLoadingByKey[key] = true;
        generateThumbnail(file)
            .then(function (thumbnail) {
                thumbnailByKey[key] = thumbnail;
            })
            .catch(function () {
                thumbnailByKey[key] = "";
            })
            .finally(function () {
                delete thumbnailLoadingByKey[key];
                renderFiles();
            });
    }

    function createRemoveButton(file, index) {
        var remove = document.createElement("button");
        remove.type = "button";
        remove.className = "file-remove";
        remove.setAttribute("aria-label", file.name + " dosyasini kaldir");
        remove.setAttribute("data-remove-index", String(index));
        remove.textContent = "x";
        return remove;
    }

    function createListItem(file, index) {
        var item = document.createElement("div");
        item.className = "file-item file-item-list";

        var icon = document.createElement("span");
        icon.className = "file-icon";
        icon.textContent = extensionOf(file.name);

        var meta = document.createElement("div");
        meta.className = "file-meta";

        var order = document.createElement("span");
        order.className = "file-order";
        order.textContent = "#" + String(index + 1);

        var name = document.createElement("span");
        name.className = "file-name";
        name.textContent = file.name;

        var size = document.createElement("span");
        size.className = "file-size";
        size.textContent = formatSize(file.size);

        meta.appendChild(order);
        meta.appendChild(name);
        meta.appendChild(size);

        item.appendChild(icon);
        item.appendChild(meta);
        item.appendChild(createRemoveButton(file, index));
        return item;
    }

    function createGridItem(file, index) {
        var item = document.createElement("div");
        item.className = "file-item file-item-grid";

        var key = fileKey(file);
        var previewShell = document.createElement("div");
        previewShell.className = "file-preview-shell";

        var thumbnail = thumbnailByKey[key];
        var isLoadingThumbnail = Boolean(thumbnailLoadingByKey[key]);

        if (thumbnail) {
            var image = document.createElement("img");
            image.className = "file-preview-image";
            image.src = thumbnail;
            image.alt = file.name + " onizleme";
            previewShell.appendChild(image);
        } else {
            if (!isLoadingThumbnail) {
                requestThumbnail(file);
                isLoadingThumbnail = true;
            }

            var fallback = document.createElement("div");
            fallback.className = "file-preview-fallback";
            fallback.textContent = isLoadingThumbnail ? "Onizleme hazirlaniyor..." : extensionOf(file.name);
            previewShell.appendChild(fallback);
        }

        var meta = document.createElement("div");
        meta.className = "file-meta";

        var order = document.createElement("span");
        order.className = "file-order";
        order.textContent = "#" + String(index + 1);

        var name = document.createElement("span");
        name.className = "file-name";
        name.textContent = file.name;

        var size = document.createElement("span");
        size.className = "file-size";
        size.textContent = extensionOf(file.name) + " | " + formatSize(file.size);

        meta.appendChild(order);
        meta.appendChild(name);
        meta.appendChild(size);

        item.appendChild(previewShell);
        item.appendChild(meta);
        item.appendChild(createRemoveButton(file, index));
        return item;
    }

    function renderFiles() {
        fileList.innerHTML = "";
        fileList.setAttribute("data-view-mode", viewMode);

        selectedFiles.forEach(function (file, index) {
            var item = viewMode === "grid" ? createGridItem(file, index) : createListItem(file, index);
            fileList.appendChild(item);
        });

        fileCount.textContent = "Secili dosya: " + selectedFiles.length;
        emptyState.classList.toggle("is-hidden", selectedFiles.length > 0);
    }

    function addFiles(filesToAdd) {
        var existing = {};
        selectedFiles.forEach(function (file) {
            existing[fileKey(file)] = true;
        });

        Array.from(filesToAdd).forEach(function (file) {
            var key = fileKey(file);
            if (!existing[key]) {
                selectedFiles.push(file);
                existing[key] = true;
                if (viewMode === "grid") {
                    requestThumbnail(file);
                }
            }
        });

        syncInputFiles();
        renderFiles();
    }

    function removeFileAt(index) {
        if (index < 0 || index >= selectedFiles.length) {
            return;
        }
        var removedFile = selectedFiles[index];
        var key = fileKey(removedFile);
        delete thumbnailByKey[key];
        delete thumbnailLoadingByKey[key];
        selectedFiles.splice(index, 1);
        syncInputFiles();
        renderFiles();
    }

    function openFilePicker() {
        // Clear native value before opening so selecting the same file triggers change event.
        fileInput.value = "";
        fileInput.click();
    }

    pickButton.addEventListener("click", openFilePicker);

    fileInput.addEventListener("change", function () {
        addFiles(fileInput.files);
    });

    fileList.addEventListener("click", function (event) {
        var target = event.target;
        if (!(target instanceof HTMLElement)) {
            return;
        }
        var button = target.closest("[data-remove-index]");
        if (!(button instanceof HTMLElement)) {
            return;
        }
        event.preventDefault();
        event.stopPropagation();

        var indexText = button.getAttribute("data-remove-index");
        if (indexText === null) {
            return;
        }
        removeFileAt(Number(indexText));
    });

    dropzone.addEventListener("click", openFilePicker);

    dropzone.addEventListener("dragover", function (event) {
        event.preventDefault();
        dropzone.classList.add("active");
    });

    dropzone.addEventListener("dragleave", function () {
        dropzone.classList.remove("active");
    });

    dropzone.addEventListener("drop", function (event) {
        event.preventDefault();
        dropzone.classList.remove("active");

        if (!event.dataTransfer || !event.dataTransfer.files) {
            return;
        }

        addFiles(event.dataTransfer.files);
    });

    viewModeButtons.forEach(function (button) {
        button.addEventListener("click", function () {
            var mode = button.getAttribute("data-view-mode");
            if (mode) {
                setViewMode(mode);
            }
        });
    });

    form.addEventListener("submit", function () {
        syncInputFiles();
    });

    if (nativeInputWrapper) {
        nativeInputWrapper.classList.add("is-hidden");
    }

    restoreViewMode();
    setViewMode(viewMode);
    renderFiles();
})();
