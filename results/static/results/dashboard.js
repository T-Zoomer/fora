function resultsApp() {
    return {
        results: [],
        loading: true,
        selectedIndex: null,
        chatOpen: false,

        // Phase-specific state
        proposedThemes: [],   // user-editable themes for Phase 2
        allAnswers: [],
        editorOpen: false,    // transient: theme editor open (never persisted)
        runningIds: {},       // {topic_id: true} while full pipeline runs (Phase 1)
        discoveringIds: {},   // {topic_id: true} while re-discovering (Phase 2)
        classifyingIds: {},   // {topic_id: true} while classifying (Phase 2)
        rediscoverOpen: false,
        rediscoverPrompt: '',

        // Chat
        chatMessages: [],
        chatInput: '',
        chatLoading: false,

        // ─── View helpers ──────────────────────────────
        isFailed() {
            if (this.selectedIndex === null) return false;
            const s = this.results[this.selectedIndex]?.status;
            const id = this.results[this.selectedIndex]?.topic_id;
            return !s || ['pending', 'failed', 'running'].includes(s) || !!this.runningIds[id];
        },
        isEditor() {
            if (this.selectedIndex === null) return false;
            const s = this.results[this.selectedIndex]?.status;
            return this.editorOpen || s === 'discovering';
        },
        isResults() {
            if (this.selectedIndex === null) return false;
            const s = this.results[this.selectedIndex]?.status;
            return !this.editorOpen && ['classifying', 'completed'].includes(s);
        },

        // ─── Data loading ──────────────────────────────
        async loadResults() {
            this.loading = true;
            try {
                const response = await fetch(`/results/${INTERVIEW_ID}/api/results/`);
                const data = await response.json();
                this.results = data.results || [];
                if (this.results.length > 0) {
                    const firstCompleted = this.results.findIndex(r => r.status === 'completed');
                    const idx = firstCompleted >= 0 ? firstCompleted : 0;
                    this.selectedIndex = idx;
                    const status = this.results[idx]?.status;
                    this.loadAnswers(this.results[idx]?.topic_id);
                }
            } catch (error) {
                console.error('Failed to load results:', error);
            } finally {
                this.loading = false;
            }
        },

        async loadAnswers(interviewId) {
            try {
                const response = await fetch(`/results/api/answers/${interviewId}/`);
                const data = await response.json();
                this.allAnswers = data.answers || [];
            } catch (error) {
                console.error('Failed to load answers:', error);
            }
        },

        // ─── Interview selection ───────────────────────
        selectInterview(index) {
            this.selectedIndex = index;
            this.chatOpen = false;
            this.proposedThemes = [];
            this.allAnswers = [];
            this.editorOpen = false;
            this.rediscoverOpen = false;
            this.loadAnswers(this.results[index]?.topic_id);
        },

        // ─── Retry failed analysis ─────────────────────
        async runSingle(index) {
            const result = this.results[index];
            if (!result) return;
            const id = result.topic_id;
            this.runningIds = { ...this.runningIds, [id]: true };
            this.results[index] = { ...this.results[index], status: 'running' };
            try {
                const response = await fetch(`/results/api/run/${id}/`, {
                    method: 'POST',
                    headers: { 'X-CSRFToken': this.getCsrfToken(), 'Content-Type': 'application/json' }
                });
                const data = await response.json();
                if (data.success) {
                    await this.loadResults();
                    this.selectedIndex = index;
                } else {
                    alert('Analysis failed: ' + (data.error || 'Unknown error'));
                    this.results[index] = { ...this.results[index], status: 'failed' };
                }
            } catch (error) {
                alert('Network error: ' + error.message);
                this.results[index] = { ...this.results[index], status: 'failed' };
            } finally {
                const ids = { ...this.runningIds };
                delete ids[id];
                this.runningIds = ids;
            }
        },

        // ─── Editor: re-discover themes ────────────────
        async discoverThemes(index, customPrompt = '') {
            const result = this.results[index];
            if (!result) return;
            const id = result.topic_id;
            this.discoveringIds = { ...this.discoveringIds, [id]: true };
            // Optimistically set status to 'discovering'
            this.results[index] = { ...this.results[index], status: 'discovering' };

            try {
                const response = await fetch(`/results/api/discover/${id}/`, {
                    method: 'POST',
                    headers: { 'X-CSRFToken': this.getCsrfToken(), 'Content-Type': 'application/json' },
                    body: JSON.stringify({ custom_prompt: customPrompt }),
                });
                const data = await response.json();
                if (data.success) {
                    this.proposedThemes = data.proposed_themes || [];
                    this.editorOpen = true;
                    await this.loadAnswers(id);
                } else {
                    alert('Discovery failed: ' + (data.error || 'Unknown error'));
                }
            } catch (error) {
                alert('Network error: ' + error.message);
            } finally {
                const ids = { ...this.discoveringIds };
                delete ids[id];
                this.discoveringIds = ids;
            }
        },

        // Re-discover (from inside Phase 2 editor) — opens inline prompt panel
        toggleRediscover() {
            this.rediscoverOpen = !this.rediscoverOpen;
            if (!this.rediscoverOpen) this.rediscoverPrompt = '';
        },

        async rediscoverThemes(index) {
            this.rediscoverOpen = false;
            const prompt = this.rediscoverPrompt;
            this.rediscoverPrompt = '';
            await this.discoverThemes(index, prompt);
        },

        // ─── Editor → results view (no API) ───────────
        backToResults(index) {
            this.editorOpen = false;
            this.proposedThemes = [];
            this.rediscoverOpen = false;
            this.rediscoverPrompt = '';
        },

        // ─── Results → editor (no API) ─────────────────
        async openEditor(index) {
            const result = this.results[index];
            if (!result) return;
            // Sort proposed_themes to match the results view order (by count descending)
            const themes = JSON.parse(JSON.stringify(result.proposed_themes || []));
            const countMap = {};
            for (const t of (result.themes || [])) countMap[t.name] = t.count || 0;
            themes.sort((a, b) => (countMap[b.name] || 0) - (countMap[a.name] || 0));
            this.proposedThemes = themes;
            this.editorOpen = true;
            await this.loadAnswers(result.topic_id);
        },

        // ─── Editor → results: run classification ──────
        async runClassification(index) {
            const result = this.results[index];
            if (!result || this.proposedThemes.length === 0) return;
            const id = result.topic_id;
            this.classifyingIds = { ...this.classifyingIds, [id]: true };
            this.results[index] = { ...this.results[index], status: 'classifying' };

            try {
                const response = await fetch(`/results/api/classify/${id}/`, {
                    method: 'POST',
                    headers: { 'X-CSRFToken': this.getCsrfToken(), 'Content-Type': 'application/json' },
                    body: JSON.stringify({ themes: this.proposedThemes })
                });
                const data = await response.json();
                if (data.success) {
                    this.editorOpen = false;
                    this.proposedThemes = [];
                    await this.loadResults();
                    this.selectedIndex = index;
                } else {
                    alert('Classification failed: ' + (data.error || 'Unknown error'));
                    this.results[index] = { ...this.results[index], status: 'editing' };
                }
            } catch (error) {
                alert('Network error: ' + error.message);
                this.results[index] = { ...this.results[index], status: 'editing' };
            } finally {
                const ids = { ...this.classifyingIds };
                delete ids[id];
                this.classifyingIds = ids;
            }
        },

        // ─── Theme editor operations ───────────────────
        updateThemeName(i, val) {
            const themes = [...this.proposedThemes];
            themes[i] = { ...themes[i], name: val.trim() };
            this.proposedThemes = themes;
        },

        updateThemeDesc(i, val) {
            const themes = [...this.proposedThemes];
            themes[i] = { ...themes[i], description: val.trim() };
            this.proposedThemes = themes;
        },

        deleteTheme(i) {
            this.proposedThemes = this.proposedThemes.filter((_, idx) => idx !== i);
        },

        addTheme() {
            this.proposedThemes = [...this.proposedThemes, { name: 'New theme', description: '' }];
        },

        // ─── Results view helpers ──────────────────────
        getSortedThemes() {
            if (this.selectedIndex === null) return [];
            const themes = this.results[this.selectedIndex]?.themes || [];
            return [...themes].sort((a, b) => {
                if (a.name === 'Other') return 1;
                if (b.name === 'Other') return -1;
                return b.count - a.count;
            });
        },

        getDonutGradient() {
            const sorted = this.getSortedThemes();
            if (sorted.length === 0) return '#e5e7eb';
            const total = sorted.reduce((sum, t) => sum + t.count, 0);
            if (total === 0) return '#e5e7eb';
            let currentAngle = 0;
            const segments = [];
            sorted.forEach(theme => {
                const angle = (theme.count / total) * 360;
                segments.push(`${this.getThemeBarColor(theme)} ${currentAngle}deg ${currentAngle + angle}deg`);
                currentAngle += angle;
            });
            return `conic-gradient(${segments.join(', ')})`;
        },

        getThemePercent(theme) {
            const total = this.results[this.selectedIndex]?.answer_count || 0;
            if (!total) return '0.0';
            return ((theme.count / total) * 100).toFixed(1);
        },

        getMaxThemeCount() {
            if (this.selectedIndex === null) return 0;
            const themes = this.results[this.selectedIndex]?.themes || [];
            return Math.max(...themes.map(t => t.count), 0);
        },

        getBarWidth(count) {
            const themes = this.results[this.selectedIndex]?.themes || [];
            const maxCount = Math.max(...themes.map(t => t.count), 1);
            return (count / maxCount) * 100;
        },

        getThemeBarColor(theme) {
            const sentiment = this.getThemeSentiment(theme);
            if (sentiment !== null) return this.getSentimentColor(sentiment);
            if (theme.name === 'Other') return '#d1d5db';
            const idx = this.getSortedThemes().findIndex(t => t.name === theme.name);
            return this.getThemeColor(idx);
        },

        getExploreBarColor(theme) {
            const result = this.results[this.selectedIndex];
            if (result?.sentiment?.answers?.length > 0) {
                const sentiment = this.getThemeSentiment(theme);
                if (sentiment !== null) return this.getSentimentColor(sentiment);
            }
            return this.getThemeBarColor(theme);
        },

        getThemeColor(index) {
            const colors = ['#c7d2fe', '#a5b4fc', '#bfdbfe', '#93c5fd', '#c4b5fd', '#d8b4fe', '#a5f3fc', '#99f6e4', '#bbf7d0', '#fde68a', '#fed7aa', '#fecaca'];
            return colors[index % colors.length];
        },

        getSentimentEmoji(score) {
            if (score == null) return '';
            if (score >= 7) return '😊';
            if (score >= 4) return '😐';
            return '😟';
        },

        getSentimentColor(score) {
            if (score == null) return '#d1d5db';
            const normalized = (score - 1) / 9;
            if (normalized <= 0.5) {
                const r = 254, g = Math.round(202 + (normalized * 2) * 38), b = Math.round(202 - (normalized * 2) * 22);
                return `rgb(${r}, ${g}, ${b})`;
            } else {
                const t = (normalized - 0.5) * 2;
                return `rgb(${Math.round(254 - t * 67)}, ${Math.round(240 + t * 7)}, ${Math.round(180 + t * 28)})`;
            }
        },

        getScoreBarHeight(score) {
            if (this.selectedIndex === null) return 0;
            const answers = this.results[this.selectedIndex]?.sentiment?.answers || [];
            const count = answers.filter(a => Math.round(a.score) === score).length;
            if (count === 0) return 0;
            const maxCount = Math.max(...[1,2,3,4,5,6,7,8,9,10].map(s =>
                answers.filter(a => Math.round(a.score) === s).length
            ), 1);
            return Math.max((count / maxCount) * 80, 4);
        },

        getThemeSentiment(theme) {
            if (this.selectedIndex === null) return null;
            const result = this.results[this.selectedIndex];
            if (!result?.sentiment?.answers || !theme?.answer_ids) return null;
            const scores = theme.answer_ids.map(id => result.sentiment.answers.find(a => a.id === id)?.score).filter(s => s != null);
            if (scores.length === 0) return null;
            return scores.reduce((a, b) => a + b, 0) / scores.length;
        },

        getAnswerThemeColor(answerId) {
            if (this.selectedIndex === null) return '#e5e7eb';
            const sorted = this.getSortedThemes();
            for (let i = 0; i < sorted.length; i++) {
                const ids = sorted[i].answer_ids || [];
                if (ids.includes(answerId)) {
                    if (sorted[i].name === 'Other') return '#d1d5db';
                    return this.getThemeColor(i);
                }
            }
            return '#e5e7eb';
        },

        getAnswerSentimentBorder(answerId) {
            const result = this.results[this.selectedIndex];
            if (!result?.sentiment?.answers) return '#e5e7eb';
            const answer = result.sentiment.answers.find(a => a.id === answerId);
            const score = answer?.score;
            if (score == null) return '#e5e7eb';
            if (score >= 7) return 'rgba(34, 197, 94, 0.5)';
            if (score >= 4) return '#e5e7eb';
            return 'rgba(239, 68, 68, 0.5)';
        },

        // Returns [{excerpt, color}] for every theme this answer belongs to
        getAnswerHighlights(answerId) {
            if (this.selectedIndex === null) return [];
            const sorted = this.getSortedThemes();
            const highlights = [];
            for (let i = 0; i < sorted.length; i++) {
                const excerpt = (sorted[i].excerpts || {})[String(answerId)];
                if (excerpt) highlights.push({ excerpt, color: this.getThemeBarColor(sorted[i]) });
            }
            return highlights;
        },

        // Highlight a single excerpt in one colour (used in Explore Themes)
        highlightExcerpt(text, excerpt, color = '#fef08a') {
            return this.highlightAll(text, excerpt ? [{ excerpt, color }] : []);
        },

        // Highlight multiple excerpts in their respective colours
        highlightAll(text, highlights) {
            const escaped = text.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
            if (!highlights || highlights.length === 0) return escaped;

            // Find positions for each excerpt
            const spans = [];
            for (const { excerpt, color } of highlights) {
                if (!excerpt || !excerpt.trim()) continue;
                const esc = excerpt.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
                const idx = escaped.toLowerCase().indexOf(esc.toLowerCase());
                if (idx !== -1) spans.push({ start: idx, end: idx + esc.length, color });
            }
            if (spans.length === 0) return escaped;

            // Sort by position, drop overlaps
            spans.sort((a, b) => a.start - b.start);
            const clean = [spans[0]];
            for (let i = 1; i < spans.length; i++) {
                if (spans[i].start >= clean[clean.length - 1].end) clean.push(spans[i]);
            }

            // Build HTML
            let result = '', pos = 0;
            for (const { start, end, color } of clean) {
                result += escaped.slice(pos, start);
                result += `<mark style="background-color:${color};border-radius:2px;padding:0 1px;">`;
                result += escaped.slice(start, end);
                result += '</mark>';
                pos = end;
            }
            return result + escaped.slice(pos);
        },

        // ─── Chat ──────────────────────────────────────
        async sendChatMessage() {
            if (!this.chatInput.trim() || this.chatLoading) return;

            const userMessage = this.chatInput.trim();
            this.chatInput = '';
            this.chatMessages.push({ role: 'user', content: userMessage });
            this.chatLoading = true;

            this.$nextTick(() => {
                const container = this.$refs.chatMessages;
                if (container) container.scrollTop = container.scrollHeight;
            });

            try {
                const response = await fetch(`/results/${INTERVIEW_ID}/api/chat/`, {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                        'X-CSRFToken': this.getCsrfToken()
                    },
                    body: JSON.stringify({
                        message: userMessage,
                        history: this.chatMessages.slice(0, -1)
                    })
                });

                const data = await response.json();
                if (data.success) {
                    this.chatMessages.push({ role: 'assistant', content: data.response });
                } else {
                    this.chatMessages.push({ role: 'assistant', content: 'Error: ' + (data.error || 'Something went wrong') });
                }
            } catch (error) {
                this.chatMessages.push({ role: 'assistant', content: 'Error: ' + error.message });
            } finally {
                this.chatLoading = false;
                this.$nextTick(() => {
                    const container = this.$refs.chatMessages;
                    if (container) container.scrollTop = container.scrollHeight;
                });
            }
        },

        getCsrfToken() {
            const name = 'csrftoken';
            if (document.cookie) {
                const cookies = document.cookie.split(';');
                for (let cookie of cookies) {
                    cookie = cookie.trim();
                    if (cookie.startsWith(name + '=')) return decodeURIComponent(cookie.substring(name.length + 1));
                }
            }
            return null;
        },
    };
}
