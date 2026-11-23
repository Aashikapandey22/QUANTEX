/**
 * QUANTEX Voice Interaction Controller
 * Web Speech API integration for speech-to-text recognition and text-to-speech audio synthesis.
 */
class VoiceAssistant {
    constructor(options = {}) {
        this.triggerBtn = document.getElementById('voice-trigger-btn');
        this.statusIndicator = document.getElementById('voice-status-indicator');
        this.innerVoiceBtn = document.getElementById('agent-voice-btn');
        
        this.onCommandRecognized = options.onCommand || null;

        this.recognition = null;
        this.synth = window.speechSynthesis || null;
        this.isListening = false;
        this.isSpeaking = false;

        this.initRecognition();
        this.bindEvents();
    }

    initRecognition() {
        const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
        if (!SpeechRecognition) {
            console.warn('Web Speech API is not supported in this browser. Falling back to text input.');
            if (this.triggerBtn) {
                this.triggerBtn.title = 'Voice recognition not supported in this browser. Use typed commands.';
            }
            return;
        }

        this.recognition = new SpeechRecognition();
        this.recognition.continuous = false;
        this.recognition.interimResults = false;
        this.recognition.lang = 'en-IN'; // Indian English accent optimization

        this.recognition.onstart = () => {
            this.isListening = true;
            this.updateUI('listening');
        };

        this.recognition.onresult = (event) => {
            const transcript = event.results[0][0].transcript;
            console.log('Voice recognized transcript:', transcript);
            this.updateUI('processing');
            if (this.onCommandRecognized) {
                this.onCommandRecognized(transcript);
            }
        };

        this.recognition.onerror = (event) => {
            console.warn('Speech recognition error:', event.error);
            this.isListening = false;
            this.updateUI('idle');
            if (event.error === 'not-allowed') {
                alert('Microphone access was denied. Please allow microphone permissions in browser settings.');
            }
        };

        this.recognition.onend = () => {
            this.isListening = false;
            this.updateUI('idle');
        };
    }

    bindEvents() {
        if (this.triggerBtn) {
            this.triggerBtn.addEventListener('click', () => this.toggleListening());
        }
        if (this.innerVoiceBtn) {
            this.innerVoiceBtn.addEventListener('click', () => this.toggleListening());
        }
    }

    toggleListening() {
        if (!this.recognition) {
            alert('Voice recognition is not supported in this browser environment. Please type your command in the AI Terminal.');
            return;
        }

        if (this.isListening) {
            this.recognition.stop();
        } else {
            try {
                this.recognition.start();
            } catch (err) {
                console.error('Failed to start recognition:', err);
            }
        }
    }

    speak(text) {
        if (!this.synth) return;
        this.synth.cancel(); // Stop any ongoing speech

        // Strip markdown characters from speech
        const cleanText = text.replace(/[*#_`]/g, '').slice(0, 300); // Read first concise paragraph
        const utterance = new SpeechSynthesisUtterance(cleanText);
        utterance.rate = 1.0;
        utterance.pitch = 1.0;

        utterance.onstart = () => {
            this.isSpeaking = true;
            this.updateUI('speaking');
        };
        utterance.onend = () => {
            this.isSpeaking = false;
            this.updateUI('idle');
        };
        utterance.onerror = () => {
            this.isSpeaking = false;
            this.updateUI('idle');
        };

        this.synth.speak(utterance);
    }

    updateUI(state) {
        if (!this.triggerBtn) return;
        this.triggerBtn.classList.remove('listening', 'speaking');

        if (state === 'listening') {
            this.triggerBtn.classList.add('listening');
            if (this.statusIndicator) this.statusIndicator.style.backgroundColor = '#F43F5E';
        } else if (state === 'speaking') {
            this.triggerBtn.classList.add('speaking');
            if (this.statusIndicator) this.statusIndicator.style.backgroundColor = '#06B6D4';
        } else {
            if (this.statusIndicator) this.statusIndicator.style.backgroundColor = '#64748B';
        }
    }
}

window.VoiceAssistant = VoiceAssistant;
