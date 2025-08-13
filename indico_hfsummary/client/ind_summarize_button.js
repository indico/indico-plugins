import React, {useMemo, useState, useEffect} from 'react';
import ReactDOM from 'react-dom';
import {Modal, Dropdown, TextArea, Button, Form, Message, Loader, Grid, GridRow, GridColumn, Header, Card, CardContent} from 'semantic-ui-react';
import styles from '/home/zeynep/dev/indico/plugins/indico-plugin-hf-summary/indico_hfsummary/client/summarize_button.module.scss';
import {Translate} from 'indico/react/i18n';

const PROMPT_OPTIONS = [
  { key: 'default', text: 'Default', value: 'default' }, 
  { key: 'tldr', text: 'TL;DR', value: 'tldr' }, 
  { key: 'dev', text: 'Dev minutes (group by project)', value: 'dev' }, 
  { key: 'grumpy', text: 'Grumpy', value: 'grumpy' },  
  { key: 'old-angry-engineer', text: 'Old and angry engineer', value: 'old-angry-engineer' }, 
  { key: 'funny', text: 'LOL', value: 'funny' },
  { key: 'custom', text: 'Custom…', value: 'custom' }, 
];

function buildPrompt(selectedKey, customPromptText) { // build the prompt text based on the selected key and custom input
  
  switch (selectedKey) { // handle different prompt types based on the selected key
    case 'default': 
      return `You are a precise assistant that summarizes meeting minutes accurately and clearly. Stick to the facts. Do not add opinions, assumptions, or inferred content.

    Instructions:
    - Use concise bullet points, grouped into clearly named sections.
    - Avoid assumptions or repetition.
    - Ensure the summary is easy to scan and logically structured.
    - Do not explain your reasoning, process, or how you grouped the content. Only output the final summary.
    - DO NOT create \"Miscellaneous\", \"Misc\", \"Other\", or \"General\" sections.
    - Omit the miscellaneous meeting minutes and exclude them in the summary.
    - Combine the relevant meeting minutes under the same section.
    - Limit to maximum 2 bullet points for each section.
    - Format each section like this: 
      ## Section Title
      - First bullet point
      - Second bullet point

Now, summarize the following meeting minutes:`;

    case 'tldr':
      return `Summarize this meeting in TL;DR style (short, essentials only). 
      Format each section like this: 
      ## Section Title
      - First bullet point
      - Second bullet point
      Now, summarize the following meeting minutes:`;

    case 'dev':
      return `You are a precise assistant that summarizes development meeting minutes accurately and clearly. Stick to the facts. Do not add opinions, assumptions, or inferred content. The input contains updates categorized under headers such as Dev and Misc, with emojis indicating the type of update (e.g., Status: 🚧 WIP | 👀 Under Review | ✅ Merged; Types: 🐛 Bugfix | 🎉 Feature/Improvement | 🔧 Internal change | 🐱‍💻 Security).

Instructions:
- Group updates by project or module (e.g., Newdle, Indico, Check-in App, Room Booking/Burotel).
- For each group, provide a short list of completed work and optionally WIP/Under Review.
- Keep PR/issue numbers only if relevant.
- Do not mention any Misc items.
- Remove emojis unless they clarify status/type.
- Be brief.
- Write in bullet points under each section. 
- Format each section like this: 
      ## Section Title
      - First bullet point
      - Second bullet point

Now, summarize the following meeting minutes:`;

    case 'grumpy':
      return `Your persona: You hate your job, and you hate meetings, and you want to make everyone know about this when summarizing the nonsense you had to work on last week.
Format each section like this:
## Section Title
 - First bullet point
 - Second bullet point
Now, summarize the following meeting minutes:`; 

    case 'old-angry-engineer':
      return `Your persona: You're an 80-year-old angry and grumpy grandpa and computer engineer with a witty sense of humor and this week it is your job to summarize the last week's meeting notes.  Be grumpy but also do grandpa jokes. Do not use emojis.
Format each section like this: 
      ## Section Title
      - First bullet point
      - Second bullet point
Now, summarize the following meeting minutes:`;

    case 'funny':
      return `Imagine you're a stand-up comedian summarizing a meeting. Stick to the facts. End with a mic-drop line. Format each section like this: 
      ## Section Title
      - First bullet point
      - Second bullet point
Be concise, brief and humorous. 
Now, summarize the following meeting minutes:`;

    case 'custom':
      return `${(customPromptText?.trim() || `You are a precise assistant that summarizes meeting minutes accurately and clearly. Stick to the facts. Do not add opinions, assumptions, or inferred content.

Instructions:
- Use concise bullet points, grouped into clearly named sections.
- Avoid assumptions or repetition.
- Ensure the summary is easy to scan and logically structured.
- Do not explain your reasoning, process, or how you grouped the content. Only output the final summary.
- DO NOT create \"Miscellaneous\", \"Misc\", \"Other\", or \"General\" sections.
- Omit the miscellaneous meeting minutes and exclude them in the summary.
- Combine the relevant meeting minutes under the same section.
- Limit to maximum 2 bullet points for each section.
- Format each section like this: 
      ## Section Title
      - First bullet point
      - Second bullet point`)}

Now, summarize the following meeting minutes:`;
 
    default: // fallback case incase of an unknown key
      return `You are a precise assistant that summarizes meeting minutes accurately and clearly. Stick to the facts. Do not add opinions, assumptions, or inferred content.

Instructions:
- Use concise bullet points, grouped into clearly named sections.
- Avoid assumptions or repetition.
- Ensure the summary is easy to scan and logically structured.
- Do not explain your reasoning, process, or how you grouped the content. Only output the final summary.
- DO NOT create \"Miscellaneous\", \"Misc\", \"Other\", or \"General\" sections.
- Omit the miscellaneous meeting minutes and exclude them in the summary.
- Combine the relevant meeting minutes under the same section.
- Limit to maximum 2 bullet points for each section.
Now, summarize the following meeting minutes:`;
  }

}

function SummarizeButton({ eventId }) {  // react component to handle the summarization button and modal
  const [open, setOpen] = useState(false); 
  const [selectedPromptKey, setSelectedPromptKey] = useState('default'); 
  const [customPromptText, setCustomPromptText] = useState(''); 
  const [loading, setLoading] = useState(false); 
  const [error, setError] = useState(null); 
  const [summaryHtml, setSummaryHtml] = useState(''); 
  const [editedPromptText, setEditedPromptText] = useState(''); // state for manually edited prompt

  const promptText = useMemo( () => buildPrompt(selectedPromptKey, customPromptText),[selectedPromptKey, customPromptText]);

  // clear edited prompt when usr changes dropdown selection
  useEffect(() => {
    setEditedPromptText('');
  }, [selectedPromptKey, customPromptText]); 

  async function runSummarize() { // function to run the summarization process
    if (!eventId) { 
      setError('Missing eventId.');
      return;
    }
    setLoading(true); // set loading state to true
    setError(null); 
    setSummaryHtml(''); // clear previous summary 
    try {
      const finalPromptText = editedPromptText || promptText;
      const url = `/plugin/hfsummary/summarize-event/${eventId}?prompt=${encodeURIComponent(finalPromptText)}`; // url with the prompt text
      const resp = await fetch(url, { method: 'GET', headers: { Accept: 'application/json' } }); // fetch the summary from the server
      if (!resp.ok) throw new Error(`HTTP ${resp.status}`); 
      const data = await resp.json(); // parse the JSON response
      if (data.summary_html) { // if there is summary_html in the response
        setSummaryHtml(data.summary_html); // set the summary HTML
      } else {
        setError('No summary returned.');
      }
    } catch (e) {
      setError(`Error during summarization: ${e.message}`);
    } finally {
      setLoading(false);
    }
  };

  return ( 
    <Modal 
      open={open} 
      onClose={() => setOpen(false)} 
      onOpen={() => setOpen(true)} 
      trigger={<li><a>Summarize</a></li>} // trigger the modal
    >
      <Modal.Header>Summarize Meeting</Modal.Header>

      <Modal.Content>
        <Grid celled="internally">
          <GridRow columns={2}>
            <GridColumn>
              <Header
                as="h3"
                content={Translate.string('Select Prompt')}
                subheader={Translate.string('You can choose from the predefined ones, edit or write your own custom prompt')}
              />

              <Form.Field> {/* Dropdown to select prompt type */}
              
              <Dropdown
              id="prompt-select" 
              selection // selection dropdown
              options={PROMPT_OPTIONS} 
              value={selectedPromptKey} 
              onChange={(_, { value }) => setSelectedPromptKey(value)} 
              />
              </Form.Field>

              <Card raised fluid>
                  <CardContent>
                    <Form loading={loading}> {/* form to select prompt type and enter custom prompt text + added loading thing :) */}
                      

                      {selectedPromptKey === 'custom' && ( // if custom prompt is selected, show the text area for custom input
                        <Form.Field id="custom-prompt-container"> {/* container for custom prompt input */}
                          <label>Custom prompt</label> 
                          <TextArea // text area for custom prompt input
                            id="custom-prompt" 
                            placeholder="Type your custom instructions…"
                            value={customPromptText} 
                            onChange={(_, { value }) => setCustomPromptText(value)}
                          />
                        </Form.Field>
                      )}

                      <Form.Field> {/* text area to show the prompt text that will be sent to the model */}
                        <label>Preview of prompt sent to the model (editable)</label>
                        <TextArea 
                          value={editedPromptText || promptText}  // use edited prompt text if available, otherwise use generated prompt
                          onChange={(_, { value }) => setEditedPromptText(value)}
                          placeholder={promptText}
                          style={{ minHeight: 140 }} 
                        /> 
                      </Form.Field>

                      <Button
                        id="summary-button" 
                        primary // primary button style
                        type="button" 
                        onClick={runSummarize} // onClick handler to run the summarization
                        data-event-id={eventId} // passing the event ID as data attribute
                        disabled={loading} // disable button while loading
                      >
                        {loading ? 'Summarizing…' : 'Generate summary'}
                      </Button>
                      </Form>
                  </CardContent>
              </Card>
            </GridColumn>
            <GridColumn styleName="column-divider">
              <Header
                as="h3"
                content={Translate.string('Preview')}
                subheader={Translate.string(
                  'Summary'
                )}
              />
              
                <Card raised fluid>
                  <CardContent>
                    {loading && ( 
                    <div style={{ marginTop: 16 }}> 
                      <Loader active inline='centered' />
                    </div>
                  )}

                  {error && ( 
                    <Message negative style={{ marginTop: 16 }}>
                      <Message.Header>Couldn\'t get a summary</Message.Header>
                      <p>{error}</p>
                    </Message>
                  )}


                  {summaryHtml && ( // if there is a summary HTML, display it
                    <div id="summary-output" 
                    className={styles.previewCard}
                    style={{ marginTop: 16 }}
                    dangerouslySetInnerHTML={{ __html: summaryHtml }}
                    />
                  )}
                  </CardContent>
                </Card>
              
              
            </GridColumn>
          </GridRow>
        </Grid>

      </Modal.Content>
    </Modal>
  );
}


customElements.define(
  'ind-summarize-button',
  class extends HTMLElement {
    connectedCallback() {
      const eventId = this.getAttribute('event-id'); // get the event id
      ReactDOM.render(<SummarizeButton eventId={eventId} />, this);
    }
    disconnectedCallback() {
      ReactDOM.unmountComponentAtNode(this);
    }
  }
);
