(function () {
    "use strict";

    if (!document.querySelector("[data-live-jobs]")) {
        return;
    }

    var STATUS_CLASSES = ["status-pending", "status-running", "status-completed", "status-failed"];
    var STATUS_LABELS = {
        pending: "PENDING",
        running: "RUNNING",
        completed: "COMPLETED",
        failed: "FAILED"
    };

    var reconnectDelayMs = 1000;
    var maxReconnectDelayMs = 10000;

    function setHidden(element, hidden) {
        if (!element) {
            return;
        }
        element.classList.toggle("is-hidden", hidden);
    }

    function setStatusBadge(statusElement, status) {
        if (!statusElement) {
            return;
        }

        STATUS_CLASSES.forEach(function (className) {
            statusElement.classList.remove(className);
        });
        statusElement.classList.add("status-" + status);
        statusElement.textContent = STATUS_LABELS[status] || String(status || "").toUpperCase();
    }

    function truncateText(value, maxLength) {
        if (value.length <= maxLength) {
            return value;
        }
        return value.slice(0, maxLength - 3) + "...";
    }

    function updateDashboardCard(payload) {
        var card = document.querySelector('[data-job-card-id="' + payload.job_id + '"]');
        if (!card) {
            return;
        }

        var statusElement = card.querySelector("[data-job-status]");
        var errorElement = card.querySelector("[data-job-error]");
        setStatusBadge(statusElement, payload.status);

        var errorMessage = String(payload.error_message || "");
        if (errorElement) {
            errorElement.textContent = truncateText(errorMessage, 120);
        }
        setHidden(errorElement, errorMessage.length === 0);
    }

    function updateJobDetail(payload) {
        var detailRoot = document.querySelector('[data-job-detail-id="' + payload.job_id + '"]');
        if (!detailRoot) {
            return;
        }

        var statusElement = detailRoot.querySelector("[data-job-status]");
        var errorElement = detailRoot.querySelector("[data-job-error]");
        var progressElement = detailRoot.querySelector("[data-job-progress]");
        var downloadElement = detailRoot.querySelector("[data-job-download]");
        var retryForm = detailRoot.querySelector("[data-job-retry-form]");

        setStatusBadge(statusElement, payload.status);

        var errorMessage = String(payload.error_message || "");
        if (errorElement) {
            errorElement.textContent = errorMessage;
        }
        setHidden(errorElement, errorMessage.length === 0);

        var isRunningState = payload.status === "pending" || payload.status === "running";
        setHidden(progressElement, !isRunningState);

        var hasOutput = Boolean(payload.has_output && payload.output_url);
        if (hasOutput && downloadElement) {
            downloadElement.setAttribute("href", payload.output_url);
        }
        setHidden(downloadElement, !hasOutput);
        setHidden(retryForm, payload.status !== "failed" || hasOutput);
    }

    function handlePayload(payload) {
        if (!payload || !payload.job_id) {
            return;
        }
        updateDashboardCard(payload);
        updateJobDetail(payload);
    }

    function connectWebSocket() {
        var protocol = window.location.protocol === "https:" ? "wss" : "ws";
        var socket = new WebSocket(protocol + "://" + window.location.host + "/ws/jobs/");

        socket.onopen = function () {
            reconnectDelayMs = 1000;
        };

        socket.onmessage = function (event) {
            try {
                handlePayload(JSON.parse(event.data));
            } catch (error) {
                console.error("Invalid websocket payload", error);
            }
        };

        socket.onerror = function () {
            socket.close();
        };

        socket.onclose = function () {
            window.setTimeout(connectWebSocket, reconnectDelayMs);
            reconnectDelayMs = Math.min(maxReconnectDelayMs, reconnectDelayMs * 2);
        };
    }

    connectWebSocket();
})();

