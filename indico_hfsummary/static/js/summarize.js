document.addEventListener('DOMContentLoaded', function () {
    const promptSelect = document.getElementById('prompt-select');
    const customPromptContainer = document.getElementById('custom-prompt-container');
    const customPrompt = document.getElementById('custom-prompt');
    const summaryButton = document.getElementById('summary-button');

    promptSelect.addEventListener('change', function () {
        customPromptContainer.style.display = this.value === 'custom' ? 'block' : 'none';
    });

    summaryButton.addEventListener('click', function () {
        const eventId = this.getAttribute('data-event-id');
        const selectedPrompt = promptSelect.value;
        const customPromptText = customPrompt.value.trim();

        let prompt = '';
        switch (selectedPrompt) {
        
            case 'grumpy':
                prompt = `Your persona: A passive-aggressive AI who's forced to summarize boring corporate meetings. Tone: Sarcastic, dry, visibly annoyed. Add sighs and eyerolls if necessary.

                Format each section like this:
                **Section Title**
                • First bullet point
                • Second bullet point;
                Now summarize this mess:`;
                break;
            case 'angry':
                prompt = `Your persona: You're an 80-year-old angry computer engineer, whose back hurts. Summarize this meeting like you're done with all of this but have a witty sense of humour and secretly love your job.

                Format each section like this:
                **Section Title**
                • First bullet point
                • Second bullet point; 
                Now summarize this mess:`;
                break;
            case 'funny':
                prompt = `Imagine you're a stand-up comedian summarizing a meeting. Be funny, witty, but keep the core ideas intact.
                Every bullet should sound like you're roasting the meeting — without being cruel. Stay fact-based.
                End with a mic drop line.

                Format each section like this:
                **Section Title**
                • First bullet point
                • Second bullet point`;
                break;
            case 'custom':
                prompt = customPromptText || 'Please summarize the event.';
                break;
            default:
                prompt = 'Please summarize the event.';
        }

        

        fetch(`/plugin/hfsummary/summarize-event/${eventId}?prompt=${encodeURIComponent(prompt)}`, {
            method: 'GET',
            headers: { 'Accept': 'application/json' }
        })
            .then(response => response.json())
            .then(data => {
                if (data.summary_html) {
                    const plainText = data.summary_html.replace(/<[^>]+>/g, '');
                    console.log("Summary (plain text):\n", plainText);
                    document.getElementById('summary-output').textContent = plainText;
                } else {
                    console.warn("No summary returned.");
                }
            })
            .catch(error => {
                console.error("Error during summarization:", error);
            });
    });
});
