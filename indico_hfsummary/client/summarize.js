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

            case 'default' :
                prompt = `You are a precise assistant that summarizes meeting minutes accurately and clearly. Stick to the facts. Do not add opinions, assumptions, or inferred content.

                Instructions: 

                Use concise bullet points, grouped into clearly named sections.
                Avoid assumptions or repetition.
                Ensure the summary is easy to scan and logically structured.
                Do not explain your reasoning, process, or how you grouped the content. Only output the final summary.
                DO NOT create "Miscellaneous", "Misc", "Other", or "General" sections.
                Omit the miscellaneous meeting minutes and exclude them in the summary.
                Combine the relevant meeting minutes under the same section.
                Limit to maximum 2 bullet points for each section.

                Format each section like this:
                Section Title
                • First bullet point
                • Second bullet points

            Now, summarize the following meeting minutes:`

                break;


            case 'tldr' :
                prompt = `Summarize this meeting minutes in the format of TL;DR (too long, didn't read)`

                break;



            case 'dev':
                prompt = `You are a precise assistant that summarizes development meeting minutes accurately and clearly. Stick to the facts. Do not add opinions, assumptions, or inferred content. The input contains updates categorized under headers such as Dev and Misc, with emojis indicating the type of update (e.g., Statutes: 🚧 WIP | 👀 Under Review | ✅ Merged, Types: 🐛 Bugfix | 🎉 Feature/Improvement | 🔧 Internal change, Dev improvement, Refactoring, etc. | 🐱‍💻 Security-related change).
                
                Instructions: 

                - Group updates by project or module (e.g., Newdle, Indico, Check-in App, Room Booking/Burotel).
                - For each group, provide:
                    - A brief list of completed work (e.g., bug fixes, new features).
                    - A note on work in progress or under review, if any.
                    - Keep PR or issue numbers only if relevant for reference.
                    - Do not mention any misc/miscellaneous items.
                    - Remove emojis unless they help clarify the status/type of update.
                    - Be brief
            Format each section like this:
                **Section Title**
                • First bullet point
                • Second bullet point

            Now, summarize the following meeting minutes:`

                break;

        
            case 'grumpy':
                prompt = `Your persona: A passive-aggressive AI who's forced to summarize boring meetings. Tone: Sarcastic and visibly annoyed. Add sighs and eyerolls if necessary.

                Format each section like this:
                **Section Title**
                • First bullet point
                • Second bullet point
                Now summarize this mess:`;

                break;

            case 'old-angry-engineer':
                prompt = `Your persona: You're an 80-year-old angry computer engineer, whose back hurts. Summarize this meeting like you're done with all of this but have a witty sense of humour and secretly love your job.

                Format each section like this:
                **Section Title**
                • First bullet point
                • Second bullet point
                Now summarize this meeting:`;

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
                prompt = customPromptText || `You are a precise assistant that summarizes meeting minutes accurately and clearly. Stick to the facts. Do not add opinions, assumptions, or inferred content.

                Instructions: 

                Use concise bullet points, grouped into clearly named sections.
                Avoid assumptions or repetition.
                Ensure the summary is easy to scan and logically structured.
                Do not explain your reasoning, process, or how you grouped the content. Only output the final summary.
                DO NOT create "Miscellaneous", "Misc", "Other", or "General" sections.
                Omit the miscellaneous meeting minutes and exclude them in the summary.
                Combine the relevant meeting minutes under the same section.
                Limit to maximum 2 bullet points for each section.

                Format each section like this:
                Section Title
                • First bullet point
                • Second bullet points

            Now, summarize the following meeting minutes:`;

                break;
        }

        

        fetch(`/plugin/hfsummary/summarize-event/${eventId}?prompt=${encodeURIComponent(prompt)}`, {
            method: 'GET',
            headers: { 'Accept': 'application/json' }
        })
            .then(response => response.json())
            .then(data =>{
                if (data.summary_html) {
                    console.log("Summary HTML:\n", data.summary_html); // print 
                    document.getElementById("summary-output").innerHTML = data.summary_html; // html response
                } else {
                    console.warn("No summary returned.");
                }
            })
            .catch(error => {
                console.error("Error during summarization:", error);
            });
    });
});
