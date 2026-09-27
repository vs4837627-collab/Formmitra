// FormMitra Frontend Application Logic

let currentLanguage = 'en';
let currentAnalysis = null;
let currentFileId = null;

// DOM Elements
const dropzone = document.getElementById('dropzone');
const fileInput = document.getElementById('fileInput');
const samplesGrid = document.getElementById('samplesGrid');
const loadingBox = document.getElementById('loadingBox');
const resultsContainer = document.getElementById('resultsContainer');
const heroCard = document.getElementById('heroCard');

// Tabs
const tabButtons = document.querySelectorAll('.tab-btn');
const tabPanes = document.querySelectorAll('.tab-pane');

// Chat Drawer
const chatDrawer = document.getElementById('chatDrawer');
const floatingChatBtn = document.getElementById('floatingChatBtn');
const chatCloseBtn = document.getElementById('chatCloseBtn');
const chatMessages = document.getElementById('chatMessages');
const chatInput = document.getElementById('chatInput');
const chatSendBtn = document.getElementById('chatSendBtn');
const quickPrompts = document.getElementById('quickPrompts');

// Search & Filter
const fieldSearch = document.getElementById('fieldSearch');
const filterPillBtns = document.querySelectorAll('.filter-pill-btn');

let activeFieldFilter = 'all';

// Initialize
document.addEventListener('DOMContentLoaded', () => {
    loadSampleForms();
    setupLanguageSelector();
    setupDropzone();
    setupTabs();
    setupChat();
    setupFieldFilters();
    setupActionButtons();
});

// ==========================================
// LANGUAGE SELECTOR
// ==========================================
function setupLanguageSelector() {
    const langBtns = document.querySelectorAll('.lang-btn');
    langBtns.forEach(btn => {
        btn.addEventListener('click', () => {
            langBtns.forEach(b => b.classList.remove('active'));
            btn.classList.add('active');
            currentLanguage = btn.dataset.lang;
            
            // If already analyzing a file, prompt or re-analyze if user wants
            if (currentFileId && currentAnalysis) {
                const reanalyze = confirm(`Switch language to ${btn.textContent}? Re-analyzing will translate all form explanations and instructions.`);
                if (reanalyze) {
                    reanalyzeCurrentDocument();
                }
            }
        });
    });
}

// ==========================================
// SAMPLES LOADER
// ==========================================
async function loadSampleForms() {
    try {
        const res = await fetch('/api/sample-forms');
        const data = await res.json();
        
        if (data.samples && data.samples.length > 0) {
            samplesGrid.innerHTML = '';
            data.samples.forEach(sample => {
                const chip = document.createElement('button');
                chip.className = 'sample-chip';
                const icon = sample.type === 'PDF' ? '📄' : '🖼️';
                chip.innerHTML = `${icon} <strong>${sample.display_name}</strong>`;
                chip.addEventListener('click', () => analyzeSample(sample.filename));
                samplesGrid.appendChild(chip);
            });
        }
    } catch (e) {
        console.error('Failed to load sample documents:', e);
    }
}

// ==========================================
// DROPZONE & FILE UPLOAD
// ==========================================
function setupDropzone() {
    dropzone.addEventListener('click', () => fileInput.click());

    dropzone.addEventListener('dragover', (e) => {
        e.preventDefault();
        dropzone.classList.add('dragover');
    });

    dropzone.addEventListener('dragleave', () => {
        dropzone.classList.remove('dragover');
    });

    dropzone.addEventListener('drop', (e) => {
        e.preventDefault();
        dropzone.classList.remove('dragover');
        if (e.dataTransfer.files.length > 0) {
            uploadFormFile(e.dataTransfer.files[0]);
        }
    });

    fileInput.addEventListener('change', () => {
        if (fileInput.files.length > 0) {
            uploadFormFile(fileInput.files[0]);
        }
    });
}

async function uploadFormFile(file) {
    showLoading();
    
    const formData = new FormData();
    formData.append('file', file);
    formData.append('language', currentLanguage);

    try {
        animateLoadingSteps();
        const res = await fetch('/api/analyze-form', {
            method: 'POST',
            body: formData
        });

        if (!res.ok) {
            const err = await res.json();
            throw new Error(err.detail || 'Analysis request failed');
        }

        const data = await res.json();
        currentAnalysis = data.analysis;
        currentFileId = data.file_id;
        renderAnalysis(data.analysis);
    } catch (err) {
        alert('Error analyzing form: ' + err.message);
        hideLoading();
    }
}

async function analyzeSample(filename) {
    showLoading();
    try {
        animateLoadingSteps();
        const res = await fetch(`/api/analyze-sample/${encodeURIComponent(filename)}?language=${currentLanguage}`, {
            method: 'POST'
        });

        if (!res.ok) {
            const err = await res.json();
            throw new Error(err.detail || 'Sample analysis failed');
        }

        const data = await res.json();
        currentAnalysis = data.analysis;
        currentFileId = data.file_id;
        renderAnalysis(data.analysis);
    } catch (err) {
        alert('Error analyzing sample: ' + err.message);
        hideLoading();
    }
}

async function reanalyzeCurrentDocument() {
    if (!currentFileId) return;
    showLoading();
    try {
        animateLoadingSteps();
        const res = await fetch(`/api/analyze-sample/${encodeURIComponent(currentFileId)}?language=${currentLanguage}`, {
            method: 'POST'
        });
        if (res.ok) {
            const data = await res.json();
            currentAnalysis = data.analysis;
            renderAnalysis(data.analysis);
        } else {
            hideLoading();
        }
    } catch (err) {
        hideLoading();
    }
}

// ==========================================
// LOADING ANIMATION
// ==========================================
function showLoading() {
    heroCard.style.display = 'none';
    resultsContainer.style.display = 'none';
    loadingBox.style.display = 'block';
    window.scrollTo({ top: 0, behavior: 'smooth' });
}

function hideLoading() {
    loadingBox.style.display = 'none';
    heroCard.style.display = 'block';
}

function animateLoadingSteps() {
    const steps = document.querySelectorAll('.step-item');
    steps.forEach((s, idx) => {
        s.classList.remove('active');
        setTimeout(() => {
            s.classList.add('active');
        }, (idx + 1) * 1200);
    });
}

// ==========================================
// RENDER ANALYSIS RESULTS
// ==========================================
function renderAnalysis(data) {
    loadingBox.style.display = 'none';
    resultsContainer.style.display = 'block';
    floatingChatBtn.style.display = 'flex';

    // 1. Overview Section
    document.getElementById('formTitle').textContent = data.form_title || 'Document Analysis';
    document.getElementById('formAuthority').textContent = data.issuing_authority || 'Official Authority';
    document.getElementById('formCategory').textContent = data.document_category || 'Document';
    document.getElementById('formSummary').textContent = data.simple_summary || 'No summary available.';
    document.getElementById('formEligibility').textContent = data.who_should_fill || 'Anyone authorized';
    document.getElementById('formSubmissionMode').textContent = data.submission_mode || 'Standard';
    document.getElementById('formFee').textContent = data.fee_details || 'Free / Not Specified';
    document.getElementById('formEstimatedTime').textContent = data.estimated_time_to_fill || '15-20 mins';
    document.getElementById('formDeadline').textContent = data.deadline_or_validity || 'Not specified';

    // 2. Pre-flight Document Checklist
    renderChecklist(data.document_checklist || []);

    // 3. Field-by-Field Breakdown
    renderSectionsAndFields(data.sections || []);

    // 4. Critical Mistakes
    renderMistakes(data.critical_mistakes || []);

    // 5. Step-by-Step Guide
    renderSteps(data.step_by_step_instructions || []);

    // Switch to first tab (Checklist or Overview)
    switchTab('tab-checklist');

    // Reset Chat messages for new document
    initChatWithFormContext(data);
}

// ==========================================
// RENDER CHECKLIST
// ==========================================
function renderChecklist(checklist) {
    const grid = document.getElementById('checklistGrid');
    const counter = document.getElementById('checklistCounter');
    grid.innerHTML = '';

    if (checklist.length === 0) {
        grid.innerHTML = '<p class="text-muted">No specific supporting documents identified.</p>';
        counter.textContent = '0 items';
        return;
    }

    let checkedCount = 0;
    const total = checklist.length;
    updateCounter();

    function updateCounter() {
        counter.textContent = `${checkedCount} of ${total} documents ready`;
    }

    checklist.forEach((item, idx) => {
        const card = document.createElement('div');
        card.className = 'doc-item';
        card.innerHTML = `
            <input type="checkbox" class="doc-checkbox" id="doc_${idx}">
            <div class="doc-content">
                <h4>${escapeHtml(item.document_name)}</h4>
                <p class="doc-purpose">${escapeHtml(item.purpose || '')}</p>
                <div class="doc-badges">
                    <span class="badge-tag ${item.is_mandatory ? 'badge-mandatory' : 'badge-optional'}">
                        ${item.is_mandatory ? 'Mandatory' : 'Optional'}
                    </span>
                    <span class="badge-tag badge-copy">${escapeHtml(item.original_or_copy || 'Photocopy')}</span>
                    ${item.where_to_get ? `<span class="badge-tag badge-original">📍 ${escapeHtml(item.where_to_get)}</span>` : ''}
                </div>
            </div>
        `;

        const checkbox = card.querySelector('.doc-checkbox');
        card.addEventListener('click', (e) => {
            if (e.target !== checkbox) {
                checkbox.checked = !checkbox.checked;
            }
            if (checkbox.checked) {
                card.classList.add('checked');
                checkedCount++;
            } else {
                card.classList.remove('checked');
                checkedCount--;
            }
            updateCounter();
        });

        grid.appendChild(card);
    });
}

// ==========================================
// RENDER SECTIONS & FIELDS
// ==========================================
function renderSectionsAndFields(sections) {
    const container = document.getElementById('fieldsContainer');
    container.innerHTML = '';

    let totalFields = 0;

    sections.forEach((sec, sIdx) => {
        const secDiv = document.createElement('div');
        secDiv.className = 'section-group';
        secDiv.dataset.sectionTitle = sec.section_title.toLowerCase();

        secDiv.innerHTML = `
            <div class="section-header">
                <h3>${escapeHtml(sec.section_title)}</h3>
                <span>${sec.fields ? sec.fields.length : 0} fields</span>
            </div>
            <div class="fields-grid" id="sec_grid_${sIdx}"></div>
        `;

        const fieldsGrid = secDiv.querySelector(`#sec_grid_${sIdx}`);
        (sec.fields || []).forEach(field => {
            totalFields++;
            const fCard = document.createElement('div');
            fCard.className = 'field-card';
            fCard.dataset.label = (field.field_label || '').toLowerCase();
            fCard.dataset.meaning = (field.plain_english_meaning || '').toLowerCase();
            fCard.dataset.mandatory = field.is_mandatory ? 'true' : 'false';

            fCard.innerHTML = `
                <div>
                    <div class="field-top">
                        <span class="field-label">${escapeHtml(field.field_label)}</span>
                        <span class="badge-tag ${field.is_mandatory ? 'badge-mandatory' : 'badge-optional'}">
                            ${field.is_mandatory ? 'Required' : 'Optional'}
                        </span>
                    </div>
                    <p class="field-meaning">${escapeHtml(field.plain_english_meaning || '')}</p>
                    
                    <div class="field-instruction-box">
                        <div class="instruction-title">What to write / Format:</div>
                        <div class="instruction-text">${escapeHtml(field.what_to_enter || '')}</div>
                        ${field.sample_value ? `
                            <div class="sample-row">
                                <span style="color:#64748b; font-weight:600;">Sample entry:</span>
                                <span class="sample-badge">${escapeHtml(field.sample_value)}</span>
                            </div>
                        ` : ''}
                        ${field.format_rules ? `
                            <div class="sample-row" style="color:#b45309; font-size:0.78rem;">
                                <span>📐 Rules: ${escapeHtml(field.format_rules)}</span>
                            </div>
                        ` : ''}
                    </div>
                </div>

                <div>
                    ${field.mistake_risk ? `
                        <div style="background:#fffbeb; border-left:3px solid #d97706; padding:0.4rem 0.6rem; font-size:0.78rem; color:#92400e; border-radius:0 4px 4px 0; margin-bottom:0.5rem;">
                            ⚠️ <strong>Watch out:</strong> ${escapeHtml(field.mistake_risk)}
                        </div>
                    ` : ''}

                    <div class="field-footer">
                        <span>${escapeHtml(field.section_name || sec.section_title)}</span>
                        ${field.supporting_document ? `
                            <span class="field-proof" title="Verify from this document">
                                📑 ${escapeHtml(field.supporting_document)}
                            </span>
                        ` : ''}
                    </div>
                </div>
            `;
            fieldsGrid.appendChild(fCard);
        });

        container.appendChild(secDiv);
    });

    document.getElementById('fieldsTabCount').textContent = totalFields;
}

// ==========================================
// RENDER MISTAKES
// ==========================================
function renderMistakes(mistakes) {
    const container = document.getElementById('mistakesContainer');
    container.innerHTML = '';

    if (mistakes.length === 0) {
        container.innerHTML = '<p class="text-muted">No high-risk rejection traps detected for this form.</p>';
        return;
    }

    mistakes.forEach(m => {
        const severity = (m.severity || 'WARNING').toLowerCase();
        const card = document.createElement('div');
        card.className = `mistake-card ${severity}`;
        
        const icon = severity === 'critical' ? '🚫' : (severity === 'warning' ? '⚠️' : '💡');

        card.innerHTML = `
            <div class="mistake-icon">${icon}</div>
            <div class="mistake-content">
                <h4>${escapeHtml(m.title)}</h4>
                <p class="mistake-rejection"><strong>Why forms get rejected:</strong> ${escapeHtml(m.why_it_causes_rejection)}</p>
                <div class="mistake-prevention">
                    <span>✅ <strong>How to avoid:</strong> ${escapeHtml(m.how_to_prevent)}</span>
                </div>
            </div>
        `;
        container.appendChild(card);
    });
}

// ==========================================
// RENDER STEPS
// ==========================================
function renderSteps(steps) {
    const list = document.getElementById('stepsList');
    list.innerHTML = '';

    if (steps.length === 0) {
        list.innerHTML = '<p class="text-muted">No step sequence provided.</p>';
        return;
    }

    steps.forEach((step, idx) => {
        const card = document.createElement('div');
        card.className = 'step-card';
        card.innerHTML = `
            <div class="step-number">${idx + 1}</div>
            <div class="step-text">${escapeHtml(step)}</div>
        `;
        list.appendChild(card);
    });
}

// ==========================================
// TABS HANDLING
// ==========================================
function setupTabs() {
    tabButtons.forEach(btn => {
        btn.addEventListener('click', () => {
            switchTab(btn.dataset.target);
        });
    });
}

function switchTab(targetId) {
    tabButtons.forEach(b => {
        b.classList.toggle('active', b.dataset.target === targetId);
    });
    tabPanes.forEach(p => {
        p.classList.toggle('active', p.id === targetId);
    });
}

// ==========================================
// FIELD SEARCH & FILTERS
// ==========================================
function setupFieldFilters() {
    fieldSearch.addEventListener('input', applyFieldFilters);

    filterPillBtns.forEach(btn => {
        btn.addEventListener('click', () => {
            filterPillBtns.forEach(b => b.classList.remove('active'));
            btn.classList.add('active');
            activeFieldFilter = btn.dataset.filter;
            applyFieldFilters();
        });
    });
}

function applyFieldFilters() {
    const query = fieldSearch.value.toLowerCase().trim();
    const cards = document.querySelectorAll('.field-card');
    const sections = document.querySelectorAll('.section-group');

    cards.forEach(card => {
        const label = card.dataset.label;
        const meaning = card.dataset.meaning;
        const isMandatory = card.dataset.mandatory === 'true';

        const matchesQuery = !query || label.includes(query) || meaning.includes(query);
        let matchesPill = true;
        if (activeFieldFilter === 'mandatory') matchesPill = isMandatory;
        if (activeFieldFilter === 'optional') matchesPill = !isMandatory;

        if (matchesQuery && matchesPill) {
            card.style.display = 'flex';
        } else {
            card.style.display = 'none';
        }
    });

    // Hide empty section headers
    sections.forEach(sec => {
        const visibleCards = sec.querySelectorAll('.field-card:not([style*="display: none"])');
        sec.style.display = visibleCards.length > 0 ? 'block' : 'none';
    });
}

// ==========================================
// ASK MITRA CHAT
// ==========================================
function setupChat() {
    floatingChatBtn.addEventListener('click', () => {
        chatDrawer.classList.add('open');
        chatInput.focus();
    });

    chatCloseBtn.addEventListener('click', () => {
        chatDrawer.classList.remove('open');
    });

    chatSendBtn.addEventListener('click', sendChatMessage);
    chatInput.addEventListener('keypress', (e) => {
        if (e.key === 'Enter') sendChatMessage();
    });
}

function initChatWithFormContext(data) {
    chatMessages.innerHTML = '';
    
    // Welcome message
    const welcome = document.createElement('div');
    welcome.className = 'msg msg-ai';
    welcome.innerHTML = `
        Hello! I'm <strong>FormMitra</strong>. I have analyzed your <strong>${escapeHtml(data.form_title)}</strong>. 
        Feel free to ask me anything about filling this form, confusing fields, ink rules, or required documents!
    `;
    chatMessages.appendChild(welcome);

    // Initial prompt suggestions
    updateQuickPrompts([
        "Can I leave optional fields blank?",
        "What are the top rejection mistakes for this form?",
        "What supporting documents are mandatory?"
    ]);
}

function updateQuickPrompts(questions) {
    quickPrompts.innerHTML = '';
    questions.forEach(q => {
        const btn = document.createElement('button');
        btn.className = 'quick-prompt-btn';
        btn.textContent = q;
        btn.addEventListener('click', () => {
            chatInput.value = q;
            sendChatMessage();
        });
        quickPrompts.appendChild(btn);
    });
}

async function sendChatMessage() {
    const text = chatInput.value.trim();
    if (!text) return;

    // Append user message
    const uMsg = document.createElement('div');
    uMsg.className = 'msg msg-user';
    uMsg.textContent = text;
    chatMessages.appendChild(uMsg);
    chatInput.value = '';
    chatMessages.scrollTop = chatMessages.scrollHeight;

    // AI typing placeholder
    const aiMsg = document.createElement('div');
    aiMsg.className = 'msg msg-ai';
    aiMsg.textContent = 'Mitra is thinking...';
    chatMessages.appendChild(aiMsg);
    chatMessages.scrollTop = chatMessages.scrollHeight;

    try {
        const res = await fetch('/api/ask-mitra', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                query: text,
                file_id: currentFileId,
                analysis_context: currentAnalysis,
                language: currentLanguage
            })
        });

        if (!res.ok) throw new Error('Failed to get answer');
        const data = await res.json();

        aiMsg.innerHTML = escapeHtml(data.answer).replace(/\n/g, '<br>');
        
        if (data.caution_note) {
            const caution = document.createElement('div');
            caution.className = 'caution-pill';
            caution.innerHTML = `⚠️ <strong>Caution:</strong> ${escapeHtml(data.caution_note)}`;
            aiMsg.appendChild(caution);
        }

        if (data.suggested_next_questions && data.suggested_next_questions.length > 0) {
            updateQuickPrompts(data.suggested_next_questions);
        }

    } catch (e) {
        aiMsg.textContent = "I'm having a little trouble connecting right now. Please try asking again!";
    }
    chatMessages.scrollTop = chatMessages.scrollHeight;
}

// ==========================================
// ACTION BUTTONS (PRINT & RESET)
// ==========================================
function setupActionButtons() {
    document.getElementById('btnPrintGuide').addEventListener('click', () => {
        window.print();
    });

    document.getElementById('btnNewUpload').addEventListener('click', () => {
        resultsContainer.style.display = 'none';
        heroCard.style.display = 'block';
        currentAnalysis = null;
        currentFileId = null;
        fileInput.value = '';
        floatingChatBtn.style.display = 'none';
        chatDrawer.classList.remove('open');
        window.scrollTo({ top: 0, behavior: 'smooth' });
    });

    document.getElementById('btnOpenChatFromBar').addEventListener('click', () => {
        chatDrawer.classList.add('open');
        chatInput.focus();
    });
}

function escapeHtml(str) {
    if (!str) return '';
    return String(str)
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;')
        .replace(/'/g, '&#039;');
}
