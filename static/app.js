// Gifomatic - Frontend JavaScript

// State
let currentJobId = null;
let selectedGifs = new Set();
let allGifs = [];
let mergedGifs = [];
let currentTab = 'original';
let lightboxIndex = 0;
let lightboxGifs = [];
let currentEventSource = null;
let isProcessing = false;

// Crop state
let videoMetadata = null;  // {width, height, duration, fps}
let thumbnails = [];
let currentThumbnailIndex = 0;
let cropData = null;       // {x, y, w, h} in original video pixels
let isDrawingCrop = false;
let cropStartX = 0;
let cropStartY = 0;
let cropCanvas = null;
let cropCtx = null;
let currentThumbnailImg = null;

// Default settings
const defaultSettings = {
    maxDuration: 5,
    width: 480,
    fps: 10,
    threshold: 30
};

// Security: HTML escape function to prevent XSS
function escapeHtml(text) {
    if (text === null || text === undefined) {
        return '';
    }
    const div = document.createElement('div');
    div.textContent = String(text);
    return div.innerHTML;
}

// Security: Validate URL to prevent javascript: and data: injection
function isValidUrl(url) {
    if (!url || typeof url !== 'string') {
        return false;
    }
    // Only allow relative URLs starting with / or http(s) URLs to same origin
    if (url.startsWith('/')) {
        // Ensure no protocol injection via //
        return !url.startsWith('//');
    }
    try {
        const parsed = new URL(url, window.location.origin);
        return parsed.origin === window.location.origin;
    } catch {
        return false;
    }
}

// Security: Validate filename format
function isValidFilename(filename) {
    if (!filename || typeof filename !== 'string') {
        return false;
    }
    // Only allow alphanumeric, underscore, hyphen, and .gif extension
    return /^[a-zA-Z0-9_\-]+\.gif$/i.test(filename);
}

// Security: Sanitize filename for display
function sanitizeFilename(filename) {
    if (!isValidFilename(filename)) {
        return 'invalid_file.gif';
    }
    return escapeHtml(filename);
}

// Toast notification system
function showToast(message, type = 'success', duration = 3000) {
    // Remove any existing toast
    const existingToast = document.querySelector('.toast-notification');
    if (existingToast) {
        existingToast.remove();
    }

    // Create toast element
    const toast = document.createElement('div');
    toast.className = `toast-notification toast-${type}`;
    toast.textContent = message;

    // Add to body
    document.body.appendChild(toast);

    // Trigger animation
    requestAnimationFrame(() => {
        toast.classList.add('toast-visible');
    });

    // Auto-remove after duration
    setTimeout(() => {
        toast.classList.remove('toast-visible');
        setTimeout(() => {
            if (toast.parentNode) {
                toast.remove();
            }
        }, 300); // Wait for fade out animation
    }, duration);
}

// DOM Elements
const videoInput = document.getElementById('video-input');
const processBtn = document.getElementById('process-btn');
const uploadForm = document.getElementById('upload-form');
const fileNameDisplay = document.getElementById('file-name');
const progressSection = document.getElementById('progress-section');
const progressFill = document.getElementById('progress-fill');
const progressText = document.getElementById('progress-text');
const gifSection = document.getElementById('gif-section');
const gifGrid = document.getElementById('gif-grid');
const gifCount = document.getElementById('gif-count');
const actionBar = document.getElementById('action-bar');
const mergeBtn = document.getElementById('merge-btn');
const downloadSelectedBtn = document.getElementById('download-selected-btn');
const downloadAllBtn = document.getElementById('download-all-btn');
const selectAllBtn = document.getElementById('select-all-btn');
const unselectAllBtn = document.getElementById('unselect-all-btn');
const selectionInfo = document.getElementById('selection-info');
const tabOriginal = document.getElementById('tab-original');
const tabMerged = document.getElementById('tab-merged');
const originalContent = document.getElementById('original-content');
const mergedContent = document.getElementById('merged-content');
const mergedGrid = document.getElementById('merged-grid');
const mergedCountEl = document.getElementById('merged-count');
const noMergedMsg = document.getElementById('no-merged');

// Lightbox elements
const lightbox = document.getElementById('lightbox');
const lightboxImg = document.getElementById('lightbox-img');
const lightboxFilename = document.getElementById('lightbox-filename');
const lightboxCounter = document.getElementById('lightbox-counter');
const lightboxClose = document.querySelector('.lightbox-close');
const lightboxPrev = document.querySelector('.lightbox-prev');
const lightboxNext = document.querySelector('.lightbox-next');
const lightboxOverlay = document.querySelector('.lightbox-overlay');

// Previous jobs elements
const previousJobsSection = document.getElementById('previous-jobs');
const jobsList = document.getElementById('jobs-list');

// Crop elements
const cropSection = document.getElementById('crop-section');
const cropContainer = document.querySelector('.crop-container');
const cropCanvasEl = document.getElementById('crop-canvas');
const cropDimensions = document.getElementById('crop-dimensions');
const thumbnailContainers = document.querySelectorAll('.thumb-container');
const resetCropBtn = document.getElementById('reset-crop-btn');
const skipCropBtn = document.getElementById('skip-crop-btn');
const confirmCropBtn = document.getElementById('confirm-crop-btn');

// Settings elements
const settingsSection = document.querySelector('.settings-section');
const settingsToggle = document.getElementById('settings-toggle');
const settingsHeader = document.querySelector('.settings-header');
const maxDurationInput = document.getElementById('max-duration');
const maxDurationValue = document.getElementById('max-duration-value');
const gifWidthSelect = document.getElementById('gif-width');
const gifFpsSelect = document.getElementById('gif-fps');
const sceneThresholdInput = document.getElementById('scene-threshold');
const thresholdValue = document.getElementById('threshold-value');
const presetButtons = document.querySelectorAll('.preset-btn');

// Event Listeners
videoInput.addEventListener('change', handleFileSelect);
uploadForm.addEventListener('submit', handleUpload);
mergeBtn.addEventListener('click', handleMerge);
downloadSelectedBtn.addEventListener('click', downloadSelected);
downloadAllBtn.addEventListener('click', downloadAll);
selectAllBtn.addEventListener('click', selectAll);
unselectAllBtn.addEventListener('click', unselectAll);
tabOriginal.addEventListener('click', () => switchTab('original'));
tabMerged.addEventListener('click', () => switchTab('merged'));

// Lightbox events
lightboxClose.addEventListener('click', closeLightbox);
lightboxOverlay.addEventListener('click', closeLightbox);
lightboxPrev.addEventListener('click', () => navigateLightbox(-1));
lightboxNext.addEventListener('click', () => navigateLightbox(1));
document.addEventListener('keydown', handleLightboxKeys);

// Settings events
settingsHeader.addEventListener('click', toggleSettings);
maxDurationInput.addEventListener('input', updateDurationDisplay);
sceneThresholdInput.addEventListener('input', updateThresholdDisplay);
presetButtons.forEach(btn => btn.addEventListener('click', applyPreset));

// Crop events
thumbnailContainers.forEach(container => {
    container.addEventListener('click', () => {
        const index = parseInt(container.dataset.index, 10);
        selectThumbnail(index);
    });
});
resetCropBtn.addEventListener('click', resetCrop);
skipCropBtn.addEventListener('click', skipCropAndProcess);
confirmCropBtn.addEventListener('click', confirmCropAndProcess);

// Load existing jobs on page load
loadExistingJobs();
initSettings();

function handleFileSelect(e) {
    const file = e.target.files[0];
    if (file) {
        // Sanitize filename for display
        fileNameDisplay.textContent = file.name;
        processBtn.disabled = false;
    } else {
        fileNameDisplay.textContent = '';
        processBtn.disabled = true;
    }
}

// Settings functions
function initSettings() {
    updateDurationDisplay();
    updateThresholdDisplay();
}

function toggleSettings() {
    settingsSection.classList.toggle('collapsed');
}

function updateDurationDisplay() {
    maxDurationValue.textContent = maxDurationInput.value + 's';
}

function updateThresholdDisplay() {
    thresholdValue.textContent = sceneThresholdInput.value;
}

function applyPreset(e) {
    const preset = e.target.dataset.preset;

    switch (preset) {
        case 'small':
            maxDurationInput.value = 3;
            gifWidthSelect.value = '320';
            gifFpsSelect.value = '5';
            sceneThresholdInput.value = 30;
            break;
        case 'balanced':
            maxDurationInput.value = 5;
            gifWidthSelect.value = '480';
            gifFpsSelect.value = '10';
            sceneThresholdInput.value = 30;
            break;
        case 'hd':
            maxDurationInput.value = 5;
            gifWidthSelect.value = '720';
            gifFpsSelect.value = '15';
            sceneThresholdInput.value = 25;
            break;
        case 'max':
            maxDurationInput.value = 10;
            gifWidthSelect.value = '1080';
            gifFpsSelect.value = '24';
            sceneThresholdInput.value = 20;
            break;
    }

    updateDurationDisplay();
    updateThresholdDisplay();
}

function getSettings() {
    return {
        max_duration: maxDurationInput.value,
        width: gifWidthSelect.value,
        fps: gifFpsSelect.value,
        threshold: sceneThresholdInput.value
    };
}

async function handleUpload(e) {
    e.preventDefault();

    const file = videoInput.files[0];
    if (!file) return;

    // Reset state
    resetState();

    // Show progress
    progressSection.classList.remove('hidden');
    processBtn.disabled = true;
    progressText.textContent = 'Uploading video...';

    // Create form data
    const formData = new FormData();
    formData.append('video', file);

    try {
        // Upload video and get preview data
        const response = await fetch('/upload-preview', {
            method: 'POST',
            body: formData
        });

        const data = await response.json();

        if (data.error) {
            showError(data.error);
            return;
        }

        // Validate job_id format (UUID)
        if (!data.job_id || !/^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i.test(data.job_id)) {
            showError('Invalid response from server');
            return;
        }

        currentJobId = data.job_id;
        videoMetadata = data.video;
        thumbnails = data.thumbnails || [];

        // Hide progress, show crop UI
        progressSection.classList.add('hidden');
        showCropUI();

    } catch (error) {
        showError('Failed to upload video: ' + escapeHtml(error.message));
    }
}

function loadCachedGifs(gifs, merged = []) {
    // Validate and add all cached GIFs to grid
    for (const gif of gifs) {
        if (isValidUrl(gif.url) && isValidFilename(gif.filename)) {
            addGifToGrid(gif);
        }
    }

    // Add merged GIFs if any
    if (merged && merged.length > 0) {
        for (let i = 0; i < merged.length; i++) {
            if (isValidUrl(merged[i].url) && isValidFilename(merged[i].filename)) {
                mergedGifs.push(merged[i]);
                addMergedGifToGrid(merged[i], i);
            }
        }
        updateMergedCount();
    }

    isProcessing = false;
    handleComplete(allGifs.length);
    updateProcessingUI();
    progressText.textContent = `Loaded ${allGifs.length} GIFs` + (mergedGifs.length > 0 ? ` + ${mergedGifs.length} merged` : '') + ' from cache';
}

function startEventStream(jobId) {
    // Validate jobId format before creating EventSource
    if (!/^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i.test(jobId)) {
        showError('Invalid job ID');
        return;
    }

    isProcessing = true;
    updateProcessingUI();

    const eventSource = new EventSource(`/stream/${encodeURIComponent(jobId)}`);
    currentEventSource = eventSource;

    eventSource.onmessage = function(event) {
        let data;
        try {
            data = JSON.parse(event.data);
        } catch {
            return; // Ignore malformed data
        }

        switch (data.type) {
            case 'gif':
                // Validate data before adding
                if (isValidUrl(data.url) && isValidFilename(data.filename)) {
                    addGifToGrid(data);
                }
                break;

            case 'complete':
                handleComplete(data.total);
                eventSource.close();
                currentEventSource = null;
                isProcessing = false;
                updateProcessingUI();
                break;

            case 'cancelled':
                handleCancelled();
                eventSource.close();
                currentEventSource = null;
                isProcessing = false;
                updateProcessingUI();
                break;

            case 'error':
                showError(data.message || 'Processing failed');
                eventSource.close();
                currentEventSource = null;
                isProcessing = false;
                updateProcessingUI();
                break;

            case 'keepalive':
                // Ignore keepalive
                break;
        }
    };

    eventSource.onerror = function() {
        // Connection error - may be normal if processing is done
        eventSource.close();
        currentEventSource = null;
        isProcessing = false;
        updateProcessingUI();
    };
}

function addGifToGrid(data) {
    const { url, filename } = data;

    // Validate inputs
    if (!isValidUrl(url) || !isValidFilename(filename)) {
        console.warn('Invalid GIF data received');
        return;
    }

    allGifs.push({ url, filename });
    const gifIndex = allGifs.length - 1;

    // Create GIF element using safe DOM manipulation
    const gifItem = document.createElement('div');
    gifItem.className = 'gif-item';
    gifItem.dataset.filename = filename;
    gifItem.dataset.index = gifIndex;

    // Create image
    const img = document.createElement('img');
    img.src = url;
    img.alt = sanitizeFilename(filename);
    img.loading = 'lazy';

    // Create action buttons container
    const actions = document.createElement('div');
    actions.className = 'gif-actions';

    // Create download button
    const downloadBtn = document.createElement('a');
    downloadBtn.href = url;
    downloadBtn.download = filename;
    downloadBtn.className = 'gif-action-btn gif-download';
    downloadBtn.title = 'Download';
    downloadBtn.onclick = function(e) { e.stopPropagation(); };
    downloadBtn.innerHTML = '<svg viewBox="0 0 24 24"><path d="M19 9h-4V3H9v6H5l7 7 7-7zM5 18v2h14v-2H5z"/></svg>';

    // Create grayscale button
    const grayscaleBtn = document.createElement('button');
    grayscaleBtn.className = 'gif-action-btn gif-grayscale';
    grayscaleBtn.title = 'Convert to Grayscale';
    grayscaleBtn.innerHTML = '<svg viewBox="0 0 24 24"><path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm0 18c-4.41 0-8-3.59-8-8s3.59-8 8-8 8 3.59 8 8-3.59 8-8 8zm0-14c-3.31 0-6 2.69-6 6s2.69 6 6 6 6-2.69 6-6-2.69-6-6-6z"/></svg>';
    grayscaleBtn.onclick = function(e) {
        e.stopPropagation();
        convertToGrayscale(filename);
    };

    // Create delete button
    const deleteBtn = document.createElement('button');
    deleteBtn.className = 'gif-action-btn gif-delete';
    deleteBtn.title = 'Delete';
    deleteBtn.innerHTML = '<svg viewBox="0 0 24 24"><path d="M6 19c0 1.1.9 2 2 2h8c1.1 0 2-.9 2-2V7H6v12zM19 4h-3.5l-1-1h-5l-1 1H5v2h14V4z"/></svg>';
    deleteBtn.onclick = function(e) {
        e.stopPropagation();
        deleteGif(filename, gifItem);
    };

    actions.appendChild(downloadBtn);
    actions.appendChild(grayscaleBtn);
    actions.appendChild(deleteBtn);

    // Create overlay
    const overlay = document.createElement('div');
    overlay.className = 'gif-overlay';
    const checkmark = document.createElement('div');
    checkmark.className = 'checkmark';
    checkmark.textContent = '\u2713';
    overlay.appendChild(checkmark);

    // Create label
    const label = document.createElement('div');
    label.className = 'gif-label';
    label.textContent = filename; // textContent is safe from XSS

    // Assemble
    gifItem.appendChild(img);
    gifItem.appendChild(actions);
    gifItem.appendChild(overlay);
    gifItem.appendChild(label);

    // Click on image opens lightbox
    img.addEventListener('click', (e) => {
        e.stopPropagation();
        openLightbox(gifIndex, 'original');
    });

    // Click on item (not image) toggles selection
    gifItem.addEventListener('click', () => toggleSelection(gifItem, filename));

    gifGrid.appendChild(gifItem);

    // Update count and show action bar
    updateGifCount();
    updateActionBar();
    progressText.textContent = `Generated ${allGifs.length} GIFs...`;
    progressFill.style.width = '50%'; // Indeterminate progress
}

function toggleSelection(element, filename) {
    if (!isValidFilename(filename)) {
        return;
    }

    if (selectedGifs.has(filename)) {
        selectedGifs.delete(filename);
        element.classList.remove('selected');
    } else {
        selectedGifs.add(filename);
        element.classList.add('selected');
    }

    updateSelectionUI();
}

function selectAll() {
    const gifItems = gifGrid.querySelectorAll('.gif-item');
    gifItems.forEach(item => {
        const filename = item.dataset.filename;
        if (isValidFilename(filename)) {
            selectedGifs.add(filename);
            item.classList.add('selected');
        }
    });
    updateSelectionUI();
}

function unselectAll() {
    const gifItems = gifGrid.querySelectorAll('.gif-item');
    gifItems.forEach(item => {
        item.classList.remove('selected');
    });
    selectedGifs.clear();
    updateSelectionUI();
}

function updateSelectionUI() {
    updateActionBar();
}

function updateActionBar() {
    const selectedCount = selectedGifs.size;
    const totalCount = allGifs.length;
    const mergedCount = mergedGifs.length;

    // Show action bar if we have GIFs
    if (totalCount > 0 || mergedCount > 0) {
        actionBar.classList.remove('hidden');
        actionBar.classList.add('visible');
    } else {
        actionBar.classList.add('hidden');
        actionBar.classList.remove('visible');
    }

    // Update based on current tab
    if (currentTab === 'original') {
        if (selectedCount > 0) {
            selectionInfo.textContent = `${selectedCount} selected`;
        } else {
            selectionInfo.textContent = `${totalCount} GIFs`;
        }
        // Show all buttons for original tab
        selectAllBtn.style.display = '';
        unselectAllBtn.style.display = '';
        downloadSelectedBtn.style.display = '';
        mergeBtn.style.display = '';

        // Enable/disable based on state
        selectAllBtn.disabled = totalCount === 0 || selectedCount === totalCount;
        unselectAllBtn.disabled = selectedCount === 0;
        downloadSelectedBtn.disabled = selectedCount === 0;
        downloadAllBtn.disabled = totalCount === 0;
        mergeBtn.disabled = selectedCount < 2;
    } else {
        selectionInfo.textContent = `${mergedCount} merged GIFs`;
        // Hide selection buttons for merged tab
        selectAllBtn.style.display = 'none';
        unselectAllBtn.style.display = 'none';
        downloadSelectedBtn.style.display = 'none';
        mergeBtn.style.display = 'none';
        downloadAllBtn.disabled = mergedCount === 0;
    }
}

function updateGifCount() {
    const count = allGifs.length;
    gifCount.textContent = `${count} GIF${count !== 1 ? 's' : ''}`;
}

function handleComplete(total) {
    progressFill.style.width = '100%';
    progressText.textContent = `Complete! Generated ${total} GIFs`;
    processBtn.disabled = false;

    // Keep progress section visible with Reprocess button
    // Hide the progress bar but keep the section
    setTimeout(() => {
        progressFill.style.width = '0%';
        progressText.textContent = 'Adjust settings above and click Reprocess to regenerate GIFs';
    }, 2000);
}

function handleCancelled() {
    progressFill.style.width = '0%';
    progressText.textContent = `Cancelled. ${allGifs.length} GIFs generated.`;
    processBtn.disabled = false;
    showToast('Processing cancelled', 'info');
}

function updateProcessingUI() {
    const cancelBtn = document.getElementById('cancel-btn');
    const reprocessBtn = document.getElementById('reprocess-btn');

    if (cancelBtn) {
        cancelBtn.style.display = isProcessing ? '' : 'none';
        cancelBtn.disabled = !isProcessing;
    }

    if (reprocessBtn) {
        // Show reprocess button when we have a job and not currently processing
        reprocessBtn.style.display = (currentJobId && !isProcessing) ? '' : 'none';
    }
}

async function cancelJob() {
    if (!currentJobId || !isProcessing) {
        return;
    }

    try {
        const response = await fetch(`/cancel/${encodeURIComponent(currentJobId)}`, {
            method: 'POST'
        });

        const data = await response.json();

        if (data.error) {
            showToast('Cancel failed: ' + data.error, 'error');
            return;
        }

        showToast('Cancelling...', 'info');

    } catch (error) {
        showToast('Cancel failed: ' + error.message, 'error');
    }
}

async function reprocessJob() {
    if (!currentJobId || isProcessing) {
        return;
    }

    // Get current settings
    const settings = getSettings();

    // Clear current UI
    gifGrid.innerHTML = '';
    mergedGrid.innerHTML = '';
    allGifs = [];
    mergedGifs = [];
    selectedGifs.clear();
    noMergedMsg.style.display = 'block';
    updateGifCount();
    updateMergedCount();
    updateActionBar();

    // Show progress
    progressSection.classList.remove('hidden');
    gifSection.classList.remove('hidden');
    progressFill.style.width = '0%';
    progressText.textContent = 'Reprocessing with new settings...';

    try {
        const response = await fetch('/reprocess', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                job_id: currentJobId,
                max_duration: settings.max_duration,
                width: settings.width,
                fps: settings.fps,
                threshold: settings.threshold
            })
        });

        const data = await response.json();

        if (data.error) {
            showToast('Reprocess failed: ' + data.error, 'error');
            progressSection.classList.add('hidden');
            return;
        }

        showToast('Reprocessing started!', 'success');

        // Start SSE connection
        startEventStream(currentJobId);

    } catch (error) {
        showToast('Reprocess failed: ' + error.message, 'error');
        progressSection.classList.add('hidden');
    }
}

async function handleMerge() {
    if (selectedGifs.size < 2) {
        showToast('Please select at least 2 GIFs to merge', 'error');
        return;
    }

    if (selectedGifs.size > 20) {
        showToast('Maximum 20 GIFs can be merged at once', 'error');
        return;
    }

    // Validate all selected filenames
    const validSelected = Array.from(selectedGifs).filter(isValidFilename);
    if (validSelected.length < 2) {
        showToast('Invalid selection', 'error');
        return;
    }

    mergeBtn.disabled = true;
    mergeBtn.textContent = 'Merging...';

    try {
        const response = await fetch('/merge', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                job_id: currentJobId,
                selected: validSelected
            })
        });

        const data = await response.json();

        if (data.error) {
            showToast('Merge failed: ' + data.error, 'error');
            return;
        }

        // Validate response
        if (!isValidUrl(data.url)) {
            showToast('Invalid response from server', 'error');
            return;
        }

        // Show merged result (adds to merged tab without switching)
        showMergedResult(data.url);

        // Show success toast
        showToast('GIFs merged successfully! Check Merged tab.', 'success');

        // Deselect all after successful merge
        unselectAll();

    } catch (error) {
        showToast('Merge failed: ' + error.message, 'error');
    } finally {
        mergeBtn.disabled = false;
        mergeBtn.textContent = 'Merge Selected';
        updateActionBar();
    }
}

function showMergedResult(url) {
    if (!isValidUrl(url)) {
        console.warn('Invalid merged URL');
        return;
    }

    const filename = url.split('/').pop();
    if (!isValidFilename(filename)) {
        console.warn('Invalid merged filename');
        return;
    }

    mergedGifs.push({ url, filename });

    // Add to merged grid
    addMergedGifToGrid({ url, filename });

    // Update merged count
    updateMergedCount();

    // Update action bar to reflect new merged count
    updateActionBar();
}

function addMergedGifToGrid(data, index = null) {
    const { url, filename } = data;

    // Validate inputs
    if (!isValidUrl(url) || !isValidFilename(filename)) {
        console.warn('Invalid merged GIF data');
        return;
    }

    // Hide empty message
    noMergedMsg.style.display = 'none';

    // Create GIF element using safe DOM manipulation
    const gifItem = document.createElement('div');
    gifItem.className = 'gif-item';
    gifItem.dataset.filename = filename;

    const idx = index !== null ? index : mergedGifs.length - 1;

    // Create image
    const img = document.createElement('img');
    img.src = url;
    img.alt = sanitizeFilename(filename);
    img.loading = 'lazy';

    // Create action buttons container
    const actions = document.createElement('div');
    actions.className = 'gif-actions';

    // Create download button
    const downloadBtn = document.createElement('a');
    downloadBtn.href = url;
    downloadBtn.download = filename;
    downloadBtn.className = 'gif-action-btn gif-download';
    downloadBtn.title = 'Download';
    downloadBtn.onclick = function(e) { e.stopPropagation(); };
    downloadBtn.innerHTML = '<svg viewBox="0 0 24 24"><path d="M19 9h-4V3H9v6H5l7 7 7-7zM5 18v2h14v-2H5z"/></svg>';

    // Create grayscale button
    const grayscaleBtn = document.createElement('button');
    grayscaleBtn.className = 'gif-action-btn gif-grayscale';
    grayscaleBtn.title = 'Convert to Grayscale';
    grayscaleBtn.innerHTML = '<svg viewBox="0 0 24 24"><path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm0 18c-4.41 0-8-3.59-8-8s3.59-8 8-8 8 3.59 8 8-3.59 8-8 8zm0-14c-3.31 0-6 2.69-6 6s2.69 6 6 6 6-2.69 6-6-2.69-6-6-6z"/></svg>';
    grayscaleBtn.onclick = function(e) {
        e.stopPropagation();
        convertToGrayscale(filename, true);
    };

    // Create delete button
    const deleteBtn = document.createElement('button');
    deleteBtn.className = 'gif-action-btn gif-delete';
    deleteBtn.title = 'Delete';
    deleteBtn.innerHTML = '<svg viewBox="0 0 24 24"><path d="M6 19c0 1.1.9 2 2 2h8c1.1 0 2-.9 2-2V7H6v12zM19 4h-3.5l-1-1h-5l-1 1H5v2h14V4z"/></svg>';
    deleteBtn.onclick = function(e) {
        e.stopPropagation();
        deleteMergedGif(filename, gifItem);
    };

    actions.appendChild(downloadBtn);
    actions.appendChild(grayscaleBtn);
    actions.appendChild(deleteBtn);

    // Create label
    const label = document.createElement('div');
    label.className = 'gif-label';
    label.textContent = filename; // textContent is safe from XSS

    // Assemble
    gifItem.appendChild(img);
    gifItem.appendChild(actions);
    gifItem.appendChild(label);

    // Click on image opens lightbox
    img.addEventListener('click', (e) => {
        e.stopPropagation();
        openLightbox(idx, 'merged');
    });

    mergedGrid.appendChild(gifItem);
}

function switchTab(tab) {
    currentTab = tab;

    // Update tab buttons
    tabOriginal.classList.toggle('active', tab === 'original');
    tabMerged.classList.toggle('active', tab === 'merged');

    // Update tab content
    originalContent.classList.toggle('active', tab === 'original');
    mergedContent.classList.toggle('active', tab === 'merged');

    // Update action bar based on current tab
    updateActionBar();
}

function updateMergedCount() {
    mergedCountEl.textContent = mergedGifs.length;
}

async function downloadSelected() {
    if (selectedGifs.size === 0) return;

    // Download each selected GIF
    for (const filename of selectedGifs) {
        if (!isValidFilename(filename)) continue;

        const gif = allGifs.find(g => g.filename === filename);
        if (gif && isValidUrl(gif.url)) {
            downloadFile(gif.url, gif.filename);
            await sleep(300); // Small delay between downloads
        }
    }
}

async function downloadAll() {
    const gifsToDownload = currentTab === 'merged' ? mergedGifs : allGifs;

    if (gifsToDownload.length === 0) return;

    // Download all GIFs
    for (const gif of gifsToDownload) {
        if (isValidUrl(gif.url) && isValidFilename(gif.filename)) {
            downloadFile(gif.url, gif.filename);
            await sleep(300); // Small delay between downloads
        }
    }
}

function downloadFile(url, filename) {
    // Validate before download
    if (!isValidUrl(url) || !isValidFilename(filename)) {
        console.warn('Invalid download parameters');
        return;
    }

    const a = document.createElement('a');
    a.href = url;
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
}

function sleep(ms) {
    return new Promise(resolve => setTimeout(resolve, ms));
}

// Lightbox functions
function openLightbox(index, type = 'original') {
    lightboxGifs = type === 'merged' ? mergedGifs : allGifs;

    // Validate index
    if (index < 0 || index >= lightboxGifs.length) {
        return;
    }

    lightboxIndex = index;
    updateLightbox();
    lightbox.classList.remove('hidden');
    document.body.style.overflow = 'hidden';
}

function closeLightbox() {
    lightbox.classList.add('hidden');
    document.body.style.overflow = '';
}

function navigateLightbox(direction) {
    const newIndex = lightboxIndex + direction;
    if (newIndex >= 0 && newIndex < lightboxGifs.length) {
        lightboxIndex = newIndex;
        updateLightbox();
    }
}

function updateLightbox() {
    const gif = lightboxGifs[lightboxIndex];
    if (!gif) return;

    // Validate before setting
    if (isValidUrl(gif.url)) {
        lightboxImg.src = gif.url;
    }
    if (isValidFilename(gif.filename)) {
        lightboxFilename.textContent = gif.filename; // textContent is safe
    }
    lightboxCounter.textContent = `${lightboxIndex + 1} / ${lightboxGifs.length}`;

    // Update nav button states
    lightboxPrev.disabled = lightboxIndex === 0;
    lightboxNext.disabled = lightboxIndex === lightboxGifs.length - 1;
}

function handleLightboxKeys(e) {
    if (lightbox.classList.contains('hidden')) return;

    switch (e.key) {
        case 'Escape':
            closeLightbox();
            break;
        case 'ArrowLeft':
            navigateLightbox(-1);
            break;
        case 'ArrowRight':
            navigateLightbox(1);
            break;
    }
}

function resetState() {
    // Close any existing event source
    if (currentEventSource) {
        currentEventSource.close();
        currentEventSource = null;
    }

    currentJobId = null;
    selectedGifs.clear();
    allGifs = [];
    mergedGifs = [];
    currentTab = 'original';
    isProcessing = false;

    // Reset crop state
    videoMetadata = null;
    thumbnails = [];
    currentThumbnailIndex = 0;
    cropData = null;
    isDrawingCrop = false;
    currentThumbnailImg = null;

    gifGrid.innerHTML = '';
    mergedGrid.innerHTML = '';

    progressFill.style.width = '0%';
    progressSection.classList.add('hidden');
    cropSection.classList.add('hidden');

    actionBar.classList.add('hidden');
    actionBar.classList.remove('visible');

    // Reset tabs
    switchTab('original');
    noMergedMsg.style.display = 'block';

    updateGifCount();
    updateMergedCount();
    updateProcessingUI();
}

function showError(message) {
    // Sanitize message for display
    const safeMessage = escapeHtml(message);
    progressText.textContent = 'Error: ' + message; // textContent is safe
    progressFill.style.width = '0%';
    progressFill.style.background = '#e74c3c';
    processBtn.disabled = false;

    setTimeout(() => {
        progressFill.style.background = '';
    }, 3000);
}

async function loadExistingJobs() {
    try {
        const response = await fetch('/jobs');
        const data = await response.json();

        if (data.jobs && data.jobs.length > 0) {
            previousJobsSection.classList.remove('hidden');
            jobsList.innerHTML = '';

            for (const job of data.jobs) {
                // Validate job_id format (UUID)
                if (!/^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i.test(job.job_id)) {
                    continue;
                }

                const jobItem = document.createElement('div');
                jobItem.className = 'job-item';

                // Use textContent for safe rendering
                const jobIdSpan = document.createElement('span');
                jobIdSpan.textContent = job.job_id.substring(0, 8) + '... ';

                const countSpan = document.createElement('span');
                countSpan.className = 'job-count';
                countSpan.textContent = `(${parseInt(job.gif_count, 10) || 0} GIFs)`;

                jobItem.appendChild(jobIdSpan);
                jobItem.appendChild(countSpan);

                // Store job_id in closure, not in DOM attribute to prevent tampering
                const safeJobId = job.job_id;
                jobItem.addEventListener('click', () => loadExistingJob(safeJobId));

                jobsList.appendChild(jobItem);
            }
        }
    } catch (error) {
        console.error('Failed to load existing jobs:', error);
    }
}

async function loadExistingJob(jobId) {
    // Validate jobId format
    if (!/^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i.test(jobId)) {
        showError('Invalid job ID');
        return;
    }

    resetState();
    gifSection.classList.remove('hidden');
    progressSection.classList.remove('hidden');
    progressText.textContent = 'Loading existing job...';

    try {
        const response = await fetch(`/load/${encodeURIComponent(jobId)}`);
        const data = await response.json();

        if (data.error) {
            showError(data.error);
            return;
        }

        // Validate returned job_id
        if (!data.job_id || !/^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i.test(data.job_id)) {
            showError('Invalid response from server');
            return;
        }

        currentJobId = data.job_id;
        loadCachedGifs(data.gifs, data.merged || []);

    } catch (error) {
        showError('Failed to load job: ' + escapeHtml(error.message));
    }
}

// Convert GIF to grayscale
async function convertToGrayscale(filename, isMerged = false) {
    if (!currentJobId || !isValidFilename(filename)) {
        return;
    }

    try {
        const response = await fetch('/grayscale', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                job_id: currentJobId,
                filename: filename
            })
        });

        const data = await response.json();

        if (data.error) {
            showToast('Grayscale failed: ' + data.error, 'error');
            return;
        }

        // Validate response
        if (!isValidUrl(data.url) || !isValidFilename(data.filename)) {
            showToast('Invalid response from server', 'error');
            return;
        }

        // Add the grayscale GIF to the appropriate list
        if (isMerged) {
            mergedGifs.push({ url: data.url, filename: data.filename });
            addMergedGifToGrid({ url: data.url, filename: data.filename });
            updateMergedCount();
        } else {
            allGifs.push({ url: data.url, filename: data.filename });
            addGifToGrid({ url: data.url, filename: data.filename });
            updateGifCount();
        }

        // Show success toast
        showToast('Grayscale created!', 'success');

    } catch (error) {
        showToast('Grayscale failed: ' + error.message, 'error');
    }
}

// Delete a GIF
async function deleteGif(filename, element) {
    if (!currentJobId || !isValidFilename(filename)) {
        return;
    }

    if (!confirm('Delete this GIF?')) {
        return;
    }

    try {
        const response = await fetch('/delete', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                job_id: currentJobId,
                filename: filename
            })
        });

        const data = await response.json();

        if (data.error) {
            alert('Delete failed: ' + escapeHtml(data.error));
            return;
        }

        // Remove from allGifs array
        const index = allGifs.findIndex(g => g.filename === filename);
        if (index > -1) {
            allGifs.splice(index, 1);
        }

        // Remove from selection if selected
        selectedGifs.delete(filename);

        // Remove from DOM
        element.remove();

        // Update counts
        updateGifCount();
        updateActionBar();

    } catch (error) {
        alert('Delete failed: ' + escapeHtml(error.message));
    }
}

// Delete a merged GIF
async function deleteMergedGif(filename, element) {
    if (!currentJobId || !isValidFilename(filename)) {
        return;
    }

    if (!confirm('Delete this merged GIF?')) {
        return;
    }

    try {
        const response = await fetch('/delete', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                job_id: currentJobId,
                filename: filename
            })
        });

        const data = await response.json();

        if (data.error) {
            alert('Delete failed: ' + escapeHtml(data.error));
            return;
        }

        // Remove from mergedGifs array
        const index = mergedGifs.findIndex(g => g.filename === filename);
        if (index > -1) {
            mergedGifs.splice(index, 1);
        }

        // Remove from DOM
        element.remove();

        // Update counts
        updateMergedCount();
        updateActionBar();

        // Show empty message if no merged GIFs left
        if (mergedGifs.length === 0) {
            noMergedMsg.style.display = 'block';
        }

    } catch (error) {
        alert('Delete failed: ' + escapeHtml(error.message));
    }
}

// =============================================================================
// CROP FUNCTIONALITY
// =============================================================================

function showCropUI() {
    if (!videoMetadata || !thumbnails.length) {
        showToast('No video data available', 'error');
        return;
    }

    // Show crop section
    cropSection.classList.remove('hidden');

    // Load thumbnails into the strip
    thumbnailContainers.forEach((container, index) => {
        const img = container.querySelector('.thumb');
        const timeSpan = container.querySelector('.thumb-time');

        if (thumbnails[index]) {
            img.src = thumbnails[index].url;
            const timestamp = thumbnails[index].timestamp;
            const minutes = Math.floor(timestamp / 60);
            const seconds = Math.floor(timestamp % 60);
            timeSpan.textContent = `${minutes}:${seconds.toString().padStart(2, '0')}`;
            container.style.display = '';
        } else {
            container.style.display = 'none';
        }
    });

    // Initialize crop canvas
    initCropCanvas();

    // Select first thumbnail
    selectThumbnail(0);

    // Update crop dimensions display
    updateCropDimensions();
}

function initCropCanvas() {
    cropCanvas = cropCanvasEl;
    cropCtx = cropCanvas.getContext('2d');

    // Set up canvas event listeners
    setupCropCanvasEvents();
}

function selectThumbnail(index) {
    if (index < 0 || index >= thumbnails.length) return;

    currentThumbnailIndex = index;

    // Update active state on thumbnail containers
    thumbnailContainers.forEach((container, i) => {
        if (i === index) {
            container.classList.add('active');
        } else {
            container.classList.remove('active');
        }
    });

    // Load the selected thumbnail into the canvas
    loadThumbnailImage(thumbnails[index].url);
}

function loadThumbnailImage(url) {
    const img = new Image();
    img.crossOrigin = 'anonymous';

    img.onload = function() {
        currentThumbnailImg = img;

        // Set canvas size to match image aspect ratio
        // Scale to fit container while maintaining aspect ratio
        const containerWidth = cropContainer.clientWidth;
        const scale = containerWidth / img.width;
        const displayHeight = img.height * scale;

        cropCanvas.width = containerWidth;
        cropCanvas.height = displayHeight;

        // Draw the image
        cropCtx.drawImage(img, 0, 0, cropCanvas.width, cropCanvas.height);

        // Redraw crop overlay if exists
        if (cropData) {
            drawCropOverlay();
        }
    };

    img.onerror = function() {
        console.error('Failed to load thumbnail:', url);
    };

    img.src = url;
}

function setupCropCanvasEvents() {
    // Mouse events
    cropCanvas.addEventListener('mousedown', startCrop);
    cropCanvas.addEventListener('mousemove', updateCrop);
    cropCanvas.addEventListener('mouseup', endCrop);
    cropCanvas.addEventListener('mouseleave', endCrop);

    // Touch events for mobile
    cropCanvas.addEventListener('touchstart', handleTouchStart, { passive: false });
    cropCanvas.addEventListener('touchmove', handleTouchMove, { passive: false });
    cropCanvas.addEventListener('touchend', handleTouchEnd);
}

function getCanvasCoords(e) {
    const rect = cropCanvas.getBoundingClientRect();
    let clientX, clientY;

    if (e.touches) {
        clientX = e.touches[0].clientX;
        clientY = e.touches[0].clientY;
    } else {
        clientX = e.clientX;
        clientY = e.clientY;
    }

    return {
        x: clientX - rect.left,
        y: clientY - rect.top
    };
}

function startCrop(e) {
    e.preventDefault();
    isDrawingCrop = true;

    const coords = getCanvasCoords(e);
    cropStartX = coords.x;
    cropStartY = coords.y;

    // Reset crop data
    cropData = null;
    cropContainer.classList.remove('has-crop');
}

function updateCrop(e) {
    if (!isDrawingCrop) return;
    e.preventDefault();

    const coords = getCanvasCoords(e);
    const currentX = coords.x;
    const currentY = coords.y;

    // Calculate rectangle
    const x = Math.min(cropStartX, currentX);
    const y = Math.min(cropStartY, currentY);
    const w = Math.abs(currentX - cropStartX);
    const h = Math.abs(currentY - cropStartY);

    // Store canvas coordinates temporarily
    cropData = { canvasX: x, canvasY: y, canvasW: w, canvasH: h };

    // Redraw
    drawCropOverlay();
}

function endCrop(e) {
    if (!isDrawingCrop) return;
    isDrawingCrop = false;

    // Finalize crop if valid size
    if (cropData && cropData.canvasW > 10 && cropData.canvasH > 10) {
        // Convert to original video pixels
        const originalCrop = convertToOriginalPixels(cropData);
        cropData = originalCrop;
        cropContainer.classList.add('has-crop');
        updateCropDimensions();
    } else {
        cropData = null;
        cropContainer.classList.remove('has-crop');
        updateCropDimensions();
        // Redraw without crop
        if (currentThumbnailImg) {
            cropCtx.drawImage(currentThumbnailImg, 0, 0, cropCanvas.width, cropCanvas.height);
        }
    }
}

// Touch event handlers
function handleTouchStart(e) {
    if (e.touches.length === 1) {
        startCrop(e);
    }
}

function handleTouchMove(e) {
    if (e.touches.length === 1) {
        updateCrop(e);
    }
}

function handleTouchEnd(e) {
    endCrop(e);
}

function drawCropOverlay() {
    if (!currentThumbnailImg || !cropCtx) return;

    // Clear and redraw image
    cropCtx.drawImage(currentThumbnailImg, 0, 0, cropCanvas.width, cropCanvas.height);

    if (!cropData) return;

    // Get canvas coordinates
    let x, y, w, h;

    if (cropData.canvasX !== undefined) {
        // Still drawing, use canvas coordinates
        x = cropData.canvasX;
        y = cropData.canvasY;
        w = cropData.canvasW;
        h = cropData.canvasH;
    } else {
        // Finalized crop, convert back to canvas coordinates for display
        const scale = cropCanvas.width / videoMetadata.width;
        x = cropData.x * scale;
        y = cropData.y * scale;
        w = cropData.w * scale;
        h = cropData.h * scale;
    }

    // Draw semi-transparent overlay on non-selected areas
    cropCtx.fillStyle = 'rgba(0, 0, 0, 0.5)';

    // Top
    cropCtx.fillRect(0, 0, cropCanvas.width, y);
    // Bottom
    cropCtx.fillRect(0, y + h, cropCanvas.width, cropCanvas.height - (y + h));
    // Left
    cropCtx.fillRect(0, y, x, h);
    // Right
    cropCtx.fillRect(x + w, y, cropCanvas.width - (x + w), h);

    // Draw crop border
    cropCtx.strokeStyle = '#6c5ce7';
    cropCtx.lineWidth = 2;
    cropCtx.strokeRect(x, y, w, h);

    // Draw corner handles
    const handleSize = 8;
    cropCtx.fillStyle = '#6c5ce7';

    // Top-left
    cropCtx.fillRect(x - handleSize/2, y - handleSize/2, handleSize, handleSize);
    // Top-right
    cropCtx.fillRect(x + w - handleSize/2, y - handleSize/2, handleSize, handleSize);
    // Bottom-left
    cropCtx.fillRect(x - handleSize/2, y + h - handleSize/2, handleSize, handleSize);
    // Bottom-right
    cropCtx.fillRect(x + w - handleSize/2, y + h - handleSize/2, handleSize, handleSize);
}

function convertToOriginalPixels(canvasCrop) {
    if (!videoMetadata || !cropCanvas) return null;

    // Canvas is scaled to fit container
    const scale = videoMetadata.width / cropCanvas.width;

    let x = Math.round(canvasCrop.canvasX * scale);
    let y = Math.round(canvasCrop.canvasY * scale);
    let w = Math.round(canvasCrop.canvasW * scale);
    let h = Math.round(canvasCrop.canvasH * scale);

    // Ensure within video bounds
    x = Math.max(0, Math.min(x, videoMetadata.width - 64));
    y = Math.max(0, Math.min(y, videoMetadata.height - 64));
    w = Math.min(w, videoMetadata.width - x);
    h = Math.min(h, videoMetadata.height - y);

    // Ensure even numbers for codec compatibility
    x = x - (x % 2);
    y = y - (y % 2);
    w = w - (w % 2);
    h = h - (h % 2);

    // Minimum size check
    if (w < 64 || h < 64) {
        return null;
    }

    return { x, y, w, h };
}

function updateCropDimensions() {
    if (cropData && cropData.w && cropData.h) {
        cropDimensions.textContent = `Crop: ${cropData.w} x ${cropData.h} at (${cropData.x}, ${cropData.y})`;
    } else if (videoMetadata) {
        cropDimensions.textContent = `Full frame: ${videoMetadata.width} x ${videoMetadata.height}`;
    } else {
        cropDimensions.textContent = 'Full frame';
    }
}

function resetCrop() {
    cropData = null;
    cropContainer.classList.remove('has-crop');
    updateCropDimensions();

    // Redraw canvas without crop overlay
    if (currentThumbnailImg && cropCtx) {
        cropCtx.drawImage(currentThumbnailImg, 0, 0, cropCanvas.width, cropCanvas.height);
    }
}

function skipCropAndProcess() {
    cropData = null;
    startProcessingWithSettings();
}

function confirmCropAndProcess() {
    startProcessingWithSettings();
}

async function startProcessingWithSettings() {
    if (!currentJobId) {
        showToast('No video uploaded', 'error');
        return;
    }

    // Hide crop section
    cropSection.classList.add('hidden');

    // Show progress
    progressSection.classList.remove('hidden');
    gifSection.classList.remove('hidden');
    progressText.textContent = 'Starting processing...';

    // Get settings
    const settings = getSettings();

    // Build request body
    const requestBody = {
        job_id: currentJobId,
        settings: {
            max_duration: parseFloat(settings.max_duration),
            fps: parseInt(settings.fps, 10),
            width: parseInt(settings.width, 10),
            threshold: parseInt(settings.threshold, 10)
        }
    };

    // Add crop if defined
    if (cropData && cropData.w && cropData.h) {
        requestBody.crop = {
            x: cropData.x,
            y: cropData.y,
            w: cropData.w,
            h: cropData.h
        };
    }

    try {
        const response = await fetch('/start-processing', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(requestBody)
        });

        const data = await response.json();

        if (data.error) {
            showError(data.error);
            return;
        }

        // Validate job_id
        if (!data.job_id || !/^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i.test(data.job_id)) {
            showError('Invalid response from server');
            return;
        }

        // Update job ID (might be different if cached)
        currentJobId = data.job_id;

        // Check if cached
        if (data.cached && data.gifs) {
            progressText.textContent = 'Loading from cache...';
            loadCachedGifs(data.gifs, data.merged || []);
        } else {
            progressText.textContent = 'Processing video, detecting scenes...';
            // Start SSE connection
            startEventStream(currentJobId);
        }

    } catch (error) {
        showError('Failed to start processing: ' + escapeHtml(error.message));
    }
}
