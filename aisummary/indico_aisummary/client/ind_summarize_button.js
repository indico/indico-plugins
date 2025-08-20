// This file is part of the Indico plugins.
// Copyright (C) 2002 - 2025 CERN
//
// The Indico plugins are free software; you can redistribute
// them and/or modify them under the terms of the MIT License;
// see the LICENSE file for more details.

import React, {useMemo, useState, useEffect} from 'react';
import ReactDOM from 'react-dom';
import {Modal, Dropdown, TextArea, Button, Form, Message, Loader, Segment, Dimmer, Grid, GridRow, GridColumn, Header, Card, CardContent} from 'semantic-ui-react';
import './ind_summarize_button.module.scss'
import {Translate} from 'indico/react/i18n';
import {indicoAxios, handleAxiosError} from 'indico/utils/axios';

const PROMPT_OPTIONS = [
  { key: 'default', text: 'Default', value: 'default' }, 
  { key: 'tldr', text: 'TL;DR', value: 'tldr' }, 
  { key: 'dev', text: 'Dev minutes (group by project)', value: 'dev' }, 
  { key: 'grumpy', text: 'Grumpy', value: 'grumpy' },  
  { key: 'old-angry-engineer', text: 'Old and angry engineer', value: 'old-angry-engineer' }, 
  { key: 'funny', text: 'LOL', value: 'funny' },
  { key: 'custom', text: 'Custom…', value: 'custom' }, 
];

const LOCAL_STORAGE_KEY = 'savedPrompts';
const SUMMARY_STORAGE_KEY = 'hfSummaryHtml';


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
      return `Summarize this meeting in TL;DR style (Too long, didn't read format). Be short, take essentials only. 
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


Format each section like this: 
      ## Section Title
      - First bullet point
      - Second bullet point      
Now, summarize the following meeting minutes:`;
 
    default: 
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

function SummarizeButton({ eventId }) {  // main react component to handle the summarization button and modal
  const [open, setOpen] = useState(false); 
  const [selectedPromptKey, setSelectedPromptKey] = useState('default'); 
  const [customPromptText, setCustomPromptText] = useState(''); 
  const [loading, setLoading] = useState(false); 
  const [error, setError] = useState(null); 
  const [summaryHtml, setSummaryHtml] = useState(''); 
  const [editedPromptText, setEditedPromptText] = useState(''); 
  const [savedPrompts, setSavedPrompts] = useState([]);
  const [manageModalOpen, setManageModalOpen] = useState(false);
  const [saving, setSaving] = useState(false);

 // Combine predefined and saved prompts for dropdown
  const allPromptOptions = [
    ...PROMPT_OPTIONS,
    ...savedPrompts.map((prompt, idx) => ({
      key: `saved-${idx}`,
      text: prompt.slice(0, 30) + (prompt.length > 30 ? '...' : ''),
      value: `saved-${idx}`,
      promptText: prompt,
    })),
  ];


  const promptText = useMemo(() => { // memoized prompt text based on selected key and custom input
  if (selectedPromptKey.startsWith('saved-')) { 
    const saved = allPromptOptions.find(opt => opt.value === selectedPromptKey); 
    return saved?.promptText || ''; 
  }
  return buildPrompt(selectedPromptKey, customPromptText); 
}, [selectedPromptKey, customPromptText, allPromptOptions]); 

  // clear edited prompt when user changes dropdown selection
  useEffect(() => { 
    setEditedPromptText(''); 
  }, [selectedPromptKey, customPromptText]); 

  useEffect(() => { // load saved prompts from local storage
      const prompts = JSON.parse(localStorage.getItem(LOCAL_STORAGE_KEY)) || [];
      setSavedPrompts(prompts);
  }, []);

  function saveCustomPrompt() { // save custom prompt to local storage
    if (customPromptText.trim()) {
        const prompts = [...savedPrompts, customPromptText.trim()];
        setSavedPrompts(prompts);
        localStorage.setItem(LOCAL_STORAGE_KEY, JSON.stringify(prompts));
    }
  }

  function deleteSavedPrompt(idx) { // delete saved prompt from local storage
    const prompts = savedPrompts.filter((_, i) => i !== idx);
    setSavedPrompts(prompts);
    localStorage.setItem(LOCAL_STORAGE_KEY, JSON.stringify(prompts));
  }


  // When a saved prompt is selected, set its text
  function handlePromptChange(_, { value }) { 
    setSelectedPromptKey(value);
    const saved = allPromptOptions.find(opt => opt.value === value && opt.promptText);
    if (saved) {
      setCustomPromptText(saved.promptText); // Show saved prompt in preview
    } else if (value === 'custom') { 
      setCustomPromptText('');
    } else {
      setCustomPromptText(''); // Reset for predefined prompts
    }
  }


  useEffect(() => { // load saved summary from local storage
      const savedSummary = localStorage.getItem(SUMMARY_STORAGE_KEY);
      if (savedSummary) {
        setSummaryHtml(savedSummary);
      }
  }, []);


  // saving summary to event note when the save button is clicked
  async function saveSummaryToEventNote() {
  if (!summaryHtml) {
    setError('Summary is empty. Cannot save.');
    return;
  }
  setSaving(true);
  
  const noteResp = await indicoAxios.get(`/event/${eventId}/api/note`);
  console.log('noteResp.data:', noteResp.data);

  const currentRevision = noteResp.data.id;
  const existingHtml = noteResp.data.html || '';
  const updatedHtml = existingHtml + '<hr><h2>Summary</h2>' + summaryHtml;
  
  setSaving(false);
 
  
  try {
    await indicoAxios.post(`/event/${eventId}/api/note`, 
    { source: updatedHtml, render_mode:'html',revision_id: currentRevision});
    } 
  catch (e) {
    setError(`Error during saving summary: ${handleAxiosError(e)}`);
  } finally {
    setSaving(false);
  }
}

  async function runSummarize() { // function to run the summarization process
    if (!eventId) { 
      setError('Missing eventId.');
      return;
    }
    setLoading(true); 
    setError(null); 
    setSummaryHtml(''); // clear previous summary 
    try {
      const finalPromptText = editedPromptText || promptText; 

      const resp = await indicoAxios.get(`/plugin/aisummary/summarize-event/${eventId}`, {
      params: {
        prompt: finalPromptText
      }
    });
      const data = resp.data;

        if (data.summary_html) { // if there is summary_html in the response
        setSummaryHtml(data.summary_html); // set the summary HTML
        localStorage.setItem(SUMMARY_STORAGE_KEY, data.summary_html); // add to local storage

      }
      else {
        setError('No summary returned.');
      }
    } catch (e) {
      setError(`Error during summarization: ${handleAxiosError(e)}`);
    } finally {
      setLoading(false);
    }
  };

  return ( 
     <>
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
                selection
                options={allPromptOptions}
                value={selectedPromptKey}
                onChange={handlePromptChange}
              />
              </Form.Field>
              <Button
                size="tiny"
                type="button"
                onClick={() => setManageModalOpen(true)}
                style={{ marginTop: '0.5em' }}
              >
              Manage Saved Prompts
             </Button>

               <Card raised fluid>
                  <CardContent>
                    <Form > {/* form to select prompt type and enter custom prompt text */}

                      {selectedPromptKey === 'custom' && ( // if custom prompt is selected, show the text area for custom input
                        <Form.Field id="custom-prompt-container"> {/* container for custom prompt input */}
                          <label>Custom prompt</label> 
                          <TextArea // text area for custom prompt input
                            id="custom-prompt" 
                            placeholder="Type your custom instructions…"
                            value={customPromptText} 
                            onChange={(_, { value }) => setCustomPromptText(value)}
                          />
                          <Button 
                          type="button" 
                          onClick={saveCustomPrompt}
                          style={{ marginTop: '0.5em' }}
                          >
                            Save Custom Prompt
                          </Button>
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
                        primary 
                        type="button" 
                        onClick={runSummarize}                       
                        disabled={loading} 
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
              
                <Card raised fluid styleName="preview-card-wrapper">
                  <CardContent >
                    <Segment basic style={{ position: 'relative', minHeight: '250px' }}> 
                        {loading && (
                          <Dimmer active inverted>
                            <Loader>Loading summary...</Loader>
                          </Dimmer>
                        )}
                        {error && ( 
                          <Message negative>
                            <Message.Header>Couldn\'t get a summary</Message.Header>
                            <p>{error}</p>
                          </Message>
                        )}
                        {summaryHtml && ( // if there is a summary HTML, display it                    
                          <div id="summary-output" 
                          styleName="preview-card"
                          dangerouslySetInnerHTML={{ __html: summaryHtml }}
                          />
                        )}

                        {summaryHtml && (
                          <div style = {{ display:'flex', gap: '0.5em', marginTop: '1em'}}>
                            <Button   // save the summary to event note button 
                              size="tiny"
                              primary
                              onClick={saveSummaryToEventNote}
                              style={{ marginTop: '1em' }}
                              disabled={saving} 
                            >
                              {saving ? 'Saving…' : 'Save summary'}
                            </Button>

                            <Button // clear summary button
                            size="tiny"
                            type="button"
                            onClick={() => { // clear the summary from local storage
                              setSummaryHtml('');
                              localStorage.removeItem(SUMMARY_STORAGE_KEY);
                            }}
                            style={{ marginTop: '1em' }}
                          >
                             Clear summary
                           </Button>
                          </div>
                      )}
                    </Segment>
                  </CardContent>
                </Card>
            </GridColumn>
          </GridRow>
        </Grid>

      </Modal.Content>
    </Modal>

    <Modal
      open={manageModalOpen}
      onClose={() => setManageModalOpen(false)}
      size="small"
    >
      <Modal.Header>Manage Saved Prompts</Modal.Header>
      <Modal.Content>
        {savedPrompts.length === 0 ? (
          <p>No saved prompts yet.</p>
        ) : (
          savedPrompts.map((prompt, idx) => (
            <Segment key={idx} style={{ display: 'flex', justifyContent: 'space-between' }}> 
              <span style={{ flex: 1, marginRight: '1em', overflowWrap: 'anywhere' }}>{prompt}</span>
              <Button size="mini" negative onClick={() => deleteSavedPrompt(idx)}>
                Delete
              </Button>
            </Segment>
          ))
        )}
      </Modal.Content>
      <Modal.Actions>
        <Button onClick={() => setManageModalOpen(false)}>Close</Button>
      </Modal.Actions>
    </Modal>


</>

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
