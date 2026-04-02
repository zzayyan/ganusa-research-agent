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
        this.style.height = (this.scrollHeight < 200 ? this.scrollHeight : 200) + 'px';
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
        html = html.replace(/^### (.*)$/gm, '<h3>$1</h3>');
        html = html.replace(/^## (.*)$/gm, '<h2>$1</h2>');
        // Bold
        html = html.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');
        // Italic
        html = html.replace(/\*(.*?)\*/g, '<em>$1</em>');
        // Lists — wrap consecutive <li> items in <ul>
        html = html.replace(/^- (.*)$/gm, '<li>$1</li>');
        html = html.replace(/((?:<li>.*<\/li>\n?)+)/g, '<ul>$1</ul>');
        // Paragraphs over double newlines
        html = html.split('\n\n').map(p => {
            const trimmed = p.trim();
            if (!trimmed) return '';
            if (trimmed.startsWith('<h') || trimmed.startsWith('<ul') || trimmed.startsWith('<li')) return p;
            return `<p>${p.replace(/\n/g, '<br/>')}</p>`;
        }).join('');
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
        
        // Attach event to toggle accordion
        header.addEventListener("click", () => {
            accordion.classList.toggle("open");
            // If opening, maybe recalculate max height dynamically, CSS handles a large max-height
        });
        
        // Start opened automatically
        accordion.classList.add("open");

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
                body: JSON.stringify({ question }),
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
                            
                            if (data.type === "progress") {
                                const node = data.node;
                                const state = data.state;
                                finalResult = { ...finalResult, ...state };
                                
                                if (node === "planner") {
                                    let extra = "";
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
                                    addStep("planner", "Planning Strategy", "Deconstructing query into search intents:", extra);
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
                                                        <img src="https://www.google.com/s2/favicons?domain=${escapeHtml(hostname)}&sz=16" class="w-3 h-3 rounded-full" onerror="this.src='data:image/svg+xml;base64,PHN2ZyB4bWxucz0iaHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmciIHZpZXdCb3g9IjAgMCA1MTIgNTEyIj48cGF0aCBmaWxsPSIjY2JkNWUxIiBkPSJNMzUyIDI1NmMwIDIyLjItMTcgNDAtNDAgNDBzLTQwLTE3LjgtNDAtNDAgMTctNDAgNDAtNDAgNDAgMTcuOCA0MCA0MHpNMTQ0IDI1NmMwIDIyLjItMTcgNDAtNDAgNDBzLTQwLTE3LjgtNDAtNDAgMTctNDAgNDAtNDAgNDAgMTcuOCA0MCA0MHpNMjU2IDEyOGMwLTIyLjIgMTctNDAgNDAtNDBzNDAgMTcuOCA0MCA0MC0xNyA0MC00MCA0MC00MC0xNy44LTQwLTQwek0yNTYgMzg0YzAgMjIuMi0xNyA0MC00MCA0MHMtNDAtMTcuOC00MC00MCAxNy00MCA0MC00MCA0MCAxNy44IDQwIDQweiIvPjwvc3ZnPg=='" />
                                                        <a href="${escapeHtml(res.url)}" target="_blank" class="font-semibold text-blue-600 hover:underline truncate">${escapeHtml(res.title)}</a>
                                                    </div>
                                                    <span class="text-[10px] text-gray-400 line-clamp-2">${escapeHtml(res.content || 'Content retrieved...')}</span>
                                                </li>`;
                                            }).join('')}
                                            ${len > 5 ? `<li class="text-xs text-gray-400 pl-1 mt-1 font-medium">+${len - 5} more sources</li>` : ''}
                                        </ul>`;
                                    }
                                    addStep("search", "Web Search", `Evaluated ${len} search results...`, extra);
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
