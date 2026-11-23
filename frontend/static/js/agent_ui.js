/**
 * QUANTEX AI Agent Interface Manager
 * Handles the persistent AI Terminal drawer, real-time PLAN -> ACT -> OBSERVE telemetry,
 * and user message streaming.
 */
class AgentUIManager {
    constructor() {
        this.drawer = document.getElementById('agent-drawer');
        this.toggleBtn = document.getElementById('agent-drawer-toggle');
        this.closeBtn = document.getElementById('agent-drawer-close');
        this.stream = document.getElementById('agent-chat-stream');
        this.input = document.getElementById('agent-input-field');
        this.sendBtn = document.getElementById('agent-send-btn');
        this.chipsBar = document.getElementById('prompt-chips');

        this.badgePlan = document.getElementById('step-badge-plan');
        this.badgeAct = document.getElementById('step-badge-act');
        this.badgeObserve = document.getElementById('step-badge-observe');
        this.badgeRespond = document.getElementById('step-badge-respond');

        this.bindEvents();
    }

    bindEvents() {
        if (this.toggleBtn) {
            this.toggleBtn.addEventListener('click', () => this.toggleDrawer());
        }
        if (this.closeBtn) {
            this.closeBtn.addEventListener('click', () => this.closeDrawer());
        }

        if (this.sendBtn) {
            this.sendBtn.addEventListener('click', () => this.handleSend());
        }
        if (this.input) {
            this.input.addEventListener('keydown', (e) => {
                if (e.key === 'Enter') this.handleSend();
            });
        }

        if (this.chipsBar) {
            this.chipsBar.addEventListener('click', (e) => {
                if (e.target.classList.contains('chip')) {
                    const cmd = e.target.getAttribute('data-cmd');
                    if (cmd) {
                        this.openDrawer();
                        this.executeCommand(cmd);
                    }
                }
            });
        }
    }

    toggleDrawer() {
        if (this.drawer) this.drawer.classList.toggle('closed');
    }

    openDrawer() {
        if (this.drawer) this.drawer.classList.remove('closed');
    }

    closeDrawer() {
        if (this.drawer) this.drawer.classList.add('closed');
    }

    setBadges(state) {
        const badges = [this.badgePlan, this.badgeAct, this.badgeObserve, this.badgeRespond];
        badges.forEach(b => {
            if (b) {
                b.classList.remove('in-progress', 'done');
            }
        });

        if (state === 'plan') {
            this.badgePlan?.classList.add('in-progress');
        } else if (state === 'act') {
            this.badgePlan?.classList.add('done');
            this.badgeAct?.classList.add('in-progress');
        } else if (state === 'observe') {
            this.badgePlan?.classList.add('done');
            this.badgeAct?.classList.add('done');
            this.badgeObserve?.classList.add('in-progress');
        } else if (state === 'respond') {
            badges.forEach(b => b?.classList.add('done'));
        }
    }

    appendUserMessage(text) {
        if (!this.stream) return;
        const msg = document.createElement('div');
        msg.className = 'agent-msg user';
        msg.innerHTML = `
            <div class="msg-header font-mono">YOU</div>
            <div class="msg-content">${this.escapeHtml(text)}</div>
        `;
        this.stream.appendChild(msg);
        this.stream.scrollTop = this.stream.scrollHeight;
    }

    appendAssistantMessage(result) {
        if (!this.stream) return;
        const pipeline = result.pipeline || {};
        const responseText = result.response || 'No response generated.';

        const msg = document.createElement('div');
        msg.className = 'agent-msg assistant';

        // Render Telemetry Box
        let telemetryHtml = '<div style="background:#0A0E13;border:1px solid #1E293B;border-radius:3px;padding:8px;margin-bottom:8px;font-family:JetBrains Mono;font-size:10px;">';
        
        // 1. Intent & Entities Badge Bar
        const intentName = pipeline.intent || 'GENERAL_QUERY';
        const entities = pipeline.entities || {};
        const validSyms = entities.valid_symbols || [];
        const invalidSyms = entities.invalid_symbols || [];
        const verStatus = pipeline.verification_status || 'VERIFIED';

        telemetryHtml += `<div style="display:flex;flex-wrap:wrap;gap:6px;margin-bottom:6px;align-items:center;">`;
        telemetryHtml += `<span style="background:#1E293B;color:#38BDF8;padding:2px 6px;border-radius:2px;font-weight:700;">INTENT: ${this.escapeHtml(intentName)}</span>`;
        if (validSyms.length > 0) {
            telemetryHtml += `<span style="background:#064E3B;color:#34D399;padding:2px 6px;border-radius:2px;">SYMBOLS: ${this.escapeHtml(validSyms.join(', '))}</span>`;
        }
        if (invalidSyms.length > 0) {
            telemetryHtml += `<span style="background:#4C0519;color:#FB7185;padding:2px 6px;border-radius:2px;">REJECTED: ${this.escapeHtml(invalidSyms.join(', '))}</span>`;
        }
        telemetryHtml += `<span style="background:#172554;color:#93C5FD;padding:2px 6px;border-radius:2px;margin-left:auto;">${this.escapeHtml(verStatus)}</span>`;
        telemetryHtml += `</div>`;

        if (pipeline.plan && pipeline.plan.length) {
            telemetryHtml += `<div style="color:#38BDF8;font-weight:600;margin-bottom:2px;">[PLAN]</div>`;
            pipeline.plan.forEach(step => {
                telemetryHtml += `<div style="color:#94A3B8;margin-left:8px;">• ${this.escapeHtml(step)}</div>`;
            });
        }

        if (pipeline.act && pipeline.act.length) {
            telemetryHtml += `<div style="color:#F59E0B;font-weight:600;margin-top:4px;margin-bottom:2px;">[ACT - TOOLS EXECUTED]</div>`;
            pipeline.act.forEach(t => {
                telemetryHtml += `<div style="color:#E2E8F0;margin-left:8px;">➔ Tool: <strong>${t.tool}</strong> (${t.status})</div>`;
            });
        } else {
            telemetryHtml += `<div style="color:#64748B;font-weight:600;margin-top:4px;margin-bottom:2px;">[ACT - TOOLS EXECUTED]</div>`;
            telemetryHtml += `<div style="color:#64748B;margin-left:8px;font-style:italic;">None (No market tools required)</div>`;
        }

        if (pipeline.observe && pipeline.observe.length) {
            telemetryHtml += `<div style="color:#10B981;font-weight:600;margin-top:4px;margin-bottom:2px;">[OBSERVE - VERIFICATION]</div>`;
            pipeline.observe.forEach(obs => {
                telemetryHtml += `<div style="color:#A7F3D0;margin-left:8px;">✔ ${this.escapeHtml(obs)}</div>`;
            });
        }

        telemetryHtml += '</div>';

        // Format markdown response text
        const formattedResponse = this.formatMarkdown(responseText);

        msg.innerHTML = `
            <div class="msg-header font-mono">QUANTEX AGENT ✦ VERIFIED RESPONSE</div>
            ${telemetryHtml}
            <div class="msg-content markdown-body" style="font-size:12px;">${formattedResponse}</div>
        `;

        this.stream.appendChild(msg);
        this.stream.scrollTop = this.stream.scrollHeight;

        // Auto speak summary with Voice Assistant if configured
        if (window.voiceAssistant) {
            window.voiceAssistant.speak(responseText);
        }
    }

    async handleSend() {
        if (!this.input) return;
        const query = this.input.value.trim();
        if (!query) return;

        this.input.value = '';
        await this.executeCommand(query);
    }

    async executeCommand(query) {
        this.openDrawer();
        this.appendUserMessage(query);
        this.setBadges('plan');

        try {
            setTimeout(() => this.setBadges('act'), 500);
            setTimeout(() => this.setBadges('observe'), 1200);

            const res = await window.API.runAgentCommand(query);
            this.setBadges('respond');

            if (res.success && res.result) {
                this.appendAssistantMessage(res.result);
                // Also trigger live updates for portfolio and charts if affected
                if (window.quantexApp) {
                    window.quantexApp.refreshActiveData();
                }
            } else {
                throw new Error(res.error || 'Execution failed.');
            }
        } catch (err) {
            this.setBadges('respond');
            const errMsg = document.createElement('div');
            errMsg.className = 'agent-msg assistant';
            errMsg.innerHTML = `
                <div class="msg-header font-mono" style="color:#F43F5E;">EXECUTION ERROR</div>
                <div class="msg-content">${this.escapeHtml(err.message)}</div>
            `;
            this.stream.appendChild(errMsg);
            this.stream.scrollTop = this.stream.scrollHeight;
        }
    }

    formatMarkdown(text) {
        // Simple fast institutional markdown renderer
        return text
            .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
            .replace(/\*(.*?)\*/g, '<em>$1</em>')
            .replace(/`(.*?)`/g, '<code style="background:#17222E;padding:1px 4px;border-radius:2px;font-family:JetBrains Mono;">$1</code>')
            .replace(/\n\n/g, '<br><br>')
            .replace(/\n• /g, '<br>• ')
            .replace(/\n- /g, '<br>• ');
    }

    escapeHtml(str) {
        const div = document.createElement('div');
        div.textContent = str;
        return div.innerHTML;
    }
}

window.AgentUIManager = AgentUIManager;
