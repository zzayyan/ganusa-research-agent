const SAMPLE_QUESTIONS = [
    "Who is the current president of Indonesia?",
    "What are the latest developments in quantum computing?",
    "How does climate change affect coral reefs?",
    "Explain LangGraph to a beginner"
];

document.addEventListener("DOMContentLoaded", () => {
    const questionInput = document.getElementById("question");
    const form = document.getElementById("question-form");
    const submitBtn = document.getElementById("submit-btn");
    const stopBtn = document.getElementById("stop-btn");
    const welcomeScreen = document.getElementById("welcome-screen");
    const sampleContainer = document.getElementById("sample-questions");
    const chatContent = document.getElementById("chat-content");
    const chatContainer = document.getElementById("chat-container");
    const errorToast = document.getElementById("error-toast");
    const errorMessage = document.getElementById("error-message");
    const themeToggle = document.getElementById("theme-toggle");
    const newChatBtn = document.getElementById("new-chat-btn");

    // Theme Toggle Logic
    const currentTheme = localStorage.getItem('theme') || 'light';
    if (currentTheme === 'dark') document.documentElement.classList.add('dark');

    if (themeToggle) {
        themeToggle.addEventListener('click', () => {
            document.documentElement.classList.toggle('dark');
            const theme = document.documentElement.classList.contains('dark') ? 'dark' : 'light';
            localStorage.setItem('theme', theme);
        });
    }

    // New Chat button
    if (newChatBtn) {
        newChatBtn.addEventListener('click', () => {
            location.reload();
        });
    }

    // ── Mode Toggle ───────────────────────────────────────
    let currentMode = localStorage.getItem('researchMode') || 'basic';
    const modeBasicBtn = document.getElementById('mode-basic-btn');
    const modeDeepBtn  = document.getElementById('mode-deep-btn');

    const applyModeUI = (mode) => {
        if (mode === 'basic') {
            modeBasicBtn.classList.add('active');
            modeDeepBtn.classList.remove('active');
        } else {
            modeDeepBtn.classList.add('active');
            modeBasicBtn.classList.remove('active');
        }
    };
    applyModeUI(currentMode);

    modeBasicBtn.addEventListener('click', () => {
        currentMode = 'basic';
        localStorage.setItem('researchMode', 'basic');
        applyModeUI('basic');
    });
    modeDeepBtn.addEventListener('click', () => {
        currentMode = 'deep';
        localStorage.setItem('researchMode', 'deep');
        applyModeUI('deep');
    });

    // ── Custom Model Dropdown Logic ───────────────────────────────────────
    let selectedModelValue = localStorage.getItem('selectedModel') || 'amazon.nova-pro-v1:0';
    let selectedModelLabel = localStorage.getItem('selectedModelLabel') || 'AWS Nova Pro';
    const dropdownBtn = document.getElementById('model-dropdown-btn');
    const dropdownMenu = document.getElementById('model-dropdown-menu');
    const dropdownSelected = document.getElementById('model-dropdown-selected');
    
    const setDropdownUI = (val, initialLoad=false) => {
        if (!dropdownBtn) return;
        document.querySelectorAll('.model-option').forEach(opt => {
            const check = opt.querySelector('.check-icon');
            if (opt.dataset.value === val) {
                check.classList.remove('opacity-0');
                check.classList.add('opacity-100');
                if (dropdownSelected) {
                    dropdownSelected.innerHTML = `<i class="${opt.dataset.icon}"></i><span>${opt.dataset.label}</span>`;
                }
                selectedModelLabel = opt.dataset.label;
            } else {
                check.classList.remove('opacity-100');
                check.classList.add('opacity-0');
            }
        });
    };
    
    setDropdownUI(selectedModelValue, true);

    if (dropdownBtn && dropdownMenu) {
        dropdownBtn.addEventListener('click', (e) => {
            e.stopPropagation();
            dropdownMenu.classList.toggle('hidden');
        });

        document.querySelectorAll('.model-option').forEach(opt => {
            opt.addEventListener('click', (e) => {
                e.stopPropagation();
                selectedModelValue = opt.dataset.value;
                localStorage.setItem('selectedModel', selectedModelValue);
                setDropdownUI(selectedModelValue);
                dropdownMenu.classList.add('hidden');
            });
        });

        document.addEventListener('click', (e) => {
            if (!dropdownBtn.contains(e.target) && !dropdownMenu.contains(e.target)) {
                dropdownMenu.classList.add('hidden');
            }
        });
    }

    // Populate samples
    SAMPLE_QUESTIONS.forEach(sample => {
        const btn = document.createElement("button");
        btn.type = "button";
        btn.className = "flex items-center gap-3 w-full text-left p-4 rounded-xl border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 hover:border-blue-300 dark:hover:border-blue-500 hover:shadow-md hover:-translate-y-0.5 transition-all text-sm font-medium text-gray-700 dark:text-gray-300";
        btn.innerHTML = `<i class="fa-solid fa-arrow-right text-blue-500 opacity-0 group-hover:opacity-100 transition-opacity"></i> <span class="flex-grow">${sample}</span>`;
        btn.onclick = () => {
            questionInput.value = sample;
            // auto resize
            questionInput.style.height = 'auto';
            questionInput.style.height = (questionInput.scrollHeight) + 'px';
            questionInput.focus();
        };
        sampleContainer.appendChild(btn);
    });

    // Auto-resize textarea
    questionInput.addEventListener("input", function() {
        this.style.height = 'auto';
        this.style.height = (this.scrollHeight < 200 ? Math.max(100, this.scrollHeight) : 200) + 'px';
        submitBtn.disabled = !this.value.trim();
    });

    // Handle Enter to submit (Shift+Enter for new line)
    questionInput.addEventListener('keydown', function(e) {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            if (this.value.trim() && !submitBtn.disabled) {
                form.dispatchEvent(new Event("submit", { cancelable: true, bubbles: true }));
            }
        }
    });

    const showError = (msg) => {
        errorMessage.textContent = msg;
        errorToast.classList.remove("opacity-0", "translate-y-[-20px]", "pointer-events-none");
        errorToast.classList.add("opacity-100", "translate-y-0");
        setTimeout(() => {
            errorToast.classList.remove("opacity-100", "translate-y-0");
            errorToast.classList.add("opacity-0", "translate-y-[-20px]", "pointer-events-none");
        }, 5000);
    };

    const scrollToBottom = () => {
        chatContainer.scrollTo({
            top: chatContainer.scrollHeight,
            behavior: 'smooth'
        });
    };

    // XSS-safe HTML escaping — uses the DOM itself, no regex hacks
    const escapeHtml = (str) => {
        const div = document.createElement('div');
        div.textContent = String(str ?? '');
        return div.innerHTML;
    };

    const simpleMarkdown = (text, citations = []) => {
        if (!text) return "";
        let html = text.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
        
        // Extract code blocks temporarily
        const codeBlocks = [];
        html = html.replace(/```(?:[a-zA-Z0-9+-]+)?\n([\s\S]*?)```/g, (match, code) => {
            const langMatch = match.match(/^```([a-zA-Z0-9+-]+)\n/);
            const lang = langMatch ? langMatch[1] : '';
            const safeCode = code.replace(/&lt;/g, '<').replace(/&gt;/g, '>').replace(/&amp;/g, '&').replace(/</g, '&lt;').replace(/>/g, '&gt;');
            codeBlocks.push(`<div class="relative group my-4"><div class="absolute right-2 top-2 z-10 opacity-0 group-hover:opacity-100 transition-opacity duration-200"><button class="code-copy-btn bg-gray-700/80 hover:bg-gray-600 text-gray-200 rounded-md py-1.5 px-2 flex items-center gap-1.5 backdrop-blur-sm border border-gray-600/50 shadow-sm" title="Copy code"><i class="fa-regular fa-copy text-xs"></i><span class="text-[10px] font-semibold">Copy</span></button></div><pre class="bg-[#0d1117] dark:bg-[#0d1117] p-4 rounded-xl overflow-x-auto text-[13px] block border border-gray-200 dark:border-gray-700 shadow-sm m-0"><code class="${lang ? 'language-' + lang : ''} font-mono text-gray-300 dark:text-gray-300">${safeCode}</code></pre></div>`);
            return `__CODE_BLOCK_${codeBlocks.length - 1}__`;
        });
        html = html.replace(/```([\s\S]*?)```/g, (match, code) => {
            const val = code.trim();
            codeBlocks.push(`<div class="relative group my-4"><div class="absolute right-2 top-2 z-10 opacity-0 group-hover:opacity-100 transition-opacity duration-200"><button class="code-copy-btn bg-gray-700/80 hover:bg-gray-600 text-gray-200 rounded-md py-1.5 px-2 flex items-center gap-1.5 backdrop-blur-sm border border-gray-600/50 shadow-sm" title="Copy code"><i class="fa-regular fa-copy text-xs"></i><span class="text-[10px] font-semibold">Copy</span></button></div><pre class="bg-[#0d1117] dark:bg-[#0d1117] p-4 rounded-xl overflow-x-auto text-[13px] block border border-gray-200 dark:border-gray-700 shadow-sm m-0"><code class="font-mono text-gray-300 dark:text-gray-300">${val}</code></pre></div>`);
            return `__CODE_BLOCK_${codeBlocks.length - 1}__`;
        });

        // Extract inline code
        const inlineCodes = [];
        html = html.replace(/`([^`\n]+)`/g, (match, code) => {
            inlineCodes.push(`<code class="bg-gray-100 dark:bg-gray-800 text-pink-600 dark:text-pink-400 px-1.5 py-0.5 rounded-md font-mono text-[13px] border border-gray-200 dark:border-gray-700">${code}</code>`);
            return `__INLINE_CODE_${inlineCodes.length - 1}__`;
        });

        // Inline citations tracking like [1] or [1, 2]
        html = html.replace(/\[((?:\d+,\s*)*\d+)\]/g, (match, numStr) => {
            const nums = numStr.split(',').map(n => parseInt(n.trim(), 10));
            let badges = nums.map(num => {
                const cite = citations.find(c => c.id === num || c.id === num.toString());
                if (!cite) return match;
                
                let hostStr = "source";
                try {
                    const u = new URL(cite.url);
                    let hostParts = u.hostname.replace('www.', '').split('.');
                    if (hostParts.length >= 2) {
                        hostStr = hostParts[hostParts.length - 2];
                        if (['co', 'com', 'org', 'net', 'gov', 'edu', 'ac'].includes(hostStr) && hostParts.length >= 3) {
                            hostStr = hostParts[hostParts.length - 3];
                        }
                    } else {
                        hostStr = hostParts[0];
                    }
                } catch(e) {}
                
                return `<a href="${cite.url}" target="_blank" class="inline-citation" title="${cite.title || cite.url}">${hostStr}</a>`;
            });
            return badges.join('');
        });

        // Headings (### before ##)
        let headingCount = 0;
        html = html.replace(/^### (.*)$/gm, (m, title) => {
            headingCount++;
            return `<h3 id="h-${Date.now()}-${headingCount}" class="scroll-mt-6 group flex items-center gap-2"><a href="#h-${Date.now()}-${headingCount}" class="opacity-0 group-hover:opacity-100 text-blue-500 text-lg transition-opacity"><i class="fa-solid fa-link text-xs"></i></a>${title}</h3>`;
        });
        html = html.replace(/^## (.*)$/gm, (m, title) => {
            headingCount++;
            return `<h2 id="h-${Date.now()}-${headingCount}" class="scroll-mt-6 group flex items-center gap-2"><a href="#h-${Date.now()}-${headingCount}" class="opacity-0 group-hover:opacity-100 text-blue-500 text-lg transition-opacity"><i class="fa-solid fa-link text-sm"></i></a>${title}</h2>`;
        });
        html = html.replace(/^# (.*)$/gm, (m, title) => {
            headingCount++;
            return `<h1 id="h-${Date.now()}-${headingCount}" class="scroll-mt-6">${title}</h1>`;
        });

        // Bold
        html = html.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');
        // Italic
        html = html.replace(/\*(.*?)\*/g, '<em>$1</em>');
        // Tables
        const tableBlocks = [];
        html = html.replace(/(?:(?:^|\n)[^\n]*\|[^\n]*)+(?=\n|$)/g, (match) => {
            if (!/\|?[\s-:]*[-:]+[\s-:]*\|/.test(match)) return match;
            
            let rows = match.trim().split('\n');
            let tableHtml = '<div class="overflow-x-auto my-6"><table class="w-full text-sm text-left border-collapse border border-gray-200 dark:border-gray-700 shadow-sm rounded-lg overflow-hidden">';
            let isHeader = true;
            
            rows.forEach((row, i) => {
                if (/^\|?[\s-:]*[-:]+[\s-:]*\|?([\s-:]*[-:]+[\s-:]*\|?)*$/.test(row)) {
                    isHeader = false;
                    return;
                }
                
                let cells = row.split('|');
                if (row.trim().startsWith('|')) cells.shift();
                if (row.trim().endsWith('|')) cells.pop();
                
                if (cells.length === 0) return;
                
                tableHtml += '<tr class="border-b border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 hover:bg-gray-50 dark:hover:bg-gray-750 transition-colors">';
                cells.forEach(cell => {
                    let cellTag = isHeader ? 'th' : 'td';
                    let cellClasses = isHeader 
                        ? 'px-4 py-3 bg-gray-50 dark:bg-gray-800/80 font-semibold text-gray-900 dark:text-gray-100 whitespace-nowrap' 
                        : 'px-4 py-3 text-gray-700 dark:text-gray-300';
                    tableHtml += `<${cellTag} class="${cellClasses}">${cell.trim()}</${cellTag}>`;
                });
                tableHtml += '</tr>';
                if (i === 0) isHeader = false;
            });
            tableHtml += '</table></div>';
            tableBlocks.push(tableHtml);
            return `\n\n__TABLE_BLOCK_${tableBlocks.length - 1}__\n\n`;
        });

        // Lists — wrap consecutive <li> items in <ul>
        html = html.replace(/^- (.*)$/gm, '<li>$1</li>');
        html = html.replace(/((?:<li>.*<\/li>\n?)+)/g, '<ul>$1</ul>');
        
        // Paragraphs over double newlines
        html = html.split('\n\n').map(p => {
            const trimmed = p.trim();
            if (!trimmed) return '';
            if (trimmed.startsWith('<h') || trimmed.startsWith('<ul') || trimmed.startsWith('<li') || trimmed.startsWith('__CODE_BLOCK_') || trimmed.startsWith('__TABLE_BLOCK_')) return p;
            return `<p>${p.replace(/\n/g, '<br/>')}</p>`;
        }).join('');

        // Restore tables
        tableBlocks.forEach((tableH, i) => {
            html = html.replace(`__TABLE_BLOCK_${i}__`, tableH);
        });

        // Restore inline codes
        inlineCodes.forEach((codeHtml, i) => {
            html = html.replace(`__INLINE_CODE_${i}__`, codeHtml);
        });

        // Restore code blocks
        codeBlocks.forEach((codeHtml, i) => {
            html = html.replace(`__CODE_BLOCK_${i}__`, codeHtml);
        });

        return html;
    };

    let abortController = null;

    stopBtn.addEventListener("click", () => {
        if (abortController) {
            abortController.abort();
        }
    });

    form.addEventListener("submit", async (e) => {
        e.preventDefault();
        const question = questionInput.value.trim();
        if (!question) return;

        // Abort previous request if any
        if (abortController) abortController.abort();
        abortController = new AbortController();

        // UI Reset
        submitBtn.disabled = true;
        submitBtn.classList.add("hidden");
        stopBtn.classList.remove("hidden");
        questionInput.value = '';
        questionInput.style.height = 'auto';
        
        // Hide welcome screen if present
        if (welcomeScreen) {
            welcomeScreen.style.display = 'none';
        }

        // 1. Render User Message
        const tplUser = document.getElementById("tpl-user-msg");
        const nodeUser = tplUser.content.cloneNode(true);
        nodeUser.querySelector(".user-text").textContent = question;
        chatContent.appendChild(nodeUser);
        scrollToBottom();

        // 2. Render AI Shell
        const tplAi = document.getElementById("tpl-ai-msg");
        const nodeAi = tplAi.content.cloneNode(true);
        const aiWrapper = nodeAi.querySelector('.flex'); // The main wrapper
        const accordion = nodeAi.querySelector('.process-accordion');
        const header = nodeAi.querySelector('.process-header');
        const processList = nodeAi.querySelector('.process-list');
        const statusSummary = nodeAi.querySelector('.status-summary');
        const statusIcon = nodeAi.querySelector('.status-icon');
        const finalAnswerContainer = nodeAi.querySelector('.final-answer-container');
        const finalAnswerBox = nodeAi.querySelector('.final-answer');
        const sourcesContainer = nodeAi.querySelector('.sources-container');
        const modelNameText = nodeAi.querySelector('.model-name-text');
        
        if (modelNameText) {
            modelNameText.textContent = selectedModelLabel;
        }
        
        // Attach event to toggle accordion
        header.addEventListener("click", () => {
            accordion.classList.toggle("open");
            // If opening, maybe recalculate max height dynamically, CSS handles a large max-height
        });
        
        // Start opened automatically
        accordion.classList.add("open");

        // Inject mode badge into accordion header
        const modeForRequest = currentMode;
        const badgeLabel = modeForRequest === 'deep' ? '🔬 Deep' : '⚡ Basic';
        const badge = document.createElement('span');
        badge.className = `mode-badge ${modeForRequest}`;
        badge.textContent = badgeLabel;
        statusSummary.appendChild(badge);

        chatContent.appendChild(nodeAi);
        scrollToBottom();

        const addStep = (id, title, desc, extraHtml = "") => {
            let item = processList.querySelector(`[data-step-id="${id}"]`);
            if (!item) {
                item = document.createElement("li");
                item.className = "step-item active";
                item.dataset.stepId = id;
                item.innerHTML = `
                    <div class="font-bold text-gray-800 dark:text-gray-200 tracking-tight leading-tight">${title}</div>
                    <div class="text-gray-500 text-xs mt-1 desc-box">${desc}</div>
                    <div class="extra-box mt-2">${extraHtml}</div>
                `;
                processList.appendChild(item);
                scrollToBottom();
            } else {
                item.querySelector('.desc-box').textContent = desc;
                if (extraHtml) {
                    item.querySelector('.extra-box').innerHTML = extraHtml;
                }
            }

            // Mark previous steps as done
            const allSteps = Array.from(processList.querySelectorAll('.step-item'));
            const currentIndex = allSteps.indexOf(item);
            allSteps.forEach((st, idx) => {
                if (idx < currentIndex) {
                    st.classList.remove('active');
                    st.classList.add('done');
                } else if (idx === currentIndex) {
                    st.classList.add('active');
                    st.classList.remove('done');
                }
            });
        };

        try {
            addStep("start", "Initializing", "Sending query to agent...");
            
            const response = await fetch("/research/stream", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ question, mode: modeForRequest, model: selectedModelValue }),
                signal: abortController.signal
            });

            if (!response.ok) {
                const errData = await response.json().catch(() => null);
                throw new Error((errData && errData.detail) || "Something went wrong.");
            }

            const reader = response.body.getReader();
            const decoder = new TextDecoder();
            let buffer = "";
            let finalResult = { question };
            let reactSteps = {};

            const renderReactStep = (stepIdx) => {
                const stepData = reactSteps[stepIdx];
                const id = `react_step_${stepIdx}`;
                
                let obsHtml = "";
                if (stepData.observation) {
                    if (stepData.results && stepData.results.length > 0) {
                        let linksHtml = `<div class="space-y-2 mt-1">` + stepData.results.map(r => {
                            let hostname = '';
                            try { hostname = new URL(r.url).hostname; } catch(e) {}
                            return `
                            <div class="flex flex-col text-[11px] text-gray-600 dark:text-gray-300 bg-white dark:bg-gray-800 p-2.5 rounded-md border border-gray-200 dark:border-gray-700 shadow-sm hover:border-blue-300 dark:hover:border-blue-700 transition-colors">
                                <div class="flex items-center gap-2 truncate">
                                    <img src="https://www.google.com/s2/favicons?domain=${escapeHtml(hostname)}&sz=16" class="w-3.5 h-3.5 rounded-full flex-none bg-gray-100 dark:bg-gray-700" alt="icon" onerror="this.style.display='none'" />
                                    <a href="${escapeHtml(r.url)}" target="_blank" class="font-semibold text-blue-600 dark:text-blue-400 hover:text-blue-700 dark:hover:text-blue-300 hover:underline truncate">${escapeHtml(r.title)}</a>
                                </div>
                                <div class="mt-1 text-[10px] text-gray-400 dark:text-gray-500 truncate w-full group">
                                    <span class="opacity-0 group-hover:opacity-100 transition-opacity float-right text-blue-500 ml-2">&rarr;</span>
                                    ${escapeHtml(r.url)}
                                </div>
                            </div>`;
                        }).join("") + `</div>`;
                        
                        obsHtml = `
                        <div class="mt-3 bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 shadow-sm rounded-lg overflow-hidden fade-in">
                            <details class="group">
                                <summary class="cursor-pointer p-2.5 flex items-center justify-between text-[11px] font-medium text-gray-600 dark:text-gray-400 hover:bg-gray-50 dark:hover:bg-gray-750 transition-colors list-none outline-none select-none">
                                    <div class="flex items-center gap-2.5 w-full">
                                        <div class="bg-blue-100 dark:bg-blue-900/40 text-blue-600 dark:text-blue-400 rounded p-1 flex-none flex items-center justify-center h-5 w-5">
                                            <i class="fa-solid fa-bars-staggered text-[10px]"></i>
                                        </div>
                                        <span class="flex-grow py-0.5">${escapeHtml(stepData.observation)}</span>
                                        <i class="fa-solid fa-chevron-down text-gray-400 text-[10px] transition-transform duration-200 group-open:rotate-180 flex-none mr-2"></i>
                                    </div>
                                    <style>summary::-webkit-details-marker {display: none;}</style>
                                </summary>
                                <div class="px-4 pb-3 pt-2 border-t border-gray-100 dark:border-gray-700 bg-gray-50 dark:bg-gray-800/30">
                                    ${linksHtml}
                                </div>
                            </details>
                        </div>`;
                    } else {
                        obsHtml = `
                        <div class="mt-3 bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 shadow-sm rounded-lg p-2.5 flex items-start gap-2.5 fade-in">
                            <div class="bg-blue-100 dark:bg-blue-900/40 text-blue-600 dark:text-blue-400 rounded p-1 flex-none mt-0.5 h-5 w-5 flex items-center justify-center">
                                <i class="fa-solid fa-bars-staggered text-[10px]"></i>
                            </div>
                            <div class="text-[11px] text-gray-600 dark:text-gray-400 font-medium leading-relaxed py-0.5">
                                ${escapeHtml(stepData.observation)}
                            </div>
                        </div>`;
                    }
                }

                let actionLabel = stepData.action === "search" ? "Search Web" : "Finish ReAct";
                let actionDesc = stepData.action === "search" ? stepData.action_input.query : "Proceeding to synthesis stage";
                let actionIcon = stepData.action === "search" ? "fa-magnifying-glass" : "fa-flag-checkered";
                let colorClass = stepData.action === "search" ? "text-indigo-500" : "text-emerald-500";

                let actionHtml = `
                    <div class="mt-3 flex flex-col gap-2 fade-in">
                        <div class="text-[10px] font-bold uppercase tracking-wider ${colorClass} flex items-center gap-1.5">
                            <i class="fa-solid ${actionIcon}"></i>
                            ${escapeHtml(actionLabel)}
                        </div>
                        <div class="text-[11.5px] font-mono text-gray-600 dark:text-gray-300 bg-gray-50 dark:bg-gray-800/80 border border-gray-200 dark:border-gray-700 rounded-md p-2.5 break-words whitespace-pre-wrap leading-relaxed shadow-sm">
                            ${escapeHtml(actionDesc)}
                        </div>
                    </div>
                `;

                let coverageHtml = "";
                if (stepData.coverage && Object.keys(stepData.coverage).length > 0) {
                    let tagsContext = Object.entries(stepData.coverage).map(([aspect, status]) => {
                        let badgeClass = "";
                        let icon = "";
                        if (status === "COVERED") {
                            badgeClass = "bg-emerald-100 text-emerald-700 dark:bg-emerald-900/30 dark:text-emerald-400 border-emerald-200 dark:border-emerald-800";
                            icon = "fa-check";
                        } else if (status === "PARTIAL") {
                            badgeClass = "bg-amber-100 text-amber-700 dark:bg-amber-900/30 dark:text-amber-400 border-amber-200 dark:border-amber-800";
                            icon = "fa-minus";
                        } else {
                            badgeClass = "bg-rose-100 text-rose-700 dark:bg-rose-900/30 dark:text-rose-400 border-rose-200 dark:border-rose-800";
                            icon = "fa-xmark";
                        }
                        return `<div class="flex items-center gap-1.5 text-[9.5px] border rounded px-1.5 py-0.5 ${badgeClass} font-semibold">
                                    <i class="fa-solid ${icon} text-[8px]"></i>
                                    <span class="truncate max-w-[150px]" title="${escapeHtml(aspect)}">${escapeHtml(aspect)}</span>
                                </div>`;
                    }).join("");
                    
                    coverageHtml = `
                    <div class="mt-3 flex flex-col gap-1.5">
                        <span class="text-[10px] text-gray-500 dark:text-gray-400 font-medium">Coverage Evaluation:</span>
                        <div class="flex items-start gap-1.5 flex-wrap">
                            ${tagsContext}
                        </div>
                    </div>`;
                }

                const extra = `
                    <div class="mt-2">
                        <div class="text-[12px] text-gray-800 dark:text-gray-200 leading-relaxed border-l-2 border-purple-500 pl-3 py-0.5" style="border-image: linear-gradient(to bottom, #a855f7, #6366f1) 1;">
                            <span class="text-purple-500 font-bold mr-1">R:</span>
                            ${escapeHtml(stepData.thought)}
                        </div>
                        ${coverageHtml}
                        ${actionHtml}
                        ${obsHtml}
                    </div>
                `;

                
                addStep(id, `Reason & Act <span class="text-xs text-gray-400 font-normal ml-1">Iter ${stepIdx + 1}</span>`, ``, extra);
                statusSummary.innerHTML = `Exploring angle ${stepIdx + 1}...`;
            };

            while (true) {
                const { value, done } = await reader.read();
                if (done) break;
                buffer += decoder.decode(value, { stream: true });
                
                const lines = buffer.split("\n\n");
                buffer = lines.pop(); 
                
                for (const line of lines) {
                    if (line.startsWith("data: ")) {
                        const payloadStr = line.substring(6);
                        if (!payloadStr.trim()) continue;
                        
                        try {
                            const data = JSON.parse(payloadStr);

                            if (data.type === "error") throw new Error(data.detail);

                            if (data.type === "react_step") {
                                reactSteps[data.step] = { ...data, observation: "" };
                                renderReactStep(data.step);
                            }
                            else if (data.type === "react_observation") {
                                if (reactSteps[data.step]) {
                                    reactSteps[data.step].observation = data.observation;
                                    reactSteps[data.step].results = data.results;
                                    reactSteps[data.step].evidence_count = data.evidence_count;
                                    renderReactStep(data.step);
                                }
                            }
                            else if (data.type === "progress") {
                                const node = data.node;
                                const state = data.state;
                                finalResult = { ...finalResult, ...state };

                                if (node === "planner") {
                                    // Capture time_range set by planner
                                    if (state.time_range) finalResult.time_range = state.time_range;

                                    const tr = state.time_range;
                                    const trLabels = { day: "📅 Today", week: "📅 This week", month: "📅 This month", year: "📅 This year" };
                                    const trBadge = (tr && trLabels[tr])
                                        ? `<span style="display:inline-flex;align-items:center;font-size:10px;font-weight:700;padding:1px 7px;border-radius:9999px;background:#fffbeb;color:#b45309;border:1px solid #fcd34d;margin-left:4px;">${trLabels[tr]}</span>`
                                        : "";

                                    let extra = "";
                                    if (modeForRequest === "deep") {
                                        // Deep mode: show research plan narrative — no sub-questions
                                        const planText = state.plan || "Formulating research strategy...";
                                        extra = `
                                            <div class="mt-2 flex flex-col gap-1.5">
                                                <div class="flex items-start gap-2 text-xs text-gray-600 dark:text-gray-300 bg-indigo-50/60 dark:bg-indigo-900/20 p-2.5 rounded-lg border border-indigo-100 dark:border-indigo-800">
                                                    <i class="fa-solid fa-map text-indigo-400 mt-0.5 flex-none"></i>
                                                    <span class="leading-relaxed">${escapeHtml(planText)}</span>
                                                </div>
                                                <div class="flex items-center gap-1.5 text-[10px] text-indigo-500 dark:text-indigo-400 font-semibold pl-1">
                                                    <i class="fa-solid fa-robot text-[9px]"></i>
                                                    ReAct agent will autonomously form search queries
                                                </div>
                                            </div>`;
                                        addStep("planner", `Research Strategy${trBadge}`, "", extra);
                                    } else {
                                        // Basic mode: show sub-questions list
                                        if (state.sub_questions && state.sub_questions.length > 0) {
                                            extra = `<ul class="list-none pl-1 space-y-2 mt-2">
                                                ${state.sub_questions.map(sq => `
                                                    <li class="flex items-start gap-2 text-xs text-gray-600 dark:text-gray-300 bg-gray-100/50 dark:bg-gray-800/50 p-2 rounded-md border border-gray-100 dark:border-gray-700">
                                                        <i class="fa-solid fa-magnifying-glass text-blue-400 mt-0.5"></i>
                                                        <span>${sq}</span>
                                                    </li>
                                                `).join('')}
                                            </ul>`;
                                        }
                                        addStep("planner", `Planning Strategy${trBadge}`, "Deconstructing query into search intents:", extra);
                                    }
                                    statusSummary.textContent = "Planning research...";

                                } else if (node === "search") {
                                    const len = state.search_results ? state.search_results.length : 0;
                                    let extra = "";
                                    if (state.search_results && state.search_results.length > 0) {
                                        extra = `<ul class="list-none space-y-2 mt-2">
                                            ${state.search_results.slice(0, 5).map(res => {
                                                let hostname = '';
                                                try { hostname = new URL(res.url).hostname; } catch(e) {}
                                                return `
                                                <li class="flex flex-col text-xs text-gray-600 dark:text-gray-300 bg-white dark:bg-gray-800 p-2 rounded-md border border-gray-200 dark:border-gray-700 shadow-sm">
                                                    <div class="flex items-center gap-2 mb-1 truncate">
                                                        <img src="https://www.google.com/s2/favicons?domain=${escapeHtml(hostname)}&sz=16" class="w-3 h-3 rounded-full" onerror="this.src='data:image/svg+xml;base64,PHN2ZyB4bWxucz0iaHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmciIHZpZXdCb3g9IjAgMCA1MTIgNTEyIj48cGF0aCBmaWxsPSIjY2JkNWUxIiBkPSJNMzUyIDI1NmMwIDIyLjItMTcgNDAtNDAgNDBzLTQwLTE3LjgtNDAtNDAgMTctNDAgNDAtNDAgNDAgMTcuOCA0MCA0MHpNMTQ0IDI1NmMwIDIyLjItMTcgNDAtNDAgNDBzLTQwLTE3LjgtNDAtNDAgMTctNDAgNDAtNDAgNDAgMTcuOCA0MCA0MHpNMjU2IDEyOGMwLTIyLjIgMTctNDAgNDAtNDBzNDAgMTcuOCA0MCA0MC0xNyA0MC00MCA0MC00MC0xNy44LTQwLTQwek0yNTYgMzg0YzAgMjIuMi0xNyA0MC00MCA0MHMtNDAtMTcuOC00MC00MCAxNy00MCA0MC00MCA0MCAxNy44IDQwIDQweiIvPjwvc3ZnPg==' " />
                                                        <a href="${escapeHtml(res.url)}" target="_blank" class="font-semibold text-blue-600 hover:underline truncate">${escapeHtml(res.title)}</a>
                                                    </div>
                                                    <span class="text-[10px] text-gray-400 line-clamp-2">${escapeHtml(res.content || 'Content retrieved...')}</span>
                                                </li>`;
                                            }).join('')}
                                            ${len > 5 ? `<li class="text-xs text-gray-400 pl-1 mt-1 font-medium">+${len - 5} more sources</li>` : ''}
                                        </ul>`;
                                    }
                                    addStep("search", `Web Search`, `Evaluated ${len} search results...`, extra);
                                    statusSummary.textContent = "Searching web sources...";

                                } else if (node === "verifier") {
                                    const conf = state.confidence_score ? (state.confidence_score*100).toFixed(0) : 0;
                                    let isHigh = conf > 75;
                                    let extra = `
                                        <div class="mt-2 bg-gray-50 dark:bg-gray-800 border ${isHigh ? 'border-green-200 dark:border-green-800' : 'border-yellow-200 dark:border-yellow-800'} rounded-lg p-3">
                                            <div class="flex items-center justify-between mb-2">
                                                <span class="text-xs font-semibold text-gray-700 dark:text-gray-300">Confidence Score</span>
                                                <span class="text-xs font-bold ${isHigh ? 'text-green-600' : 'text-yellow-600'}">${conf}%</span>
                                            </div>
                                            <div class="w-full bg-gray-200 rounded-full h-1.5 hide-overflow">
                                                <div class="h-1.5 rounded-full ${isHigh ? 'bg-green-500' : 'bg-yellow-500'}" style="width: ${conf}%"></div>
                                            </div>
                                        </div>
                                    `;
                                    addStep("verifier", "Verifying Facts", `Cross-checking evidence:`, extra);
                                    statusSummary.textContent = "Verifying evidence...";

                                } else if (node === "reflector") {
                                    addStep("reflector", "Reflecting", state.reflection_notes || "Identifying gaps, needs retry.");
                                    statusSummary.textContent = "Self-correcting...";

                                } else if (node === "synthesizer") {
                                    addStep("synthesizer", "Synthesizing", "Drafting final comprehensive answer...");
                                    statusSummary.textContent = "Synthesizing final answer...";
                                }
                            }

                        } catch (errParse) {
                            console.error("Chunk parse error", errParse);
                        }
                    }
                }
            }

            // Finish up
            const allSteps = Array.from(processList.querySelectorAll('.step-item'));
            allSteps.forEach(st => {
                st.classList.remove('active');
                st.classList.add('done');
            });

            // Auto-close accordion
            setTimeout(() => {
                accordion.classList.remove("open");
            }, 500);
            
            // Update accordion header to "Finished"
            statusSummary.textContent = `Researched successfully`;
            statusIcon.className = "status-icon w-5 h-5 flex flex-none items-center justify-center rounded-full bg-green-100 text-green-600";
            statusIcon.innerHTML = `<i class="fa-solid fa-check text-xs"></i>`;

            
            // Reveal final answer
            finalAnswerContainer.classList.remove("hidden");
            finalAnswerContainer.classList.add("fade-in");
            finalAnswerBox.innerHTML = simpleMarkdown(finalResult.final_answer || "No answer generated.", finalResult.citations || []);

            // Handle Deep Mode Presentation
            if (modeForRequest === 'deep') {
                const contentWrapper = aiWrapper.querySelector('.content-wrapper');
                const basicIconWrap = aiWrapper.querySelector('.basic-icon-wrap');
                const tocSidebar = aiWrapper.querySelector('.toc-sidebar');
                const tocNav = aiWrapper.querySelector('.toc-nav');

                // Adjust layout for Notion-style formal report
                finalAnswerContainer.classList.add('mt-6');
                basicIconWrap.classList.add('hidden'); // Hide the avatar icon
                contentWrapper.className = "content-wrapper flex-grow min-w-0 w-full transition-all duration-300 bg-white dark:bg-gray-800 p-6 md:p-8 rounded-2xl shadow-sm border border-gray-200 dark:border-gray-700";
                
                // Build TOC
                const headings = finalAnswerBox.querySelectorAll('h2, h3');
                if (headings.length > 0) {
                    // tocSidebar.classList.remove('hidden');
                    tocSidebar.classList.add('xl:block');

                    headings.forEach(h => {
                        const link = document.createElement('a');
                        link.href = `#${h.id}`;
                        link.textContent = h.textContent;
                        link.className = `block py-1.5 px-2.5 rounded hover:bg-black/5 dark:hover:bg-white/10 hover:text-blue-600 dark:hover:text-blue-400 transition truncate text-gray-600 dark:text-gray-400 ${h.tagName === 'H3' ? 'pl-6 text-[11.5px]' : 'font-medium mt-1'}`;
                        
                        link.addEventListener('click', (e) => {
                            e.preventDefault();
                            h.scrollIntoView({ behavior: 'smooth', block: 'start' });
                            // Highlight active
                            tocNav.querySelectorAll('a').forEach(a => a.classList.remove('text-blue-600', 'dark:text-blue-400', 'bg-blue-50', 'dark:bg-blue-900/30'));
                            link.classList.add('text-blue-600', 'dark:text-blue-400', 'bg-blue-50', 'dark:bg-blue-900/30');
                        });
                        tocNav.appendChild(link);
                    });
                }
            } else {
                // Formatting for Basic mode
                finalAnswerBox.classList.add('pt-1', 'pl-1');
            }

            // Code Highlights & Copy
            finalAnswerBox.querySelectorAll('pre code').forEach((block) => {
                if (window.hljs) hljs.highlightElement(block);
            });

            finalAnswerBox.querySelectorAll('.code-copy-btn').forEach(btn => {
                btn.addEventListener('click', () => {
                    const block = btn.parentElement.nextElementSibling.querySelector('code');
                    if (!block) return;
                    const code = block.innerText;
                    navigator.clipboard.writeText(code);
                    const origHtml = btn.innerHTML;
                    btn.innerHTML = `<i class="fa-solid fa-check text-xs text-green-400"></i><span class="text-[10px] font-semibold text-green-400">Copied!</span>`;
                    setTimeout(() => btn.innerHTML = origHtml, 2000);
                });
            });

            // Copy to Clipboard logic
            const copyBtn = aiWrapper.querySelector('.copy-btn');
            if (copyBtn) {
                copyBtn.addEventListener('click', () => {
                    const textToCopy = finalResult.final_answer || "No answer generated.";
                    
                    const showSuccess = () => {
                        const originalHtml = copyBtn.innerHTML;
                        copyBtn.innerHTML = `<i class="fa-solid fa-check text-green-500"></i><span class="text-green-500">Copied!</span>`;
                        setTimeout(() => copyBtn.innerHTML = originalHtml, 2000);
                    };

                    if (navigator.clipboard && window.isSecureContext) {
                        navigator.clipboard.writeText(textToCopy)
                            .then(showSuccess)
                            .catch(err => console.error("Copy failed", err));
                    } else {
                        // Fallback for non-HTTPS or certain browsers
                        let textArea = document.createElement("textarea");
                        textArea.value = textToCopy;
                        textArea.style.position = "absolute";
                        textArea.style.opacity = "0";
                        document.body.appendChild(textArea);
                        textArea.focus();
                        textArea.select();
                        try {
                            document.execCommand('copy');
                            showSuccess();
                        } catch (err) {
                            console.error('Fallback copy failed', err);
                        }
                        document.body.removeChild(textArea);
                    }
                });
            }


            // Add sources dynamically if present
            if (finalResult.citations && finalResult.citations.length > 0) {
                sourcesContainer.classList.remove("hidden");
                sourcesContainer.classList.add("flex");
                sourcesContainer.innerHTML = finalResult.citations.map((c, i) => `
                    <a href="${c.url}" target="_blank" class="flex items-center gap-2 bg-gray-100 dark:bg-gray-800 hover:bg-gray-200 dark:hover:bg-gray-700 border border-gray-200 dark:border-gray-700 transition-colors rounded-full px-3 py-1.5 text-xs text-gray-700 dark:text-gray-300 font-medium whitespace-nowrap shadow-sm">
                        <i class="fa-solid fa-link text-gray-400"></i>
                        <span class="max-w-[150px] truncate">${c.title || c.url}</span>
                    </a>
                `).join('');
            }
            
            scrollToBottom();

        } catch (err) {
            if (err.name === 'AbortError') {
                console.log("Request aborted");
                addStep("abort", "Cancelled", "Riset dibatalkan oleh pengguna.");
                statusSummary.textContent = "Research stopped";
                statusIcon.className = "status-icon w-5 h-5 flex flex-none items-center justify-center rounded-full bg-gray-200 text-gray-500";
                statusIcon.innerHTML = `<i class="fa-solid fa-stop text-[10px]"></i>`;
            } else {
                console.error(err);
                showError(err.message || "An unexpected error occurred.");
                statusSummary.textContent = "Research failed";
                statusIcon.className = "status-icon w-5 h-5 flex flex-none items-center justify-center rounded-full bg-red-100 text-red-600";
                statusIcon.innerHTML = `<i class="fa-solid fa-times text-xs"></i>`;
            }
        } finally {
            submitBtn.classList.remove("hidden");
            stopBtn.classList.add("hidden");
            submitBtn.disabled = false;
            submitBtn.innerHTML = '<i class="fa-solid fa-arrow-up text-sm"></i>';
            questionInput.focus();
            abortController = null;
        }
    });
});
